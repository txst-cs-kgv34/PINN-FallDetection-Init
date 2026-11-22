# Reconciling the A11 physics results

## What was established earlier

In the matched full-fall Model B comparison, physics had lower five-seed
subject-mean error for 12 of 15 held-out subjects on each primary endpoint.

| Endpoint | Physics | No physics | Reduction | Subjects favoring physics | Holm p |
|:--|--:|--:|--:|--:|--:|
| Normalized forecast RMSE | 1.5883 | 1.7292 | 8.15% | 12/15 | 0.0646 |
| Theta RMSE | 21.4843° | 22.7223° | 5.45% | 12/15 | 0.1354 |
| CoM-x RMSE | 28.4642 cm | 30.9527 cm | 8.04% | 12/15 | 0.0646 |

These numbers support a promising descriptive advantage in that experiment.
Because the adjusted p-values exceeded 0.05, they do not establish a universal
or pipeline-independent effect.

## What changed later

The current Physics-Ready A11 diagnostic is not an exact replication:

- 64 strict-primary A11 trials replaced the earlier 70 accepted trials;
- unified Physics-Ready processing replaced mixed legacy-pole/audit conversion;
- activity and fall-direction conditioning were added;
- coordinate and accepted-trial decisions changed with the new data pipeline.

The six trials omitted from the current strict-primary set are:

- `S48A11T01`, `S48A11T02`, `S48A11T05`;
- `S56A11T01`, `S56A11T03`, `S56A11T04`.

Therefore a reversed mean in the newer experiment shows sensitivity to the
pipeline/data definition. It does not make the earlier recorded comparison
false.

## Why the warm-start pilot was inconclusive

The V2 pilot compared a frozen validation-optimal λ=0 checkpoint with nonzero
arms that resumed AdamW training. All nonzero candidates selected epoch 0 as
their best validation checkpoint, and degradation began at epoch 1 while the
ramped physics coefficients were tiny. Continued training, optimizer reset,
and physics were inseparable.

## What V3 isolates

V3 trains λ=0, 1e-4, 1e-3, and 1e-2 from the same state and with the same
optimization protocol. It is the first calibration that can cleanly determine
whether a nonzero CartPole weight helps the current 64-trial pipeline.

## Reporting language

Use this wording after the completed five-seed V3 confirmation:

> The earlier matched Model B experiment showed a consistent descriptive
> physics advantage across 12 of 15 held-out subjects, although adjusted
> subject-level tests were not below 0.05. A later Physics-Ready A11 diagnostic
> changed the trial set, processing, and conditioning and did not reproduce the
> mean advantage. A warm-start calibration was inconclusive because continued
> optimization was not matched. We therefore designed a matched from-scratch
> four-weight calibration to isolate the residual's effect in the current
> pipeline. Across five seeds, validation selected nonzero physics in 17 of 25
> fold-seed models, but held-out mean normalized MSE, theta RMSE, and CoM-x RMSE
> were 4.74%, 1.20%, and 1.58% worse than matched λ=0, with no corrected test
> below 0.05. Horizontal equation consistency improved without a forecasting
> benefit. We therefore report the earlier advantage as pipeline-specific and
> use the current matched result to redesign activity-specific planar physics.
