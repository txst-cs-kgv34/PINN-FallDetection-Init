# Findings: Fall-Source Ratio Ablation

## Executive conclusion

Changing the real-to-synthetic fall ratio from 50:50 to either 40:60 or
60:40 did **not improve overall thresholded fall-detection performance**.
The three mixed-source ratios produced nearly identical mean balanced
accuracy:

- 40:60: 0.9023
- 50:50: 0.9037
- 60:40: 0.9022

The frozen 50:50 condition retained the highest mixed-source balanced
accuracy and F1. The 60:40 condition produced the highest AUPRC and
specificity among the mixed-source ratios, but this ranking improvement did
not translate into better balanced accuracy, sensitivity, or F1 at the
validation-selected threshold.

The primary full-data detector therefore remains **real falls + real ADL**.
If one mixed-source condition is reported as the main synthetic-inclusive
configuration, retain **50:50** because it has the best overall thresholded
metric balance. Report 60:40 as a useful secondary ablation showing improved
precision-recall ranking, not as a new overall winner.

## Experiment verification

The package contains all 50 requested new runs:

- 25 runs for 40:60: five subject-disjoint folds × five seeds;
- 25 runs for 60:40: five subject-disjoint folds × five seeds;
- complete metrics, validation/test predictions, and training histories for
  every run;
- 25 matched fold/seed settings across all six compared scenarios.

The batch implementation also matches the intended design:

| Target ratio | Real falls per epoch | Synthetic falls per epoch | Effective ratio |
|---|---:|---:|---:|
| 40:60 | 410 | 614 | 40.039% : 59.961% |
| 60:40 | 614 | 410 | 59.961% : 40.039% |

Both conditions retained 32 real-ADL windows and 32 fall windows per batch.
Thus batch size, class balance, folds, seeds, architecture, optimizer, training
steps, and validation procedure were held fixed.

## Main three-ratio result

Values are means across the five fold means after averaging the five seeds
inside each fold.

| Real:synthetic fall ratio | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP events/min ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| 40:60 | 0.9023 | 0.8451 | 0.9594 | 0.7932 | 0.9673 | 0.8771 | 0.2738 |
| **50:50** | **0.9037** | **0.8476** | 0.9598 | **0.8035** | 0.9704 | 0.8967 | 0.2760 |
| 60:40 | 0.9022 | 0.8421 | **0.9623** | 0.8013 | **0.9707** | **0.9187** | **0.2730** |

Relative to 50:50:

| Candidate | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP events/min |
|---|---:|---:|---:|---:|---:|---:|---:|
| 40:60 minus 50:50 | −0.145 pp | −0.251 pp | −0.039 pp | −1.026 pp | −0.313 pp | −1.962 pp | −0.0021 |
| 60:40 minus 50:50 | −0.153 pp | −0.555 pp | +0.250 pp | −0.223 pp | +0.027 pp | +2.196 pp | −0.0030 |

The practical interpretation is that the thresholded classifier is insensitive
to moderate source-ratio changes between 40% and 60% real falls. None of the
new ratios solves the remaining mixed-source gap.

## Fold-level behavior

### Balanced accuracy

| Fold | 40:60 | 50:50 | 60:40 | Best ratio |
|---|---:|---:|---:|---|
| Fold 1 | 0.7853 | **0.7921** | 0.7754 | 50:50 |
| Fold 2 | **0.9811** | 0.9651 | 0.9794 | 40:60 |
| Fold 3 | 0.9341 | 0.9378 | **0.9467** | 60:40 |
| Fold 4 | 0.8791 | **0.8991** | 0.8857 | 50:50 |
| Fold 5 | **0.9317** | 0.9245 | 0.9236 | 40:60 |

No ratio won consistently across subjects. The 50:50 ratio won two folds,
40:60 won two, and 60:40 won one. Fold 1 remained the most difficult
mixed-source fold, while Fold 5 retained the largest false-positive burden.

### AUPRC trend

The strongest directional result was AUPRC. The 60:40 ratio exceeded 40:60 in
all five folds and exceeded 50:50 in four of five folds:

| Fold | 40:60 | 50:50 | 60:40 |
|---|---:|---:|---:|
| Fold 1 | 0.6934 | 0.6898 | **0.7501** |
| Fold 2 | 0.9807 | 0.9990 | **1.0000** |
| Fold 3 | 0.9509 | 0.9155 | **0.9536** |
| Fold 4 | 0.9456 | 0.9593 | **0.9719** |
| Fold 5 | 0.8148 | **0.9199** | 0.9177 |

