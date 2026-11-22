# Findings — A11 matched from-scratch calibration V3, five seeds

## Executive conclusion

The complete matched experiment does not support a forecasting advantage from
validation-selected CartPole physics on the current 64-trial strict-primary A11
pipeline. Selected V3 had higher mean held-out error than its matched λ=0 arm
on all three primary endpoints. None of the subject-level paired comparisons
was significant after Holm correction.

Physics did substantially improve the horizontal equation residual, proving
that the optimizer can enforce that part of the specified dynamics. It did not
translate into better unseen-subject trajectories. For the current pipeline,
matched λ=0 remains the A11 forecasting reference.

## Completion and integrity audit

- 100/100 candidates: four λ arms × five folds × five seeds.
- 25/25 validation selections and 25/25 matched λ=0 evaluations.
- 75 paired held-out subject-seed evaluations and 320 paired trial-seed
  evaluations per condition.
- 320 selected and 320 matched λ=0 prediction archives.
- 26,245 training-history rows; no non-finite value.
- Identical initialization hash and pre-training validation loss across the
  four λ arms within every fold-seed.
- Exact equality of time, theta target, and x target for every paired trial.
- Checkpoints and λ values selected using validation data only.

## Primary five-seed comparison

Positive improvement means `matched λ=0 − selected V3`; positive favors V3.

| Endpoint | Selected V3 | Matched λ=0 | V3 improvement | Relative | Subject wins V3/N | Bootstrap 95% CI | Holm p |
|:--|--:|--:|--:|--:|--:|:--|--:|
| Normalized forecast MSE | 3.4892 | 3.3313 | -0.1579 | -4.74% | 7/8 | -0.5522 to +0.1163 | 1.0000 |
| Theta RMSE | 21.9119° | 21.6521° | -0.2598° | -1.20% | 10/5 | -1.4345° to +0.5189° | 1.0000 |
| CoM-x RMSE | 30.3129 cm | 29.8412 cm | -0.4717 cm | -1.58% | 8/7 | -2.0702 to +0.6142 cm | 1.0000 |

Theta RMSE favored V3 for 10 subjects, but five larger adverse differences
made its mean worse. This is why both win counts and effect magnitudes must be
reported. The intervals include zero and do not demonstrate equivalence; they
show that this experiment did not establish a benefit.

## Weight-selection stability

Validation selected:

| λ | Fold-seed selections |
|---:|---:|
| 0 | 8/25 |
| 0.0001 | 3/25 |
| 0.001 | 7/25 |
| 0.01 | 7/25 |

Every fold selected nonzero physics in three or four of its five seeds, but no
single nonzero weight was stable. The same validation subject could select
weights ranging from zero to `0.01` across seeds:

| Fold | Validation subject | Nonzero selections | Weights across seeds |
|---:|:---|---:|:--|
| 1 | S63 | 3/5 | 0.01, 0, 0, 0.0001, 0.001 |
| 2 | S62 | 4/5 | 0.01, 0.001, 0.001, 0, 0.01 |
| 3 | S57 | 3/5 | 0.01, 0.01, 0.001, 0, 0 |
| 4 | S55 | 3/5 | 0, 0, 0.001, 0.0001, 0.001 |
| 5 | S43 | 4/5 | 0.001, 0.0001, 0, 0.01, 0.01 |

Among the 17 fold-seed models that selected nonzero physics, test normalized
MSE improved in 7 and worsened in 10; theta and x RMSE each improved in 10 and
worsened in 7. Descriptively, larger validation improvement was negatively
associated with test improvement (Pearson correlations approximately -0.81,
-0.75, and -0.75 for normalized MSE, theta RMSE, and x RMSE). With only 17
nonzero selections these correlations are diagnostic, not inferential, but
they show that one validation subject is too unstable for the next calibration.

## Seed stability

Positive values favor selected V3.

| Seed | Normalized-MSE improvement | Theta-RMSE improvement | CoM-x improvement |
|---:|---:|---:|---:|
| 1 | -0.75% | +1.08% | +1.02% |
| 2 | -1.78% | -1.22% | -0.33% |
| 3 | +4.38% | +2.74% | +1.49% |
| 4 | -14.11% | -4.13% | -6.18% |
| 5 | -12.46% | -4.68% | -4.07% |

