# Original vs synthetic S57 CoM distribution comparison

## Comparison design

The analysis compares the 3 original A11 trials (S57A11T03, S57A11T04, S57A11T05) with all 100 saved synthetic trajectories. Distances use the **0-1.87 s shared interval**, where every original and synthetic trajectory is available. This prevents unequal real-trial lengths and the unsupported 30-second extrapolation from dominating the result. Because S57's shortest pre-cutoff trial is brief, this shared-window analysis describes only the early trajectory and must be interpreted accordingly.

Wasserstein-1 distance is computed separately for the marginal distributions of CoM angle `theta` and forward CoM position `x`. Its units are directly interpretable: degrees for `theta` and centimeters for `x`. A value of zero would indicate identical empirical distributions. The reported confidence intervals resample complete trajectories, not individual time points.

## Results

| Variable | Pooled W1 | Trajectory-bootstrap 95% CI | Mean time-resolved W1 | Median real-to-real W1 | Median synthetic split-half W1 |
|---|---:|---:|---:|---:|---:|
| theta | 2.477 deg | [1.910, 5.324] | 6.200 deg | 6.775 deg | 0.263 deg |
| x | 5.371 cm | [2.424, 7.171] | 5.609 cm | 4.107 cm | 0.019 cm |

### Sensitivity to the comparison horizon

| Shared horizon | theta W1 | x W1 |
|---|---:|---:|
| 0-0.25 s | 4.846 deg | 0.490 cm |
| 0-0.50 s | 4.703 deg | 0.480 cm |
| 0-1.00 s | 3.539 deg | 0.712 cm |
| 0-1.87 s | 2.477 deg | 5.371 cm |

Relative to the pole code's output scales, the normalized marginal distances are `0.0991` for `theta` and `0.2148` for `x`; their descriptive mean is `0.1569`. This is **not** a joint multivariate Wasserstein distance.

## Interpretation

The line plots show that the synthetic ensemble overlaps the early low-motion portion of the original trials, but it does not reproduce the rapid trial-specific terminal CoM excursions consistently. Over the common interval, **26.4%** of original theta samples but only **2.8%** of original x samples lie inside the synthetic pointwise 5-95% envelope. The low x coverage, despite a moderate W1 distance, indicates an overly narrow synthetic x distribution rather than broad trial-to-trial coverage. The initial-angle-matched plots reinforce that matching `theta(0)` alone is insufficient because the generator fixes initial velocities to zero while the original trials have measured trial-specific initial derivatives.

For context, compare each pooled W1 with the median real-to-real W1 in the table. A pooled value below that baseline means the marginal real-synthetic mismatch is smaller than typical differences among the real trials; a value above it means the mismatch exceeds that within-subject trial variability. The synthetic split-half baseline indicates how much apparent distance arises merely by dividing the generated set in two. The combined mean-and-distance figure makes these comparisons visible without relying on the W1 curve alone.

The distances quantify distributional mismatch, but they should not be treated as population-level validation: there are only 3 original trials from one subject, and the trajectories used to train the model are also being used here for comparison. A held-out trial or additional subjects would be required for generalization claims.

## Reproduce

```bash
python analysis/compare_original_synthetic_distributions.py
```
