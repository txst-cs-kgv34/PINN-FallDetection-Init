# Findings — pending matched from-scratch A11 calibration V3

Results are pending. Run the seed-1 pilot before the five-seed confirmation.

## Scientific question

When all optimization conditions are matched from initialization onward, does
a validation-selected nonzero CartPole weight improve held-out A11 forecasting
over λ=0 in the current 64-trial Physics-Ready pipeline?

## Why the previous results are not a contradiction

The earlier Model B full-fall comparison reported a descriptive physics
advantage: normalized forecast RMSE, theta RMSE, and CoM-x RMSE were lower for
physics in 12 of 15 held-out subjects. The corresponding improvements were
8.15%, 5.45%, and 8.04%. The Holm-adjusted p-values were 0.0646, 0.1354, and
0.0646, respectively. Therefore the defensible conclusion was “promising and
consistent descriptive advantage,” not “proven universal advantage.”

The current diagnostic uses 64 strict-primary trials instead of the older 70,
a unified Physics-Ready coordinate pipeline instead of mixed legacy/audit
conversion, and additional conditioning. It is a new domain and preprocessing
test, not a direct rerun of the earlier experiment.

The V2 warm-start pilot was additionally confounded: λ=0 remained frozen at a
validation-selected optimum while nonzero candidates restarted AdamW and
continued optimizing the data loss. All 15 nonzero candidates had their best
validation score at epoch 0. Their epoch-1 degradation occurred while physics
weights were still extremely small, so that pilot cannot identify physics as
the cause of the degradation.

## What V3 fixes

- λ=0, 1e-4, 1e-3, and 1e-2 start from an identical state per seed-fold.
- All arms train from scratch with identical optimizers, learning rates,
  batches, schedules, minimum training periods, patience, and checkpoint rules.
- λ is selected using the validation subject only.
- Test data are evaluated only after selection.
- Selected V3 is paired against the newly trained matched λ=0 arm.
- Initialization hashes and pre-training validation values are checked.

## Advisor-facing statement

> The earlier result was not fabricated: in its matched 70-trial pipeline,
> physics had lower descriptive error for 12 of 15 subjects on each primary
> endpoint. We also reported that the Holm-adjusted tests did not cross 0.05.
> The newer experiment changed the accepted-trial set, coordinate construction,
> and conditioning, so its different outcome is a reproducibility and domain-
> sensitivity finding rather than evidence that the earlier numbers were
> false. Our first calibration pilot also had a warm-start continuation
> confound. We are now running a matched from-scratch four-weight experiment to
> isolate the effect of the CartPole residual in the current data pipeline.

## Result fields to complete after the pilot

- selected λ for each fold;
- matched initialization audit;
- validation trajectories across all four weights;
- selected V3 versus matched λ=0 held-out metrics;
- subject wins, bootstrap intervals, Wilcoxon tests, and Holm correction;
- angular/horizontal residual changes and physics/data gradient ratios;
- go/no-go decision for seeds 2–5.
