"""Guardrails for the A7 pipeline.

Run with:  python -m pytest tests -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_loader import TARGET, build_features, load_jobs  # noqa: E402
from evaluate import refills_needed  # noqa: E402
from model import GroupMean, IntervalRegressor  # noqa: E402
from optimise import select_booked_order, select_exact, select_value_density  # noqa: E402
from sustainability import BENCHMARKS, LITRES_PER_US_GALLON  # noqa: E402


@pytest.fixture(scope="module")
def jobs():
    return load_jobs()


def test_planning_features_never_see_dirtiness(jobs):
    """The whole two-stage design rests on this: dirtiness is not known at booking."""
    planning = build_features(jobs.head(100), "planning")
    assert not any("dirt" in column.lower() for column in planning.columns)


def test_onsite_features_add_dirtiness_and_its_interaction(jobs):
    onsite = build_features(jobs.head(100), "onsite")
    assert "dirtiness" in onsite.columns
    assert any(column.endswith("_x_dirtiness") for column in onsite.columns)


def test_no_post_job_column_reaches_any_feature_set(jobs):
    """duration, lateness, rating and revenue are outcomes, not inputs."""
    outcomes = ["duration", "late", "rating", "revenue", "distance", "arrival"]
    for stage in ("size_only", "planning", "onsite"):
        columns = " ".join(build_features(jobs.head(100), stage).columns).lower()
        assert not any(outcome in columns for outcome in outcomes)


def test_interior_clean_is_parsed_from_items_not_slot_type(jobs):
    """slot_type carries no water signal; the add-on inside items is the driver."""
    assert jobs["addon_interior_clean"].isin([0, 1]).all()
    by_addon = jobs.groupby("addon_interior_clean")[TARGET].mean()
    assert by_addon[1] - by_addon[0] > 15

    by_slot = jobs.groupby("slot_type")[TARGET].mean()
    assert by_slot.max() - by_slot.min() < 2


def test_refills_counts_a_topup_before_the_job_that_overflows():
    assert refills_needed([50, 50, 50, 50], 200) == 0
    assert refills_needed([50, 50, 50, 50], 150) == 1
    assert refills_needed([80, 80, 80], 100) == 2


def test_interval_brackets_the_prediction_and_covers_its_level():
    rng = np.random.default_rng(7)
    X = pd.DataFrame({"size_suv": rng.integers(0, 2, 4000).astype(float)})
    y = pd.Series(40 + 15 * X["size_suv"] + rng.normal(0, 3, 4000))

    model = IntervalRegressor(GroupMean(), level=0.90)
    model.fit(X.iloc[:2000], y.iloc[:2000])
    model.calibrate(X.iloc[2000:3000], y.iloc[2000:3000])

    holdout = X.iloc[3000:]
    low, high = model.predict_interval(holdout)
    assert (low < high).all()

    covered = ((y.iloc[3000:] >= low) & (y.iloc[3000:] <= high)).mean()
    assert 0.85 < covered < 0.95


def test_benchmarks_carry_a_source_and_convert_from_gallons():
    for benchmark in BENCHMARKS:
        assert benchmark["source"]
        assert benchmark["gallons_per_wash"] > 0
    assert LITRES_PER_US_GALLON == pytest.approx(3.785411784)


def test_exact_knapsack_beats_greedy_on_the_classic_trap():
    """Density-greedy takes the 6 first and misses the optimal 5+5."""
    weights = np.array([6.0, 5.0, 5.0])
    values = np.array([7.0, 5.0, 5.0])
    assert select_exact(weights, values, 10.0).tolist() == [False, True, True]
    assert select_value_density(weights, values, 10.0).tolist() == [True, False, False]


def test_selections_never_exceed_capacity():
    rng = np.random.default_rng(7)
    for _ in range(50):
        weights = rng.uniform(20, 100, 8)
        values = rng.uniform(300, 2000, 8)
        for select in (select_booked_order, select_value_density, select_exact):
            chosen = select(weights, values, 200.0)
            assert weights[chosen].sum() <= 200.0 + 1e-6


def test_booked_order_stops_at_the_first_job_it_cannot_cover():
    weights = np.array([80.0, 80.0, 80.0, 10.0])
    values = np.ones(4)
    assert select_booked_order(weights, values, 200.0).tolist() == [True, True, False, False]
