# A11 current-data physics diagnostic — completed comparison

Positive improvement means `no physics − physics`, so positive values favor physics.

| Metric | Physics | No physics | Physics improvement | Relative | Subject wins P/N | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.4861 | 3.3006 | -0.1856 | -5.62% | 7/8 | 0.7788 |
| Theta RMSE (degrees) | 22.8186° | 21.5777° | -1.2409° | -5.75% | 7/8 | 0.7788 |
| CoM-x RMSE (cm) | 31.9421 cm | 29.8429 cm | -2.0992 cm | -7.03% | 5/10 | 0.3210 |

Interpret the held-out trajectory endpoints above as primary. The residual diagnostics only show agreement with the specified CartPole equations.

All 320 paired prediction targets were verified exactly identical between conditions.

## Diagnostic decision

A11-only training did not recover the earlier physics advantage. Compared with
the unified current-data A11 subset, isolation narrowed the physics penalty but
did not reverse it. Physics also showed higher seed variability, was selected
at epoch 10 or earlier in 4 of 25 folds/seeds, and never won the seed-mean x
RMSE comparison.

The full V2 should therefore not use the fixed `0.01` weight unchanged. First
run an A11 calibration with data-only warm starts, a ramped and
validation-selected physics weight, normalized angular/horizontal residual
heads, and activity-defined rather than observed endpoint-derived direction.
The detailed rationale and the staged V2 plan are in the root `FINDINGS.md`.
