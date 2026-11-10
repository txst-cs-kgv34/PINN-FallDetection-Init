# Physics versus no-physics comparison

This folder contains the reproducible paired analysis of the matched full-fall
five-seed experiments.

## Main result

| Metric | Physics | No physics | Physics reduction | Subjects favoring Physics | Holm-adjusted p |
|:---|---:|---:|---:|---:|---:|
| Normalized forecast RMSE | 1.5883 | 1.7292 | 8.15% | 12/15 | 0.0646 |
| Theta RMSE | 21.4843° | 22.7223° | 5.45% | 12/15 | 0.1354 |
| CoM x RMSE | 28.4642 cm | 30.9527 cm | 8.04% | 12/15 | 0.0646 |

The main analysis averages the five seeds within each subject and then compares
the 15 paired subjects. Trial-level plots are exploratory because trials from
the same subject are correlated. Normalized RMSE is the square root of each
subject-seed normalized MSE.

## Reproduce

From the experiment root:

```bash
python comparison/generate_comparison.py
```

The script validates exact one-to-one matching before calculating results. Its
inputs are preserved in `input/`; regenerated artifacts are written to
`outputs/`.

## Figures

- `physics_vs_no_physics_subject_boxplots.png`: advisor-facing side-by-side
  boxes for normalized RMSE, theta RMSE in degrees, and CoM x RMSE in cm. Each
  box contains the five optimization seeds for one held-out subject.
- `physics_vs_no_physics_subject_differences.png`: subject means over seeds;
  positive bars mean Physics has lower error.
- `physics_vs_no_physics_seed_means.png`: subject-balanced means for every
  optimization seed.
- `physics_vs_no_physics_trial_scatter.png`: exploratory paired trial means.

## Tables

- `statistical_summary.csv`: subject-level paired statistics, bootstrap
  intervals, effect sizes, and Holm-adjusted Wilcoxon p-values.
- `subject_mean_comparison.csv`: paired means and differences for every subject.
- `seed_mean_comparison.csv`: subject-balanced results for every seed.
- `paired_subject_seed_metrics.csv`: all 75 matched subject-seed rows.
- `paired_trial_seed_metrics.csv`: all 350 matched trial-seed rows.
- `comparison_summary.json`: machine-readable audit and summary.

Physics residuals are not a primary comparison endpoint. The no-physics
model's four positive context coordinates are latent features rather than
physically identified controller gains, so its post-hoc residual magnitudes are
not directly comparable evidence of forecast quality.
