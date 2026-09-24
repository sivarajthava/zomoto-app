"""In-memory data loader and caching service for Zomato restaurants dataset."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.config import settings
from app.models import MetadataResponse, Restaurant


class DataLoader:
    """Singleton in-memory data store for high-performance restaurant lookups."""

    _instance: Optional[DataLoader] = None

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or settings.absolute_data_path
        self._df: Optional[pd.DataFrame] = None
        self._metadata: Optional[MetadataResponse] = None

    @classmethod
    def get_instance(cls, data_path: Optional[Path] = None) -> DataLoader:
        """Retrieve or initialize the singleton DataLoader instance."""
        if cls._instance is None:
            cls._instance = cls(data_path=data_path)
            cls._instance.load_data()
        return cls._instance

    def load_data(self, force_reload: bool = False) -> pd.DataFrame:
        """Load the preprocessed Parquet dataset into memory with caching."""
        if self._df is not None and not force_reload:
            return self._df

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Processed dataset not found at {self.data_path}. "
                "Please run 'python scripts/ingest_data.py' to generate it."
            )

        start = time.perf_counter()
        df = pd.read_parquet(self.data_path)

        # Ensure types and fast indexing columns
        df["city_lower"] = df["city"].astype(str).str.lower().str.strip()
        df["locality_lower"] = df["locality"].astype(str).str.lower().str.strip()
        df["name_lower"] = df["name"].astype(str).str.lower().str.strip()
        df["cuisines_set"] = [
            set(c.tolist() if isinstance(c, np.ndarray) else c)
            if isinstance(c, (list, np.ndarray)) else set()
            for c in df["cuisines_list"]
        ]

        # Precompute static base heuristic score: (Rating * 0.6) + (log10(Votes + 1) * 0.4)
        ratings = df["aggregate_rating"].fillna(2.5).to_numpy()
        votes = df["votes"].fillna(0).to_numpy()
        df["base_score"] = np.round((ratings * 0.6) + (np.log10(votes + 1.0) * 0.4), 3)

        # Convert budget_tier to Categorical for fast mask lookups
        df["budget_tier"] = df["budget_tier"].astype("category")

        # Cache metadata
        all_cuisines = set()
        for c_set in df["cuisines_set"]:
            all_cuisines.update(c.title() for c in c_set if c)

        self._metadata = MetadataResponse(
            total_restaurants=len(df),
            cities=sorted(df["city"].unique().tolist()),
            localities=sorted(df["locality"].unique().tolist()),
            cuisines=sorted(all_cuisines),
            budget_tiers=["low", "medium", "high"],
        )

        self._df = df
        elapsed = (time.perf_counter() - start) * 1000
        print(f"Loaded {len(df)} restaurants into memory in {elapsed:.2f}ms.")
        return self._df

    @property
    def df(self) -> pd.DataFrame:
        """Return the loaded in-memory DataFrame."""
        if self._df is None:
            return self.load_data()
        return self._df

    @property
    def metadata(self) -> MetadataResponse:
        """Return pre-computed metadata for frontend filters."""
        if self._metadata is None:
            self.load_data()
        assert self._metadata is not None
        return self._metadata

    @staticmethod
    def row_to_restaurant(row: pd.Series | Dict) -> Restaurant:
        """Convert a DataFrame row or dictionary into a validated Restaurant entity."""
        if isinstance(row, pd.Series):
            data = row.to_dict()
        else:
            data = dict(row)

        cuisines_list = data.get("cuisines_list")
        if isinstance(cuisines_list, np.ndarray):
            cuisines_list = cuisines_list.tolist()
        elif not isinstance(cuisines_list, list):
            cuisines_list = []

        rating = data.get("aggregate_rating")
        if pd.isna(rating):
            rating = None
        else:
            rating = float(rating)

        return Restaurant(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            city=str(data.get("city", "")),
            locality=str(data.get("locality", "")),
            address=str(data.get("address", "")),
            cuisines_list=cuisines_list,
            cuisines_str=str(data.get("cuisines_str", "")),
            average_cost_for_two=float(data.get("average_cost_for_two", 0.0)),
            budget_tier=str(data.get("budget_tier", "low")),
            aggregate_rating=rating,
            votes=int(data.get("votes", 0)),
            rest_type=str(data.get("rest_type", "")),
            dish_liked=str(data.get("dish_liked", "")),
            online_order=str(data.get("online_order", "No")),
            book_table=str(data.get("book_table", "No")),
            url=str(data.get("url", "")),
        )


def get_data_loader() -> DataLoader:
    """Dependency helper to obtain the singleton DataLoader."""
    return DataLoader.get_instance()
