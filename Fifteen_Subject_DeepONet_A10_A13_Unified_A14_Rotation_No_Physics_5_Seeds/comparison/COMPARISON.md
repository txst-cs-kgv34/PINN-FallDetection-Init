# Physics versus no-physics comparison

Both conditions completed 25 planar and 25 rotation fold/seed models. The comparison uses the same held-out subjects and first averages the five optimization seeds within each subject. Lower values are better for every reported metric.

## Primary subject-level results

| Model | Metric | No physics | Physics | Physics change | Physics lower-error subjects | Holm-adjusted p |
|:--|:--|--:|--:|--:|--:|--:|
| A10–A13 | Normalized MSE | 2.914 | 3.314 | +13.7% | 20.0% | 0.0299 |
| A10–A13 | $\theta$ RMSE (deg) | 21.423 | 23.484 | +9.6% | 13.3% | 0.0299 |
| A10–A13 | x RMSE (cm) | 29.221 | 31.962 | +9.4% | 13.3% | 0.0299 |
| A10–A13 | Angular residual RMSE | 15.373 | 13.481 | -12.3% | 86.7% | 0.0024 |
| A10–A13 | Horizontal residual RMSE | 262.693 | 7.228 | -97.2% | 100.0% | 0.000549 |
| A14 | Normalized MSE | 8.869 | 7.976 | -10.1% | 30.8% | 1.0000 |
| A14 | $\theta$ RMSE (deg) | 30.784 | 29.859 | -3.0% | 38.5% | 1.0000 |
| A14 | x RMSE (cm) | 45.811 | 43.862 | -4.3% | 38.5% | 1.0000 |
| A14 | Yaw RMSE (deg) | 127.769 | 120.232 | -5.9% | 69.2% | 1.0000 |
| A14 | Angular residual RMSE | 13.610 | 12.358 | -9.2% | 84.6% | 1.0000 |
| A14 | Horizontal residual RMSE | 112.918 | 16.394 | -85.5% | 100.0% | 0.0032 |
| A14 | Yaw residual RMSE | 9.816 | 8.102 | -17.5% | 76.9% | 1.0000 |

## Interpretation

- **A10–A13:** physics reduced the angular residual by 12.3% and the horizontal residual by 97.2%, but forecast errors increased: normalized MSE by 13.7%, theta RMSE by 9.6%, and x RMSE by 9.4%. The trajectory-error differences remain significant after within-group Holm correction.
- **A14:** physics reduced mean normalized MSE by 10.1%, theta RMSE by 3.0%, x RMSE by 4.3%, and yaw RMSE by 5.9%. These trajectory improvements were not significant after subject-level Holm correction and were not uniform across subjects.
- **A14 dynamics:** the horizontal residual fell by 85.5% and remained significant after correction; angular and yaw residuals also decreased descriptively.
- The result supports physics as a strong dynamics regularizer, but not as a universal trajectory-accuracy improvement at the current fixed weight of 0.01. For A10–A13, the no-physics model is the preferred forecasting model. For A14, the physics model is promising for rotation/yaw modeling, but the gain should be confirmed with a physics-weight ablation.
- Baseline controller gains are not identified by a physics loss, so its residuals are diagnostics of an unconstrained pathway rather than interpretable recovered controller parameters.

## Statistical unit

The paired Wilcoxon tests use one value per held-out subject after averaging the five seeds (15 subjects for A10–A13 and 13 eligible subjects for A14). Holm correction is applied separately across all reported metrics within each model group. This avoids treating repeated seeds as independent subjects.

See `physics_vs_no_physics_subject_boxplots.png`, `physics_vs_no_physics_summary.csv`, `paired_subject_wilcoxon_holm.csv`, and `subject_seed_averaged_metrics.csv` in this directory.
