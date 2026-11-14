# Source-balanced 1:1 comparison

Compared 100 completed scenario runs across 25 matched fold/seed settings.

## Descriptive winner

The highest mean test-trial balanced accuracy was produced by **Real falls + real ADL** (0.9433).

| Scenario | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP/min ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Real falls + real ADL | 0.943 | 0.909 | 0.978 | 0.881 | 0.987 | 0.960 | 0.170 |
| Synthetic falls + real ADL | 0.878 | 0.826 | 0.929 | 0.714 | 0.962 | 0.825 | 0.463 |
| Original combined + real ADL | 0.886 | 0.834 | 0.938 | 0.740 | 0.966 | 0.870 | 0.417 |
| Source-balanced 1:1 falls + real ADL | 0.904 | 0.848 | 0.960 | 0.804 | 0.970 | 0.897 | 0.276 |

## Interpretation rule

The 1:1 ratio was fixed before this test run, so this is a confirmatory comparison rather than test-set selection among several mixture ratios. Check the paired fold differences and Holm-adjusted tests before claiming an improvement.

Seeds are averaged within each fold before paired Wilcoxon tests. Holm correction is applied across the three comparisons between Balanced 1:1 and the prior scenarios for each metric. With five folds, inference remains exploratory.
