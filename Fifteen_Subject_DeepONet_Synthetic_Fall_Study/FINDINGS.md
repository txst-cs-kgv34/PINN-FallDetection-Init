# Findings: validation-selected synthetic fall trajectories

## 1. Study question

This experiment asked whether the validation-selected Physics DeepONet models can generate conditional CoM trajectories whose shape and kinematics fall within the natural variability observed between real falls from the training subjects.

The analysis does not claim that the trajectories are de novo falls. Every sample uses the first 0.40 seconds of a real training trial as context and inherits that trial's apparent-contact endpoint.

## 2. Data accounting and leakage control

- 25 Physics models were available: five folds × five optimization seeds.
- Generator seeds were ranked separately within each fold using only validation-subject normalized forecast MSE.
- The top two seeds per fold were retained, producing ten generator checkpoints.
- No test-subject error was used for seed selection.
- No validation or test subject supplied a generation context or a real-real quality threshold.
- The ten generators produced 516 trajectories from 70 unique real source contexts.
- The quality reference contained 489 within-subject real-real trial pairs.
- The two generators produced 258 matched synthetic-synthetic diversity pairs.

The experimental split remains appropriate for the later detector study, provided detector evaluation continues to use only unseen real subjects.

## 3. Identifier interpretation

`F01_R01` means **Fold 1, validation rank 1**. `R01` does not mean round 1.

The complete identifier `F01_R01_S03_S43A11T02` means:

- `F01`: Fold 1
- `R01`: the best validation-ranked generator in Fold 1
- `S03`: optimization-seed index 3, base seed 20261103
- `S43A11T02`: source training trial used for conditional generation

## 4. Primary quality result

Of 516 generated trajectories:

- 461 passed both normalized RMSE and DTW: **89.3%**
- 281 passed the kinematic requirement: **54.5%**
- 257 passed both shape and kinematic gates: **49.8%**

Failure decomposition:

| Shape gate | Kinematic gate | Count | Interpretation |
|---|---|---:|---|
| Pass | Pass | 257 | Complete predefined pass |
| Pass | Fail | 204 | Shape is acceptable, but kinematics are outside the reference envelope |
| Fail | Pass | 24 | Kinematics pass, but RMSE or DTW fails |
| Fail | Fail | 31 | Both shape and kinematics fail |

The model usually captures the overall trajectory shape, but only about half of the outputs satisfy the stricter combined kinematic criterion.

## 5. Which measurements caused rejection?

| Gate metric | Trajectories exceeding the fold threshold | Failure rate |
|---|---:|---:|
| Peak angular acceleration difference | 306/516 | 59.3% |
| Peak angular velocity difference | 161/516 | 31.2% |
| Peak horizontal velocity difference | 136/516 | 26.4% |
| Peak horizontal acceleration difference | 108/516 | 20.9% |
| Horizontal displacement difference | 81/516 | 15.7% |
| Angular displacement difference | 79/516 | 15.3% |
| DTW | 40/516 | 7.8% |
| Normalized RMSE | 30/516 | 5.8% |

Peak angular-acceleration mismatch is the dominant discriminator. The metric is an absolute synthetic-real difference, so this result does not by itself mean synthetic acceleration is always too high; it means the synthetic and real peaks frequently differ more than the fold's natural real-real limit.

## 6. Fold-level heterogeneity

| Fold | Validation subject | Passing trajectories | Pass rate |
|---:|---|---:|---:|
| 1 | S63 | 40/104 | 38.5% |
| 2 | S62 | 62/102 | 60.8% |
| 3 | S57 | 67/104 | 64.4% |
| 4 | S55 | 67/104 | 64.4% |
| 5 | S43 | 21/102 | 20.6% |

Fold 5 performs substantially worse than Folds 2–4. Its training real-real distribution also yields narrower limits, including normalized DTW 0.359 and angular-displacement difference 32.508°, compared with looser limits in several other folds. Its low count therefore reflects both model error and stricter fold-specific reference variability.

Quality is also subject-dependent. Examples include:

- S63: 28/30 passes, 93.3%
- S44: 33/40 passes, 82.5%
- S34: 6/40 passes, 15.0%
- S56: 8/40 passes, 20.0%
- S32: 9/40 passes, 22.5%

These counts are descriptive because the same subject can occur in multiple training folds.

## 7. Validation rank versus synthetic quality

