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
saturated cell-mean model reaches 5.90 ± 0.04 L mean absolute error at booking time and
2.40 ± 0.01 L on site over ten seeds, against an 11.15 ± 0.06 L baseline. Translating this
into tank planning, we show that the
conventional arithmetic of dividing tank capacity by mean consumption overstates capacity
badly: the resulting figures hold only 53–91% of the time. At a 95% service level the
defensible capacities are 2, 4 and 5 jobs for the 200, 280 and 350 L vans. Because crews
average 262 L per day, refills are routine rather than exceptional, and we report refill
frequency as the operationally meaningful quantity. Choosing *which* jobs to serve rather than how many, an exact knapsack captures 13 points
more revenue than serving in booked order for under 4 points more jobs, while a greedy
rule reaches 99% of that — but optimising on point predictions doubles the rate at which
plans overflow the tank, from 5.9% of crew-days to 11.9%, because tight packing consumes
the slack that absorbed prediction error. Planning on the interval's upper bound removes
overflow entirely for about ten points of throughput. Finally, we compare Doorstep against
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

## 2. Related work

Ten studies, grouped by the question they answer for this module.

**What a car wash actually consumes.** Monney et al. [1] give empirical estimates of water
consumption and pollution loads across the commercial carwash industry, establishing that
per-vehicle consumption must be measured rather than assumed. Maciejewska and Reizer [2]
compare four professional wash types across Poland and find carbon footprints from 0.88 kg
CO₂ (hand wash, gas heating) to 4.46 kg CO₂ (rollover wash, electric heating), concluding
that wash *type* dominates the footprint. Zaneti et al. [3] audit a full-scale car-wash
reclamation plant over 22 weeks and report almost 70% reclamation, needing fewer than 40 L
of fresh water per wash. Together these frame our comparison: the spread across facility
types is far wider than the spread within one, so a single "conventional car wash" figure
would be meaningless. [3] also corroborates our own result independently — at under 40 L
fresh per wash, a reclaim-equipped facility uses less than our measured 55.7 L, and a mobile
van cannot reclaim because the water leaves with it.

**Predicting water demand.** Donkor et al. [4] review urban water-demand forecasting and find
that method complexity is a weak predictor of accuracy — simple models frequently match
sophisticated ones once the right variables are present. Our finding that three model
families are indistinguishable once `interior_clean` is parsed is the same observation at
job scale.

**Deciding under an uncertain capacity constraint.** Kleywegt and Papastavrou [5, 6]
formalise the dynamic and stochastic knapsack, where item sizes are random and capacity may
be violated. Han et al. [7] give a robust-optimisation treatment of the chance-constrained
binary knapsack, replacing a hard capacity constraint with one that must hold at a stated
probability. This is precisely our tank problem: our service-level formulation is a
chance constraint solved empirically by resampling rather than analytically, and their work
is why we report capacity at a service level rather than as a single number.

**Why optimising on predictions can backfire.** Elmachtoub and Grigas [8] show that
minimising prediction error is not the same as minimising decision cost, and that a
better-fitting model can yield worse decisions once its output is fed to an optimiser. Our
result that the exact knapsack doubles the tank-overflow rate relative to serving in booked
order is an instance of exactly this, arrived at empirically.

**Turning a prediction into a safe input.** Lei et al. [9] give distribution-free prediction
intervals with finite-sample coverage from a held-out calibration split, and Koenker and
Bassett [10] establish quantile regression as the alternative route to the same quantity. We
use the split-calibration construction of [9]; our decision to plan against the interval's
upper bound rather than its centre is the practical consequence.

**Routing and capacity in service fleets.** Braekers et al. [11] classify the vehicle routing
literature and note that most capacitated variants treat demand as deterministic. A7 supplies
the per-job distribution that a stochastic-demand routing model would need, which is why the
handover to A12 passes the distribution rather than the mean.

**What we do not borrow.** No published study we found models water consumption at the level
of an individual mobile wash job, and none reports the interaction structure we observe
(dirtiness multiplying a vehicle-size base while an interior add-on contributes a constant).
The per-job model here is built from the data rather than adapted from prior work.

## 3. Data

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

## 4. Exploratory findings that shaped the model

Four findings from `notebooks/01_exploration.ipynb` determined the modelling approach.

**The service tier is a decoy.** All five `slot_type` values average between 54.9 and
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

## 5. Method

### 5.1 Two prediction stages

Because dirtiness arrives late, the module trains two models on disjoint feature sets:

| Stage | Features | Available when |
|---|---|---|
| Planning | vehicle size, `interior_clean` | the booking is taken |
| On-site | the above plus dirtiness and its size interaction | the crew has seen the car |

