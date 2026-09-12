"""Train the A7 water-consumption models and write the module deliverables.

Run from the repository root:  python src/train.py
"""

from datetime import datetime, timezone
from itertools import product

import pandas as pd
from sklearn.model_selection import train_test_split

from data_loader import (
    DIRTINESS_LEVELS,
    RESULTS,
    ROOT,
    SEED,
    TARGET,
    VEHICLE_SIZES,
    build_features,
    load_jobs,
    load_vehicles,
)
from evaluate import (
    crew_day_loads,
    interval_coverage,
    jobs_per_tank,
    metrics_by_job_type,
    refill_plan,
    regression_metrics,
)
from model import MODEL_ORDER, IntervalRegressor, build_model
from optimise import evaluate_plans
from sustainability import sustainability_comparison

TEST_SIZE = 0.2
CALIBRATION_SIZE = 0.25  # of the training split, giving a 60/20/20 fit/calibrate/test
INTERVAL_LEVEL = 0.90
SELECTION_TOLERANCE = 0.01  # relative MAE

RUNS = [
    ("size_only", "global_mean"),
    ("size_only", "size_mean"),
    ("planning", "size_mean"),
    ("planning", "linear"),
    ("planning", "gbm"),
    ("onsite", "size_mean"),
    ("onsite", "linear"),
    ("onsite", "gbm"),
]

EXPERIMENTS = ROOT / "experiments.csv"
CONSUMPTION_MODEL = RESULTS / "consumption_model.csv"
TANK_CAPACITY = RESULTS / "tank_capacity.csv"
REFILL_PLANNING = RESULTS / "refill_planning.csv"
SUSTAINABILITY = RESULTS / "sustainability.csv"
TANK_PLAN = RESULTS / "tank_plan.csv"


def run_experiments(df, idx_train, idx_test):
    y = df[TARGET]
    interior_test = df.loc[idx_test, "addon_interior_clean"]

    results = []
    for stage, model_name in RUNS:
        X = build_features(df, stage)
        model = build_model(model_name).fit(X.loc[idx_train], y.loc[idx_train])
        prediction = model.predict(X.loc[idx_test])

        results.append(
            {
                "stage": stage,
                "model": model_name,
                "n_train": len(idx_train),
                "n_test": len(idx_test),
                "n_features": X.shape[1],
                **regression_metrics(y.loc[idx_test], prediction),
                **metrics_by_job_type(y.loc[idx_test], prediction, interior_test),
            }
        )
    return pd.DataFrame(results)


