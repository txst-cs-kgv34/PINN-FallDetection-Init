# A13 kinematic reconstruction pilot

## Outcome

Ran 4 leave-one-trial-out folds. Each fold used the other 3 trials and kept the held-out trial completely unseen.

| Method | Mean 3D RMSE (m) | Median 3D RMSE (m) |
|---|---:|---:|
| training_mean | 0.1968 | 0.1499 |
| polynomial_ridge | 0.1963 | 0.1494 |

## Key findings

The polynomial model improves mean 3D RMSE over the training mean by only 0.0005 m. Treat the simple training mean as a competitive baseline rather than claiming a meaningful smoothing advantage.

S43A13T02 is the largest polynomial reconstruction error (0.3615 m) and has a duration error of 1.033 s. Mean duration absolute error across the four folds is 0.400 s. The later PINN must operate in physical seconds and report timing separately from phase-normalized shape.

The standing head-to-foot-midpoint proxy spans 0.890–0.927 of reported stature across the four trials. This is a frame-orientation check, not a stature estimate.

## Fixed reconstruction rules

- Input/output uses a fixed standing-body frame per trial: hip-left to hip-right, foot-midpoint to head, and an orthogonal forward axis oriented toward the nose proxy.
- CoM is the documented female segment-mass proxy. Coordinates are raw input converted to metres; no temporal filter is applied.
- Every onset-to-apparent-contact trajectory is resampled to 101 normalized phase points and expressed as displacement from its onset frame.
- The polynomial model uses phase powers 1–5, no intercept, and ridge λ=1e-06. These settings are fixed for all folds.
- Duration is predicted only as the median duration of the training trials; the model is therefore a trajectory-shape baseline, not a physical-time fall predictor.

## Interpretation

This pilot asks whether a simple training-trial template can reconstruct an unseen A13 CoM trajectory after body-frame and phase alignment. It is the benchmark for a later PINN. A PINN must be compared on the same held-out folds and must not use the held-out trajectory to select loss weights or preprocessing.

The standing-body vertical is not a measured gravity vector, and the origin is not a calibrated floor contact. No forces, torques or perturbations are inferred here.

## Next PINN step

Use CoM position as the observed state and obtain velocity/acceleration through automatic differentiation of a smooth network. Begin with a point-mass residual in the standing-body frame. Because external forces and contacts were not measured, any learned forcing term must be labeled an effective residual—not a recovered physical perturbation.

## Files

- `fold_metrics.csv`: held-out errors for both fixed baselines.
- `fold_predictions.csv`: actual and predicted trajectories for every fold.
- `subject_frames.json`: per-trial fixed coordinate transforms and stature-span checks.
- `model_parameters.json`: fixed polynomial/ridge settings and fitted fold coefficients.
- `plots/`: held-out trajectory comparisons.
