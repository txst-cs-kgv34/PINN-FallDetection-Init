# Findings: Low-Real-Data Synthetic Augmentation

## Executive conclusion

The completed experiment does **not** support using the current synthetic A11 front-fall trajectories as a substitute for missing real falls in this detector configuration.

The best overall condition remained **100% real falls + real ADL**, with mean test-trial balanced accuracy of **0.9433**. Adding the quality-approved synthetic falls to reduced-real training did not recover the performance lost by removing real falls:

- at 25% real data, augmentation changed balanced accuracy from **0.9161 to 0.9065** (-0.96 percentage points);
- at 50% real data, augmentation changed balanced accuracy from **0.9364 to 0.9060** (-3.04 percentage points).

The augmented models produced slightly higher specificity and fewer false-positive events on average, but this came with lower fall sensitivity. Therefore, they became more conservative rather than better balanced fall detectors.

## Experiment integrity

The result archive contains the complete prespecified study:

- 4 new conditions × 5 subject-disjoint folds × 5 model seeds = **100 new runs**;
- 25 frozen 100%-real reference runs;
- 25 frozen full-data source-balanced reference runs;
- **150 total rows** across 25 matched fold/seed settings;
- real-only validation and test data in every condition;
- validation-only threshold selection;
- fixed real-fall membership across model seeds and paired conditions;
- 25% subsets nested inside the corresponding 50% subsets in every fold.

The selected real-fall counts were:

| Fold | Available training falls | 25% subset | 50% subset |
|---|---:|---:|---:|
| Fold 1 | 43 | 11 | 22 |
| Fold 2 | 43 | 11 | 22 |
| Fold 3 | 42 | 11 | 21 |
| Fold 4 | 40 | 10 | 20 |
| Fold 5 | 42 | 11 | 21 |

The subset audit found no nesting violations. The paired real-only and augmented conditions used the same real trajectories, so their difference isolates the addition of synthetic falls rather than a change in real-data membership.

## Six-condition result

Values below are means across the five subject-fold means after averaging the five training seeds within each fold.

| Training condition | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP events/min ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| **100% real** | **0.9433** | 0.9089 | **0.9778** | **0.8806** | **0.9873** | **0.9600** | **0.1699** |
| 50% real | 0.9364 | **0.9200** | 0.9527 | 0.8347 | 0.9831 | 0.9438 | 0.3355 |
| 25% real | 0.9161 | 0.8794 | 0.9527 | 0.8044 | 0.9780 | 0.9306 | 0.3633 |
| 25% real + synthetic | 0.9065 | 0.8587 | 0.9544 | 0.7932 | 0.9702 | 0.9026 | 0.3414 |
| 50% real + synthetic | 0.9060 | 0.8515 | 0.9605 | 0.8008 | 0.9731 | 0.9204 | 0.2609 |
| 100% real + synthetic (1:1) | 0.9037 | 0.8476 | 0.9598 | 0.8035 | 0.9704 | 0.8967 | 0.2760 |

The full-real model is the descriptive winner. It has the highest balanced accuracy, F1, AUROC, and AUPRC, while also producing the lowest mean false-positive burden.

## Direct effect of adding synthetic falls

The table below compares each augmented condition with its paired real-only condition. Positive values favor augmentation for the first six metrics; negative values favor augmentation for false-positive events.

| Real-data fraction | Δ balanced accuracy | Δ sensitivity | Δ specificity | Δ F1 | Δ AUROC | Δ AUPRC | Δ FP/min |
|---|---:|---:|---:|---:|---:|---:|---:|
| 25% | -0.0096 | -0.0207 | +0.0016 | -0.0113 | -0.0078 | -0.0279 | -0.0219 |
| 50% | -0.0304 | -0.0685 | +0.0078 | -0.0339 | -0.0100 | -0.0234 | -0.0746 |

At 25%, augmentation reduced fall sensitivity by 2.07 percentage points while specificity improved by only 0.16 points. At 50%, sensitivity fell by 6.85 points while specificity increased by 0.78 points. The sensitivity loss was therefore larger than the specificity gain, producing lower balanced accuracy.

The reduction in false-positive events is not evidence that the augmented detector is superior: it predicted falls less readily and consequently missed more real falls.

## Fold-level consistency

Balanced-accuracy changes from adding synthetic falls were:

| Held-out fold | 25% augmented − real-only | 50% augmented − real-only |
|---|---:|---:|
| Fold 1 | -0.0665 | -0.1095 |
| Fold 2 | -0.0225 | -0.0333 |
| Fold 3 | +0.0345 | +0.0481 |
| Fold 4 | -0.0269 | -0.0686 |
| Fold 5 | +0.0337 | +0.0115 |

Augmentation helped balanced accuracy in Folds 3 and 5 but hurt it in Folds 1, 2, and 4 at both fractions. The most pronounced harm occurred in Fold 1, where sensitivity dropped substantially. This subject-dependent behavior indicates that the synthetic distribution does not generalize uniformly across held-out subject groups.

## Statistical interpretation

No paired comparison was significant after Holm correction at 0.05.

