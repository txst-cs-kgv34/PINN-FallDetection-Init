# A10-A13 activity-specific physics V2 — five-seed confirmation

Positive improvement means `matched λ=0 − selected V2`; positive values favor selected V2.

| Metric | Selected V2 | Matched λ=0 | V2 improvement | Relative | Subject wins V2/N | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.5870 | 3.6887 | +0.1017 | +2.76% | 8/7 | 1.0000 |
| Theta RMSE (degrees) | 23.0432° | 23.2487° | +0.2056° | +0.88% | 8/7 | 1.0000 |
| CoM-x RMSE (cm) | 31.3921 cm | 31.6980 cm | +0.3059 cm | +0.97% | 9/6 | 1.0000 |

Selected weight counts across fold-seed models: `{'0.0': 9, '0.0001': 2, '0.001': 5, '0.01': 9}`.

## Descriptive activity results

Positive percentages favor selected V2. These activity rows are descriptive; subject-level inference remains primary.

| Activity | Normalized MSE | Theta RMSE | CoM-x RMSE |
|:--|--:|--:|--:|
| A10 | +0.32% | +0.31% | +0.22% |
| A11 | -1.16% | -1.13% | -0.82% |
| A12 | +2.99% | +2.43% | +2.00% |
| A13 | +4.76% | +0.63% | +1.16% |

Weights and checkpoints were selected only from the two validation subjects using subject-activity-balanced forecast MSE. Test subjects were evaluated after selection.

All four arms were trained from scratch with the same initialization, optimizer, schedule, data order, and checkpoint rule within each seed-fold.
