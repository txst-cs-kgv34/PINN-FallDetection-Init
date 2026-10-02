# S43 A13 controlled physics-weight experiment

## Outcome

The best tested nonzero physics weight improved on the matched data-only network.

| Metric | Value |
|---|---:|
| Data-only mean held-out 3D RMSE | 0.4618 m |
| Best tested PINN weight | 0.1 |
| Best PINN mean held-out 3D RMSE | 0.2975 m |
| PINN RMSE reduction relative to data-only | 35.6% |
| Matched fold/seed runs improved over data-only | 6 / 8 |
| Training-mean baseline RMSE | 0.1961 m |
| Best PINN RMSE above training mean | 51.7% |
| Best PINN runs beating training mean | 4 / 8 |
| Gravity-only sanity-check RMSE | 2.6625 m |
| Best PINN physics residual RMS | 3.0733 m/s² |
| Whole-trial folds | 4 |
| Seeds per fold and weight | 2 |

## Design

The data-only and PINN models use the same trajectory network, hard onset position/velocity constraints, physical-time inputs, trial conditions, folds, seeds, optimizer and epochs. Only the physics-loss weight changes. Condition normalization uses the three training trials in each fold. The untrained gravity-only curve is a sanity check rather than a realistic supported-body model.

Tested physics weights: 0, 0.01, 0.1, 1, 10.

The largest remaining error is S43A13T02 at 0.8269 m for seed 43014; this trial is 21.0 training standard deviations outside at least one training-condition range.

## Interpretation gate

This is an exploratory four-trial, single-subject, single-activity comparison. Selecting the best weight from the same four folds is model selection, not independent validation. The learned effective acceleration still combines support, voluntary control, contact, measurement/model error and any true perturbation; it is not a recovered external force.

Synthetic generation remains gated on consistent improvement over the data-only and training-mean baselines, acceptable residual behavior, and later validation on additional real trials or activities.