Using dirtiness in the planning-time model would be leakage, and would produce a model that
benchmarks well and fails in deployment. Post-job columns — `duration_minutes`,
`late_minutes`, `rating`, `revenue` — are outcomes rather than inputs and are excluded from
both stages by construction, a property enforced by a test rather than by convention.

### 5.2 Model families

Three families were compared at each stage against two baselines: a global mean, a
per-vehicle-size group mean, a saturated cell mean, linear regression with the
size × dirtiness interaction, and gradient boosting.

Every split-dependent number in this paper is the average over **ten seeds**, reported with
its standard deviation. A single split would not distinguish these models from one another,
as Section 6.1 shows. Seed 7, which matches the dataset generator, is among the ten and is
the one used for the published per-scenario figures.

### 5.3 Prediction intervals

Point estimates are inadequate for capacity planning, so each scenario carries a 90%
interval from residual quantiles. These are calibrated on a split disjoint from both the
fitting and test splits — a 60/20/20 arrangement. Calibrating and measuring coverage on the
same rows would report the nominal level back by construction rather than measuring
anything.

### 5.4 Tank capacity and refills

Capacity is evaluated by resampling observed per-job consumption 20,000 times and asking how
often *n* jobs actually fit, rather than dividing capacity by the mean. Refills are counted
by walking each crew-day in arrival order and topping up before any job the remaining water
cannot cover, assuming each day starts with a full tank.

### 5.5 Choosing the best set of jobs

