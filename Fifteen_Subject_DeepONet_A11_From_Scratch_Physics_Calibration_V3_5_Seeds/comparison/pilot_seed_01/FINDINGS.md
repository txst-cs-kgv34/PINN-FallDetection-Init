# A11 matched from-scratch physics calibration V3 — one-seed pilot

Positive improvement means `matched λ=0 − selected V3`; positive values favor selected V3.

| Metric | Selected V3 | Matched λ=0 | V3 improvement | Relative | Subject wins V3/N | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.6716 | 3.6441 | -0.0275 | -0.75% | 9/3 | 0.4738 |
| Theta RMSE (degrees) | 21.5392° | 21.7734° | +0.2342° | +1.08% | 7/5 | 0.5303 |
| CoM-x RMSE (cm) | 30.3499 cm | 30.6641 cm | +0.3142 cm | +1.02% | 9/3 | 0.4738 |

Selected weight counts across fold-seed models: `{'0.0': 1, '0.001': 1, '0.01': 3}`.

Weights and checkpoints were selected only from the validation subject. Test subjects were evaluated after selection.

All four arms were trained from scratch with the same initialization, optimizer, schedule, data order, and checkpoint rule within each seed-fold.
