# S43 phase-aligned real-trial baseline

## Outcome

Validated 16 fully annotated raw trials across 5 fall types. Each dynamics window runs from the manual `fall_onset` mark through the manual `apparent_contact` mark, inclusive.

**Recommended first modeling family: A13 — Rightfall.** This is a data-screening priority based on the median burden of existing audit flags and exact repeated transitions among the annotated trials. It is not a biomechanical quality label.

## Activity summary

| Activity | Description | Annotated trials | Median onset→contact (s) | Median screening burden | Median leave-one-out 3D RMSE (m) |
|---|---|---:|---:|---:|---:|
| A10 | Backfall | 3 | 0.800 | 0.455 | 0.4122 |
| A11 | Frontfall | 3 | 0.967 | 0.500 | 0.1459 |
| A12 | Leftfall | 4 | 0.600 | 0.500 | 0.1822 |
| A13 | Rightfall | 3 | 0.767 | 0.296 | 0.2166 |
| A14 | Rotatefall (turn and fall) | 3 | 1.567 | 0.582 | 0.2537 |

## What the baseline means

- Coordinates are the original supplied skeleton coordinates converted to metres. No filter is used.
- CoM is the toolkit's documented sex-specific segment-mass proxy. Each trajectory is expressed as displacement from its own onset frame.
- Phase normalization interpolates each onset-to-apparent-contact window to 101 points. It supports shape comparison but removes absolute duration; durations remain in `phase_windows.csv`.
- The leave-one-out reference for a trial is the mean normalized trajectory of the other annotated trials in the same activity. It is a simple comparison benchmark, not a trained model.
- Screening burden is `review_flag_fraction + exact_repeat_transition_fraction` inside the dynamics window. Its only purpose is transparent prioritization.

## Scientific limits

`apparent_contact` is a manual skeleton observation. There are no force plates, contact labels, timestamps, videos or camera/floor calibration, so it must not be described as measured impact. Camera X/Y/Z are not verified world-horizontal/vertical axes. These outputs do not identify joint forces, torques or perturbations.

## Files

- `phase_windows.csv`: validated phase frames, nominal times and durations.
- `trial_priority.csv`: within-activity screening ranks for the annotated windows.
- `phase_aligned_com.csv`: 101-point CoM and foot-relative CoM trajectories.
- `leave_one_out_baseline.csv`: reference-only comparison errors.
- `plots/`: real-trial overlays and activity mean ± one standard deviation.
- `phase_validation.json`: annotation provenance and validation result.

## Next modeling step

Start with A13 and keep one whole trial held out. Fit a kinematic reconstruction baseline first, then introduce a PINN state model using CoM position/velocity and an explicitly documented external-perturbation assumption. Do not use the held-out trial to tune filtering, phase boundaries or loss weights.
