"""Choose the best set of jobs to fit one tank.

The module brief asks, given a tank capacity, for the best set of jobs to fit in a day.
Selection has to be made from *predicted* water, since actual consumption is only known
once the job is done, but feasibility is judged against actual consumption. That gap is
the point: a plan built on point predictions fits the mean, not the day.

`revenue` is the objective, not a feature. It equals the booking's `total_price` and is
therefore known when the plan is made; it is never used to predict water.
"""

import numpy as np
import pandas as pd

from data_loader import TARGET

SCALE = 10  # decilitres, so the knapsack works in integers


def select_booked_order(weights, values, capacity):
    """Serve in booked order until the tank cannot cover the next job, then stop.

    This is the manager's default and the baseline to beat: run out at job six and the
    rest of the day is cancelled.
    """
    chosen = np.zeros(len(weights), bool)
    chosen[: int(np.searchsorted(np.cumsum(weights), capacity, side="right"))] = True
    return chosen


def select_value_density(weights, values, capacity):
    """Greedily take the highest revenue per litre that still fits."""
    chosen = np.zeros(len(weights), bool)
    remaining = capacity
    for i in np.argsort(-(values / weights)):
        if weights[i] <= remaining:
            chosen[i] = True
            remaining -= weights[i]
    return chosen


def select_exact(weights, values, capacity):
    """Exact 0/1 knapsack by dynamic programming over integer decilitres."""
    w = np.rint(np.asarray(weights) * SCALE).astype(int)
    cap = int(round(capacity * SCALE))
    best = np.zeros(cap + 1)
    keep = np.zeros((len(w), cap + 1), bool)

    for i, (wi, vi) in enumerate(zip(w, values)):
        if wi > cap:
            continue
        candidate = best.copy()
        candidate[wi:] = best[: cap + 1 - wi] + vi
        keep[i] = candidate > best
        best = np.where(keep[i], candidate, best)

    chosen = np.zeros(len(w), bool)
    remaining = cap
    for i in range(len(w) - 1, -1, -1):
        if keep[i, remaining]:
            chosen[i] = True
            remaining -= w[i]
    return chosen


METHODS = {
    "booked_order": select_booked_order,
    "value_density": select_value_density,
    "exact_knapsack": select_exact,
}


def evaluate_plans(df, vehicles, weight_columns):
    """Serve-rate, revenue and overflow for each tank, planning basis and method.

    Overflow is the share of crew-days where the plan's *actual* consumption exceeded
    the tank — the failure the module exists to prevent.
    """
    ordered = df.sort_values(["date", "crew_id", "arrival_time"])
    days = [
        (g[TARGET].to_numpy(), g["revenue"].to_numpy(), {c: g[c].to_numpy() for c in weight_columns.values()})
        for _, g in ordered.groupby(["date", "crew_id"])
    ]
    total_jobs = sum(len(actual) for actual, _, _ in days)
    total_revenue = sum(values.sum() for _, values, _ in days)

    rows = []
    for _, vehicle in vehicles.iterrows():
        capacity = float(vehicle["capacity_litres"])
        for basis, column in weight_columns.items():
            for method_name, select in METHODS.items():
                jobs = revenue = overflows = 0
                for actual, values, weights in days:
                    w = weights[column]
                    chosen = (
                        np.ones(len(w), bool)
                        if w.sum() <= capacity
                        else select(w, values, capacity)
                    )
                    jobs += int(chosen.sum())
                    revenue += float(values[chosen].sum())
                    overflows += int(actual[chosen].sum() > capacity)

                rows.append(
                    {
                        "vehicle_type": vehicle["vehicle_type"],
                        "capacity_litres": capacity,
                        "planning_basis": basis,
                        "method": method_name,
                        "jobs_served_pct": round(jobs / total_jobs * 100, 1),
                        "revenue_captured_pct": round(revenue / total_revenue * 100, 1),
                        "overflow_pct_of_crew_days": round(overflows / len(days) * 100, 1),
                    }
                )
    return pd.DataFrame(rows)
