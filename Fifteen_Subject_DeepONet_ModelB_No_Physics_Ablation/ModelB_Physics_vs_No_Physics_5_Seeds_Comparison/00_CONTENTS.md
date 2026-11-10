# Comparison package contents

This directory contains the completed paired five-seed comparison.

## Read first

- `README.md` — experiment design, main metrics, and file guide.
- `FINDINGS.md` — detailed scientific interpretation and sensitivity analysis.
- `comparison_summary.json` — machine-readable statistical summary.

## Comparison tables

- `paired_seed_metrics.csv` — five paired seed-level rows.
- `paired_subject_metrics.csv` — 15 subject means across five seeds.
- `paired_subject_seed_metrics.csv` — all 75 subject-seed pairs.
- `paired_trial_metrics.csv` — 66 trial means across five seeds.
- `paired_trial_seed_metrics.csv` — all 330 trial-seed pairs.
- `paired_fold_seed_metrics.csv` — all 25 fold-seed comparisons.
- `training_selection_comparison.csv` — selected checkpoint epochs and validation losses.

## Figures

- `figures/paired_seed_means.png`
- `figures/paired_subject_means.png`
- `figures/paired_subject_difference_boxplots.png`
- `figures/physics_vs_no_physics_five_seed_side_by_side_boxplots.png`
- `figures/paired_fold_difference_heatmaps.png`
- `figures/paired_subject_scatter.png`

## Reproducibility

- `compare_five_seed_results.py` regenerates the tables, JSON summary, and figures.
- `plot_five_seed_side_by_side_boxplots.py` regenerates the requested
  three-panel side-by-side five-seed boxplot.

The archive was verified after packaging by extracting it into a separate directory and checking every expected file.

