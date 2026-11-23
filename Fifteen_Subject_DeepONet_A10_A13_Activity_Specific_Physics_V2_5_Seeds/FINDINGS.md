# A10-A13 activity-specific physics V2: full five-seed findings

## Decision

The validation-selected activity-specific V2 condition has a small descriptive
advantage over its matched from-scratch lambda=0 condition: normalized forecast
MSE improved 2.76%, theta RMSE 0.88%, and CoM-x RMSE 0.97%. Physics also
reduced horizontal residual RMSE by 22.62%.

This is **not a statistically confirmed forecasting advantage**. The
subject-bootstrap confidence intervals include zero, the subject win/loss
counts are close, and all Holm-adjusted p-values are 1.0. Lambda selection is
unstable. The forecasting result must be reported as descriptive. For the
synthetic-data stage, the project decision is nevertheless to retain the
all-head direct-physics model and select two validation-ranked generators,
followed by the established trajectory-quality gate.

The full result reverses the seed-1 A13 warning: A13 is favorable in the
five-seed aggregate. A11, not A13, is the activity that consistently favors the
no-physics comparator in the aggregate.

## Primary held-out-subject comparison

Positive improvement means `matched lambda=0 - selected V2`. The independent
unit is one held-out subject after averaging its five matched optimization
seeds (`n=15`).

| Metric | Selected V2 | Matched lambda=0 | Mean improvement | Relative | Wins V2/N | Bootstrap 95% CI | Holm p |
|:--|--:|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.5870 | 3.6887 | +0.1017 | +2.76% | 8/7 | [-0.0659, +0.3102] | 1.0000 |
| Theta RMSE | 23.0432 degrees | 23.2487 degrees | +0.2056 degrees | +0.88% | 8/7 | [-0.1720, +0.6486] | 1.0000 |
| CoM-x RMSE | 31.3921 cm | 31.6980 cm | +0.3059 cm | +0.97% | 9/6 | [-0.2367, +0.8814] | 1.0000 |

The median subject improvements were much smaller than the means: +0.0007
normalized MSE, +0.0365 degrees theta RMSE, and +0.1140 cm CoM-x RMSE. This
shows that a few larger subject gains drive part of the average advantage.

## Seed stability

| Seed | Normalized MSE | Theta RMSE | CoM-x RMSE | Reading |
|:--|--:|--:|--:|:--|
| 1 | -1.90% | +0.41% | +0.03% | Mixed |
| 2 | +1.66% | +0.74% | +1.05% | V2 favored |
| 3 | +4.23% | +2.01% | +1.98% | V2 favored |
| 4 | +8.82% | +1.20% | +1.82% | V2 favored |
| 5 | -0.23% | -0.06% | -0.25% | Slight lambda=0 advantage |

Three of five seeds favor V2 on all three endpoints, but the effect is not
uniform. Seed 4 supplies the largest normalized-MSE gain; seed 5 is essentially
neutral/slightly negative.

## Activity results

These descriptive rows first average trials within each held-out
subject-activity-seed cell. They do not isolate a causal per-activity physics
effect because one global lambda was selected for the entire unified model.

| Activity | Selected / no-physics normalized MSE | Relative | Theta RMSE relative | CoM-x RMSE relative | Interpretation |
|:--|--:|--:|--:|--:|:--|
| A10 backfall | 1.6844 / 1.6899 | +0.32% | +0.31% | +0.22% | Neutral |
| A11 frontfall | 2.4948 / 2.4662 | -1.16% | -1.13% | -0.82% | Lambda=0 favored |
| A12 leftfall | 4.0339 / 4.1581 | +2.99% | +2.43% | +2.00% | Strongest broadly positive activity |
| A13 rightfall | 5.1385 / 5.3953 | +4.76% | +0.63% | +1.16% | Positive aggregate, seed-dependent |

Activity-by-seed signs remain heterogeneous:

- A10 improves on all three endpoints in seeds 1-3 and worsens in seeds 4-5.
- A11 improves on all three only in seed 1; its five-seed aggregate favors
  lambda=0.
- A12 improves on all three in seeds 3-4, is mixed in seeds 1-2, and is almost
  neutral/slightly worse in seed 5.
- A13 improves on all three in seeds 3-5, is mixed in seed 2, and worsens in
  seed 1.

These patterns must remain visible in reporting, but they are not being used
to remove physics from A10 or A11 and are not a basis for four separate
trajectory networks.

## Lambda selection and validation-to-test transfer