Capacity analysis says how many jobs fit; it does not say *which*. Given a crew-day's
bookings and a tank, the module selects a subset by three methods: serving in booked order
until the tank cannot cover the next job (the manager's default, and the baseline),
greedily taking the highest revenue per litre, and an exact 0/1 knapsack solved by dynamic
programming over integer decilitres. Revenue is the objective rather than a feature — it
equals the booking's quoted `total_price`, so it is known when the plan is made and is
never used to predict water.

Each method is run from three planning bases: actual consumption (an oracle no planner can
reach), the planning-time model's point estimate, and the upper end of its 90% interval.
Selection uses the planning basis; feasibility is judged against actual consumption. The
gap between the two is what a real plan is exposed to.

## 6. Results

### 6.1 Prediction accuracy

Mean and standard deviation over ten seeds:

| Stage | Model | MAE (L) | RMSE (L) | R² |
|---|---|---|---|---|
| Baseline | global mean | 11.152 ± 0.062 | 13.626 ± 0.079 | −0.000 ± 0.000 |
| Baseline | per-vehicle-size mean | 8.922 ± 0.067 | 10.914 ± 0.067 | 0.358 ± 0.006 |
| Planning | cell mean | **5.897 ± 0.038** | 7.276 ± 0.043 | **0.715 ± 0.004** |
| Planning | linear | 5.897 ± 0.038 | 7.277 ± 0.043 | 0.715 ± 0.004 |
| Planning | gradient boosting | 5.896 ± 0.038 | 7.277 ± 0.043 | 0.715 ± 0.004 |
| On-site | cell mean | **2.397 ± 0.014** | 2.997 ± 0.016 | **0.952 ± 0.001** |
| On-site | linear | 2.397 ± 0.015 | 2.996 ± 0.017 | 0.952 ± 0.001 |
| On-site | gradient boosting | 2.397 ± 0.014 | 2.997 ± 0.016 | 0.952 ± 0.001 |

The three families are indistinguishable, and the ten-seed spread is what makes that
statement defensible rather than merely apparent: they differ by 0.001 L while the
seed-to-seed standard deviation is 0.038 L at planning time — the noise between splits is
roughly forty times the gap between models. Reported from one split, the ranking between
them would be an artefact of which rows happened to land in the test set. This
is not a disappointing result but an informative one: the underlying structure is a small,
fully-populated contingency table, with 6 cells at planning time and 24 on site, each
supported by hundreds to thousands of observations. Once the correct features are present
there is nothing left for a flexible model to find. Accordingly, model selection takes the
simplest family within 1% of the best MAE rather than the raw minimum, which selects the
cell mean at both stages. Selecting by raw argmin would have shipped a gradient-boosting
ensemble for a 0.0003 L improvement.

The on-site RMSE of 3.00 L sits at the noise floor identified in the EDA, meaning the on-site
model extracts essentially all available signal. Measured interval coverage on the held-out
test split is 0.8985 ± 0.0053 at planning time and 0.9000 ± 0.0052 on site over ten seeds,
against a 0.90 nominal level.

The gap between the two stages quantifies the cost of not knowing dirtiness: MAE roughly
doubles, from 2.40 L to 5.90 L, and the interval widens from about ±5 L to about ±12 L.

### 6.2 Tank capacity

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

These capacities are stable: repeating the resampling under ten different seeds returns the
same 2 / 4 / 5 jobs at every service level, so the figures are a property of the consumption
distribution rather than of one draw.

### 6.3 Refill frequency

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

### 6.4 The best set of jobs

Share of all jobs and all revenue captured, and the share of crew-days where the plan's
actual consumption exceeded the tank:

| Tank | Basis | Method | Jobs | Revenue | Overflow |
|---|---|---|---|---|---|
| 200 L | oracle | booked order | 59.3% | 58.5% | 0.0% |
| 200 L | oracle | exact knapsack | 63.1% | 71.7% | 0.0% |
| 200 L | point | booked order | 59.0% | 58.3% | 5.9% |
| 200 L | point | value density | 61.1% | 70.3% | 8.1% |
| 200 L | point | exact knapsack | 61.8% | 71.0% | **11.9%** |
| 200 L | safe | exact knapsack | 52.3% | 61.9% | **0.0%** |
| 280 L | point | exact knapsack | 78.8% | 84.8% | 10.5% |
| 280 L | safe | exact knapsack | 68.9% | 77.0% | 0.0% |
| 350 L | point | exact knapsack | 87.8% | 91.6% | 7.0% |
| 350 L | safe | exact knapsack | 79.4% | 85.4% | 0.0% |

Three results, in increasing order of interest.

**Optimising by value buys revenue, not jobs.** On the 200 L van the exact knapsack
captures 13.2 points more revenue than booked order for only 3.8 points more jobs, by
preferring jobs worth more per litre. The operational gain is in what is served, not how
much.

**Exact optimisation barely beats greedy.** Value-density greedy reaches 70.9% of revenue
against the knapsack's 71.7% — about 99% of optimal. Crew-days contain a median of four
jobs, and knapsack instances that small are rarely hard. The exact solver is worth building
in order to *know* the greedy rule is sufficient; it is not worth deploying over it.

**Better optimisation makes the plan more fragile.** This is the result we did not expect.
Planning on point predictions, booked order overflows the 200 L tank on 5.9% of crew-days,
but the exact knapsack overflows on 11.9% — optimising doubles the failure rate. Packing a
tank to its limit consumes exactly the slack that absorbed prediction error; a loose plan
is accidentally robust. Planning instead on the upper end of the 90% interval removes
overflow entirely, at a cost of roughly ten points of jobs and revenue.

That trade is the module's central practical claim: an optimiser fed point estimates
optimises the mean day and fails the bad one. The interval is not decoration on the
prediction, it is what makes the optimiser safe to use.

### 6.5 Sustainability comparison

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

## 7. Limitations

- **Simulated data.** Every figure describes a generated dataset with known structure. Real
  consumption would carry measurement error and operator variation that this data lacks by
  construction.
- **The noise floor may be an artefact.** The uniform ≈3.0 L within-cell scatter is a
  property of the generator. Real jobs would likely show heteroscedasticity that this
  analysis would then be wrong to exclude.
- **Refill counts assume water is always available.** No travel time to a water source and no
  queueing is modelled; refills are counted, not costed.
- **Water for travel and crew use is outside scope.** Only per-job consumption is modelled.
- **The job selection assumes a known, droppable day.** All of a crew-day's bookings are
  treated as known before the day starts and as free to drop. In reality bookings arrive
  over time, and refusing a confirmed booking carries a customer cost this model does not
  price. The figures are therefore an upper bound on what selection can achieve.
- **Selection plans one tank-load and ignores refills.** The two are analysed separately;
  a combined model would decide when to refill and what to serve jointly.
- **Revenue is the only objective.** A real operation would weigh customer retention,
  fairness across crews, and travel distance alongside it.
- **The sustainability benchmarks are US figures** applied to an Indian operating context,
  and different sources define freshwater use differently — with and without reclaim, make-up
  water against total applied. The table reports the definitional split rather than averaging
  across it.

## 8. Conclusions

The module's most transferable finding is methodological. The largest available predictor was
hidden inside a delimited string rather than exposed as a column, and the strongest predictor
overall was unavailable at prediction time. Neither is visible from a correlation matrix, and
both determined the shape of the solution more than any modelling choice did. Once the
features were right, three model families of very different capacity performed identically —
which suggests that effort spent on feature semantics returned more here than effort spent on
model selection would have.

The optimisation result points the same way. The exact knapsack was worth building mainly
to establish that a greedy rule already reaches 99% of it, and the more consequential
finding was not about solution quality at all: optimising against point predictions doubled
the rate at which plans overflowed the tank. A better optimiser made the operation less
reliable, because packing to the limit spends the slack that had been quietly absorbing
prediction error. Uncertainty and optimisation cannot be treated as separate concerns —
the optimiser has to consume the interval, not the point.

Operationally, the module's recommendation is that capacity be quoted as an interval with a
stated service level, that refill frequency, not jobs per tank, be treated as the planning
quantity, and that any selection run against the interval's upper bound rather than its
centre. Downstream consumers should take the distribution rather than the mean;
`INTEGRATION.md` records that contract.

## 9. Reproducing

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe src/train.py
.venv/Scripts/python.exe -m pytest tests -q
```

Seed 7 throughout, matching the dataset generator. `src/train.py` regenerates every figure in
sections 6.1 to 6.5 and appends each run to `experiments.csv`.

## References

[1] I. Monney, E. A. Donkor, and R. Buamah, "Clean vehicles, polluted waters: empirical
estimates of water consumption and pollution loads of the carwash industry," *Heliyon*,
vol. 6, no. 5, e03952, 2020, doi: 10.1016/j.heliyon.2020.e03952.

[2] K. Maciejewska and M. Reizer, "Evaluating the impacts of different car washing systems on
carbon footprint: insights from Poland," *Sustainability*, vol. 17, no. 4, art. 1384, 2025,
doi: 10.3390/su17041384.

[3] R. N. Zaneti, R. Etchepare, and J. Rubio, "Car wash wastewater treatment and water reuse
— a case study," *Water Science and Technology*, vol. 67, no. 1, pp. 82–88, 2013,
doi: 10.2166/wst.2012.492.

[4] E. A. Donkor, T. A. Mazzuchi, R. Soyer, and J. A. Roberson, "Urban water demand
forecasting: review of methods and models," *Journal of Water Resources Planning and
Management*, vol. 140, no. 2, pp. 146–159, 2014,
doi: 10.1061/(ASCE)WR.1943-5452.0000314.

[5] A. J. Kleywegt and J. D. Papastavrou, "The dynamic and stochastic knapsack problem,"
*Operations Research*, vol. 46, no. 1, pp. 17–35, 1998, doi: 10.1287/opre.46.1.17.

[6] J. D. Papastavrou, S. Rajagopalan, and A. J. Kleywegt, "The dynamic and stochastic
knapsack problem with deadlines," *Management Science*, vol. 42, no. 12, pp. 1706–1718,
1996, doi: 10.1287/mnsc.42.12.1706.

[7] J. Han, K. Lee, C. Lee, K.-S. Choi, and S. Park, "Robust optimization approach for a
chance-constrained binary knapsack problem," *Mathematical Programming*, vol. 157, no. 1,
pp. 277–296, 2015, doi: 10.1007/s10107-015-0931-0.

[8] A. N. Elmachtoub and P. Grigas, "Smart 'predict, then optimize'," *Management Science*,
vol. 68, no. 1, pp. 9–26, 2022, doi: 10.1287/mnsc.2020.3922.

[9] J. Lei, M. G'Sell, A. Rinaldo, R. J. Tibshirani, and L. Wasserman, "Distribution-free
predictive inference for regression," *Journal of the American Statistical Association*,
vol. 113, no. 523, pp. 1094–1111, 2018, doi: 10.1080/01621459.2017.1307116.

[10] R. Koenker and G. Bassett, "Regression quantiles," *Econometrica*, vol. 46, no. 1,
pp. 33–50, 1978, doi: 10.2307/1913643.

[11] K. Braekers, K. Ramaekers, and I. Van Nieuwenhuyse, "The vehicle routing problem: state
of the art classification and review," *Computers & Industrial Engineering*, vol. 99,
pp. 300–313, 2016, doi: 10.1016/j.cie.2015.12.007.

### Data and non-academic sources

[12] US Environmental Protection Agency, *WaterSense at Work: Best Management Practices for
Commercial and Institutional Facilities*, Section 5.5 Vehicle Washing, October 2012. Figures
attributed there to Chris Brown. Reclaim figures are freshwater make-up, not total water
applied.

[13] US Environmental Protection Agency, WaterSense, *Who Needs a Hose?* Publishes a
6 gal/min garden-hose flow rate; the per-wash figure used here is derived from that rate.

[14] International Carwash Association, *Water Use, Evaporation, and Carryout in Professional
Carwashes*, 2018. Measurements at 12 sites (6 conveyor, 6 in-bay) during 2017. An industry
body reporting on its own sector.

[15] Doorstep simulated dataset, Track A, generated by `data/raw/generate_doorstep.py` with
seed 7.
