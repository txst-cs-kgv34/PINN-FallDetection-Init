# Source-Balanced Augmentation Findings

## Experiment status

Completed on November 14, 2026. All 25 source-balanced runs finished:

- five subject-disjoint folds;
- five fixed seeds per fold: 11, 22, 33, 44, and 55;
- 32 real-ADL, 16 real-fall, and 16 synthetic-fall windows per training batch;
- real-only validation and test data;
- 100 matched runs in the final four-scenario comparison (75 prior + 25 new).

## Main conclusion

**Real falls + real ADL remains the winning full-data scenario.** It achieved the
highest mean test-trial balanced accuracy, sensitivity, F1, AUROC, and AUPRC, and
the lowest false-positive burden.

The source-balanced 1:1 condition was the best scenario that used synthetic falls.
It improved over both synthetic-only training and the original synthetic-heavy
combined condition, but it did not outperform real-only training.

Therefore, source balancing corrected part of the original combined condition's
problem, but the current synthetic falls cannot yet be claimed to improve a
detector that already has access to all real training falls.

## Four-scenario results

Values are means across the five fold means after averaging the five seeds within
each fold.

| Training scenario | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP events/ADL min ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Real falls + real ADL** | **0.943** | **0.909** | **0.978** | **0.881** | **0.987** | **0.960** | **0.170** |
| Synthetic falls + real ADL | 0.878 | 0.826 | 0.929 | 0.714 | 0.962 | 0.825 | 0.463 |
| Original combined + real ADL | 0.886 | 0.834 | 0.938 | 0.740 | 0.966 | 0.870 | 0.417 |
| **Source-balanced 1:1 + real ADL** | **0.904** | **0.848** | **0.960** | **0.804** | **0.970** | **0.897** | **0.276** |

## What source balancing changed

Compared with the original combined condition, the balanced 1:1 sampler produced:

- **+1.77 percentage points** balanced accuracy;
- **+1.40 points** sensitivity;
- **+2.14 points** specificity;
- **+6.33 points** F1;
- **+2.65 points** AUPRC;
- **0.141 fewer false-positive events per ADL minute**, a 33.9% reduction.

Balanced accuracy improved in four of five folds relative to the original combined
condition. F1, AUROC, AUPRC, and false-positive burden were also favorable in four
of five folds. This is meaningful descriptive evidence that a synthetic-heavy
positive pool was hurting the earlier combined model.

However, compared with real-only training, balanced 1:1 was lower by:

- **3.96 percentage points** balanced accuracy;
- **6.13 points** sensitivity;
- **1.80 points** specificity;
- **7.71 points** F1;
- **6.33 points** AUPRC;
- and it produced **0.106 more false-positive events per ADL minute**.

Balanced 1:1 exceeded real-only balanced accuracy in only Fold 3. Real-only was
better in the other four folds and had higher AUROC and AUPRC in every fold.

## Statistical interpretation

No comparison passed the Holm-adjusted 0.05 threshold. For balanced accuracy:

| Balanced 1:1 comparison | Mean difference | Unadjusted p | Holm-adjusted p |
|---|---:|---:|---:|
| versus real-only | −0.0396 | 0.1250 | 0.3750 |
| versus synthetic-only | +0.0260 | 0.3125 | 0.6250 |
| versus original combined | +0.0177 | 0.3125 | 0.6250 |

The absence of statistical significance must not be interpreted as equivalence.
There are only five independent fold-level pairs. With five nonzero pairs, the
smallest possible exact two-sided Wilcoxon p-value is 0.0625 even if all five
differences have the same direction; Holm correction increases it further.
Consequently, effect direction, magnitude, and fold consistency are more
informative here than a binary p < 0.05 decision.

## Fold and error analysis

- **Fold 1 remains the hardest synthetic-data fold.** Balanced 1:1 achieved 0.792
  balanced accuracy and 0.615 sensitivity, compared with 0.847 and 0.708 for
  real-only. S44 A11 trials T02, T03, and T04 were false negatives for all five
  balanced seeds. The Fold 1 validation-selected thresholds were also high
  (mean 0.975), indicating calibration transfer difficulty rather than use of an
  arbitrary test threshold.
- **Fold 4 is the only fold where balancing reduced performance relative to the
  original combined condition.** Balanced accuracy fell by 2.67 points, driven by
  a 5.33-point sensitivity decrease while specificity was unchanged.
- **Fold 5 has the largest false-positive problem.** Balanced 1:1 produced 0.889
  false-positive events per ADL minute. It improved over the original combined
  condition (0.964), but remained worse than real-only (0.538). Fold 5 also had
  unstable validation thresholds across seeds and the largest seed-to-seed
  false-positive variation.
