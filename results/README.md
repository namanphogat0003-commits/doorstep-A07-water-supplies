# results/

Outputs produced by the A7 pipeline. Everything here is regenerated from
`data/raw/` and is reproducible — do not hand-edit.

## Status

| Artefact | Stage | Status |
|---|---|---|
| `plots/` | EDA (Week 2) | produced — see below |
| `consumption_model.csv` | required A7 deliverable | produced by `src/train.py` |
| `tank_capacity.csv` | required A7 deliverable (max jobs per tank) | produced by `src/train.py` |
| `refill_planning.csv` | refill frequency per crew-day | produced by `src/train.py` |
| `sustainability.csv` | comparison with conventional car washing | produced by `src/train.py` |
| `tank_plan.csv` | best set of jobs to fit one tank | produced by `src/train.py` |
| `model_comparison.csv` | ten-seed model comparison with spread | produced by `src/train.py` |

Regenerate both with `python src/train.py` from the repository root. That also appends
one row per model run to `experiments.csv`.

## consumption_model.csv

One row per scenario the module has to quote a figure for, for both prediction stages:

- `stage` — `planning` (booking-time, no dirtiness) or `onsite` (crew has seen the car)
- `vehicle_size`, `dirtiness_level`, `interior_clean` — the scenario; `dirtiness_level` is
  blank on planning rows because it is not knowable then
- `predicted_litres` with `pi_low_litres` / `pi_high_litres` at `interval_level` 0.90
- `n_observed`, `observed_mean_litres`, `observed_sd_litres` — empirical support per cell

Intervals are residual quantiles calibrated on a split disjoint from both the fit and the
test split. Measured coverage on the held-out test split is 0.900 for both stages.

## tank_capacity.csv

Maximum jobs per tank per vehicle at the 90 / 95 / 99% service levels, with the
mean-based figure and the probability that it actually fits, by resampling observed
per-job consumption (20,000 draws, seed 7).

## refill_planning.csv

Mid-day refills per crew-day per vehicle, counted by walking each crew-day in arrival
order and topping up before any job the remaining water cannot cover. A single
jobs-per-tank number hides the real constraint: crews average 262 L a day against tanks
of 200–350 L, so 61% / 39% / 24% of crew-days need at least one refill.

## sustainability.csv

Doorstep's measured 55.7 L per job against published figures for conventional car
washing. Benchmarks are stored in `src/sustainability.py` in their original units
(US gallons per vehicle) with their source, and converted at 3.785411784 L/gal.

Doorstep draws no reclaimed water, so its 55.7 L is entirely freshwater and compares
directly against the freshwater columns below.

| Compared with | L per wash | Doorstep is |
|---|---|---|
| friction conveyor, no reclaim | 249.1 | 22% of it |
| home hose, left running | 227.1 | 25% of it |
| in-bay automatic, no reclaim | 227.1 | 25% of it |
| in-bay automatic, measured fleet | 169.6 | 33% of it |
| conveyor, measured fleet | 113.6 | 49% of it |
| frictionless conveyor with reclaim | 63.6 | 88% of it |
| self-service wand | 56.8 | 98% of it — level |
| in-bay automatic with reclaim | 30.3 | 184% of it — worse |
| friction conveyor with reclaim | 29.5 | 189% of it — worse |

**The honest headline is not "mobile washing saves water".** It beats home washing and
typical operating car washes by a wide margin, and lands level with a self-service bay,
but a reclaim-equipped tunnel uses about half what Doorstep does per car. Mobile washing
cannot reclaim — the water leaves with the van — so that gap is structural, not an
operations problem to be tuned away. The defensible claims are against home washing and
against unreclaimed or typical operating facilities.

Sources, for citation in the paper:

- US EPA, *WaterSense at Work: Best Management Practices for Commercial and Institutional
  Facilities*, Section 5.5 Vehicle Washing, October 2012. Figures attributed there to
  Chris Brown. Reclaim figures are freshwater make-up, not total water applied.
- US EPA WaterSense, *Who Needs a Hose?* — publishes a 6 gal/min hose flow rate, not a
  per-wash total; the 60 gal figure here is that rate over a ten-minute wash and is
  labelled as derived.
- International Carwash Association, *Water Use, Evaporation, and Carryout in Professional
  Carwashes*, 2018, measuring 12 sites (6 conveyor, 6 in-bay) during 2017. Note this is an
  industry body reporting on its own sector.

## tank_plan.csv

The module brief's third roadmap item: given a tank capacity, the best set of jobs to fit
in a day. Each row is one tank size, one planning basis and one selection method.

Columns:

