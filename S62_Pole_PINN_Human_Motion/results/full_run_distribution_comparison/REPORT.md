# Original vs synthetic S62 CoM distribution comparison

## Comparison design

The analysis compares the 10 original A11 trials (S62A11T01, S62A11T02, S62A11T03, S62A11T04, S62A11T05, S63A11T01, S63A11T02, S63A11T03, S63A11T04, S63A11T05) with all 100 saved synthetic trajectories. Distances use the **0-0.23 s shared interval**, where every original and synthetic trajectory is available. This prevents unequal real-trial lengths and the unsupported 30-second extrapolation from dominating the result. Because S62's shortest pre-cutoff trial is brief, this shared-window analysis describes only the early trajectory and must be interpreted accordingly.

Wasserstein-1 distance is computed separately for the marginal distributions of CoM angle `theta` and forward CoM position `x`. Its units are directly interpretable: degrees for `theta` and centimeters for `x`. A value of zero would indicate identical empirical distributions. The reported confidence intervals resample complete trajectories, not individual time points.

## Results

| Variable | Pooled W1 | Trajectory-bootstrap 95% CI | Mean time-resolved W1 | Median real-to-real W1 | Median synthetic split-half W1 |
|---|---:|---:|---:|---:|---:|
| theta | 2.759 deg | [1.388, 4.657] | 2.794 deg | 5.304 deg | 0.321 deg |
| x | 3.009 cm | [0.996, 5.337] | 3.024 cm | 1.858 cm | 0.001 cm |

### Sensitivity to the comparison horizon

| Shared horizon | theta W1 | x W1 |
|---|---:|---:|
| 0-0.23 s | 2.759 deg | 3.009 cm |

Relative to the pole code's output scales, the normalized marginal distances are `0.1104` for `theta` and `0.1204` for `x`; their descriptive mean is `0.1154`. This is **not** a joint multivariate Wasserstein distance.

## Interpretation

The line plots show that the synthetic ensemble overlaps the early low-motion portion of the original trials, but it does not reproduce the rapid trial-specific terminal CoM excursions consistently. Over the common interval, **46.2%** of original theta samples but only **1.2%** of original x samples lie inside the synthetic pointwise 5-95% envelope. The low x coverage, despite a moderate W1 distance, indicates an overly narrow synthetic x distribution rather than broad trial-to-trial coverage. The initial-angle-matched plots reinforce that matching `theta(0)` alone is insufficient because the generator fixes initial velocities to zero while the original trials have measured trial-specific initial derivatives.

For context, compare each pooled W1 with the median real-to-real W1 in the table. A pooled value below that baseline means the marginal real-synthetic mismatch is smaller than typical differences among the real trials; a value above it means the mismatch exceeds that within-subject trial variability. The synthetic split-half baseline indicates how much apparent distance arises merely by dividing the generated set in two. The combined mean-and-distance figure makes these comparisons visible without relying on the W1 curve alone.

The distances quantify distributional mismatch, but they should not be treated as population-level validation: there are only 10 original trials from one subject, and the trajectories used to train the model are also being used here for comparison. A held-out trial or additional subjects would be required for generalization claims.

## Reproduce

```bash
python analysis/compare_original_synthetic_distributions.py
```
