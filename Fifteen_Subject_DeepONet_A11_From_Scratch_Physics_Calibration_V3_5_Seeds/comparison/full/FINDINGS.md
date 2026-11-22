# A11 matched from-scratch physics calibration V3 — five-seed confirmation

Positive improvement means `matched λ=0 − selected V3`; positive values favor selected V3.

| Metric | Selected V3 | Matched λ=0 | V3 improvement | Relative | Subject wins V3/N | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.4892 | 3.3313 | -0.1579 | -4.74% | 7/8 | 1.0000 |
| Theta RMSE (degrees) | 21.9119° | 21.6521° | -0.2598° | -1.20% | 10/5 | 1.0000 |
| CoM-x RMSE (cm) | 30.3129 cm | 29.8412 cm | -0.4717 cm | -1.58% | 8/7 | 1.0000 |

Selected weight counts across fold-seed models: `{'0.0': 8, '0.0001': 3, '0.001': 7, '0.01': 7}`.

Weights and checkpoints were selected only from the validation subject. Test subjects were evaluated after selection.

All four arms were trained from scratch with the same initialization, optimizer, schedule, data order, and checkpoint rule within each seed-fold.
