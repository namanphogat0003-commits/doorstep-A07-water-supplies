# Integration note — A7 Water and Supplies

Regenerate everything below with `python src/train.py` from the repository root.

## What I produce

All files live in `results/`, are rewritten on every run, and are reproducible from
`data/raw/`. Column definitions are in `results/README.md`.

| File | One row is | Key columns and units |
|---|---|---|
| `consumption_model.csv` | one scenario | `predicted_litres`, `pi_low_litres`, `pi_high_litres` (litres, 90% interval); `n_observed`, `observed_mean_litres`, `observed_sd_litres` |
| `tank_capacity.csv` | one vehicle | `max_jobs_at_90pct` / `_95pct` / `_99pct` (whole jobs), `mean_based_jobs`, `p_mean_based_fits` |
| `refill_planning.csv` | one vehicle | `mean_refills_per_day`, `p95_refills_per_day`, `pct_days_no_refill` and siblings (percent of crew-days) |
| `tank_plan.csv` | one tank × basis × method | `jobs_served_pct`, `revenue_captured_pct`, `overflow_pct_of_crew_days` |
| `sustainability.csv` | one published benchmark | `benchmark_litres_per_wash`, `doorstep_pct_of_benchmark`, `source` |

**Update cadence:** on demand. There is no scheduled job — the figures change only when
`data/raw/` changes or the pipeline does.

### Picking a row from consumption_model.csv

Two prediction stages, because `dirtiness_level` is only observed when the crew arrives.
Pick by what is known at the moment of the call:

| Stage | Known inputs | Use when | Test MAE (10 seeds) |
|---|---|---|---|
| `planning` | `vehicle_size`, `interior_clean` | routing, scheduling, quoting — anything before arrival | 5.90 ± 0.04 L |
| `onsite` | the above plus `dirtiness_level` | the crew is at the vehicle | 2.40 ± 0.01 L |

Join on `vehicle_size`, `interior_clean` and, for `onsite`, `dirtiness_level`.
`dirtiness_level` is blank on `planning` rows.

`interior_clean` is **not** `slot_type`. Derive it from `bookings.items`:

```python
interior_clean = bookings["items"].str.contains("interior_clean", na=False).astype(int)
```

It is on 27.9% of jobs, sold across every slot type, and adds +18.0 L. All five slot types
average 54.9–55.8 L, so a consumer keying off `slot_type` will miss the effect entirely.

**Use the interval, not just the point estimate.** At planning time the band is roughly
±12 L because dirtiness is unresolved; on site it narrows to about ±5 L.

## What I consume

Only `data/raw/`, which is immutable and supplied by faculty. No other team's output is an
input to A7, so nothing upstream can block this module.

| File | Columns used | What I assume |
|---|---|---|
| `jobs_done.csv` | `booking_id`, `date`, `crew_id`, `arrival_time`, `water_litres`, `dirtiness_level`, `revenue` | `water_litres` is litres actually used on that job; `dirtiness_level` is recorded on arrival, not booked |
| `bookings.csv` | `booking_id`, `items`, `vehicle_size`, `total_price` | `items` is a `\|`-separated list containing `interior_clean` where sold |
| `vehicles.csv` | `vehicle_type`, `capacity_litres` | `capacity_litres` is usable tank volume, not gross |

## Assumptions that could break

1. **`dirtiness_level` is not knowable before arrival.** It is uncorrelated with rain
   (−0.007) and temperature (+0.001), flat across months, and the same customer varies more
   than customers differ from one another. If a future module (A14, photo check) can predict
   dirt level from a booking photo, the planning-time model becomes obsolete and its error
   roughly halves, from 5.90 L to 2.40 L. **That is the single change that would most improve
   A7.**
2. **Tank capacity is usable volume.** If `capacity_litres` is gross and usable volume is
   lower, every jobs-per-tank figure drops. A 10% reduction moves the 95% figures from
   2 / 4 / 5 to roughly 2 / 3 / 4.
3. **Crews start each day with a full tank.** All refill counts assume this. If vans start
   partly full, refills rise and `pct_days_no_refill` is optimistic.
4. **Water for travel and crew use is zero.** Only per-job consumption is modelled. Any
   fixed daily overhead shifts every crew-day figure up by that amount.
5. **Job selection assumes a crew-day's bookings are known in advance and free to drop.**
   Refusing a confirmed booking carries a customer cost that is not priced, so
   `tank_plan.csv` is an upper bound on what selection can achieve.
6. **The data is simulated.** The uniform ~3 L within-cell noise is a property of the
   generator. Real jobs would likely be heteroscedastic, which would widen intervals
   unevenly and change the service-level figures.

## Tested against

**Nothing yet — this is the honest state.**

| Team | Status |
|---|---|
| A12 (Fleet strategy) | Not tested. A12 consumes A7's output; their `fleet_options.csv` format has not been received, and A7's output has not been run through their code. |

A7 consumes no other team's file, so there is no upstream integration to test. The
outstanding work is confirming that A12 can read `consumption_model.csv` and
`refill_planning.csv` as produced. Until that happens this section stays as it is; a
"tested" claim here with no test behind it would be worse than an empty one.

## Known incompatibilities

1. **The ground-rules column contract does not match the supplied data.** Rule 1 specifies
   `staff_id`, `travel_km`, `requested_date` and `requested_slot`; the actual dataset uses
   `crew_id`, `distance_km`, `date` and `slot_time`, and `jobs_done.csv` carries
   `dirtiness_level` and `revenue`, which the rule does not list at all. A7 follows the
   supplied `data/raw/DATA_DICTIONARY.md`, since that is what the data actually is. Any team
   that coded against the guidebook column names rather than the dataset will not join
   cleanly to A7's output, and the mismatch is in the shared contract rather than in either
   module.
2. **A7 reports intervals; most consumers expect point estimates.** `consumption_model.csv`
   deliberately carries `pi_low_litres` and `pi_high_litres`. A consumer that reads only
   `predicted_litres` will plan to the mean and, per our own optimisation results, roughly
   double its rate of running a tank dry. This is a real incompatibility of expectations,
   not a formatting one.
3. **No per-booking output.** A7 publishes a scenario lookup, not one row per booking. A team
   wanting a per-`booking_id` prediction must join on the scenario columns themselves. Say so
   and we will publish a per-booking file instead.
