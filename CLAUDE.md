# A7 — Water and Supplies

Predict per-job water consumption for Doorstep's mobile car-wash jobs, and report how many
jobs fit in one van tank. Two required deliverables: `results/consumption_model.csv` and a
maximum-jobs-per-tank figure.

## Environment

Python 3.12, `pip install -r requirements.txt`. Notebooks run on the `base` kernel
(Python 3.12.4). No virtualenv is committed.

## Data rules

- `data/raw/` is the supplied dataset and is **immutable** — never edit or regenerate it
  into the repo. `data/raw/DATA_DICTIONARY.md` is the authoritative schema.
- `data/processed/` is gitignored. Anything derived must be reproducible from `data/raw/`.
- Join on `booking_id` (`bookings` ↔ `jobs_done`), `crew_id`, `customer_id`, `date`.
- Filter `bookings.status != 'duplicate'` — those are a planted A17 data glitch with no
  `jobs_done` row.
- Seed 7 everywhere, matching the dataset generator, so resampling figures stay stable.
- `data/raw/anomaly_key.json` is faculty-only ground truth for module A17. Do not use it.

## Modelling constraints (established in the EDA, `notebooks/01_exploration.ipynb`)

These are non-obvious and shape every later choice:

- `slot_type` carries no water signal. The real driver is the `interior_clean` add-on
  hidden inside the `|`-separated `bookings.items` string (+18.0 L, on 27.9% of jobs, sold
  across all slot types). Parse `items`; do not model off `slot_type`.
- Dirtiness is **multiplicative** on a vehicle-size base (1.00 / 1.18 / 1.35 / 1.53,
  identical across sizes) while `interior_clean` adds a flat +18 L. A purely additive
  linear model is mis-specified — log-transform the target or model the interaction.
- `dirtiness_level` is recorded on crew arrival and is not predictable from booking-time
  data. This forces **two separate models**: a planning-time one (booking features only,
  no dirtiness) and an on-site one. Using dirtiness in a planning-time model is leakage.
- Within-cell noise is additive and uniform: sd ~3.0 L for exterior and interior jobs
  alike. The wider ~7.3 L spread at planning time is unresolved dirtiness, not a property
  of interior jobs — it applies to both groups equally.
- Tank sizing must be reported as an interval at a stated service level, not a single
  number. Mean-based jobs-per-tank (3/5/6) overstates capacity; at 95% it is 2/4/5.

## Outputs

`results/` is generated, never hand-edited; `results/README.md` tracks what exists and
records the EDA reference figures that later stages are compared against. Re-running
`notebooks/01_exploration.ipynb` refreshes `results/plots/`. Log model runs in
`experiments.csv`.

## Conventions

- `src/` holds the pipeline (`data_loader.py`, `model.py`, `train.py`, `evaluate.py`);
  notebooks explore, `src/` is what actually produces deliverables.
- Commit messages: short imperative subject, then a body explaining *findings* and *why*,
  not a file list.
- The dataset is simulated — cite it as "Doorstep simulated dataset, Track A" in
  `paper/` and never present it as real operational data.