| Selected lambda | 0 | 1e-4 | 1e-3 | 1e-2 |
|:--|--:|--:|--:|--:|
| Seed-fold count | 9 | 2 | 5 | 9 |

Nonzero physics was selected in 16/25 seed-folds. Among those 16 selections,
held-out normalized MSE improved in 9 and worsened in 7. The mean nonzero-fold
test improvement was +1.63%, but the median was only +0.06%. Validation gain
and test gain were positively associated (`r=0.61`) but transfer was not
reliable fold by fold.

Across all 25 validation splits, the mean best validation MSEs for fixed
lambdas were:

| Lambda | Mean validation MSE | Mean paired gain vs lambda=0 |
|:--|--:|--:|
| 0 | 2.1407 | reference |
| 1e-4 | 2.1381 | +0.11% |
| 1e-3 | 2.1282 | +0.51% |
| 1e-2 | 2.1287 | +0.47% |

The differences are too small to lock a production lambda from this table.
The test performance of a globally fixed lambda was not evaluated by the
current selected-vs-matched comparison.

## Subject heterogeneity

For normalized MSE averaged over five seeds, the largest V2 improvements were
S44 (+1.181), S43 (+0.602), and S56 (+0.390). The largest degradations were S45
(-0.401), S46 (-0.279), and S59 (-0.165). Theta and CoM-x show a similar
pattern: S43, S44, and S56 benefit most, while S45 and S46 are among the main
losses. This heterogeneity is why the overall mean is positive while the
subject win count remains only 8/7 or 9/6.

## Physics residuals

| Residual endpoint | Selected V2 | Matched lambda=0 | Relative improvement |
|:--|--:|--:|--:|
| Angular residual RMSE | 15.2266 | 15.3236 | +0.63% |
| Horizontal residual RMSE | 189.3938 | 244.7598 | +22.62% |

Horizontal residual RMSE improved in every seed. Activity-balanced horizontal
residual improvements were +25.11% for A10, +18.82% for A11, +24.53% for A12,
and +23.04% for A13. Forecast and residual outcomes must remain separately
reported: better equation consistency alone is not sufficient evidence of
better held-out trajectories.

## Protocol and integrity audit

- Archive integrity passed.
- 100/100 full candidates are present: 4 lambdas x 5 folds x 5 seeds.
- 25/25 selected evaluations and 25/25 matched lambda=0 evaluations are present.
- All four arms share an identical initialization SHA-256 within every seed-fold.
- Pre-training validation forecast loss is exactly equal across arms within
  every seed-fold.
- All selection files choose the minimum validation metric with the predefined
  smaller-lambda tie break.
- Training, validation, and test subject roles are disjoint in every manifest.
- All 21,864 candidate-history rows are finite.
- All 1,285 paired prediction files have exactly identical `time_s`,
  `target_theta_rad`, and `target_x_m` arrays (maximum absolute difference 0).
- Selection records indicate that held-out test data were not accessed before
  lambda/checkpoint selection.

No implementation or pairing failure was found that explains the modest size
of the forecasting effect.

## Reconciliation with earlier A11 work

This result does not erase the earlier favorable 70-trial A11 Model B result.
It tests a different strict-primary dataset, unified A10-A13 architecture,
future-free activity axes, four controller heads, balanced objective, and
two-subject validation rule. Within this V2 experiment, A11 favors lambda=0;
claims from the earlier A11 pipeline remain limited to that earlier pipeline.

## Synthetic-generation decision

Use the unified A10-A13 model with direct CartPole physics active for **all four
activities**. No A10/A11 exception and no A12+A13-only mask experiment will be
run. The matched lambda=0 models remain comparison controls and will not be
used to generate the main synthetic dataset.

For each common training/validation scope:

1. Restrict the generator pool to all-head models with nonzero physics weight.
2. Rank candidates only by validation subject-activity-balanced forecast MSE.
3. Retain the best two validation models; do not select from held-out test
   performance.
4. Generate candidate trajectories with both models.
5. Apply the established trajectory-quality gate before admitting any sample:
   finite/time checks, activity direction and phase order, plausible ranges,
   smoothness, endpoint/contact behavior, physics residual thresholds,
   duplicate checks, and agreement between the two selected models.

Raw validation losses from different folds should not be globally ranked as if
the validation subjects were the same. Top-two selection must occur within a
common validation split or use a fold-balanced aggregate rule.

A14 continues to use the separate selected rotation-physics DeepONet. Its
physics comparison does not need to be repeated, although a production refit
is still needed for the final generation scope. For subject-held-out detector
experiments, both the A10-A13 and A14 generators must be trained/selected using
only the detector fold's training subjects.