- Repeated hard-negative ADLs include A02, A05, and A08/walking. Examples include
  S31 A02 T02 (false positive for all five balanced seeds), S49 A08 T01 and A02
  T05, S46 A02 T02, and several S45/S55 A05 and A08 trials.

These errors show two distinct issues: some real falls do not resemble the
synthetic training distribution closely enough, and several high-motion ADLs look
fall-like to the detector.

## Completed activity- and subject-level error report

The dedicated report in `outputs/error_analysis/ERROR_ANALYSIS.md` analyzes 12,300
held-out trial-seed predictions across all 100 runs. Its principal results are:

- Balanced 1:1 produced 111 ADL false-positive decisions. A02 Pick Up Object,
  A05 Sweeping Floor, and A08 TUG/Walking accounted for 105/111 (94.6%).
- The original combined scenario produced 170 ADL false positives and 56 real-fall
  false negatives. Source balancing reduced these to 111 and 52.
- Real-only produced only 61 ADL false positives and 30 fall false negatives.
- Against the original combined scenario, balancing corrected 94 ADL decisions
  while introducing 35, and corrected 21 fall decisions while introducing 17.
- Against real-only, balancing corrected only 21 ADL decisions while introducing
  71, and corrected 5 fall decisions while introducing 27.
- S45 had the highest Balanced 1:1 ADL false-positive rate (18.0%). S44 had the
  highest fall false-negative rate (72.0%), followed by S30 (52.0%), S49 (46.7%),
  and S32 (28.0%).
- Fold 5 remained unstable: its validation threshold was 0.590 ± 0.438 across
  seeds and it produced 0.889 false-positive events per ADL minute.
- Mean test-trial Brier score improved from 0.129 for the original combined model
  to 0.117 after balancing, but real-only remained substantially better calibrated
  at 0.037.

The report includes activity and subject summaries, trial-level seed consistency,
window-level false-positive events, scenario error transitions, calibration
tables, hard-example lists, and five figures. This task required no model reruns.

## Recommended next steps

### 1. Freeze the present conclusion

Retain these 100 runs unchanged. For the current full-real-data study, use
**real falls + real ADL as the primary detector result**. Report balanced 1:1 as
the best synthetic-inclusive ablation and as evidence that source quotas matter.

### 2. Run a low-real-data augmentation study next

This is the most informative next experiment. Synthetic data is primarily useful
when real falls are scarce; requiring it to beat a model trained with every
available real fall is a much harder and less direct question.

Use fixed real-fall fractions such as 25% and 50%. At each fraction, compare:

1. reduced real falls + real ADL;
2. the exact same reduced real-fall subset + balanced synthetic falls + real ADL.

Keep the current subject-disjoint folds, five seeds, real-only validation/test
sets, and 1:1 real/synthetic fall quota. The real-fall subset must be created from
training subjects only and shared between the paired scenarios. Any ratio or
checkpoint selection must use validation subjects only. This directly tests
whether synthetic falls recover performance lost when real falls are limited.

### 3. Keep hard-negative sampling as a separate later ablation

The error report identifies A02, A05, and A08 as the main ADL confusion classes.
Do not add activity-aware sampling to the first low-real-data study because it
would confound the synthetic-augmentation effect. If false positives remain a
limitation afterward, train one new activity-aware condition using only
training/validation subjects to define and select hard negatives.

### 4. Do not generate more of the same synthetic distribution yet

The experiment already used 226 quality-approved synthetic falls. The limitation
is not simply sample count: adding them without source control degraded the model,
and balancing only partially closed the real-only gap. Generate more trajectories
only after identifying underrepresented **training/validation** kinematic regimes
and updating the generator to target those regimes.

### 5. Protect the test set in any follow-up

The current held-out-fold results have now been inspected. They may guide an
exploratory follow-up, but repeated tuning against these same test folds would
create leakage. A final confirmatory claim should use new untouched subjects or a
nested procedure in which augmentation choices are made only on inner validation
subjects.

## Thesis-ready summary

Equalizing real and synthetic fall exposure improved the synthetic-inclusive
detector relative to the original synthetic-heavy mixture, increasing balanced
accuracy from 0.886 to 0.904 and reducing false-positive burden from 0.417 to
0.276 events per ADL minute. Nevertheless, real-only training remained strongest
at 0.943 balanced accuracy and 0.170 false-positive events per minute. Thus,
source balancing mitigated but did not eliminate the synthetic-to-real domain gap.
