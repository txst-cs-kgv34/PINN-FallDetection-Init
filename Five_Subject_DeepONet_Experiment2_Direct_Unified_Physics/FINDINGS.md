# Experiment 2 findings — Model B: direct unified physics DeepONet

## Bottom line

Model B is the strongest of the four tested approaches. It achieved the lowest
subject-averaged value for all seven reported metrics and the lowest normalized
MSE and x RMSE for every held-out subject.

The descriptive evidence supports the following conclusion:

> With these five subjects, training directly on real trajectories while adding
> the delayed cart-pole residual generalized better than real data-only training,
> synthetic subject-PINN distillation, or the current hybrid objective.

This is evidence that the full physics-informed formulation helps trajectory
prediction. Because Model B also changes the context head, the present run does
not isolate the residual term by itself. It is not evidence that the model
uniquely recovered physiological human gains.

## Protocol verification

| Check | Result |
|:---|:---|
| Completed folds | 5 of 5 |
| Device | Apple MPS |
| Training source | Real trajectories only |
| Training subjects per fold | 3 |
| Real training trials per fold | 11–13 |
| Validation | Real trajectories from one unseen subject |
| Testing | Real trajectories from a different unseen subject |
| Total real test trials | 20 |
| Total forecast samples | 2,838 |
| Context | Four 0.10-second windows; forecast begins at 0.40 s |
| Physics loss | Enabled |
| Synthetic trajectories | None |
| Validation/test leakage | Not observed in manifests |

S63A11T05 and S62A11T02 were excluded before training because they were shorter
than the fixed 0.40-second context.

## Held-out subject results

Lower is better. Each row is pooled over all valid forecast samples for the
named real test subject.

| Test subject | Trials | Forecast samples | Normalized MSE | Theta RMSE (deg) | Theta MAE (deg) | x RMSE (cm) | x MAE (cm) |
|:---:|---:|---:|---:|---:|---:|---:|---:|
| S43 | 4 | 1,013 | 0.322 | 9.292 | 7.239 | 10.721 | 8.142 |
| S63 | 4 | 218 | 0.190 | 5.769 | 4.767 | 9.236 | 7.678 |
| S55 | 5 | 424 | 0.169 | 5.234 | 3.592 | 8.850 | 6.175 |
| S57 | 3 | 489 | 0.244 | 5.980 | 4.229 | 10.805 | 7.732 |
| S62 | 4 | 694 | 0.243 | 7.945 | 5.984 | 9.426 | 7.288 |

Unlike Models C and D, Model B did not show a catastrophic S57 failure. Its
largest normalized MSE was 0.322 on S43; its subject-level x RMSE stayed within
8.85–10.81 cm.

## Subject-equal aggregate

The final mean gives every test subject one vote regardless of trajectory
length. The ± value is the sample standard deviation across the five subjects.

| Metric | Model B mean ± SD |
|:---|---:|
| Normalized MSE | 0.234 ± 0.059 |
| Theta RMSE (deg) | 6.844 ± 1.710 |
| Theta MAE (deg) | 5.162 ± 1.456 |
| x RMSE (cm) | 9.808 ± 0.897 |
| x MAE (cm) | 7.403 ± 0.750 |
| Theta W1 (deg) | 3.786 ± 2.370 |
| x W1 (cm) | 5.044 ± 2.536 |

The particularly small between-subject SDs for normalized MSE, x RMSE, and
x MAE show that Model B was substantially more stable across subjects than the
other approaches.

## Does explicit physics help? Model B versus Model A

Models A and B use the same real trajectories, folds, validation rule, and
DeepONet backbone. B adds physical gain semantics and the explicit cart-pole
residual.

| Metric | A: real data-only | B: real + physics | B improvement |
|:---|---:|---:|---:|
| Normalized MSE | 0.408 | 0.234 | 42.73% |
| Theta RMSE (deg) | 7.636 | 6.844 | 10.38% |
| Theta MAE (deg) | 6.050 | 5.162 | 14.68% |
| x RMSE (cm) | 13.362 | 9.808 | 26.60% |
| x MAE (cm) | 10.742 | 7.403 | 31.08% |
| Theta W1 (deg) | 4.499 | 3.786 | 15.84% |
| x W1 (cm) | 7.475 | 5.044 | 32.52% |

B improved normalized MSE and x RMSE on all five test subjects. It improved
theta RMSE on four of five subjects; S62 was the exception. This is the cleanest
evidence in the current study that the physics-informed formulation added value.

