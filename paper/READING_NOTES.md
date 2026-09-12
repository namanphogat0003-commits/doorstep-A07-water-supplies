# Reading notes — literature review

The bibliographic details of every reference in `A7_water_and_supplies.md` were verified
against Crossref, so the citations themselves are correct. **The papers have not all been
read in full.** Section 2's characterisations are drawn from titles, verified abstracts and
publisher summaries.

Before the viva, each paper needs a real read. The rubric asks for papers *connected* to the
work, not listed, and the viva questions each member individually.

## Status

| Ref | Paper | Abstract verified | Full text read | Owner |
|---|---|---|---|---|
| [1] | Monney et al. 2020, carwash water & pollution | no — none in Crossref | no | |
| [2] | Maciejewska & Reizer 2025, carbon footprint | yes | no | |
| [3] | Zaneti et al. 2013, reclamation case study | yes | no | |
| [4] | Donkor et al. 2014, water demand forecasting review | no | no | |
| [5] | Kleywegt & Papastavrou 1998, stochastic knapsack | no | no | |
| [6] | Papastavrou et al. 1996, knapsack with deadlines | no | no | |
| [7] | Han et al. 2015, chance-constrained knapsack | no | no | |
| [8] | Elmachtoub & Grigas 2022, Smart Predict-then-Optimize | yes | no | |
| [9] | Lei et al. 2018, distribution-free predictive inference | no | no | |
| [10] | Koenker & Bassett 1978, regression quantiles | no | no | |
| [11] | Braekers et al. 2016, VRP review | no | no | |

## Claims to check on reading

- **[1]** Section 2 says only that it establishes per-vehicle consumption must be measured.
  If the paper reports per-vehicle-type litres, add them — they would strengthen §6.5.
- **[4]** The claim that "method complexity is a weak predictor of accuracy" is the pivot for
  our argument that three model families tie. Confirm the review actually says this.
- **[8]** Our overflow result is presented as an empirical instance of the SPO argument.
  Confirm the framing matches; the paper is about linear objectives with known constraints,
  whereas our uncertainty is in the *constraint*, not the objective. This difference is worth
  stating explicitly in the paper if it holds.
- **[11]** Confirm the claim that most capacitated VRP variants treat demand as deterministic.

## Two papers still worth adding

The rubric asks for 8–10; there are 11 here. If any are dropped on reading, candidates to
replace them: a field-service / technician routing paper with stochastic service
requirements, and a newsvendor or safety-stock treatment of planning to a quantile.
