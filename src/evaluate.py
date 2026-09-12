"""Metrics and tank-capacity evaluation for the A7 pipeline."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score

from data_loader import SEED

MAX_JOBS = 10
N_DRAWS = 20000
SERVICE_LEVELS = (0.90, 0.95, 0.99)


def regression_metrics(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
        "r2": r2_score(y_true, y_pred),
    }


def metrics_by_job_type(y_true, y_pred, interior):
    """Split errors by job type; interior jobs carry most of the variance."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    interior = np.asarray(interior).astype(int)
    return {
        "mae_exterior": mean_absolute_error(y_true[interior == 0], y_pred[interior == 0]),
        "mae_interior": mean_absolute_error(y_true[interior == 1], y_pred[interior == 1]),
    }


def interval_coverage(y_true, lo, hi):
    y_true = np.asarray(y_true)
    return float(((y_true >= lo) & (y_true <= hi)).mean())


def tank_feasibility(water, capacities, n_draws=N_DRAWS, max_jobs=MAX_JOBS, seed=SEED):
    """P(n jobs fit in one tank), by resampling observed per-job consumption."""
    rng = np.random.default_rng(seed)
    water = np.asarray(water)
    return pd.DataFrame(
        {
            capacity: [
                float(
                    (
                        rng.choice(water, size=(n_draws, n), replace=True).sum(axis=1)
                        <= capacity
                    ).mean()
                )
                for n in range(1, max_jobs + 1)
            ]
            for capacity in capacities
        },
        index=pd.Index(range(1, max_jobs + 1), name="jobs_in_tank"),
    )


def jobs_per_tank(water, vehicles, service_levels=SERVICE_LEVELS, seed=SEED):
    """Maximum jobs per tank at each service level, against the mean-based figure.

    Mean-based division ignores the spread of per-job consumption and overstates
    capacity, which is why the deliverable quotes a service level.
    """
    water = np.asarray(water)
    capacities = list(vehicles["capacity_litres"])
    feasibility = tank_feasibility(water, capacities, seed=seed)
    mean_water = float(water.mean())

    rows = []
    for _, vehicle in vehicles.iterrows():
        capacity = vehicle["capacity_litres"]
        probabilities = feasibility[capacity]
        mean_based = int(capacity // mean_water)
        row = {
            "vehicle_type": vehicle["vehicle_type"],
            "capacity_litres": capacity,
            "mean_based_jobs": mean_based,
            "p_mean_based_fits": round(float(probabilities.get(mean_based, 0.0)), 4),
        }
        for level in service_levels:
            feasible = probabilities.index[probabilities >= level]
            row[f"max_jobs_at_{int(level * 100)}pct"] = int(feasible.max()) if len(feasible) else 0
        rows.append(row)
    return pd.DataFrame(rows)
