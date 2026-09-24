"""Unit tests for Phase 2 data ingestion and preprocessing pipeline."""

import time
from pathlib import Path

import pandas as pd
import pytest

from scripts.ingest_data import (
    assign_budget_tier,
    clean_cost,
    clean_rating,
    parse_cuisines,
    OUTPUT_PARQUET,
)


class TestDataCleaningFunctions:
    """Test individual data cleaning and normalization helper functions."""

    @pytest.mark.parametrize(
        "raw_rate,expected",
        [
            ("4.1/5", 4.1),
            ("3.9 /5", 3.9),
            ("4.5", 4.5),
            ("5.0/5", 5.0),
            ("1.0/5", 1.0),
            ("NEW", None),
            ("-", None),
            ("Opening Soon", None),
            ("nan", None),
            (None, None),
            ("0.5/5", None),  # below valid 1.0 floor
            ("6.0/5", None),  # above valid 5.0 ceiling
        ],
    )
    def test_clean_rating(self, raw_rate, expected):
        assert clean_rating(raw_rate) == expected

    @pytest.mark.parametrize(
        "raw_cost,expected",
        [
            ("800", 800.0),
            ("1,200", 1200.0),
            ("₹ 1,500", 1500.0),
            ("450.0", 450.0),
            ("", None),
            ("nan", None),
            (None, None),
            ("0", None),  # out of bound anomaly
            ("50000", None),  # extreme anomaly
        ],
    )
    def test_clean_cost(self, raw_cost, expected):
        assert clean_cost(raw_cost) == expected

    @pytest.mark.parametrize(
        "cost,expected_tier",
        [
            (250.0, "low"),
            (500.0, "low"),
            (501.0, "medium"),
            (1200.0, "medium"),
            (1500.0, "medium"),
            (1501.0, "high"),
            (2800.0, "high"),
            (None, "low"),
        ],
    )
    def test_assign_budget_tier(self, cost, expected_tier):
        assert assign_budget_tier(cost) == expected_tier

    def test_parse_cuisines(self):
        raw = "North Indian, Mughlai , Chinese, "
        cuisines = parse_cuisines(raw)
        assert cuisines == ["north indian", "mughlai", "chinese"]

        assert parse_cuisines(None) == []
        assert parse_cuisines("") == []


class TestProcessedParquetDataset:
    """Verify quality gates for the processed Parquet dataset artifact."""

    @pytest.fixture(scope="module")
    def dataset(self):
        assert OUTPUT_PARQUET.exists(), f"Processed dataset not found at {OUTPUT_PARQUET}"
        start = time.perf_counter()
        df = pd.read_parquet(OUTPUT_PARQUET)
        load_time = time.perf_counter() - start
        return df, load_time

    def test_dataset_row_count_and_speed(self, dataset):
        df, load_time = dataset
        # Quality Gate: >= 8,000 records
        assert len(df) >= 8000, f"Expected >= 8000 rows, got {len(df)}"
        # Quality Gate: load time < 100ms
        assert load_time < 0.20, f"Parquet load time too slow: {load_time:.4f}s"

    def test_required_columns_exist(self, dataset):
        df, _ = dataset
        required_cols = [
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
        ]
        for col in required_cols:
            assert col in df.columns, f"Missing required column: {col}"

    def test_zero_nulls_in_critical_columns(self, dataset):
        df, _ = dataset
        critical_cols = ["id", "name", "city", "locality", "average_cost_for_two", "budget_tier"]
        for col in critical_cols:
            null_count = df[col].isna().sum()
            assert null_count == 0, f"Column '{col}' has {null_count} nulls; expected 0"

    def test_budget_tier_values(self, dataset):
        df, _ = dataset
        valid_tiers = {"low", "medium", "high"}
        actual_tiers = set(df["budget_tier"].unique())
        assert actual_tiers.issubset(valid_tiers), f"Unexpected tiers: {actual_tiers}"

    def test_rating_ranges(self, dataset):
        df, _ = dataset
        rated = df["aggregate_rating"].dropna()
        assert len(rated) > 0, "No rated restaurants found"
        assert (rated >= 1.0).all(), "Found ratings < 1.0"
        assert (rated <= 5.0).all(), "Found ratings > 5.0"