For balanced accuracy:

- 25% real: unadjusted Wilcoxon p = **1.0000**, Holm-adjusted p = **1.0000**;
- 50% real: unadjusted Wilcoxon p = **0.4375**, Holm-adjusted p = **0.8750**.

No Holm-adjusted test for sensitivity, specificity, F1, AUROC, AUPRC, or false-positive events was below 0.05 either. The five independent units are the subject-disjoint folds; model seeds are averaged within folds and are not treated as additional independent samples.

With only five folds, a two-sided exact Wilcoxon test has very low resolution—the smallest possible p-value when all five nonzero differences point in one direction is 0.0625. Therefore, these p-values cannot establish equivalence or prove that augmentation never helps. The descriptive effect direction, fold consistency, and agreement with the earlier full-data source-balanced experiment are more informative here.

## What this experiment teaches us

### 1. Real falls are highly data-efficient for this task

Using only 50% of the real training falls achieved balanced accuracy of **0.9364**, only 0.70 percentage points below the full-real model. Even 25% real retained balanced accuracy of **0.9161**.

However, balanced accuracy alone hides remaining weaknesses. Compared with full-real training:

- 50% real reduced F1 by 4.59 points and added 0.166 false-positive events per ADL minute;
- 25% real reduced F1 by 7.62 points and added 0.193 false-positive events per ADL minute.

Thus 50% real is close to full-real on average balanced accuracy, but it is not a complete replacement for the full real dataset.

### 2. Trajectory-quality approval does not guarantee detector utility

The synthetic trajectories passed the trajectory-quality gate by resembling real trajectories under RMSE, DTW, kinematic, phase, and boundary-continuity criteria. That establishes physical and trajectory plausibility. It does **not** establish that the samples add new discriminative information for separating falls from ADLs in unseen subjects.

This downstream experiment supplies that missing task-utility test. Under the present CoM representation and Transformer, the approved synthetic set did not improve held-out real-subject detection.

### 3. Synthetic-pool dominance was not the explanation

The augmented batches forced an exact 32 ADL / 16 real-fall / 16 synthetic-fall composition. Therefore, the negative result cannot be attributed simply to the 226-sample synthetic pool numerically crowding out the smaller real-fall pool. The model saw equal numbers of real and synthetic fall windows inside every augmented training batch.

### 4. The current synthetic falls appear to regularize toward conservatism

Across the reduced-data studies, synthetic augmentation slightly improved specificity and reduced mean false-positive burden, but consistently weakened sensitivity, balanced accuracy, F1, AUROC, and AUPRC on average. A plausible interpretation is that the synthetic fall distribution narrows or shifts the learned positive class in a way that makes the decision rule less responsive to some real held-out falls.

This is an inference from the observed metric pattern, not a directly measured mechanism.

### 5. Generating more samples from the same generator is not justified now

More trajectories from the same generator and selection rule would increase sample count without evidence that they provide the missing subject-specific fall variability. The present results do not support generating more of the same synthetic data for this detector.

## Recommended decision

Use **100% real falls + real ADL** as the current primary detector configuration. Retain the synthetic dataset and its quality-verification results as an important negative downstream result: physically plausible generation was achieved, but downstream detection utility was not demonstrated.

The next detector experiment should address ADL false alarms using a prespecified activity-balanced or hard-negative ADL training policy. It should be trained with real falls and compared with the frozen full-real baseline using the same folds and seeds.

To avoid adaptive test leakage, do not target A02, A05, or A08 merely because they were difficult in the current held-out test reports. Define the ADL sampling rule from training data only, or use a test-independent rule such as equal sampling across available training activity types. If the same held-out folds continue to guide experiment design, final results should be described as exploratory unless a new untouched test set is reserved.

## What not to claim

The supported conclusion is narrow:

> The current quality-approved synthetic A11 trajectories, mixed 1:1 with real falls in the positive half of each batch, did not improve this CoM Transformer on the existing real-subject test folds at 25%, 50%, or 100% real-data availability.

The experiment does not prove that all synthetic fall data are ineffective. It did not test:

- a lower synthetic proportion such as 3:1 real-to-synthetic;
- a different generator or a diversity-aware generator objective;
- alternative synthetic quality criteria optimized for detector usefulness;
- other fall directions;
- another detector architecture;
- multiple independent real-subset selections per fold.

Any future mixture ratio or generator choice must be selected using training/validation subjects only, never by choosing the best result on these test folds.

## Result files

Primary evidence is stored under `outputs/comparison/`:

- `six_condition_summary.csv` — six-condition means and standard deviations;
- `six_condition_fold_seed_averaged_metrics.csv` — fold-level values used for inference;
- `augmentation_vs_real_only_wilcoxon_holm.csv` — paired Wilcoxon and Holm results;
- `augmentation_recovery_by_fold.csv` — descriptive recovery calculations;
- `foldwise_augmentation_gain.png` — per-fold augmentation effects;
- `augmentation_recovery_curves.png` — performance versus real-data fraction;
- `false_positive_burden.png` — false-positive trade-offs.
