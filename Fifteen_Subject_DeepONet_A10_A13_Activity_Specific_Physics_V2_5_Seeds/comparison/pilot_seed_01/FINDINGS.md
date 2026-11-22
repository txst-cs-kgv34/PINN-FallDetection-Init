# A10-A13 activity-specific physics V2: seed-1 comparison

Positive improvement means `matched lambda=0 - selected V2`; positive values
favor selected V2.

| Metric | Selected V2 | Matched lambda=0 | V2 improvement | Relative | Subject wins V2/N/tie | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.6402 | 3.5723 | -0.0680 | -1.90% | 6/3/6 | 1.0000 |
| Theta RMSE | 22.2882 degrees | 22.3790 degrees | +0.0909 degrees | +0.41% | 5/4/6 | 1.0000 |
| CoM-x RMSE | 30.8745 cm | 30.8838 cm | +0.0093 cm | +0.03% | 5/4/6 | 1.0000 |

The pilot is near neutral overall and does not establish a forecasting
advantage. Six ties occur because folds 4 and 5 selected lambda=0. Validation
selected nonzero physics in folds 1-3, but normalized-MSE improvement
transferred to the test subjects only in fold 2.

## Activity results

| Activity | Normalized MSE | Theta RMSE | CoM-x RMSE |
|:--|--:|--:|--:|
| A10 | +2.71% | +2.21% | +1.17% |
| A11 | +2.70% | +0.77% | +1.31% |
| A12 | -0.32% | +3.12% | +2.52% |
| A13 | -7.39% | -5.14% | -5.94% |

A13 is consistently worse and is the main reason to retain activity-head
analysis in the full experiment.

## Residual result

Horizontal residual RMSE improved by 18.14% overall and 40.82% among subjects
whose folds selected nonzero physics. Angular residual RMSE was 0.21% worse
overall. The residual improvement did not translate into a reliable forecast
gain in this seed.

## Decision

The implementation audit passed. Complete seeds 2-5 unchanged. Treat the
five-seed comparison as the confirmatory result, then run activity-head
ablations only if the activity pattern, especially the A13 degradation,
persists.
