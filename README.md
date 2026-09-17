# A7 — Water and Supplies

## What this module does

This module predicts how much water each mobile car-washing job will use, works out the best
set of jobs that fits inside a van's tank, and compares Doorstep's water use against
published figures for conventional car washing. The van carries its own water, so tank
capacity — not demand — is what bounds a crew's day.

## Team

- Naman Kumar — Team Lead: project coordination, ML pipeline, integration
- Ranu Raj — Data & EDA: data exploration, preprocessing, visualisation
- Vansh Rana — ML Engineer: machine learning models and training
- Priyanshu — Optimisation & Evaluation: tank-capacity optimisation and model evaluation
- Rudransh — Documentation & Paper: technical paper and project documentation

## Data

The supplied Doorstep simulated dataset in `data/raw/`, covering 1 Jan 2024 – 31 Dec 2025.
This module uses three of the files: `jobs_done.csv` (39,302 completed jobs, the target
`water_litres`), `bookings.csv` for booking-time attributes, and `vehicles.csv` for tank
capacities. `data/raw/` is immutable and nothing is written back to it.

No cleaning was needed: `jobs_done.csv` has no missing values and no duplicate rows, and
joins one-to-one with the completed bookings. The planted duplicate-booking glitch never
reaches `jobs_done`. The only missing values in the working frame are 314 blank
`bookings.total_price` cells (0.8%, blank by design), which are not used as a feature.

The one derived feature that matters is `interior_clean`, parsed out of the `|`-separated
`bookings.items` string — it is not a column of its own.

> The dataset is simulated. Cite it as "Doorstep simulated dataset, Track A". It is not real
> operational data.

## How to run

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
.venv/Scripts/python.exe src/train.py
.venv/Scripts/python.exe -m pytest tests -q
```

On macOS or Linux use `.venv/bin/python`. `src/train.py` regenerates everything in
`results/` and appends one row per run to `experiments.csv`. Re-run
`notebooks/01_exploration.ipynb` to refresh `results/plots/`.

## Results

Mean absolute error in litres per job, on a held-out test split, over ten seeds.

| Method | Metric | Score | Spread (10 seeds) |
|--------|--------|-------|-------------------|
| Baseline — global mean | MAE | 11.152 L | ± 0.062 |
| Baseline — per-vehicle-size mean | MAE | 8.922 L | ± 0.067 |
| Ours — planning-time (booking features) | MAE | 5.897 L | ± 0.038 |
| Ours — on-site (adds dirtiness) | MAE | 2.397 L | ± 0.014 |

The three model families tried at each stage — cell mean, linear with a size × dirtiness
interaction, and gradient boosting — differ by 0.001 L, roughly forty times less than the
seed-to-seed spread. They are not distinguishable, so the simplest is used.

Tank capacity at a 95% service level is 2 / 4 / 5 jobs for the 200 / 280 / 350 L vans;
dividing capacity by mean consumption gives 3 / 5 / 6, which actually fits only 91% / 53% /
70% of the time.

## Output

- `results/consumption_model.csv` — predicted litres with a 90% interval, per scenario, for
  both prediction stages. **Required deliverable.**
- `results/tank_capacity.csv` — maximum jobs per tank by service level. **Required
  deliverable.**
- `results/refill_planning.csv` — refills needed per crew-day, per tank
- `results/tank_plan.csv` — best set of jobs to fit one tank, by method and planning basis
- `results/sustainability.csv` — comparison with published car-wash water figures
- `results/model_comparison.csv` — ten-seed model comparison with spread

See `results/README.md` for column definitions and `INTEGRATION.md` for the handover
contract.

## Five things we did not expect

1. **The service tier tells you nothing.** All five `slot_type` values average 54.9–55.8 L.
   The variable that matters is the `interior_clean` add-on hidden inside the `items`
   string — 27.9% of jobs, +18.0 L.
2. **Dirtiness multiplies rather than adds.** It scales the vehicle-size base by
   1.00 / 1.18 / 1.35 / 1.53, identically across all three vehicle sizes, so an additive
   linear model is mis-specified.
3. **Dirtiness cannot be predicted before arrival.** It is uncorrelated with rain (−0.007)
   and temperature (+0.001) and flat across months, and the same customer varies more than
   customers differ from each other. The best predictor is unavailable when it is needed.
4. **Mean-based tank arithmetic is badly wrong.** Loading an EV van for the five jobs that
   280 ÷ 55.7 suggests leaves the crew short roughly every second day.
5. **Optimising the plan made it less reliable.** Choosing jobs by exact knapsack instead of
   booked order doubled the rate of running the tank dry, from 5.9% to 11.9% of crew-days,
   because tight packing spends the slack that had been absorbing prediction error.

## Limits

- Simulated data: the uniform ~3 L within-cell noise is a property of the generator, and
  real jobs would likely be heteroscedastic.
- `dirtiness_level` is unknowable at booking, so planning-time error is roughly double
  on-site error and cannot be improved with the features available.
- Job selection assumes a crew-day's bookings are known in advance and free to drop;
  refusing a confirmed booking carries a customer cost that is not modelled.
- Selection plans one tank-load and ignores refills; the two are analysed separately.
- Water for travel and crew use is not modelled, and refills are counted, not costed.
- Sustainability benchmarks are US figures applied to an Indian operating context.

## Repository Structure

- `data/` — raw and processed datasets
- `src/` — pipeline: `data_loader.py`, `model.py`, `train.py`, `evaluate.py`,
  `optimise.py`, `sustainability.py`
- `notebooks/` — exploratory analysis
- `results/` — model outputs and plots
- `tests/` — pipeline guardrails
- `paper/` — technical paper
- `experiments.csv` — experiment log
- `INTEGRATION.md` — handover contract

## Team Module

**Track:** Doorstep — Track A
**Module:** A7 — Water and Supplies