Validation rank 1 was not consistently better than rank 2 for generated-data quality:

| Generator group | Complete passes | Pass rate | Mean normalized RMSE | Mean DTW |
|---|---:|---:|---:|---:|
| Rank 1 generators | 128/258 | 49.6% | 1.0232 | 0.2186 |
| Rank 2 generators | 129/258 | 50.0% | 1.0065 | 0.2080 |

This does not invalidate validation-only selection. It shows that validation forecast loss and synthetic-quality pass rate measure related but different properties. Retaining two qualified generators was more defensible than discarding every model except rank 1.

## 8. Generator diversity

The two selected generators produce distinguishable but strongly related trajectories.

| Metric | Synthetic-synthetic mean | Real-real mean | Ratio |
|---|---:|---:|---:|
| Normalized RMSE | 0.3597 | 0.7818 | 0.46 |
| Normalized DTW | 0.0753 | 0.1709 | 0.44 |
| Theta RMSE | 5.390° | 11.829° | 0.46 |
| CoM x RMSE | 7.125 cm | 14.977 cm | 0.48 |

Selected-seed variation is approximately half the natural real-trial variation. Additional deterministic outputs from the same two generators would add little new information.

Pass/fail decisions also agree strongly between the two generators. Of the source contexts in each fold:

- Fold 1: both generators agree on every context
- Fold 2: only 4 of 51 contexts differ
- Fold 3: only 1 of 52 contexts differs
- Fold 4: only 3 of 52 contexts differ
- Fold 5: only 3 of 51 contexts differ

Quality is driven more by the source context and fold than by seed choice alone.

## 9. Context-to-forecast continuity requires another check

The synthetic files splice observed real context for `t < 0.40 s` with model forecast for `t ≥ 0.40 s`.

| Boundary measurement | Median | 95th percentile | Maximum |
|---|---:|---:|---:|
| Theta jump | 0.950° | 4.488° | 8.974° |
| CoM x jump | 1.451 cm | 6.788 cm | 10.489 cm |

The current quality gate does not directly threshold this one-step discontinuity. Acceleration measurements capture some transition behavior, but large boundary jumps can still pass. This matters for the downstream detector because it could learn the synthetic splice artifact instead of fall dynamics.

Before using the trajectories as positive detector examples, apply one controlled option and rerun the quality analysis:

1. Add a boundary-jump threshold derived from corresponding real one-step changes.
2. Continuity-anchor the forecast at the final context value, then recompute all metrics.
3. Use only the forecast interval for both synthetic falls and equivalently prepared ADL windows.

The selected approach must be applied identically across all detector conditions.

## 10. Do we need more synthetic data now?

No additional generation is recommended yet.

Reasons:

1. There are already 516 candidates and 257 provisional passes—enough for an initial downstream experiment.
2. Rerunning these deterministic checkpoints on the same 70 contexts will reproduce the same trajectories.
3. The selected generators provide less diversity than natural real trials.
4. The immediate limitation is kinematic fidelity and boundary continuity, not raw sample count.
5. Fold 5 has only 21 passes, but near-duplicate outputs would not resolve its underlying quality problem.

Recommended next sequence:

1. Resolve the 0.40-second continuity issue.
2. Rerun the same quality protocol and freeze the accepted trajectory list.
3. Begin the detector pilot with fold-specific accepted samples.
4. Compare real-only, synthetic-only, and real-plus-synthetic training under the same architecture and class balancing.
5. Evaluate only on unseen real falls and real ADL.
6. Generate additional samples only if the pilot reveals a clear data-volume or coverage limitation.

If expansion becomes necessary, prioritize genuinely new variability:

- new real contexts or additional fall directions;
- validation-qualified additional generators only if they add measurable diversity;
- bounded perturbations of initial state, inferred controller coordinates, or demographics, followed by the same quality gate.

## 11. Bottom-line conclusion

The Physics DeepONet produces useful conditional fall trajectories: 89.3% satisfy the fold-specific shape envelope, demonstrating substantial trajectory fidelity. The complete quality rate falls to 49.8% because kinematic agreement—especially angular acceleration—is more demanding. The current results justify proceeding toward a downstream detector pilot after addressing the context-to-forecast boundary, but they do not justify indiscriminately treating all 516 outputs as realistic or generating more copies from the same deterministic conditions.

