"""Train the A7 water-consumption models and write the module deliverables.

Run from the repository root:  python src/train.py
"""

import subprocess
from datetime import datetime, timezone
from itertools import product

import numpy as np
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

# Rule 4: one run is an anecdote. Every split-dependent number is reported as an
# average and a spread over these seeds. SEED (7) matches the dataset generator and is
# the one used for the published per-scenario figures and for resampling.
SEEDS = list(range(10))

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
MODEL_COMPARISON = RESULTS / "model_comparison.csv"
CONSUMPTION_MODEL = RESULTS / "consumption_model.csv"
TANK_CAPACITY = RESULTS / "tank_capacity.csv"
REFILL_PLANNING = RESULTS / "refill_planning.csv"
SUSTAINABILITY = RESULTS / "sustainability.csv"
TANK_PLAN = RESULTS / "tank_plan.csv"


def split(df, seed):
    """60/20/20 fit / calibrate / test."""
    idx_train, idx_test = train_test_split(df.index, test_size=TEST_SIZE, random_state=seed)
    idx_fit, idx_calibrate = train_test_split(
        idx_train, test_size=CALIBRATION_SIZE, random_state=seed
    )
    return idx_train, idx_fit, idx_calibrate, idx_test


def run_experiments(df, seed):
    idx_train, _, _, idx_test = split(df, seed)
    y = df[TARGET]
    interior_test = df.loc[idx_test, "addon_interior_clean"]

    results = []
    for stage, model_name in RUNS:
        X = build_features(df, stage)
        model = build_model(model_name).fit(X.loc[idx_train], y.loc[idx_train])
        prediction = model.predict(X.loc[idx_test])

        results.append(
            {
                "seed": seed,
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


def sweep_seeds(df):
    return pd.concat([run_experiments(df, seed) for seed in SEEDS], ignore_index=True)


def summarise_sweep(sweep):
    """Average and spread per stage and model, which is what Rule 5 asks us to report."""
    summary = sweep.groupby(["stage", "model"], sort=False)[
        ["mae", "rmse", "r2"]
    ].agg(["mean", "std", "min", "max"])
    summary.columns = [f"{metric}_{stat}" for metric, stat in summary.columns]
    summary.insert(0, "n_seeds", sweep.groupby(["stage", "model"], sort=False).size())
    return summary.reset_index()


def log_experiments(sweep):
    """Append one row per run in the schema Rule 6 fixes, extra columns at the end."""
    existing = 0
    if EXPERIMENTS.exists() and EXPERIMENTS.stat().st_size > 0:
        existing = len(pd.read_csv(EXPERIMENTS))

    who = subprocess.run(
        ["git", "config", "user.name"], capture_output=True, text=True
    ).stdout.strip() or "unknown"

    logged = pd.DataFrame(
        {
            "run_id": [f"R{existing + i + 1:03d}" for i in range(len(sweep))],
            "date": datetime.now(timezone.utc).date().isoformat(),
            "who": who,
            "what_changed": sweep.stage + " / " + sweep.model,
            "main_metric": "MAE",
            "value": sweep.mae.round(4),
            "seed": sweep.seed,
            "notes": sweep.apply(
                lambda r: f"RMSE {r.rmse:.3f}, R2 {r.r2:.4f}, "
                f"MAE exterior {r.mae_exterior:.3f} / interior {r.mae_interior:.3f}",
                axis=1,
            ),
            "stage": sweep.stage,
            "model": sweep.model,
            "n_features": sweep.n_features,
            "n_train": sweep.n_train,
            "n_test": sweep.n_test,
        }
    )
    header = existing == 0
    logged.to_csv(EXPERIMENTS, mode="a", header=header, index=False, encoding="utf-8")


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

    The families land within ~0.001 L of each other averaged over seeds, well inside the
    seed-to-seed spread, so selecting on raw argmin would hand the deliverable a
    gradient-boosting model for no measurable gain.
    """
    within_tolerance = candidates[
        candidates["mae_mean"] <= candidates["mae_mean"].min() * (1 + SELECTION_TOLERANCE)
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

    sweep = sweep_seeds(df)
    log_experiments(sweep)
    summary = summarise_sweep(sweep)
    summary.round(4).to_csv(MODEL_COMPARISON, index=False, encoding="utf-8")
    print(f"Model comparison over {len(SEEDS)} seeds (mean +/- sd on held-out test)")
    for _, row in summary.iterrows():
        print(
            f"  {row.stage:<10} {row.model:<12} MAE {row.mae_mean:6.3f} +/- {row.mae_std:.3f}"
            f"   RMSE {row.rmse_mean:6.3f} +/- {row.rmse_std:.3f}"
            f"   R2 {row.r2_mean:+.4f} +/- {row.r2_std:.4f}"
        )

    _, idx_fit, idx_calibrate, idx_test = split(df, SEED)
    deliverable = []
    models = {}
    for stage in ("planning", "onsite"):
        best = select_model(summary[summary.stage == stage])
        coverages = np.array(
            [
                fit_deliverable_model(df, stage, best, *split(df, seed)[1:])[1]
                for seed in SEEDS
            ]
        )
        model, _ = fit_deliverable_model(df, stage, best, idx_fit, idx_calibrate, idx_test)
        print(
            f"\n{stage}: selected {best} | "
            f"{int(INTERVAL_LEVEL * 100)}% interval coverage "
            f"{coverages.mean():.4f} +/- {coverages.std():.4f} over {len(SEEDS)} seeds"
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

    across_seeds = [jobs_per_tank(df[TARGET], vehicles, seed=seed) for seed in SEEDS]
    for level in ("max_jobs_at_90pct", "max_jobs_at_95pct", "max_jobs_at_99pct"):
        spread = pd.concat([t[level] for t in across_seeds], axis=1)
        print(
            f"  {level}: identical across {len(SEEDS)} resampling seeds: "
            f"{bool((spread.nunique(axis=1) == 1).all())}"
        )

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
    print(f"wrote {MODEL_COMPARISON.relative_to(ROOT)} ({len(summary)} rows)")
    print(f"logged {len(sweep)} runs to {EXPERIMENTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
