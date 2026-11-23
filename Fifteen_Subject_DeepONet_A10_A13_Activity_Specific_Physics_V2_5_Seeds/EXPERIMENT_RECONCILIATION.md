# Experiment rationale and reporting boundary

This V2 experiment asks whether one unified A10-A13 DeepONet benefits from a
globally calibrated CartPole constraint when each activity has a future-free
anatomical axis and its own controller head.

It is not an exact replication of either the earlier favorable 70-trial A11
Model B pipeline or the completed 64-trial strict-primary A11 V3 calibration.
Those results remain valid only for their respective datasets, preprocessing,
architectures, and selection protocols.

The controlled comparison here is internal to V2. All lambda arms start from
the same model state and use the same training protocol. Lambda is chosen using
two validation subjects and a subject-activity-balanced forecast endpoint;
held-out test subjects are accessed only after selection.

## Full five-seed reporting language

> Across five matched seeds and 15 held-out subjects, validation-selected V2
> improved normalized forecast MSE by 2.76%, theta RMSE by 0.88%, and CoM-x
> RMSE by 0.97% relative to matched from-scratch lambda=0. Horizontal physics
> residual RMSE improved by 22.62%. The forecasting differences were not
> statistically significant: all primary confidence intervals included zero
> and all Holm-adjusted p-values were 1.0. Activity-level results were
> heterogeneous: A12 and A13 favored selected V2 in aggregate, A10 was neutral,
> and A11 favored lambda=0. The next step is a unified A12+A13-only physics-mask
> confirmation before any production refit.

## What may and may not be claimed

Supported:

- V2 passed the matched-initialization, subject-split, target-pairing, and
  finite-history audits.
- Validation-selected V2 has a modest descriptive overall advantage.
- Physics substantially improves horizontal equation consistency.
- The aggregate activity pattern motivates masking direct physics loss off for
  A10 and A11 and retaining it for A12 and A13 in a follow-up.

Not supported:

- A statistically confirmed V2 forecasting advantage.
- A single locked production lambda from the current selection counts.
- A claim that every activity benefits from physics.
- Reusing the 25 cross-validation checkpoints as one final synthetic-data
  generator.
- Treating lower physics residual as proof of better forecasts.

The earlier favorable A11 Model B result and this V2 result are not mutually
exclusive. They answer different questions. The honest interpretation is that
physics benefit is pipeline- and activity-dependent, and production choices
must follow the result of the targeted mask experiment.

