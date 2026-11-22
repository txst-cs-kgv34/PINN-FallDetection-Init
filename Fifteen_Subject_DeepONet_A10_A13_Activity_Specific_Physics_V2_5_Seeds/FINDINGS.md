# A10-A13 activity-specific physics V2: seed-1 pilot findings

## Conclusion

Seed 1 does not show an overall forecasting advantage for the
validation-selected physics condition. Normalized forecast MSE was 1.90% worse,
theta RMSE was 0.41% better, and CoM-x RMSE was 0.03% better than the matched
from-scratch lambda=0 condition. All uncertainty intervals include zero and all
Holm-adjusted p-values are 1.0. This is a screening seed and not a statistical
conclusion.

The result is still informative. Validation selected nonzero physics in three
of five folds, A10 and A11 improved descriptively on all primary outcomes, A12
improved its component RMSEs, and horizontal residual RMSE decreased strongly.
A13 was consistently worse. The implementation and pairing audits passed, so
the recommended action is to complete seeds 2-5 unchanged and then decide
whether activity-head ablations are required.

## Primary held-out-subject comparison

Positive improvement means `matched lambda=0 - selected V2`; positive values
favor selected V2.

| Metric | Selected V2 | Matched lambda=0 | Mean improvement | Relative | Wins V2/N/tie | Bootstrap 95% CI | Holm p |
|:--|--:|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.6402 | 3.5723 | -0.0680 | -1.90% | 6/3/6 | [-0.4556, +0.2589] | 1.0000 |
| Theta RMSE | 22.2882 degrees | 22.3790 degrees | +0.0909 degrees | +0.41% | 5/4/6 | [-1.1550, +1.2684] | 1.0000 |
| CoM-x RMSE | 30.8745 cm | 30.8838 cm | +0.0093 cm | +0.03% | 5/4/6 | [-1.7970, +1.6323] | 1.0000 |

Six subjects are exact ties because their folds selected lambda=0. Among the
nine subjects whose folds selected nonzero physics, normalized MSE was 3.21%
worse, theta RMSE was 0.66% better, and CoM-x RMSE was 0.05% better.

## Lambda selection and validation transfer

| Fold | Validation subjects | Selected lambda | Validation MSE gain vs lambda=0 | Test normalized-MSE gain |
|:--|:--|--:|--:|--:|
| 1 | S44, S62 | 1e-4 | +5.19% | -17.47% |
| 2 | S57, S46 | 1e-2 | +3.85% | +10.97% |
| 3 | S55, S48 | 1e-3 | +0.85% | -10.12% |
| 4 | S45, S59 | 0 | 0.00% | 0.00% |
| 5 | S34, S32 | 0 | 0.00% | 0.00% |

Validation preference transferred positively only in fold 2. Fold 1 and fold 3
selected nonzero lambda but worsened held-out normalized MSE. The selected
lambda is therefore not stable enough to lock for a production generator after
one seed.

## Activity results

These rows equalize trials within held-out subject-activity cells. They are
descriptive; subject-level inference remains primary.

| Activity | Normalized MSE improvement | Theta RMSE improvement | CoM-x RMSE improvement | Interpretation |
|:--|--:|--:|--:|:--|
| A10 backfall | +2.71% | +2.21% | +1.17% | Consistent small improvement |
| A11 frontfall | +2.70% | +0.77% | +1.31% | Consistent small improvement |
| A12 leftfall | -0.32% | +3.12% | +2.52% | Mixed; component RMSEs improved |
| A13 rightfall | -7.39% | -5.14% | -5.94% | Consistent degradation |

A13 is the main activity-level concern. Its degradation appears in all three
nonzero-selected folds, not only one fold. A13 should therefore be a predefined
focus of the five-seed review.

## Subject heterogeneity

The largest improvements were S43 (+1.065 normalized MSE, +4.246 degrees theta
RMSE, +4.607 cm CoM-x RMSE) and S56 (+0.569, +4.267 degrees, +6.162 cm). The
largest degradations were S45 (-1.959, -3.400 degrees, -5.222 cm) and S46
(-1.458, -5.747 degrees, -8.702 cm). These opposing effects explain why the
mean result is near neutral despite more normalized-MSE subject wins than
losses among the non-tied subjects.

## Physics residuals

| Residual endpoint | Selected V2 | Matched lambda=0 | Relative improvement |
|:--|--:|--:|--:|
| Angular residual RMSE | 16.5917 | 16.5576 | -0.21% |
| Horizontal residual RMSE | 188.1702 | 229.8687 | +18.14% |

Among only the nine subjects evaluated with nonzero selected lambda,
horizontal residual RMSE improved by 40.82%, while angular residual RMSE was
0.37% worse. Physics is changing the learned solution in the intended
horizontal equation, but equation consistency and forecast generalization
remain separate outcomes.

## Integrity audit

- Archive integrity passed.
- 20/20 candidate trainings are present: four lambda arms x five folds.
- Five selected and five matched lambda=0 evaluations are present.
- Initial-state SHA-256 is identical across lambda arms within every fold.
- Pre-training validation loss is exactly identical across arms within every fold.
- All 257 selected/no-physics target trajectories are exactly identical.
- All 4,591 training-history rows contain finite values.
- Trial counts are A10=58, A11=64, A12=68, and A13=67.
- No evidence of subject-role leakage or post-selection test access was found.

## Next step

Run seeds 2-5 with the existing code and no protocol changes:

```bash
./run_on_mac.sh full mps
```

The completed seed-1 models will be skipped. The five-seed analysis should be
the basis for deciding whether to retain all-head physics or run the planned
activity-head ablations. If A13 remains harmful, compare `all heads`, `A10
only`, `A11 only`, `A12 only`, and `A13 only`, with an explicit candidate that
keeps A13 at lambda=0.

Do not train the final A10-A13 synthetic generator yet. First lock the
architecture and physics-head policy from the five-seed result. A14 does not
need another physics-versus-no-physics comparison; only its later all-data
production refit remains.
