# Predicting Water Consumption and Tank Capacity for Mobile Car Washing

**Module A7 — Water and Supplies**
Doorstep, Track A "Service as a Service" · BTech 7th Semester AI & ML Thematic Assessment

Naman Kumar (team lead, ML pipeline, integration) · Ranu Raj (data and EDA) ·
Vansh Rana (ML engineering) · Priyanshu (optimisation and evaluation) ·
Rudransh (documentation and paper)

---

## Abstract

Mobile car washing carries its water with it, so a crew's working day is bounded by tank
capacity rather than by demand. This module predicts per-job water consumption for Doorstep
and converts those predictions into operational capacity figures. We find that the variable
that drives consumption is not the service tier a customer books but an add-on buried inside
a delimited item list, and that the strongest single predictor — how dirty the car is — is
unobservable until the crew arrives. That forces two separate models rather than one. A
saturated cell-mean model reaches 5.93 L mean absolute error at booking time and 2.40 L on
site, against an 11.23 L baseline. Translating this into tank planning, we show that the
conventional arithmetic of dividing tank capacity by mean consumption overstates capacity
badly: the resulting figures hold only 53–91% of the time. At a 95% service level the
defensible capacities are 2, 4 and 5 jobs for the 200, 280 and 350 L vans. Because crews
average 262 L per day, refills are routine rather than exceptional, and we report refill
frequency as the operationally meaningful quantity. Finally, we compare Doorstep against
published figures for conventional car washing and find the honest result to be mixed:
mobile washing uses roughly a quarter of what home hose washing consumes, but nearly twice
what a reclaim-equipped tunnel uses.

## 1. Problem

Doorstep sends crews to customers rather than customers to a wash bay. Every litre used at
a job was loaded into a van beforehand, which makes two questions operational rather than
academic:

1. How much water will a given job consume?
2. How many jobs can a van serve before it must refill?

The second question is what actually constrains scheduling, and it cannot be answered well
without the first. A module that predicts consumption accurately but reports capacity as a
single number will mislead whoever schedules the day.

## 2. Data

The Doorstep simulated dataset covers 1 January 2024 to 31 December 2025. This analysis uses
three files: `jobs_done.csv` (39,302 completed jobs), `bookings.csv` for booking-time
attributes, and `vehicles.csv` for tank capacities.

> This dataset is simulated, generated with a fixed seed, and contains no real personal
> data. It should be cited as "Doorstep simulated dataset, Track A". Results here describe
> that simulation, not real operations.

The target is `water_litres`: mean 55.68 L, standard deviation 13.60 L, range 22.8–103.6 L.
`jobs_done` is complete, has no duplicate rows, and joins one-to-one with the completed
bookings. The duplicate-row glitch planted in `bookings` for module A17 never reaches
`jobs_done`, so this module is insulated from it.

## 3. Exploratory findings that shaped the model

Four findings from `notebooks/01_exploration.ipynb` determined the modelling approach.

**The service tier is a decoy.** All five `slot_type` values average between 55.0 and
55.8 L — the column is nearly uninformative. The variable that matters is the
`interior_clean` add-on, which appears inside the pipe-delimited `items` string on 27.9% of
jobs and adds +18.0 L. It is sold across every slot type, so a feature set built from
`slot_type` alone misses the second-largest effect available at booking time. Extracting it
requires parsing a string field rather than reading a column, which is precisely why it is
easy to miss.

**Dirtiness multiplies; the add-on adds.** Dirtiness scales the vehicle-size base by
1.00 / 1.18 / 1.35 / 1.53, and those ratios are identical across all three vehicle sizes.
`interior_clean` contributes a flat +18 L regardless of size or dirtiness. A purely additive
linear model is therefore mis-specified and needs a size × dirtiness interaction.

**Dirtiness is unknowable before arrival.** `dirtiness_level` is recorded when the crew
reaches the vehicle. It is uncorrelated with rainfall (−0.007) and temperature (+0.001),
flat across calendar months, and within-customer variation (sd 0.89) swamps between-customer
variation (sd 0.28) — it behaves as an independent draw. No booking-time feature predicts
it. This is the central constraint of the module: the best available predictor is
structurally unavailable when the prediction is most useful.

**The noise floor is additive and uniform.** Within an exact feature cell, jobs scatter with
sd ≈ 3.0 L, and this holds equally for interior and exterior jobs. The spread does not grow
with the cell mean, so the noise is additive rather than proportional. This sets a hard
floor on achievable error.

## 4. Method

### 4.1 Two prediction stages

Because dirtiness arrives late, the module trains two models on disjoint feature sets:

