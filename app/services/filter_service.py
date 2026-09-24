"""Stage 1: Deterministic retrieval and heuristic candidate filtering service."""

from __future__ import annotations

import time
from typing import List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from app.config import settings
from app.models import Restaurant, UserPreferenceRequest
from app.services.data_loader import DataLoader, get_data_loader


class FilterService:
    """High-speed in-memory filtering engine for pre-selecting restaurant candidates."""

    def __init__(self, data_loader: Optional[DataLoader] = None):
        self.data_loader = data_loader or get_data_loader()

    def filter_candidates(
        self, request: UserPreferenceRequest
    ) -> Tuple[List[Restaurant], bool]:
        """Filter and rank candidate restaurants matching user criteria.

        Returns:
            Tuple of (List[Restaurant], is_relaxed: bool)
            where is_relaxed is True if dynamic relaxation was applied.
        """
        start_time = time.perf_counter()
        df = self.data_loader.df

        # 1. Normalize Location Target
        loc_query = request.location.strip().lower()
        if loc_query in {"bangalore", "bengaluru", "bengaluru city", "bangalore city"}:
            # Broad metro search across entire dataset (None skips location filtering overhead)
            base_mask = None
        else:
            # Match specific locality or address substring
            loc_series = (
                df["locality_lower"].str.contains(loc_query, regex=False, na=False)
                | df["city_lower"].str.contains(loc_query, regex=False, na=False)
            )
            base_mask = loc_series if loc_series.any() else None

        # 2. Extract Desired Cuisines
        user_cuisines: Set[str] = {c.strip().lower() for c in request.cuisines if c.strip()}

        # 3. Progressive Filtering & Dynamic Relaxation Pipeline
        target_budget = request.budget_tier.lower()
        min_rating = request.min_rating
        is_relaxed = False

        # Attempt 0: Strict filters
        candidates_df = self._apply_filters(
            df=df,
            location_mask=base_mask,
            budget_tiers={target_budget},
            min_rating=min_rating,
            user_cuisines=user_cuisines,
        )

        # Relaxation Step 1: Broaden Budget Tier
        if len(candidates_df) < settings.min_candidates_threshold:
            is_relaxed = True
            expanded_budgets = self._get_adjacent_budgets(target_budget)
            candidates_df = self._apply_filters(
                df=df,
                location_mask=base_mask,
                budget_tiers=expanded_budgets,
                min_rating=min_rating,
                user_cuisines=user_cuisines,
            )

        # Relaxation Step 2: Lower Rating Floor by 0.5 (floor at 3.0)
        if len(candidates_df) < settings.min_candidates_threshold:
            is_relaxed = True
            relaxed_rating = max(3.0, min_rating - 0.5)
            candidates_df = self._apply_filters(
                df=df,
                location_mask=base_mask,
                budget_tiers=self._get_adjacent_budgets(target_budget),
                min_rating=relaxed_rating,
                user_cuisines=user_cuisines,
            )

        # Relaxation Step 3: Drop Strict Cuisine Overlap
        if len(candidates_df) < settings.min_candidates_threshold and user_cuisines:
            is_relaxed = True
            candidates_df = self._apply_filters(
                df=df,
                location_mask=base_mask,
                budget_tiers=self._get_adjacent_budgets(target_budget),
                min_rating=max(3.0, min_rating - 0.5),
                user_cuisines=set(),  # remove cuisine constraint
            )

        # Relaxation Step 4: City-wide Top Rated Fallback
        if len(candidates_df) == 0:
            is_relaxed = True
            candidates_df = df[df["aggregate_rating"].notna()].copy()

        # 4. Vectorized Heuristic Scoring
        scored_df = self._calculate_scores(candidates_df, user_cuisines)

        # 5. Deterministic Sort and Truncation
        # Sort: Score DESC, votes DESC, name ASC (ensures reproducible ranking)
        sorted_df = scored_df.sort_values(
            by=["candidate_score", "votes", "name"],
            ascending=[False, False, True],
        ).head(settings.max_candidates_stage_1)

        # Convert to domain entities via fast dict conversion
        results = [
            self.data_loader.row_to_restaurant(row)
            for row in sorted_df.to_dict(orient="records")
        ]

        elapsed = (time.perf_counter() - start_time) * 1000
        print(
            f"Stage 1 Filter: retrieved {len(results)} candidates in {elapsed:.2f}ms "
            f"(relaxed={is_relaxed})."
        )
        return results, is_relaxed

    @staticmethod
    def _get_adjacent_budgets(tier: str) -> Set[str]:
        """Expand requested budget tier to neighboring tiers."""
        if tier == "low":
            return {"low", "medium"}
        elif tier == "high":
            return {"medium", "high"}
        else:  # medium
            return {"low", "medium", "high"}

    @staticmethod
    def _apply_filters(
        df: pd.DataFrame,
        location_mask: Optional[pd.Series],
        budget_tiers: Set[str],
        min_rating: float,
        user_cuisines: Set[str],
    ) -> pd.DataFrame:
        """Apply combined Boolean masks to DataFrame with subset-first cuisine filtering."""
        mask = df["budget_tier"].isin(budget_tiers) & (df["aggregate_rating"] >= min_rating)
        if location_mask is not None:
            mask = mask & location_mask
        filtered = df[mask]

        if not user_cuisines or filtered.empty:
            return filtered.copy()

        # Perform fast list comprehension only on already-filtered candidate subset
        c_matches = [bool(user_cuisines.intersection(cset)) for cset in filtered["cuisines_set"]]
        return filtered[c_matches].copy()

    @staticmethod
    def _calculate_scores(df: pd.DataFrame, user_cuisines: Set[str]) -> pd.DataFrame:
        """Calculate heuristic ranking scores using precomputed base_score.

        Formula:
            Score = BaseScore + CuisineBonus
        """
        if df.empty:
            df = df.copy()
            df["candidate_score"] = 0.0
            return df

        df = df.copy()
        base_scores = df["base_score"].to_numpy()

        # Fast cuisine bonus
        if user_cuisines:
            bonuses = np.array([
                0.5 if bool(user_cuisines.intersection(cset)) else 0.0
                for cset in df["cuisines_set"]
            ])
            df["candidate_score"] = np.round(base_scores + bonuses, 3)
        else:
            df["candidate_score"] = base_scores

        return df
