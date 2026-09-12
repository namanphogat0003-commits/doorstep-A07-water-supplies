# A7 — Water and Supplies: Integration

What this module hands to the rest of Track A, and how to consume it correctly.

All figures below are computed from the Doorstep simulated dataset (39,302 completed jobs,
1 Jan 2024 – 31 Dec 2025) by `src/train.py`. Regenerate everything with:

```bash
python src/train.py
```

## What A7 provides

| File | Grain | Answers |
|---|---|---|
| `results/consumption_model.csv` | one scenario | how much water will this job take |
| `results/tank_capacity.csv` | one vehicle | how many jobs fit in one tank |
| `results/refill_planning.csv` | one vehicle | how often a crew must refill during a day |

## consumption_model.csv

Two prediction stages, because `dirtiness_level` is only observed when the crew arrives.
Pick the stage by **what is known at the moment of the call**:

| Stage | Known inputs | Use when | Test MAE |
|---|---|---|---|
| `planning` | `vehicle_size`, `interior_clean` | routing, scheduling, quoting — anything before arrival | 5.93 L |
| `onsite` | the above plus `dirtiness_level` | the crew is at the vehicle | 2.40 L |

Join on the columns `vehicle_size`, `interior_clean` and, for `onsite`, `dirtiness_level`.
`dirtiness_level` is blank on `planning` rows.

`interior_clean` is **not** `slot_type`. Derive it from `bookings.items`, which is a
`|`-separated list:

```python
interior_clean = bookings["items"].str.contains("interior_clean", na=False).astype(int)
```

It is present on 27.9% of jobs, sold across every slot type, and adds +18.0 L. A consumer
that keys off `slot_type` will miss it entirely — all five slot types average 55.0–55.8 L.

Each row carries `predicted_litres` with `pi_low_litres` / `pi_high_litres` at
`interval_level` 0.90, plus `n_observed`, `observed_mean_litres` and `observed_sd_litres`
for the cell. **Use the interval, not just the point estimate.** At planning time the band
is roughly ±12 L because dirtiness is unresolved; on site it narrows to about ±5 L.

## tank_capacity.csv and refill_planning.csv

Tank sizes come from `data/raw/vehicles.csv`: small_van 200 L, ev_van 280 L, large_van 350 L.

Maximum jobs per tank, by service level:

| Vehicle | 90% | 95% | 99% | mean-based |
|---|---|---|---|---|
| small_van (200 L) | 3 | 2 | 2 | 3 — fits only 91% of the time |
| ev_van (280 L) | 4 | 4 | 3 | 5 — fits only 53% of the time |
| large_van (350 L) | 5 | 5 | 4 | 6 — fits only 70% of the time |

**Quote the service level with the number.** Dividing capacity by the 55.7 L mean ignores
the spread of per-job consumption and overstates what a tank actually covers.

One tank does not cover a working day. Crews average 4.7 jobs and 262 L per day (p95 544 L,
max 1,151 L over 8,342 crew-days), so refills are part of normal operation, not an
exception:

| Vehicle | mean refills/day | p95 | days needing none | one | two or more |
|---|---|---|---|---|---|
| small_van | 0.88 | 3 | 38.9% | 40.3% | 20.9% |
| ev_van | 0.45 | 2 | 61.3% | 33.0% | 5.7% |
| large_van | 0.26 | 1 | 75.8% | 22.9% | 1.3% |

Refills are counted by walking each crew-day in arrival order and topping up before any job
the remaining water cannot cover, starting each day full.

## For A12 (fleet trade-offs)

Take the **distribution**, not the mean. The relevant inputs are `observed_sd_litres` per
scenario in `consumption_model.csv`, and the refill frequency above — a smaller tank is not
simply "fewer jobs per fill", it is a recurring interruption to the working day that costs
travel time to a water source. The gap between small_van and large_van is 0.88 against 0.26
refills per crew-day.

## Upstream dependencies

Reads `data/raw/jobs_done.csv`, `bookings.csv` and `vehicles.csv` only. `data/raw` is
immutable. If the dataset is reseeded, every figure in this document changes and
`src/train.py` must be re-run.

## Assumptions and limits

- **Simulated data.** Cite as "Doorstep simulated dataset, Track A". Not real operations.
- **`dirtiness_level` cannot be predicted at booking time.** It is uncorrelated with rain
  (−0.007) and temperature (+0.001), flat across months, and within-customer variation
  (sd 0.89) swamps between-customer variation (sd 0.28). Do not ask A7 for an on-site-grade
  figure before arrival, and do not feed `dirtiness_level` into a planning-time model — that
  is leakage.
- **Post-job columns are excluded** — `duration_minutes`, `late_minutes`, `rating` and
  `revenue` are outcomes, not features.
- **Water for travel or crew use is not modelled.** Figures cover per-job consumption only.
- **Refill counts assume a full tank at the start of each crew-day** and that a refill
  restores full capacity.
