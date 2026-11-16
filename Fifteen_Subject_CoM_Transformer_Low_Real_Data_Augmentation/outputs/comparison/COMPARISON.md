# Low-real-data augmentation comparison

Compared 150 runs across 25 matched fold/seed settings. The two 100% conditions are frozen references from the completed study.

## Descriptive result

The highest mean test-trial balanced accuracy was **100% real** (0.9433).

| Condition | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP/min ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 100% real | 0.943 | 0.909 | 0.978 | 0.881 | 0.987 | 0.960 | 0.170 |
| 25% real | 0.916 | 0.879 | 0.953 | 0.804 | 0.978 | 0.931 | 0.363 |
| 25% real + synthetic | 0.907 | 0.859 | 0.954 | 0.793 | 0.970 | 0.903 | 0.341 |
| 50% real | 0.936 | 0.920 | 0.953 | 0.835 | 0.983 | 0.944 | 0.336 |
| 50% real + synthetic | 0.906 | 0.851 | 0.961 | 0.801 | 0.973 | 0.920 | 0.261 |
| 100% real + synthetic | 0.904 | 0.848 | 0.960 | 0.804 | 0.970 | 0.897 | 0.276 |

## Paired augmentation tests for balanced accuracy

- 25%: mean augmented-minus-real-only = -0.0096; unadjusted p = 1.0000; Holm p = 1.0000.
- 50%: mean augmented-minus-real-only = -0.0304; unadjusted p = 0.4375; Holm p = 0.8750.

Seeds are averaged within each fold before testing. Holm correction is applied across the 25% and 50% augmentation comparisons separately for each metric. With only five folds, statistical inference is exploratory.

The recovery percentage is descriptive: it measures how much of the real-only gap to the frozen 100%-real reference was recovered by adding synthetic falls. Values can exceed 100% or be negative.
