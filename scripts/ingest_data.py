"""Data ingestion and preprocessing pipeline for Zomato restaurant dataset.

Downloads or loads the dataset from Hugging Face (ManikaSaini/zomato-restaurant-recommendation),
cleans, normalizes, handles missing values, engineers features (budget tiers, cuisines),
and serializes to data/processed/zomato_clean.parquet.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from datasets import load_dataset


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_PARQUET = PROCESSED_DIR / "zomato_clean.parquet"


def clean_rating(val: Optional[str]) -> Optional[float]:
    """Parse raw rating string into a clean float (1.0 - 5.0) or None."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if s in ("", "-", "NEW", "Opening Soon", "nan", "None"):
        return None
    # Common format: '4.1/5' or '4.1 /5'
    if "/" in s:
        s = s.split("/")[0].strip()
    try:
        r = float(s)
        if 1.0 <= r <= 5.0:
            return round(r, 2)
        return None
    except ValueError:
        return None


def clean_cost(val: Optional[str]) -> Optional[float]:
    """Parse raw cost string into a clean numeric float or None."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    # Strip commas, currency symbols, and extra spaces
    cleaned = re.sub(r"[^\d.]", "", s)
    if not cleaned:
        return None
    try:
        cost = float(cleaned)
        # Filter extreme anomalies
        if 20.0 <= cost <= 30000.0:
            return cost
        return None
    except ValueError:
        return None


def assign_budget_tier(cost: Optional[float]) -> str:
    """Classify average cost for two into 'low', 'medium', or 'high' budget tier."""
    if cost is None or pd.isna(cost) or cost <= 500:
        return "low"
    elif cost <= 1500:
        return "medium"
    else:
        return "high"


def parse_cuisines(val: Optional[str]) -> List[str]:
    """Parse comma-separated cuisine string into a normalized lowercase list."""
    if val is None or pd.isna(val):
        return []
    items = [c.strip().lower() for c in str(val).split(",") if c.strip()]
    return items


def ingest_and_preprocess(
    source_name: str = "ManikaSaini/zomato-restaurant-recommendation",
    output_path: Path = OUTPUT_PARQUET,
) -> pd.DataFrame:
    """Download, preprocess and persist the Zomato restaurant dataset."""
    print("=" * 60)
    print("Starting Zomato Data Ingestion Pipeline")
    print("=" * 60)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load dataset
    raw_cache = RAW_DIR / "zomato_raw.parquet"
    if raw_cache.exists():
        print(f"Loading raw dataset from local cache: {raw_cache}...")
        df_raw = pd.read_parquet(raw_cache)
        print(f"Loaded {len(df_raw)} raw rows from local cache.")
    else:
        print(f"Fetching dataset from Hugging Face Hub: {source_name}...")
        try:
            ds = load_dataset(source_name, split="train")
            df_raw = ds.to_pandas()
            print(f"Successfully loaded {len(df_raw)} raw rows from Hugging Face.")
            df_raw.to_parquet(raw_cache, index=False)
            print(f"Cached raw dataset snapshot to {raw_cache}")
        except Exception as exc:
            raise RuntimeError(f"Could not load dataset from Hugging Face: {exc}")

    # 2. Data Cleaning & Normalization
    print("Cleaning and normalizing restaurant records...")
    df = df_raw.copy()

    # Drop records without restaurant name
    df = df.dropna(subset=["name"])
    df["name"] = df["name"].astype(str).str.strip()
    df = df[df["name"].str.len() > 0]

    # Normalize address and location
    df["address"] = df["address"].fillna("").astype(str).str.strip()
    df["location"] = df["location"].fillna("Bangalore").astype(str).str.strip()
    df["locality"] = df["location"]  # Specific locality/neighborhood (e.g., Koramangala)
    df["city"] = "Bangalore"          # Canonical metro city for this dataset

    # Deduplicate entries by name and address
    initial_len = len(df)
    df = df.drop_duplicates(subset=["name", "address"]).copy()
    print(f"Deduplicated by (name, address): {initial_len} -> {len(df)} records.")

    # Clean numerical columns
    df["aggregate_rating"] = df["rate"].apply(clean_rating)
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)

    # Clean cost for two
    cost_series = df["approx_cost(for two people)"].apply(clean_cost)
    median_cost = cost_series.median()
    if pd.isna(median_cost) or median_cost <= 0:
        median_cost = 600.0
    print(f"Calculated overall median cost for two: INR {median_cost:.0f}")

    # Impute missing cost by locality median if available, otherwise city median
    locality_medians = cost_series.groupby(df["locality"]).transform("median")
    df["average_cost_for_two"] = (
        cost_series.fillna(locality_medians).fillna(median_cost).round(0).astype(float)
    )

    # Feature Engineering: Budget Tier
    df["budget_tier"] = df["average_cost_for_two"].apply(assign_budget_tier)

    # Feature Engineering: Cuisines
    df["cuisines_list"] = df["cuisines"].apply(parse_cuisines)
    df["cuisines_str"] = df["cuisines"].fillna("Multi-Cuisine").astype(str).str.strip()

    # Restaurant Type & Dishes Liked
    df["rest_type"] = df["rest_type"].fillna("Casual Dining").astype(str).str.strip()
    df["dish_liked"] = df["dish_liked"].fillna("").astype(str).str.strip()

    # Online order & Table booking booleans
    df["online_order"] = df["online_order"].fillna("No").astype(str).str.strip()
    df["book_table"] = df["book_table"].fillna("No").astype(str).str.strip()

    # Generate deterministic or clean ID
    df["id"] = [
        str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{name}|{addr}"))
        for name, addr in zip(df["name"], df["address"])
    ]

    # Select and organize clean columns
    clean_columns = [
        "id",
        "name",
        "city",
        "locality",
        "address",
        "cuisines_list",
        "cuisines_str",
        "average_cost_for_two",
        "budget_tier",
        "aggregate_rating",
        "votes",
        "rest_type",
        "dish_liked",
        "online_order",
        "book_table",
        "url",
    ]
    df_clean = df[clean_columns].reset_index(drop=True)

    # 3. Serialization to Parquet
    print(f"Saving preprocessed dataset to {output_path}...")
    df_clean.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)

    print("=" * 60)
    print("Preprocessed Dataset Summary:")
    print(f"Total Clean Records: {len(df_clean)}")
    print(f"Unique Localities: {df_clean['locality'].nunique()}")
    print(f"Rated Restaurants: {df_clean['aggregate_rating'].notna().sum()}")
    print("Budget Tier Distribution:")
    print(df_clean["budget_tier"].value_counts().to_string())
    print("=" * 60)
    print(f"Dataset successfully created at: {output_path}")

    return df_clean


if __name__ == "__main__":
    ingest_and_preprocess()
