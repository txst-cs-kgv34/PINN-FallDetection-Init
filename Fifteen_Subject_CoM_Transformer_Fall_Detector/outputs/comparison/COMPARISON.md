# Fall-detector scenario comparison

Compared 75 completed fold/seed runs (25 matched settings per scenario).

## Descriptive result

The highest mean test trial balanced accuracy was produced by **Real falls + real ADL** (0.9433 ± 0.0605).

This is a descriptive comparison, not permission to tune the model on the test set. Architecture and hyperparameter changes must be chosen using validation results only.

## Statistical tables

`paired_wilcoxon_holm.csv` averages the repeated seeds within each fold, performs paired Wilcoxon tests across folds, and applies Holm correction across the three scenario comparisons for each metric. With only five folds, these tests are exploratory and effect sizes plus fold-level consistency should receive more emphasis than p-values.

## Files

- `scenario_summary.csv`: descriptive mean, standard deviation, median, and range.
- `paired_wilcoxon_holm.csv`: paired differences and corrected p-values.
- `fold_seed_averaged_metrics.csv`: values supplied to the paired tests.
- `combined_run_metrics.csv`: all matched fold/seed run metrics.
- `scenario_metric_boxplots.png`: visual comparison.