def log_experiments(experiments):
    logged = experiments.copy()
    logged.insert(0, "run_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    header = not EXPERIMENTS.exists() or EXPERIMENTS.stat().st_size == 0
    logged.round(4).to_csv(EXPERIMENTS, mode="a", header=header, index=False, encoding="utf-8")


def scenario_frame(stage):
    """Every feature combination the deliverable has to quote a figure for."""
    levels = DIRTINESS_LEVELS if stage == "onsite" else [None]
    rows = product(VEHICLE_SIZES, levels, [0, 1])
    return pd.DataFrame(
        [
            {"vehicle_size": size, "dirtiness_level": dirt, "addon_interior_clean": interior}
            for size, dirt, interior in rows
        ]
    )


def select_model(candidates):
    """Prefer the simplest family within a tolerance of the best MAE.

    The families land within ~0.001 L of each other, so selecting on raw argmin would
    hand the deliverable a gradient-boosting model for no measurable gain.
    """
    within_tolerance = candidates[
        candidates["mae"] <= candidates["mae"].min() * (1 + SELECTION_TOLERANCE)
    ]
    return min(within_tolerance["model"], key=MODEL_ORDER.index)


def fit_deliverable_model(df, stage, model_name, idx_fit, idx_calibrate, idx_test):
    """Fit, calibrate and score the interval on three disjoint splits.

    Calibrating and measuring coverage on the same rows would report the nominal
    level back by construction.
    """
    X = build_features(df, stage)
    y = df[TARGET]
    model = IntervalRegressor(build_model(model_name), level=INTERVAL_LEVEL)
    model.fit(X.loc[idx_fit], y.loc[idx_fit])
    model.calibrate(X.loc[idx_calibrate], y.loc[idx_calibrate])

    coverage = interval_coverage(y.loc[idx_test], *model.predict_interval(X.loc[idx_test]))
    return model, coverage


def scenario_predictions(df, stage, model, model_name):
    scenarios = scenario_frame(stage)
    X = build_features(scenarios, stage)
    prediction = model.predict(X)
    lo, hi = model.predict_interval(X)

    group_columns = ["vehicle_size", "addon_interior_clean"]
    if stage == "onsite":
        group_columns.insert(1, "dirtiness_level")
    observed = df.groupby(group_columns)[TARGET].agg(["size", "mean", "std"])

    out = scenarios.copy()
    out["stage"] = stage
    out["model"] = model_name
    out["predicted_litres"] = prediction
    out["pi_low_litres"] = lo
    out["pi_high_litres"] = hi
    out["interval_level"] = INTERVAL_LEVEL

    support = observed.reindex(pd.MultiIndex.from_frame(scenarios[group_columns]))
    out["n_observed"] = support["size"].to_numpy()
    out["observed_mean_litres"] = support["mean"].to_numpy()
    out["observed_sd_litres"] = support["std"].to_numpy()

    return out.rename(columns={"addon_interior_clean": "interior_clean"})


def main():
    df = load_jobs()
    vehicles = load_vehicles()
    idx_train, idx_test = train_test_split(df.index, test_size=TEST_SIZE, random_state=SEED)
    idx_fit, idx_calibrate = train_test_split(
        idx_train, test_size=CALIBRATION_SIZE, random_state=SEED
    )

    experiments = run_experiments(df, idx_train, idx_test)
    log_experiments(experiments)
    print("Model comparison (held-out test split)")
    print(experiments.round(3).to_string(index=False))

    deliverable = []
    models = {}
    for stage in ("planning", "onsite"):
        candidates = experiments[experiments.stage == stage]
        best = select_model(candidates)
        model, coverage = fit_deliverable_model(
            df, stage, best, idx_fit, idx_calibrate, idx_test
        )
        print(
            f"\n{stage}: selected {best} | "
            f"{int(INTERVAL_LEVEL * 100)}% interval coverage {coverage:.3f} on held-out test"
        )
        models[stage] = model
        deliverable.append(scenario_predictions(df, stage, model, best))

    consumption_model = pd.concat(deliverable, ignore_index=True)[
        [
            "stage",
            "model",
            "vehicle_size",
            "dirtiness_level",
            "interior_clean",
            "predicted_litres",
            "pi_low_litres",
            "pi_high_litres",
            "interval_level",
            "n_observed",
            "observed_mean_litres",
            "observed_sd_litres",
        ]
    ]
    consumption_model.round(3).to_csv(CONSUMPTION_MODEL, index=False, encoding="utf-8")

    tanks = jobs_per_tank(df[TARGET], vehicles)
    tanks.to_csv(TANK_CAPACITY, index=False, encoding="utf-8")
    print("\nMaximum jobs per tank")
    print(tanks.to_string(index=False))

    refills = refill_plan(df, vehicles)
    refills.to_csv(REFILL_PLANNING, index=False, encoding="utf-8")
    print("\nRefills per crew-day")
    print(refills.to_string(index=False))

    loads = crew_day_loads(df)
    print(
        f"\ncrew-day load: mean {loads.jobs.mean():.1f} jobs, {loads.litres.mean():.0f} L "
        f"| p95 {loads.litres.quantile(0.95):.0f} L | max {loads.litres.max():.0f} L"
    )

    planning_X = build_features(df, "planning")
    df["predicted_litres"] = models["planning"].predict(planning_X)
    df["predicted_safe_litres"] = models["planning"].predict_interval(planning_X)[1]
    plans = evaluate_plans(
        df,
        vehicles,
        {
            "oracle_actual": TARGET,
            "planning_point": "predicted_litres",
            "planning_safe": "predicted_safe_litres",
        },
    )
    plans.to_csv(TANK_PLAN, index=False, encoding="utf-8")
    print("\nBest set of jobs per tank (share of all jobs / revenue, and overflow rate)")
    print(plans.to_string(index=False))

    sustainability = sustainability_comparison(df)
    sustainability.to_csv(SUSTAINABILITY, index=False, encoding="utf-8")
    print("\nWater use against published benchmarks (L per wash)")
    print(
        sustainability[
            [
                "benchmark",
                "reclaim",
                "benchmark_litres_per_wash",
                "doorstep_pct_of_benchmark",
                "source",
            ]
        ].to_string(index=False)
    )

    print(f"\nwrote {CONSUMPTION_MODEL.relative_to(ROOT)} ({len(consumption_model)} rows)")
    print(f"wrote {TANK_CAPACITY.relative_to(ROOT)} ({len(tanks)} rows)")
    print(f"wrote {REFILL_PLANNING.relative_to(ROOT)} ({len(refills)} rows)")
    print(f"wrote {SUSTAINABILITY.relative_to(ROOT)} ({len(sustainability)} rows)")
    print(f"wrote {TANK_PLAN.relative_to(ROOT)} ({len(plans)} rows)")
    print(f"logged {len(experiments)} runs to {EXPERIMENTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