| Stage | Features | Available when |
|---|---|---|
| Planning | vehicle size, `interior_clean` | the booking is taken |
| On-site | the above plus dirtiness and its size interaction | the crew has seen the car |

Using dirtiness in the planning-time model would be leakage, and would produce a model that
benchmarks well and fails in deployment. Post-job columns — `duration_minutes`,
`late_minutes`, `rating`, `revenue` — are outcomes rather than inputs and are excluded from
both stages by construction, a property enforced by a test rather than by convention.

### 4.2 Model families

Three families were compared at each stage against two baselines, all on one shared 80/20
split with a fixed seed: a global mean, a per-vehicle-size group mean, a saturated cell mean,
linear regression with the size × dirtiness interaction, and gradient boosting.

### 4.3 Prediction intervals

Point estimates are inadequate for capacity planning, so each scenario carries a 90%
interval from residual quantiles. These are calibrated on a split disjoint from both the
fitting and test splits — a 60/20/20 arrangement. Calibrating and measuring coverage on the
same rows would report the nominal level back by construction rather than measuring
anything.

### 4.4 Tank capacity and refills

Capacity is evaluated by resampling observed per-job consumption 20,000 times and asking how
often *n* jobs actually fit, rather than dividing capacity by the mean. Refills are counted
by walking each crew-day in arrival order and topping up before any job the remaining water
cannot cover, assuming each day starts with a full tank.

## 5. Results

### 5.1 Prediction accuracy

| Stage | Model | MAE (L) | RMSE (L) | R² |
|---|---|---|---|---|
| Baseline | global mean | 11.23 | 13.78 | −0.000 |
| Baseline | per-vehicle-size mean | 8.98 | 11.00 | 0.362 |
| Planning | cell mean | **5.93** | 7.32 | **0.718** |
| Planning | linear | 5.93 | 7.32 | 0.718 |
| Planning | gradient boosting | 5.93 | 7.32 | 0.718 |
| On-site | cell mean | **2.40** | 3.00 | **0.952** |
| On-site | linear | 2.40 | 3.00 | 0.952 |
| On-site | gradient boosting | 2.40 | 3.00 | 0.952 |

The three families are indistinguishable — they agree to within 0.001 L at both stages. This
is not a disappointing result but an informative one: the underlying structure is a small,
fully-populated contingency table, with 6 cells at planning time and 24 on site, each
supported by hundreds to thousands of observations. Once the correct features are present
there is nothing left for a flexible model to find. Accordingly, model selection takes the
simplest family within 1% of the best MAE rather than the raw minimum, which selects the
cell mean at both stages. Selecting by raw argmin would have shipped a gradient-boosting
ensemble for a 0.0003 L improvement.

The on-site RMSE of 3.00 L sits at the noise floor identified in the EDA, meaning the on-site
model extracts essentially all available signal. Measured interval coverage on the held-out
test split is 0.900 at planning time and 0.899 on site, against a 0.90 nominal level.

The gap between the two stages quantifies the cost of not knowing dirtiness: MAE roughly
doubles, from 2.40 L to 5.93 L, and the interval widens from about ±5 L to about ±12 L.

### 5.2 Tank capacity

| Vehicle | Capacity | Mean-based | Actually fits | 90% | 95% | 99% |
|---|---|---|---|---|---|---|
| small_van | 200 L | 3 jobs | 90.9% | 3 | **2** | 2 |
| ev_van | 280 L | 5 jobs | 53.4% | 4 | **4** | 3 |
| large_van | 350 L | 6 jobs | 69.6% | 5 | **5** | 4 |

The mean-based figures are not merely imprecise, they are wrong in a specific and damaging
direction. Loading an EV van for the five jobs that dividing 280 L by 55.68 L suggests leaves
the crew short roughly once every two days. Per-job consumption has a standard deviation of
13.60 L and a maximum of 103.6 L, and summing several draws from that distribution produces
a spread that mean arithmetic discards entirely. **A capacity figure quoted without a service
level is not a usable number.**

### 5.3 Refill frequency

A single jobs-per-tank figure conceals the real constraint. Crews average 4.7 jobs and 262 L
per day across 8,342 crew-days, with a 95th percentile of 544 L — well beyond every tank in
the fleet.

| Vehicle | Mean refills/day | p95 | No refill | One | Two or more |
|---|---|---|---|---|---|
| small_van | 0.88 | 3 | 38.9% | 40.3% | 20.9% |
| ev_van | 0.45 | 2 | 61.3% | 33.0% | 5.7% |
| large_van | 0.26 | 1 | 75.8% | 22.9% | 1.3% |

