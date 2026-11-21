# No-physics baseline findings

## Completed protocol

- The no-physics condition completed all 50 planned models: two model groups, five subject-grouped folds, and five optimization seeds.
- The unified planar baseline used the same 257 A10–A13 strict-primary trials as the physics condition, including 64 A11 frontfalls.
- The separate A14 baseline used the same 49 strict-primary trials from 13 eligible subjects and predicted theta, direction-aligned x, and yaw.
- Architecture capacity, trial filters, preprocessing, folds, seeds, optimization, and early stopping were matched. Only the CartPole and yaw loss weights were disabled.

## Held-out-subject results

Five seeds were averaged within each held-out subject before comparison. Lower values are better.

| Model | Metric | No physics | Physics | Change with physics | Holm-adjusted p |
|:--|:--|--:|--:|--:|--:|
| A10–A13 | Normalized MSE | 2.914 | 3.314 | +13.7% | 0.0299 |
| A10–A13 | Theta RMSE (deg) | 21.423 | 23.484 | +9.6% | 0.0299 |
| A10–A13 | x RMSE (cm) | 29.221 | 31.962 | +9.4% | 0.0299 |
| A14 | Normalized MSE | 8.869 | 7.976 | -10.1% | 1.0000 |
| A14 | Theta RMSE (deg) | 30.784 | 29.859 | -3.0% | 1.0000 |
| A14 | x RMSE (cm) | 45.811 | 43.862 | -4.3% | 1.0000 |
| A14 | Yaw RMSE (deg) | 127.769 | 120.232 | -5.9% | 1.0000 |

The p-values come from paired Wilcoxon tests over independent held-out subjects after averaging the five seeds, with Holm correction across metrics within each model group.

## Interpretation

- The no-physics model is the clear A10–A13 trajectory winner. Relative to it, physics increases normalized MSE by 13.7%, theta RMSE by 9.6%, and x RMSE by 9.4%.
- A14 behaves differently: physics reduces all four primary mean errors, including yaw RMSE by 5.9%. These improvements are not uniform across subjects and are not significant after correction.
- The physics condition strongly reduces dynamics residuals. That demonstrates regularization toward the specified equations, but it does not by itself imply better measured-trajectory prediction.
- Baseline controller outputs are unconstrained because they do not participate in its loss. Baseline residual magnitudes should therefore be treated only as diagnostics, not as identified physical-controller parameters.

## Decision

- Use this no-physics baseline as the current A10–A13 forecasting model.
- For A14 rotation/yaw, carry the physics model forward as an exploratory candidate and validate it through a physics-weight ablation.
- Do not claim that physics universally improves forecasting: the evidence supports a dynamics-consistency benefit, a planar accuracy cost at weight 0.01, and a promising but inconclusive A14 trajectory benefit.

The combined subject-level box plots and complete tables are in `comparison/`.
