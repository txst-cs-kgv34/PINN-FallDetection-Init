# A10-A13 activity-specific physics V2 — one-seed pilot

Positive improvement means `matched λ=0 − selected V2`; positive values favor selected V2.

| Metric | Selected V2 | Matched λ=0 | V2 improvement | Relative | Subject wins V2/N | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.6402 | 3.5723 | -0.0680 | -1.90% | 6/3 | 1.0000 |
| Theta RMSE (degrees) | 22.2882° | 22.3790° | +0.0909° | +0.41% | 5/4 | 1.0000 |
| CoM-x RMSE (cm) | 30.8745 cm | 30.8838 cm | +0.0093 cm | +0.03% | 5/4 | 1.0000 |

Selected weight counts across fold-seed models: `{'0.0': 2, '0.0001': 1, '0.001': 1, '0.01': 1}`.

## Descriptive activity results

Positive percentages favor selected V2. These activity rows are descriptive; subject-level inference remains primary.

| Activity | Normalized MSE | Theta RMSE | CoM-x RMSE |
|:--|--:|--:|--:|
| A10 | +2.71% | +2.21% | +1.17% |
| A11 | +2.70% | +0.77% | +1.31% |
| A12 | -0.32% | +3.12% | +2.52% |
| A13 | -7.39% | -5.14% | -5.94% |

Weights and checkpoints were selected only from the two validation subjects using subject-activity-balanced forecast MSE. Test subjects were evaluated after selection.

All four arms were trained from scratch with the same initialization, optimizer, schedule, data order, and checkpoint rule within each seed-fold.