This suggests that increasing the real-fall share improved probability ranking
between falls and ADLs. However, the selected operating threshold still missed
slightly more falls, so the higher AUPRC did not yield higher balanced accuracy
or F1.

## Error behavior

Across the same 3,075 held-out trial-seed decisions per ratio:

| Ratio | ADL false-positive decisions | Fall false-negative decisions | Total error decisions |
|---|---:|---:|---:|
| 40:60 | 112 | 53 | 165 |
| 50:50 | 111 | **52** | 163 |
| 60:40 | **104** | 54 | **158** |

The 60:40 ratio reduced ADL false-positive decisions, but it also increased
missed-fall decisions. This is consistent with its slightly higher specificity
and lower sensitivity.

The dominant false-positive activities did not change:

| Ratio | A02 FP | A05 FP | A08 FP | Share of all ratio FPs from A02/A05/A08 |
|---|---:|---:|---:|---:|
| 40:60 | 40 | 25 | 43 | 96.4% |
| 50:50 | 42 | 18 | 45 | 94.6% |
| 60:40 | 30 | 20 | 51 | 97.1% |

Increasing the real-fall share reduced A02 errors but increased A08 errors.
It therefore shifted the error distribution rather than eliminating the
hard-negative problem.

The most frequently missed fall subjects also remained the same. Under 60:40,
S44, S30, and S49 still accounted for most missed falls. The ratio change
improved S32 but worsened S44 and S30 relative to 50:50.

Direct trial-decision transitions confirm that corrections and newly introduced
errors nearly canceled:

| Candidate versus 50:50 | ADL corrected | ADL broken | Falls corrected | Falls broken |
|---|---:|---:|---:|---:|
| 40:60 | 30 | 31 | 11 | 12 |
| 60:40 | 43 | 36 | 10 | 12 |

## Statistical interpretation

No comparison was significant after Holm correction.

Key paired results:

- 40:60 versus 50:50 balanced accuracy: unadjusted p = 1.0000;
- 60:40 versus 50:50 balanced accuracy: unadjusted p = 0.8125;
- 60:40 versus 40:60 AUPRC: unadjusted p = 0.0625,
  Holm-adjusted p = 0.3125;
- real-only versus each new ratio F1: unadjusted p = 0.0625,
  Holm-adjusted p = 0.3125.

With only five independent folds, the smallest possible exact two-sided
Wilcoxon p-value is 0.0625. The all-fold AUPRC direction favoring 60:40 is
therefore worth reporting as a trend, but it is not statistically confirmed.

## Six-scenario conclusion

| Scenario | Balanced accuracy | Sensitivity | Specificity | F1 | AUPRC | FP events/min ↓ |
|---|---:|---:|---:|---:|---:|---:|
| **Real falls + real ADL** | **0.9433** | **0.9089** | **0.9778** | **0.8806** | **0.9600** | **0.1699** |
| Synthetic falls + real ADL | 0.8777 | 0.8261 | 0.9293 | 0.7135 | 0.8247 | 0.4633 |
| Original combined + real ADL | 0.8860 | 0.8337 | 0.9384 | 0.7402 | 0.8702 | 0.4174 |
| 40:60 + real ADL | 0.9023 | 0.8451 | 0.9594 | 0.7932 | 0.8771 | 0.2738 |
| **50:50 + real ADL** | **0.9037** | **0.8476** | 0.9598 | **0.8035** | 0.8967 | 0.2760 |
| 60:40 + real ADL | 0.9022 | 0.8421 | **0.9623** | 0.8013 | **0.9187** | **0.2730** |

Real-only remains clearly strongest. Source balancing substantially improves
the original synthetic-heavy combined condition, but changing the balanced
mixture within the tested 40:60–60:40 range does not close the remaining gap.

## Final reporting recommendation

The thesis/advisor conclusion should be:

> Source balancing was beneficial relative to naïvely pooling real and
> synthetic falls, but performance was not sensitive to moderate ratio changes
> between 40:60, 50:50, and 60:40. The 50:50 ratio gave the best overall
> thresholded metric balance, whereas 60:40 improved AUPRC without improving
> balanced accuracy. Real-only training remained the strongest full-data
> detector.

Because the ratios were proposed after earlier test results had been inspected,
this analysis is exploratory. It should be described as a ratio-sensitivity
ablation, not as independent test-set selection of an optimal ratio.
