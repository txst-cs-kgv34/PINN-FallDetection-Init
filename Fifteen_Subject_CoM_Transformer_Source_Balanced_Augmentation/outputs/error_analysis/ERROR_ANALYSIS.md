# Activity- and Subject-Level Error Analysis

## Scope

This report analyzes 12,300 held-out trial-seed predictions from 100 completed runs. All results are post-hoc and descriptive; no model was retrained.

## Key findings

- Balanced 1:1 made 111 false-positive ADL decisions. A02, A05, and A08 accounted for 105/111 (94.6%) of them.
- Source balancing reduced ADL false positives from 170 in the original combined scenario to 111, and reduced real-fall false negatives from 56 to 52.
- Real-only still made fewer errors: 61 ADL false positives and 30 fall false negatives, versus 111 and 52 for Balanced 1:1.
- The failure is concentrated rather than global: most ADL activities have near-zero false-positive rates, while S44, S30, S49, and S32 account for most missed A11 falls.
- Fold 5 is a calibration-stability problem: its Balanced 1:1 threshold was 0.590 ± 0.438 across seeds and it produced 0.889 false-positive events per ADL minute.
- Mean test-trial Brier score improved from 0.129 for the original combined condition to 0.117 after balancing, but real-only remained much better calibrated at 0.037.

## Balanced 1:1 activity-level false positives

| Activity | Unique trials | FP observations | FP rate | Mean probability |
|---|---:|---:|---:|---:|
| A08 — TUG Test/Walking | 64 | 45/320 | 14.1% | 0.491 |
| A02 — Pick Up Object | 72 | 42/360 | 11.7% | 0.412 |
| A05 — Sweeping Floor | 70 | 18/350 | 5.1% | 0.256 |
| A09 — Sit/Stand | 69 | 4/345 | 1.2% | 0.208 |
| A03 — Put On/Take Off Jacket | 66 | 2/330 | 0.6% | 0.030 |
| A01 — Drinking Water | 69 | 0/345 | 0.0% | 0.010 |
| A07 — Waving Hand | 69 | 0/345 | 0.0% | 0.014 |
| A06 — Washing Hand | 66 | 0/330 | 0.0% | 0.011 |

## Balanced 1:1 subjects with the highest error rates

| Error type | Subject | Unique trials | Error rate |
|---|---|---:|---:|
| ADL false positive | S45 | 40 | 18.0% |
| ADL false positive | S31 | 31 | 11.0% |
| ADL false positive | S49 | 39 | 8.2% |
| ADL false positive | S55 | 40 | 8.0% |
| ADL false positive | S46 | 39 | 5.1% |
| ADL false positive | S63 | 40 | 2.5% |
| ADL false positive | S57 | 37 | 1.6% |
| ADL false positive | S43 | 40 | 1.5% |
| A11 false negative | S44 | 5 | 72.0% |
| A11 false negative | S30 | 5 | 52.0% |
| A11 false negative | S49 | 3 | 46.7% |
| A11 false negative | S32 | 5 | 28.0% |
| A11 false negative | S46 | 5 | 8.0% |
| A11 false negative | S45 | 5 | 8.0% |
| A11 false negative | S43 | 4 | 5.0% |
| A11 false negative | S62 | 5 | 4.0% |

## Most consistent balanced 1:1 errors

### ADL false positives

| Trial | Activity | Subject | Error seeds | Mean probability | Mean threshold |
|---|---|---|---:|---:|---:|
| ADL_S31A02T02 | A02 — Pick Up Object | S31 | 5/5 | 0.959 | 0.590 |
| ADL_S49A08T01 | A08 — TUG Test/Walking | S49 | 4/5 | 0.986 | 0.975 |
| ADL_S49A02T05 | A02 — Pick Up Object | S49 | 4/5 | 0.983 | 0.975 |
| ADL_S46A02T02 | A02 — Pick Up Object | S46 | 4/5 | 0.976 | 0.943 |
| ADL_S45A02T01 | A02 — Pick Up Object | S45 | 4/5 | 0.938 | 0.590 |
| ADL_S55A08T03 | A08 — TUG Test/Walking | S55 | 4/5 | 0.931 | 0.590 |
| ADL_S45A02T05 | A02 — Pick Up Object | S45 | 4/5 | 0.929 | 0.590 |
| ADL_S45A05T03 | A05 — Sweeping Floor | S45 | 4/5 | 0.929 | 0.590 |
| ADL_S49A02T03 | A02 — Pick Up Object | S49 | 3/5 | 0.966 | 0.975 |
| ADL_S49A02T02 | A02 — Pick Up Object | S49 | 3/5 | 0.965 | 0.975 |

