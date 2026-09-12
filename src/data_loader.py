"""Load the supplied Doorstep data and build the A7 modelling frame.

data/raw is immutable, so every frame here is derived at run time.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results"

SEED = 7
TARGET = "water_litres"

VEHICLE_SIZES = ["hatchback", "sedan", "suv"]
DIRTINESS_LEVELS = [1, 2, 3, 4]
ADDONS = ["interior_clean", "wax_polish", "tyre_dressing", "pet_hair", "engine_bay"]

# Booking-time columns only. duration_minutes, late_minutes, rating and revenue are
# job outcomes and would leak.
BOOKING_COLUMNS = [
    "booking_id",
    "slot_type",
    "items",
    "vehicle_size",
    "is_weekend",
    "area",
    "list_price",
    "total_price",
]

STAGES = ["size_only", "planning", "onsite"]


def load_jobs():
    """Completed jobs enriched with booking attributes and parsed add-on flags."""
    jobs = pd.read_csv(RAW / "jobs_done.csv", parse_dates=["date"])
    bookings = pd.read_csv(RAW / "bookings.csv", parse_dates=["date"])

    df = jobs.merge(
        bookings[BOOKING_COLUMNS], on="booking_id", how="left", validate="one_to_one"
    )
    for addon in ADDONS:
        df[f"addon_{addon}"] = df["items"].str.contains(addon, na=False).astype(int)
    return df


def load_vehicles():
    vehicles = pd.read_csv(RAW / "vehicles.csv")
    return vehicles.sort_values("capacity_litres").reset_index(drop=True)


def build_features(df, stage):
    """Feature matrix for one prediction stage.

    size_only is the baseline set; planning is what is knowable when the booking is
    taken; onsite adds dirtiness, which the crew only observes on arrival.
    """
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}, expected one of {STAGES}")

    sizes = pd.Series(
        pd.Categorical(df["vehicle_size"], categories=VEHICLE_SIZES), index=df.index
    )
    X = pd.get_dummies(sizes, prefix="size", drop_first=True).astype(float)
    if stage == "size_only":
        return X

    X["interior_clean"] = df["addon_interior_clean"].astype(float)
    if stage == "planning":
        return X

    size_columns = [c for c in X.columns if c.startswith("size_")]
    X["dirtiness"] = df["dirtiness_level"].astype(float)
    for col in size_columns:
        X[f"{col}_x_dirtiness"] = X[col] * X["dirtiness"]
    return X