Only seed 3 favored V3 on all three endpoints. Seeds 4 and 5 produced the
largest penalties. The favorable seed-1 pilot therefore did not generalize
across optimization seeds.

## Subject heterogeneity

Five-seed mean normalized MSE favored V3 for S34, S49, S56, S46, S48, S55,
and S59. It favored λ=0 for the other eight subjects. The largest effects were:

- **S44:** V3 worse by 2.469 normalized-MSE units, 7.331°, and 9.910 cm.
- **S45:** V3 worse by 0.634 normalized-MSE units, 1.132°, and 1.413 cm.
- **S49:** V3 better by 0.765 normalized-MSE units, 1.624°, and 3.216 cm.
- **S34:** V3 better by 0.278 normalized-MSE units, 1.215°, and 1.420 cm.

S57 never favored V3 in any of its three primary seed-level comparisons when a
nonzero model was selected; S63 also usually favored λ=0. The direction and
magnitude of the physics effect are therefore subject-dependent.

## Physics residuals

| Residual | Selected V3 | Matched λ=0 | Change with V3 |
|:--|--:|--:|--:|
| Angular residual RMSE | 17.0616 | 16.1002 | 6.0% worse |
| Horizontal residual RMSE | 260.0735 | 442.1891 | 41.2% better |

For the 51 subject-seed evaluations belonging to nonzero-selected fold-seed
models, horizontal residual RMSE improved 59.7%, while angular residual RMSE
worsened 9.0%. The current objective is therefore highly effective at reducing
the horizontal equation violation but does not balance both residual heads or
improve the trajectory endpoints.

This is not evidence that CartPole physics is false. It is evidence that the
current coordinate/residual formulation and single-subject hyperparameter
selection do not yield reliable unseen-subject forecast gains.

## Relationship to the earlier 70-trial result

The earlier Model B comparison remains a valid descriptive result for its own
70-trial mixed legacy/audit pipeline: all three endpoints favored physics for
12 of 15 subjects, while its adjusted p-values remained above 0.05. The present
64-trial unified Physics-Ready experiment is the stronger evidence for the
current pipeline and does not reproduce that advantage.

The correct reporting is pipeline sensitivity, not fabrication or a universal
claim. The data definition, coordinate construction, conditioning, and
optimization protocol materially affect whether the residual helps.

## Consequence for A10–A13

Do not simply rerun the existing unified planar model with fixed λ=`0.01`, and
do not copy the A11 single-validation-subject selector. The next unified model
should use:

1. a shared context encoder and DeepONet trunk;
2. activity-defined signed axes: sagittal backward/forward for A10/A11 and
   frontal left/right for A12/A13;
3. four activity-specific controller/residual heads;
4. separately normalized and logged angular/horizontal residual components;
5. no direction feature computed from future onset-to-contact motion;
6. validation averaged equally across at least two validation subjects and all
   four activities; and
7. matched from-scratch λ=0 and physics arms.

First select a global residual-strength grid `{0, 1e-4, 1e-3, 1e-2}` applied to
the mean of the four normalized activity heads. If a nonzero strength survives
held-out testing, run head-on/head-off ablations to learn which activities
benefit; do not search all 4^4 weight combinations.

The detailed evaluation, final-generator, A14, and downstream synthetic-data
plan is in `NEXT_STEPS_A10_A14_SYNTHETIC.md`.

## Advisor-facing statement

> In the corrected five-seed, matched-from-scratch A11 calibration, validation
> selected nonzero CartPole physics in 17 of 25 fold-seed models, but this did
> not transfer to better unseen-subject forecasts. Mean normalized MSE, theta
> RMSE, and CoM-x RMSE were 4.74%, 1.20%, and 1.58% higher than matched λ=0,
> respectively, with no Holm-adjusted comparison below 0.05. Horizontal
> equation residual RMSE improved 41.2%, while angular residual RMSE worsened
> 6.0%. We therefore retain λ=0 as the current A11 forecasting reference and
> next test activity-defined coordinates and activity-specific residual heads
> in the unified A10–A13 model using multi-subject validation.
