"""Compare Doorstep's measured per-job water use against conventional car washing.

Benchmarks are external published figures, held in their original units (US gallons
per vehicle) with their source, so the paper can audit the conversion.

Sources
-------
EPA 2012
    US EPA, "WaterSense at Work: Best Management Practices for Commercial and
    Institutional Facilities", Section 5.5 Vehicle Washing, October 2012. Figures
    attributed there to Chris Brown. Reclaim figures are freshwater make-up, not
    total water applied.
EPA hose
    US EPA WaterSense, "Who Needs a Hose?" — a garden hose flows about 6 gallons
    per minute left running. The per-wash figure here is that rate over a ten-minute
    wash; EPA publishes the flow rate, not a per-wash total.
ICA 2018
    International Carwash Association, "Water Use, Evaporation, and Carryout in
    Professional Carwashes", 2018, measuring 12 sites (6 conveyor, 6 in-bay) during
    2017. Nearly all sites ran reclaim, so these are operating fleet averages of
    freshwater drawn rather than best-case figures.
"""

import pandas as pd

from data_loader import TARGET

LITRES_PER_US_GALLON = 3.785411784

BENCHMARKS = [
    {
        "benchmark": "home_hose_running",
        "gallons_per_wash": 60.0,
        "reclaim": "none",
        "source": "EPA hose",
        "basis": "6 gal/min over a 10-minute wash",
    },
    {
        "benchmark": "self_service_wand",
        "gallons_per_wash": 15.0,
        "reclaim": "not feasible",
        "source": "EPA 2012",
        "basis": "average self-service bay",
    },
    {
        "benchmark": "conveyor_friction_no_reclaim",
        "gallons_per_wash": 65.8,
        "reclaim": "none",
        "source": "EPA 2012",
        "basis": "friction conveyor without reclaim",
    },
    {
        "benchmark": "conveyor_friction_reclaim",
        "gallons_per_wash": 7.8,
        "reclaim": "yes",
        "source": "EPA 2012",
        "basis": "friction conveyor with reclaim, freshwater make-up",
    },
    {
        "benchmark": "conveyor_frictionless_reclaim",
        "gallons_per_wash": 16.8,
        "reclaim": "yes",
        "source": "EPA 2012",
        "basis": "frictionless conveyor with reclaim, freshwater make-up",
    },
    {
        "benchmark": "in_bay_automatic_no_reclaim",
        "gallons_per_wash": 60.0,
        "reclaim": "none",
        "source": "EPA 2012",
        "basis": "in-bay automatic without reclaim",
    },
    {
        "benchmark": "in_bay_automatic_reclaim",
        "gallons_per_wash": 8.0,
        "reclaim": "yes",
        "source": "EPA 2012",
        "basis": "in-bay automatic with reclaim, freshwater make-up",
    },
    {
        "benchmark": "conveyor_measured_fleet",
        "gallons_per_wash": 30.0,
        "reclaim": "mostly yes",
        "source": "ICA 2018",
        "basis": "measured fleet average, 6 conveyor sites, 2017",
    },
    {
        "benchmark": "in_bay_automatic_measured_fleet",
        "gallons_per_wash": 44.8,
        "reclaim": "mostly yes",
        "source": "ICA 2018",
        "basis": "measured fleet average, 6 in-bay sites, 2017",
    },
]


def sustainability_comparison(df):
    """Per-wash and fleet-scale comparison against each published benchmark.

    Doorstep draws no reclaimed water, so its figure is entirely freshwater and is
    directly comparable to the freshwater columns of the benchmarks.
    """
    doorstep_mean = float(df[TARGET].mean())
    n_jobs = len(df)

    rows = []
    for benchmark in BENCHMARKS:
        litres = benchmark["gallons_per_wash"] * LITRES_PER_US_GALLON
        rows.append(
            {
                "benchmark": benchmark["benchmark"],
                "reclaim": benchmark["reclaim"],
                "source": benchmark["source"],
                "basis": benchmark["basis"],
                "gallons_per_wash": benchmark["gallons_per_wash"],
                "benchmark_litres_per_wash": round(litres, 1),
                "doorstep_litres_per_wash": round(doorstep_mean, 1),
                "difference_litres": round(doorstep_mean - litres, 1),
                "doorstep_pct_of_benchmark": round(doorstep_mean / litres * 100, 1),
                "fleet_litres_saved": round((litres - doorstep_mean) * n_jobs, 0),
            }
        )
    return pd.DataFrame(rows).sort_values("benchmark_litres_per_wash", ascending=False)
