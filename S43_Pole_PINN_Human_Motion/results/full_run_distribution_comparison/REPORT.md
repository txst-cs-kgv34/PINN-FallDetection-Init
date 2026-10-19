# Original vs synthetic S43 CoM distribution comparison

## Comparison design

The analysis compares the four original A11 trials (T02-T05) with all 100 saved synthetic trajectories. Distances use the **0-2.69 s shared interval**, where every original and synthetic trajectory is available. This prevents unequal real-trial lengths and the unsupported 30-second extrapolation from dominating the result.

Wasserstein-1 distance is computed separately for the marginal distributions of CoM angle `theta` and forward CoM position `x`. Its units are directly interpretable: degrees for `theta` and centimeters for `x`. A value of zero would indicate identical empirical distributions. The reported confidence intervals resample complete trajectories, not individual time points.

## Results

| Variable | Pooled W1 | Trajectory-bootstrap 95% CI | Mean time-resolved W1 | Median real-to-real W1 | Median synthetic split-half W1 |
|---|---:|---:|---:|---:|---:|
| theta | 1.069 deg | [0.404, 2.382] | 1.230 deg | 2.022 deg | 0.226 deg |
| x | 1.839 cm | [1.205, 2.472] | 2.306 cm | 1.417 cm | 0.074 cm |

### Sensitivity to the comparison horizon

| Shared horizon | theta W1 | x W1 |
|---|---:|---:|
| 0-1.00 s | 0.630 deg | 0.523 cm |
| 0-2.00 s | 1.033 deg | 0.517 cm |
| 0-2.69 s | 1.069 deg | 1.839 cm |

Relative to the pole code's output scales, the normalized marginal distances are `0.0428` for `theta` and `0.0736` for `x`; their descriptive mean is `0.0582`. This is **not** a joint multivariate Wasserstein distance.

## Interpretation

The line plots show that the synthetic ensemble overlaps the early low-motion portion of the original trials, but it does not reproduce the rapid trial-specific terminal CoM excursions consistently. Over the common interval, **71.3%** of original theta samples but only **6.3%** of original x samples lie inside the synthetic pointwise 5-95% envelope. The low x coverage, despite a moderate W1 distance, indicates an overly narrow synthetic x distribution rather than broad trial-to-trial coverage. The initial-angle-matched plots reinforce that matching `theta(0)` alone is insufficient because the generator fixes initial velocities to zero while the original trials have measured trial-specific initial derivatives.

For context, the pooled theta W1 (1.069 deg) is below the median real-trial-pair distance (2.022 deg), so the short-horizon **marginal theta distribution** is within the observed trial-to-trial variability. The x W1 (1.839 cm) is above the median real-trial-pair distance (1.417 cm), and the horizon analysis shows that most of this x mismatch appears after 2 s. The much smaller synthetic split-half distances show that the 100 generated curves are internally similar; therefore, producing 100 files did not produce the same amount of diversity as the four original trials.

The distances quantify distributional mismatch, but they should not be treated as population-level validation: there are only four original trials from one subject, and the trajectories used to train the model are also being used here for comparison. A held-out trial or additional subjects would be required for generalization claims.

## Reproduce

```bash
python analysis/compare_original_synthetic_distributions.py
```