It is not a strict one-switch loss ablation: A uses an unconstrained latent
context vector, whereas B uses a positive physical-gain parameterization in
addition to the residual. A future `B-no-physics` control that preserves B's
gain head and sets only `physics_weight=0` would isolate the residual itself.

## Direct real physics versus subject-PINN distillation

| Metric | B: direct real physics | C: synthetic distillation | B improvement over C |
|:---|---:|---:|---:|
| Normalized MSE | 0.234 | 0.778 | 69.98% |
| Theta RMSE (deg) | 6.844 | 11.620 | 41.10% |
| Theta MAE (deg) | 5.162 | 8.992 | 42.59% |
| x RMSE (cm) | 9.808 | 16.379 | 40.12% |
| x MAE (cm) | 7.403 | 12.987 | 43.00% |
| Theta W1 (deg) | 3.786 | 7.812 | 51.53% |
| x W1 (cm) | 5.044 | 10.508 | 52.00% |

B had lower normalized MSE, x RMSE, and x MAE for every subject. C had a
slightly lower theta RMSE only for S43. The primary research-question result is
therefore in favor of direct real physics training, not synthetic-only
distillation.

This comparison evaluates the two complete approaches. Besides training source,
C includes teacher-gain NLL and synthetic consistency losses and was inherited
from Experiment 1. Therefore, the result should not be described as a causal
data-source-only ablation.

## Direct real physics versus hybrid training

| Metric | B | D: hybrid | B improvement over D |
|:---|---:|---:|---:|
| Normalized MSE | 0.234 | 0.474 | 50.71% |
| Theta RMSE (deg) | 6.844 | 7.333 | 6.67% |
| x RMSE (cm) | 9.808 | 14.337 | 31.59% |

D produced lower theta RMSE than B on S43, S63, S55, and S62, but its large
S57 error made its subject-averaged theta result worse. B had lower normalized
MSE and x RMSE on all five subjects. Adding the current synthetic objective did
not improve the direct model.

## Inferred-gain diagnostic

Mean inferred gains over the held-out trials were:

| Test subject | Mean `[Kp_theta, Kd_theta, Kp_x, Kd_x]` |
|:---:|:---|
| S43 | `[2.196, 1.175, 9.336, 1.842]` |
| S63 | `[0.000, 0.003, 0.016, 0.005]` |
| S55 | `[7.297, 0.957, 12.131, 1.664]` |
| S57 | `[0.000, 0.039, 0.034, 0.012]` |
| S62 | `[88.490, 17.338, 12.691, 14.523]` |

S63 and S57 achieved good trajectory accuracy even though their inferred gains
collapsed near zero. S55 also showed substantial trial-to-trial variation. This
means the operator can generate useful trajectories without identifying a
unique, physiologically meaningful controller tuple. Likely explanations
include gain non-identifiability, the branch network learning to rely on initial
state and demographics, or multiple gain combinations satisfying similar
residuals.

The inferred gains should therefore remain an internal effective representation.
Do not present them as recovered human neuromotor parameters without a separate
identifiability analysis.

## Training behavior

| Fold / test subject | Selected epoch | Last epoch | Validation normalized MSE |
|:---|---:|---:|---:|
| 1 / S43 | 146 | 246 | 0.077 |
| 2 / S63 | 85 | 185 | 0.213 |
| 3 / S55 | 190 | 290 | 0.116 |
| 4 / S57 | 51 | 151 | 0.153 |
| 5 / S62 | 8 | 108 | 0.572 |

Every fold stopped exactly 100 epochs after its best validation epoch, matching
the configured patience. Fold 5's early selection and higher validation error
show that validation on S43 remained difficult even though the final S62 test
result was stable.

## Conclusions and next steps

1. Use Model B as the primary model from this four-way study.
2. Report that the physics-informed formulation improved trajectory prediction
   over the real data-only control, while disclosing the different controller
   semantics and avoiding a residual-only causal claim.
3. Report that direct real physics substantially outperformed synthetic-only
   subject-PINN distillation.
4. Do not claim physical gain recovery; run gain sensitivity, permutation, and
   multi-start identifiability tests first.
5. Repeat all folds with at least three seeds. With only five paired subjects,
   even consistent descriptive improvements are not a population-level result.
6. Add subjects before making inferential or demographic claims.

## Supporting files

- `results/full/aggregate_summary.json`
- `results/full/cross_fold_metrics.csv`
- `results/full/cross_fold_results.png`
- `results/full/fold_*/training_selection.json`
- `results/full/fold_*/test_metrics_by_trial.csv`
- `results/full/fold_*/test_predictions/`
