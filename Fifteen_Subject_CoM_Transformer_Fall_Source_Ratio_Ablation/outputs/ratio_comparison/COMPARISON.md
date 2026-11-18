# Fall-source ratio comparison

Compared 150 runs across 25 matched fold/seed settings.

## Descriptive results

The overall descriptive winner by balanced accuracy was **Real falls + real ADL** (0.9433).
The best mixed-source ratio was **50:50 real:synthetic falls + real ADL** (0.9037).

| Scenario | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP/min ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Real falls + real ADL | 0.943 | 0.909 | 0.978 | 0.881 | 0.987 | 0.960 | 0.170 |
| Synthetic falls + real ADL | 0.878 | 0.826 | 0.929 | 0.714 | 0.962 | 0.825 | 0.463 |
| Original combined falls + real ADL | 0.886 | 0.834 | 0.938 | 0.740 | 0.966 | 0.870 | 0.417 |
| 40:60 real:synthetic falls + real ADL | 0.902 | 0.845 | 0.959 | 0.793 | 0.967 | 0.877 | 0.274 |
| 50:50 real:synthetic falls + real ADL | 0.904 | 0.848 | 0.960 | 0.804 | 0.970 | 0.897 | 0.276 |
| 60:40 real:synthetic falls + real ADL | 0.902 | 0.842 | 0.962 | 0.801 | 0.971 | 0.919 | 0.273 |

## Interpretation

The new 40:60 and 60:40 ratios are exploratory because they were requested after the existing held-out results had already been inspected. Use validation performance or a new untouched subject set to select a ratio for a final confirmatory claim.

Seeds are averaged within each fold before paired Wilcoxon testing. Holm correction is applied across five planned pairwise comparisons per metric. With only five independent folds, emphasize effect sizes and fold consistency.