Refilling is normal operation, not an exception. On a small van, a fifth of all crew-days
require two or more refills. For fleet planning this reframes tank size: the difference
between a 200 L and a 350 L van is not simply jobs per fill but 0.88 against 0.26
interruptions per working day, each costing travel time to a water source.

### 5.4 Sustainability comparison

Doorstep draws no reclaimed water — a mobile van cannot recover what it sprays — so its
55.7 L per job is entirely freshwater and compares directly against published freshwater
figures.

| Compared with | L per wash | Doorstep is | Source |
|---|---|---|---|
| Friction conveyor, no reclaim | 249.1 | 22% | EPA 2012 |
| Home hose, left running | 227.1 | 25% | EPA (derived) |
| In-bay automatic, no reclaim | 227.1 | 25% | EPA 2012 |
| In-bay automatic, measured fleet | 169.6 | 33% | ICA 2018 |
| Conveyor, measured fleet | 113.6 | 49% | ICA 2018 |
| Frictionless conveyor, reclaim | 63.6 | 88% | EPA 2012 |
| Self-service wand | 56.8 | 98% | EPA 2012 |
| In-bay automatic, reclaim | 30.3 | **184%** | EPA 2012 |
| Friction conveyor, reclaim | 29.5 | **189%** | EPA 2012 |

The honest reading is mixed. Mobile washing uses roughly a quarter of what home hose washing
and unreclaimed facilities consume, and about half the measured operating conveyor average.
It lands level with a self-service bay. But a reclaim-equipped tunnel uses about half what
Doorstep does per car, and that gap is structural: reclaim requires capturing runoff, which a
van parked on a customer's driveway cannot do. **The defensible claim is against home washing
and against unreclaimed or typical operating facilities — not against best-in-class fixed
sites.** Stating otherwise would be greenwashing.

Two caveats are carried in the data rather than hidden. The home-hose figure is derived: the
EPA publishes a 6 gal/min hose flow rate, not a per-wash total, and 60 gal represents that
rate over a ten-minute wash. The ICA figures come from an industry body reporting on its own
sector.

## 6. Limitations

- **Simulated data.** Every figure describes a generated dataset with known structure. Real
  consumption would carry measurement error and operator variation that this data lacks by
  construction.
- **The noise floor may be an artefact.** The uniform ≈3.0 L within-cell scatter is a
  property of the generator. Real jobs would likely show heteroscedasticity that this
  analysis would then be wrong to exclude.
- **Refill counts assume water is always available.** No travel time to a water source and no
  queueing is modelled; refills are counted, not costed.
- **Water for travel and crew use is outside scope.** Only per-job consumption is modelled.
- **The sustainability benchmarks are US figures** applied to an Indian operating context,
  and different sources define freshwater use differently — with and without reclaim, make-up
  water against total applied. The table reports the definitional split rather than averaging
  across it.

## 7. Conclusions

The module's most transferable finding is methodological. The largest available predictor was
hidden inside a delimited string rather than exposed as a column, and the strongest predictor
overall was unavailable at prediction time. Neither is visible from a correlation matrix, and
both determined the shape of the solution more than any modelling choice did. Once the
features were right, three model families of very different capacity performed identically —
which suggests that effort spent on feature semantics returned more here than effort spent on
model selection would have.

Operationally, the module's recommendation is that capacity be quoted as an interval with a
stated service level, and that refill frequency, not jobs per tank, be treated as the
planning quantity. Downstream consumers should take the distribution rather than the mean;
`INTEGRATION.md` records that contract.

## 8. Reproducing

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe src/train.py
.venv/Scripts/python.exe -m pytest tests -q
```

Seed 7 throughout, matching the dataset generator. `src/train.py` regenerates every figure in
sections 5.1 to 5.4 and appends each run to `experiments.csv`.

## References

1. US Environmental Protection Agency. *WaterSense at Work: Best Management Practices for
   Commercial and Institutional Facilities*, Section 5.5 Vehicle Washing. October 2012.
   Figures attributed there to Chris Brown. Reclaim figures are freshwater make-up, not total
   water applied.
2. US Environmental Protection Agency, WaterSense. *Who Needs a Hose?* Publishes a 6 gal/min
   garden-hose flow rate; the per-wash figure used here is derived from that rate.
3. International Carwash Association. *Water Use, Evaporation, and Carryout in Professional
   Carwashes*. 2018. Measurements at 12 sites (6 conveyor, 6 in-bay) during 2017.
4. Doorstep simulated dataset, Track A, generated by `data/raw/generate_doorstep.py` with
   seed 7.
