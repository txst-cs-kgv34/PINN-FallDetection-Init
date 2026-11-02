# Experiment 4 findings — Model D hybrid and four-model comparison

## Bottom line

Hybrid training improved substantially over synthetic-only subject-PINN
distillation, but it did not outperform direct real+physics training.

The four-model result is:

1. **Model B — direct real + physics-informed:** best overall and most stable.
2. **Model A — real data-only:** second by average metric rank; stronger in x
   and normalized error than the hybrid.
3. **Model D — hybrid:** second-best theta averages, but unstable on S57 and
   weaker in x.
4. **Model C — synthetic subject-PINN distillation:** weakest overall.

The current evidence favors feeding real trajectories directly to the unified
physics-informed operator. Synthetic teachers remain useful compared with
synthetic-only training, but their present hybrid loss does not add value beyond
Model B.

## Protocol verification

| Check | Result |
|:---|:---|
| Completed folds | 5 of 5 |
| Device | Apple MPS |
| Real training trials per fold | 11–13 |
| Synthetic training trajectories per fold | 300 |
| Synthetic teachers per fold | 3 training subjects only |
| Source weighting | 0.50 real + 0.50 synthetic |
| Physics residual | Enabled for real and synthetic paths |
| Validation | Real unseen validation subject |
| Testing | Different real unseen test subject |
| Total test trials / samples | 20 / 2,838 |
| Held-out teacher leakage | Not observed in fold manifests |

## Model D held-out subject results

| Test subject | Trials | Forecast samples | Normalized MSE | Theta RMSE (deg) | Theta MAE (deg) | x RMSE (cm) | x MAE (cm) |
|:---:|---:|---:|---:|---:|---:|---:|---:|
| S43 | 4 | 1,013 | 0.410 | 8.811 | 6.632 | 13.367 | 10.158 |
| S63 | 4 | 218 | 0.230 | 5.648 | 4.459 | 10.584 | 8.657 |
| S55 | 5 | 424 | 0.222 | 3.459 | 2.211 | 11.269 | 8.400 |
| S57 | 3 | 489 | 1.212 | 13.825 | 10.443 | 23.798 | 18.827 |
| S62 | 4 | 694 | 0.295 | 4.925 | 3.527 | 12.665 | 10.529 |

S57 is the decisive failure case. Its normalized MSE was roughly four to five
times the other hybrid subjects, and its x RMSE was almost twice the next-worst
subject.

### S57 trial detail

| Trial | Normalized MSE | Theta RMSE (deg) | x RMSE (cm) |
|:---|---:|---:|---:|
| S57A11T03 | 0.381 | 11.809 | 9.919 |
| S57A11T04 | 1.414 | 18.465 | 23.296 |
| S57A11T05 | 1.727 | 9.478 | 31.457 |

The failure is not confined to one signal: T04 has the largest angular error,
while T05 has the largest x error.

## Model D subject-equal aggregate

| Metric | Model D mean ± subject SD |
|:---|---:|
| Normalized MSE | 0.474 ± 0.419 |
| Theta RMSE (deg) | 7.333 ± 4.122 |
| Theta MAE (deg) | 5.454 ± 3.221 |
| x RMSE (cm) | 14.337 ± 5.402 |
| x MAE (cm) | 11.314 ± 4.299 |
| Theta W1 (deg) | 4.188 ± 2.861 |
| x W1 (cm) | 8.663 ± 0.579 |

The large SDs for normalized MSE and RMSE reflect the S57 instability.

## Complete four-model comparison

All values are subject-equal means; lower is better.

| Metric | A: real-only | **B: direct physics** | C: distillation | D: hybrid |
|:---|---:|---:|---:|---:|
| Normalized MSE | 0.408 | **0.234** | 0.778 | 0.474 |
| Theta RMSE (deg) | 7.636 | **6.844** | 11.620 | 7.333 |
| Theta MAE (deg) | 6.050 | **5.162** | 8.992 | 5.454 |
| x RMSE (cm) | 13.362 | **9.808** | 16.379 | 14.337 |
| x MAE (cm) | 10.742 | **7.403** | 12.987 | 11.314 |
| Theta W1 (deg) | 4.499 | **3.786** | 7.812 | 4.188 |
| x W1 (cm) | 7.475 | **5.044** | 10.508 | 8.663 |

Model B ranks first for all seven aggregate metrics. Model A ranks second for
normalized and x errors; Model D ranks second for theta errors. Model C ranks
fourth for every aggregate metric.

## Does adding real data help synthetic distillation? D versus C

| Metric | C | D | D improvement over C |
|:---|---:|---:|---:|
| Normalized MSE | 0.778 | 0.474 | 39.09% |
| Theta RMSE (deg) | 11.620 | 7.333 | 36.89% |
| Theta MAE (deg) | 8.992 | 5.454 | 39.34% |
| x RMSE (cm) | 16.379 | 14.337 | 12.47% |
| x MAE (cm) | 12.987 | 11.314 | 12.88% |
| Theta W1 (deg) | 7.812 | 4.188 | 46.38% |
| x W1 (cm) | 10.508 | 8.663 | 17.56% |

