# S43 Stage 2A delayed-PD parameter-recovery benchmark

## Decision

**PASS Stage 2A:** 12/12 cases (100.0%) passed all parameter and held-out-trajectory gates.

This benchmark establishes recoverability only for the correctly specified simulated Stage-1 plant. It does not identify a physiological controller in S43 or validate synthetic human falls.

## Aggregate results

- Median Kp relative error: 0.08%.
- Median Kd relative error: 0.53%.
- Median delay error: 0.00 observation frames.
- Median torque-limit relative error: 0.56%.
- Median held-out angle RMSE: 0.014 degrees.
- Parameter-only gates passed in 12/12 cases.

## Design

- Original Stage-1 fixed-pivot, constant-length point-mass plant; no Stage-1.5 mechanics.
- Subject mass 58.967 kg; separate A11 and A13 median onset lengths.
- Passive damping fixed to zero, so Kd is not confounded with an unknown damping term.
- Known raised-cosine torque perturbations; eight training and four unseen test trials.
- Three known controller profiles, two plant lengths, and two independent angle-noise seeds.
- 30 Hz observations with 0.12-degree Gaussian angle noise and the retained Stage-1 1.5 Hz, order-6 zero-phase filter.
- Delay searched only in whole 30 Hz frames; sub-frame recovery is not claimed.

### Development note

A preliminary 3.0 s dry run was rejected before the retained benchmark because
the tested delayed controllers produced multiple full rotations (up to about
297 degrees), outside the marked S43 fall-window regime and the intended local
recovery question. The 1.2 s retained horizon was then fixed to the scale of the
observed onset-to-contact windows. The parameter-error gates were not relaxed.

## Prespecified gates

- Kp relative error <= 15%.
- Kd relative error <= 15%.
- Delay error <= 1 frame.
- Torque-limit relative error <= 15%.
- Held-out angle RMSE <= 1.0 degree.
- At least 80% of cases must pass all gates.

## Interpretation and next step

If this benchmark passes, the inverse implementation is capable of recovering known gains, delay, and saturation under its own assumptions. The next step is a mismatch/sensitivity stage (noise, incorrect length, unknown perturbation, and nonzero passive damping) before any exploratory S43 fit. Human-data estimates must be called effective delayed-feedback parameters because the available skeleton trials contain no measured perturbation torque, center of pressure, or ground-reaction force.

## Files

- `recovery_metrics.csv`: one row per plant/profile/noise case.
- `optimization_profiles.csv`: all delay/start fits, not only winners.
- `held_out_trajectories.csv`: unseen-trial observations, truth, and predictions.
- `experiment_config.json`: complete frozen settings and trial bank.
- `plots/`: parameter and held-out trajectory figures.
