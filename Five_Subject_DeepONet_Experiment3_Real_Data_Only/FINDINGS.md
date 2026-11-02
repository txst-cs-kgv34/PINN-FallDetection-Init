# Experiment 3 findings — Model A: real data-only DeepONet

## Bottom line

Model A established a useful real-data baseline. It generalized better than the
synthetic-only subject-PINN distillation model on every subject-averaged metric,
but it was consistently weaker than Model B, which used the same real data plus
the explicit cart-pole residual.

The result separates two conclusions:

1. Direct exposure to real human trajectories was more useful than the current
   synthetic-only distillation procedure.
2. Real data alone was not sufficient to obtain the best result; explicit
   physics provided an additional improvement.

## Protocol verification

| Check | Result |
|:---|:---|
| Completed folds | 5 of 5 |
| Device | Apple MPS |
| Training source | Real trajectories only |
| Physics residual | Disabled |
| Teacher gains/checkpoints | Not used |
| Controller representation | Four-dimensional latent context vector |
| Training subjects per fold | 3 |
| Real training trials per fold | 11–13 |
| Total real test trials | 20 |
| Total forecast samples | 2,838 |
| Validation/test leakage | Not observed in manifests |

The same two short trials excluded elsewhere—S63A11T05 and S62A11T02—were
excluded here because they could not supply 0.40 seconds of context.

## Held-out subject results

| Test subject | Trials | Forecast samples | Normalized MSE | Theta RMSE (deg) | Theta MAE (deg) | x RMSE (cm) | x MAE (cm) |
|:---:|---:|---:|---:|---:|---:|---:|---:|
| S43 | 4 | 1,013 | 0.802 | 12.360 | 10.176 | 18.660 | 15.891 |
| S63 | 4 | 218 | 0.214 | 6.180 | 4.728 | 9.772 | 7.588 |
| S55 | 5 | 424 | 0.208 | 5.696 | 4.396 | 9.867 | 7.441 |
| S57 | 3 | 489 | 0.495 | 8.326 | 6.761 | 15.503 | 12.530 |
| S62 | 4 | 694 | 0.321 | 5.620 | 4.190 | 13.008 | 10.259 |

S43 was the main failure case: it had the largest error for every primary
metric. S57 was the second most difficult in normalized and x error. Performance
on S63 and S55 was comparatively stable.

## Subject-equal aggregate

| Metric | Model A mean ± subject SD |
|:---|---:|
| Normalized MSE | 0.408 ± 0.249 |
| Theta RMSE (deg) | 7.636 ± 2.861 |
| Theta MAE (deg) | 6.050 ± 2.524 |
| x RMSE (cm) | 13.362 ± 3.804 |
| x MAE (cm) | 10.742 ± 3.563 |
| Theta W1 (deg) | 4.499 ± 3.353 |
| x W1 (cm) | 7.475 ± 4.895 |

The relatively large SDs show that data-only generalization remained strongly
subject dependent.

## Model A versus direct physics Model B

| Metric | A: real data-only | B: real + physics | B improvement |
|:---|---:|---:|---:|
| Normalized MSE | 0.408 | 0.234 | 42.73% |
| Theta RMSE (deg) | 7.636 | 6.844 | 10.38% |
| Theta MAE (deg) | 6.050 | 5.162 | 14.68% |
| x RMSE (cm) | 13.362 | 9.808 | 26.60% |
| x MAE (cm) | 10.742 | 7.403 | 31.08% |
| Theta W1 (deg) | 4.499 | 3.786 | 15.84% |
| x W1 (cm) | 7.475 | 5.044 | 32.52% |

B improved normalized MSE and x RMSE for all five held-out subjects. It
improved theta RMSE for four of five subjects, with S62 as the exception. Since
the two models share real training data and the main backbone, this provides the
cleanest current evidence for the value of the physics-informed formulation.
However, it is not a pure residual-only ablation: A uses a latent vector and B
uses a positive physical-gain head. A future B variant with the same gain head
but `physics_weight=0` is required to isolate only the residual term.

## Model A versus synthetic-only Model C

| Metric | A | C: subject-PINN distillation | A improvement over C |
|:---|---:|---:|---:|
| Normalized MSE | 0.408 | 0.778 | 47.58% |
| Theta RMSE (deg) | 7.636 | 11.620 | 34.28% |
| Theta MAE (deg) | 6.050 | 8.992 | 32.72% |
| x RMSE (cm) | 13.362 | 16.379 | 18.42% |
| x MAE (cm) | 10.742 | 12.987 | 17.29% |
| Theta W1 (deg) | 4.499 | 7.812 | 42.41% |
| x W1 (cm) | 7.475 | 10.508 | 28.86% |

This result shows that direct exposure to real motion was more valuable than
the current synthetic-only teacher distribution. It does not isolate physics,
because C differs from A in both training source and loss composition.

## Model A versus hybrid Model D

D was 3.97% better in theta RMSE, 9.85% better in theta MAE, and 6.91% better
in theta W1. A was 16.19% better in normalized MSE, 7.30% better in x RMSE,
5.33% better in x MAE, and 15.89% better in x W1.

Thus, the hybrid objective improved angular prediction but degraded forward-x
prediction and overall normalized error. This is a mixed result, not evidence
that adding synthetic data generally helps a real-data model.

## Latent-vector interpretation

Model A's four context values are unconstrained latent variables. They are not
`Kp` or `Kd`, and their numerical values must not be compared with the gains
reported by Models B, C, or D. Their purpose is only to convey early-motion
information into the branch network.

The fact that A performs reasonably well confirms that the common context
encoder and forward operator can learn useful multi-subject structure without
an explicit gain interpretation. The further improvement from B indicates that
the physics-constrained version was a better inductive bias for this dataset.

## Training behavior

| Fold / test subject | Selected epoch | Last epoch | Validation normalized MSE |
|:---|---:|---:|---:|
| 1 / S43 | 16 | 116 | 0.109 |
| 2 / S63 | 201 | 301 | 0.196 |
| 3 / S55 | 216 | 316 | 0.328 |
| 4 / S57 | 87 | 187 | 0.116 |
| 5 / S62 | 24 | 124 | 0.507 |

The widely varying selected epochs are consistent with the small real training
set and fold-specific domain differences. Every fold respected the 100-epoch
early-stopping patience.

## Conclusions and next steps

1. Retain Model A as the required data-only ablation.
2. Use A versus B as the main comparison for whether the physics-informed
   formulation adds value, not as a residual-only ablation.
3. Report that real-only training outperformed synthetic-only distillation on
   the current five-subject dataset.
4. Do not use Model A's latent vector as a physical parameter estimate.
5. Repeat with multiple seeds and more subjects before inferential claims.
6. Consider subject-balanced augmentation of real trajectories, but preserve
   subject-level splits and avoid treating overlapping windows as independent
   subjects.

## Supporting files

- `results/full/aggregate_summary.json`
- `results/full/cross_fold_metrics.csv`
- `results/full/cross_fold_results.png`
- `results/full/fold_*/training_selection.json`
- `results/full/fold_*/test_metrics_by_trial.csv`