- `vehicle_type`, `capacity_litres` — the tank
- `planning_basis` — which water figure the plan was built from: `oracle_actual` (actual
  consumption, an upper bound no planner can reach), `planning_point` (the planning-time
  model's point estimate), `planning_safe` (the upper end of its 90% interval)
- `method` — `booked_order` (serve in booked order until the tank cannot cover the next
  job, then stop: the manager's default), `value_density` (greedily take the highest
  revenue per litre that fits), `exact_knapsack` (exact 0/1 knapsack by dynamic
  programming)
- `jobs_served_pct`, `revenue_captured_pct` — share of all jobs and all revenue captured
- `overflow_pct_of_crew_days` — share of crew-days where the plan's *actual* consumption
  exceeded the tank. This is the failure the module exists to prevent.

Revenue is the objective, not a feature. It equals the booking's `total_price`, so it is
known when the plan is made, and it is never used to predict water.

Three findings:

**Optimising by value buys revenue, not jobs.** On the 200 L van, booked order captures
58.5% of revenue against the exact knapsack's 71.7% — 13.2 points more revenue for only
3.8 points more jobs, by preferring jobs worth more per litre.

**Exact optimisation barely beats greedy.** Value-density greedy reaches 70.9% against the
exact 71.7%, roughly 99% of optimal. The knapsack is worth implementing to know that, not
because the operation needs it.

**Better optimisation makes overflow worse.** Planning on point predictions, booked order
overflows on 5.9% of crew-days but the exact knapsack overflows on 11.9%. Tighter packing
leaves no slack for prediction error, so the better the optimiser the more fragile the
plan. Planning on the interval's upper bound removes overflow entirely (0.0%) at a cost of
about 10 points of jobs and revenue. That trade is the reason the model reports an interval
rather than a point.

## model_comparison.csv and model selection

Every model is run under **ten seeds** (0-9), each reshuffling the 60/20/20
fit/calibrate/test split. One row per stage and model, with `mae`, `rmse` and `r2` as
`_mean`, `_std`, `_min`, `_max`.

| Stage | Model | MAE (L), mean ± sd |
|---|---|---|
| baseline | global mean | 11.152 ± 0.062 |
| baseline | per-vehicle-size mean | 8.922 ± 0.067 |
| planning | cell mean | 5.897 ± 0.038 |
| planning | linear | 5.897 ± 0.038 |
| planning | gradient boosting | 5.896 ± 0.038 |
| on-site | cell mean | 2.397 ± 0.014 |
| on-site | linear | 2.397 ± 0.015 |
| on-site | gradient boosting | 2.397 ± 0.014 |

The three families differ by 0.001 L while the seed-to-seed spread is 0.038 L — the noise
between splits is about forty times the gap between models, so they are not distinguishable
and a ranking from a single split would be an artefact. `src/train.py` therefore selects the
simplest family within 1% of the best seed-averaged MAE rather than by raw argmin; both
stages select the cell mean.

Interval coverage is 0.8985 ± 0.0053 (planning) and 0.9000 ± 0.0052 (on-site) against a
0.90 nominal level. The jobs-per-tank figures are identical under all ten resampling seeds.

## plots/

Generated by `notebooks/01_exploration.ipynb`. Re-run that notebook to refresh them.

| File | Shows |
|---|---|
| `01_target_distribution.png` | `water_litres` histogram and spread by vehicle size |
| `02_slot_type_vs_addon.png` | why `slot_type` looks flat while the `interior_clean` add-on does not |
| `03_functional_form.png` | dirtiness acts as a multiplier on a vehicle-size base |
| `04_correlation_matrix.png` | correlations among candidate features and the target |
| `05_temporal.png` | job volume grows, mean water per job stays flat |
| `06_crew_day_load.png` | jobs per crew-day and daily water demand against tank capacities |
| `07_tank_feasibility.png` | P(n jobs fit in one tank) by vehicle, with the 95% service level |

## Reference figures from EDA

These are descriptive statistics computed in the exploration notebook, **not** model
outputs. They are recorded here so later stages can be compared against them.

- per-job water: mean 55.68 L, sd 13.60 L, range 22.8–103.6 L (n = 39,302)
- tank capacities (from `data/raw/vehicles.csv`): small_van 200 L, ev_van 280 L,
  large_van 350 L
- jobs per tank, mean-based arithmetic: 3 / 5 / 6
- jobs per tank at a 95% service level (empirical resampling, seed 7): 2 / 4 / 5
- crew-day load: mean 4.7 jobs, 262 L; 61% / 39% / 24% of crew-days exceed the
  200 / 280 / 350 L tanks

The gap between the mean-based and service-level figures is the reason the final
deliverable must report an interval and a stated service level rather than a single
number.