D improved theta RMSE for all five subjects and normalized MSE for four of five;
S43 was the normalized-MSE exception. D improved x RMSE for only S55 and S57,
but those reductions were large enough to improve the subject mean.

Real trajectories therefore helped the synthetic-distillation model, especially
its angular prediction, but did not fully remove its domain-shift problems.

## Does adding synthetic data help Model B? D versus B

| Metric | B | D | D change relative to B |
|:---|---:|---:|---:|
| Normalized MSE | 0.234 | 0.474 | 102.90% higher/worse |
| Theta RMSE (deg) | 6.844 | 7.333 | 7.15% higher/worse |
| Theta MAE (deg) | 5.162 | 5.454 | 5.66% higher/worse |
| x RMSE (cm) | 9.808 | 14.337 | 46.18% higher/worse |
| x MAE (cm) | 7.403 | 11.314 | 52.83% higher/worse |
| Theta W1 (deg) | 3.786 | 4.188 | 10.61% higher/worse |
| x W1 (cm) | 5.044 | 8.663 | 71.75% higher/worse |

B had lower normalized MSE and x RMSE on all five subjects. D had lower theta
RMSE on four subjects, but its S57 regression made its subject-average theta
RMSE worse. Therefore, the synthetic objective did not improve the direct model
under the current 50/50 weighting and loss design.

## Hybrid versus real data-only

D improved theta RMSE by 3.97%, theta MAE by 9.85%, and theta W1 by 6.91%
relative to A. It was worse by 16.19% in normalized MSE, 7.30% in x RMSE, 5.33%
in x MAE, and 15.89% in x W1.

This suggests that teacher supervision contributed useful angular structure but
conflicted with real forward-x dynamics.

## Gain diagnostic

Mean inferred hybrid gains over held-out trials were:

| Test subject | Mean `[Kp_theta, Kd_theta, Kp_x, Kd_x]` |
|:---:|:---|
| S43 | `[131.039, 17.274, 9.635, 23.260]` |
| S63 | `[66.054, 14.423, 23.927, 27.817]` |
| S55 | `[212.965, 20.021, 42.916, 33.711]` |
| S57 | `[171.665, 20.440, 10.248, 19.596]` |
| S62 | `[161.256, 27.285, 11.333, 23.249]` |

The S55 averages hide large trial variation: `Kp_theta` ranged from 54.459 to
710.039 and `Kp_x` from 17.499 to 126.577. These extrapolations reinforce that
gain values are not uniquely identifiable from trajectory performance alone.

## Training behavior

| Fold / test subject | Selected epoch | Last epoch | Validation normalized MSE |
|:---|---:|---:|---:|
| 1 / S43 | 32 | 92 | 0.048 |
| 2 / S63 | 74 | 134 | 0.187 |
| 3 / S55 | 43 | 103 | 0.236 |
| 4 / S57 | 7 | 67 | 0.214 |
| 5 / S62 | 5 | 65 | 0.316 |

The checkpoints for folds 4 and 5 were selected very early, indicating that
additional hybrid fitting quickly stopped improving real validation transfer.
This is consistent with tension between the synthetic and real objectives.

Hybrid training totals can become negative because the Gaussian gain NLL
contains a learned log-variance term and omits an additive constant. A negative
training total is therefore not a negative trajectory error and must not be
compared numerically with Models A or B's training totals.

## Research-question conclusion

For the current five-subject pilot:

- **RQ1:** Yes, the direct physics-informed model B improves over the matched
  real data-only model A on every subject-averaged metric. This supports the
  full physics-informed formulation; A and B also differ in controller
  semantics, so it is not a residual-only causal ablation.
- **RQ2:** No, subject-PINN distillation C does not improve over direct unified
  real physics B. It is substantially worse as a complete approach. B and C
  differ in loss composition as well as data source.
- **Hybrid question:** Adding real data to C helps, but adding the current
  synthetic loss to B hurts overall generalization.

The evidence therefore favors direct real trajectories plus the full
physics-informed formulation as the primary approach. A same-head,
zero-physics-weight control is still needed to attribute the improvement to the
residual alone.

## Recommended follow-up

1. Repeat A/B/C/D with at least three seeds before a formal claim.
2. Keep B as the primary candidate and treat A, C, and D as ablations.
3. Add a `B-no-physics` control with B's exact positive gain head and
   `physics_weight=0` if the paper must isolate the residual term alone.
4. If revisiting D, reduce or schedule the synthetic source weight instead of a
   fixed 0.50/0.50 mixture; evaluate 0.10, 0.25, and curriculum decay.
5. Add a real-only fine-tuning phase after hybrid pretraining.
6. Diagnose S57 feature and trajectory distribution shift before another hybrid
   run.
7. Perform gain-identifiability tests; do not report inferred gains as measured
   physiology.
8. Add more manually audited subjects.

## Supporting files

- `results/four_model_comparison/four_model_summary.json`
- `results/four_model_comparison/four_model_metrics_by_subject.csv`
- `results/four_model_comparison/four_model_comparison.png`
- `results/full/aggregate_summary.json`
- `results/full/cross_fold_metrics.csv`
- `results/full/fold_*/test_metrics_by_trial.csv`