### Real A11 false negatives

| Trial | Subject | Error seeds | Mean probability | Mean threshold |
|---|---|---:|---:|---:|
| REAL_S44A11T04 | S44 | 5/5 | 0.003 | 0.975 |
| REAL_S44A11T03 | S44 | 5/5 | 0.005 | 0.975 |
| REAL_S44A11T02 | S44 | 5/5 | 0.594 | 0.975 |
| REAL_S30A11T03 | S30 | 5/5 | 0.901 | 0.987 |
| REAL_S49A11T04 | S49 | 4/5 | 0.325 | 0.975 |
| REAL_S32A11T04 | S32 | 3/5 | 0.912 | 0.948 |
| REAL_S32A11T05 | S32 | 3/5 | 0.938 | 0.948 |
| REAL_S30A11T05 | S30 | 2/5 | 0.950 | 0.987 |
| REAL_S44A11T01 | S44 | 2/5 | 0.975 | 0.975 |
| REAL_S49A11T02 | S49 | 2/5 | 0.977 | 0.975 |

## What balancing corrected or introduced

Counts below are paired trial-seed decisions. A correction means the reference scenario was wrong and Balanced 1:1 was correct; an introduction is the reverse.

| Reference | Class | Corrected | Introduced | Wrong in both |
|---|---|---:|---:|---:|
| Real | ADL | 21 | 71 | 40 |
| Real | A11 fall | 5 | 27 | 25 |
| Synthetic | ADL | 116 | 32 | 79 |
| Synthetic | A11 fall | 21 | 15 | 37 |
| Combined | ADL | 94 | 35 | 76 |
| Combined | A11 fall | 21 | 17 | 35 |

## Fold calibration for Balanced 1:1

| Fold | Threshold mean ± SD | Brier score | ECE | FP events/ADL min |
|---|---:|---:|---:|---:|
| fold_01 | 0.975 ± 0.011 | 0.116 | 0.125 | 0.205 |
| fold_02 | 0.943 ± 0.034 | 0.139 | 0.189 | 0.156 |
| fold_03 | 0.948 ± 0.040 | 0.090 | 0.142 | 0.116 |
| fold_04 | 0.987 ± 0.006 | 0.123 | 0.170 | 0.014 |
| fold_05 | 0.590 ± 0.438 | 0.119 | 0.163 | 0.889 |

## Decision and next experiment

### Decision from this report

Source balancing corrected many errors from the synthetic-heavy combined model, especially A02/A05/A08 false positives, but it still introduced substantially more errors than real-only training. The error pattern does not justify generating more of the same synthetic distribution or changing several components at once.

### Recommended next controlled study: low-real-data augmentation

Use two fixed training-data fractions, 25% and 50% of the real A11 training falls. At each fraction compare: (1) reduced real falls + real ADL and (2) the identical reduced-real subset + source-balanced synthetic falls + real ADL. This requires four new conditions, or 100 new runs with five folds and five seeds. Reuse the existing four full-data scenarios as frozen references; do not rerun them.

Use one deterministic subject-stratified real-fall subset per fold and fraction, shared by the paired conditions. Keep training seeds for model initialization rather than changing the data subset. Preserve real-only validation/test data and validation-only threshold and checkpoint selection.

Do not add hard-negative sampling to this first low-real study because that would confound the effect of synthetic augmentation. If false positives remain the main limitation afterward, run a separate activity-aware ADL sampling ablation focused on A02, A05, and A08.

### Leakage safeguards

1. Preserve the four existing scenarios; this analysis does not require rerunning them.
2. Treat the listed test-trial errors as descriptive evidence, not as samples that may be directly selected for retraining. Any hard-negative selection in a new experiment must operate on training/validation subjects only.
3. A final confirmatory claim should use new untouched subjects or nested validation because the present held-out-fold errors have now been inspected.

## Output files

See the CSV tables in this directory for complete activity, subject, trial, transition, window-event, and fold-calibration results. Figures provide compact comparisons.
