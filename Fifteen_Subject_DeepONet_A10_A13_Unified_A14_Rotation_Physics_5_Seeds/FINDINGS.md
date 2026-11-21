# Physics experiment findings

## Completed protocol

- The physics condition completed all 50 planned models: two model groups, five subject-grouped folds, and five optimization seeds.
- The unified planar model used 257 strict-primary trials: A10=58, A11=64, A12=68, and A13=67.
- The separate A14 model used 49 strict-primary trials from 13 eligible subjects. S34's only A14 trial was incomplete; S44 A14 was withheld from primary rotation fitting because the trials appear front-fall-like and may omit the turn-around.
- The physics and no-physics conditions used identical data, preprocessing, architecture, splits, seeds, optimizer, and early-stopping rules. Only the CartPole/yaw loss switches and weights differed.

## Held-out-subject results

Five seeds were averaged within each held-out subject before comparison. Lower values are better.

| Model | Metric | No physics | Physics | Change with physics | Holm-adjusted p |
|:--|:--|--:|--:|--:|--:|
| A10–A13 | Normalized MSE | 2.914 | 3.314 | +13.7% | 0.0299 |
| A10–A13 | Theta RMSE (deg) | 21.423 | 23.484 | +9.6% | 0.0299 |
| A10–A13 | x RMSE (cm) | 29.221 | 31.962 | +9.4% | 0.0299 |
| A10–A13 | Angular residual RMSE | 15.373 | 13.481 | -12.3% | 0.0024 |
| A10–A13 | Horizontal residual RMSE | 262.693 | 7.228 | -97.2% | 0.000549 |
| A14 | Normalized MSE | 8.869 | 7.976 | -10.1% | 1.0000 |
| A14 | Theta RMSE (deg) | 30.784 | 29.859 | -3.0% | 1.0000 |
| A14 | x RMSE (cm) | 45.811 | 43.862 | -4.3% | 1.0000 |
| A14 | Yaw RMSE (deg) | 127.769 | 120.232 | -5.9% | 1.0000 |
| A14 | Horizontal residual RMSE | 112.918 | 16.394 | -85.5% | 0.0032 |
| A14 | Yaw residual RMSE | 9.816 | 8.102 | -17.5% | 1.0000 |

The p-values come from paired Wilcoxon tests over independent held-out subjects after averaging the five seeds, with Holm correction across metrics within each model group.

## Interpretation

- For A10–A13, the physics residual successfully enforces dynamics but over-regularizes the trajectory at the fixed weight of 0.01. Every primary forecast metric is worse than the no-physics baseline, and the differences remain significant after correction.
- For A14, physics improves the mean normalized, theta, x, and yaw errors. Yaw RMSE falls by 5.9%, and all five activity-level seed means favor physics for yaw RMSE. The subject-level improvements are heterogeneous and are not significant after correction.
- The strongest robust benefit is physics consistency: horizontal residual RMSE drops 97.2% for A10–A13 and 85.5% for A14.
- Baseline controller gains are not identified by a physics loss. Its residuals therefore diagnose an unconstrained controller pathway and should not be interpreted as recovered physical parameters.

## Decision and next experiment

- Use the no-physics model as the current A10–A13 forecasting reference.
- Retain the physics A14 model as the more promising rotation/yaw formulation, while describing its trajectory benefit as exploratory rather than conclusive.
- Before rejecting planar physics, run a physics-weight ablation below 0.01, for example `0.0001`, `0.001`, `0.003`, and `0.01`, selected only on validation subjects. This will test whether dynamics consistency can be retained without the observed forecasting penalty.

The combined subject-level box plots and complete tables are in `comparison/`.
