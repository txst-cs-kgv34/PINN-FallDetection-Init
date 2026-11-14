# Fall-detector scenario comparison

Compared 75 completed fold/seed runs (25 matched settings per scenario).

## Descriptive result and winner

The winner is **Real falls + real ADL**. It had the highest mean test-trial balanced accuracy (0.9433 ± 0.0605) and ranked first for all six performance metrics while producing the lowest false-positive event rate.

| Metric | Real | Synthetic | Combined |
|---|---:|---:|---:|
| Balanced accuracy | **0.943** | 0.878 | 0.886 |
| Sensitivity | **0.909** | 0.826 | 0.834 |
| Specificity | **0.978** | 0.929 | 0.938 |
| F1 | **0.881** | 0.714 | 0.740 |
| AUROC | **0.987** | 0.962 | 0.966 |
| AUPRC | **0.960** | 0.825 | 0.870 |
| False-positive events/ADL minute ↓ | **0.170** | 0.463 | 0.417 |

Real-fall training also had the highest fold-averaged balanced accuracy in all five held-out subject folds. Synthetic-only training nevertheless transferred well to real test subjects, while Combined slightly improved over Synthetic but remained below Real.

This is a descriptive comparison, not permission to tune the model on the test set. Architecture and hyperparameter changes must be chosen using validation results only.

## Statistical tables

`paired_wilcoxon_holm.csv` averages the repeated seeds within each fold, performs paired Wilcoxon tests across folds, and applies Holm correction across the three scenario comparisons for each metric. No Holm-adjusted p-value is below 0.05. For balanced accuracy, Real versus Synthetic and Real versus Combined both have unadjusted p = 0.0625 and Holm-adjusted p = 0.1875. With only five fold-level pairs, these tests are exploratory and effect sizes plus fold-level consistency should receive more emphasis than p-values.

The correct conclusion is that Real is the consistent descriptive winner, not that statistical significance has been established.

## Files

- `scenario_summary.csv`: descriptive mean, standard deviation, median, and range.
- `paired_wilcoxon_holm.csv`: paired differences and corrected p-values.
- `fold_seed_averaged_metrics.csv`: values supplied to the paired tests.
- `combined_run_metrics.csv`: all matched fold/seed run metrics.
- `scenario_metric_boxplots.png`: visual comparison.
- `scenario_performance_overview.png`: mean ± SD across the five fold means.
- `foldwise_balanced_accuracy.png`: paired held-out-fold comparison.
- `paired_balanced_accuracy_differences.png`: fold differences relative to Real.
- `false_positive_events_by_fold.png`: operational false-positive comparison.
- `fold_level_metric_summary.csv`: fold-aware descriptive summary.
- `paired_fold_differences_vs_real.csv`: paired differences underlying the new plot.
