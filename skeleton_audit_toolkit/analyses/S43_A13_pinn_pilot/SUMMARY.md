# S43 A13 first PINN pilot

## Outcome

The model was trained in four whole-trial folds using physical time and initial-state conditioning. It predicts body-frame CoM displacement while automatic differentiation supplies velocity and acceleration.

| Metric | Value |
|---|---:|
| Mean PINN 3D RMSE | 0.5010 m |
| Mean training-mean 3D RMSE | 0.1961 m |
| Folds where PINN improves | 0 / 4 |
| Mean held-out physics residual RMS | 8.3258 m/s² |
| Mean effective-force RMS | 409.1 N |

## Observed inputs

- Physical time from the manual fall-onset frame.
- Raw skeleton-derived CoM in the fixed standing-body frame.
- Pre-onset CoM velocity, onset CoM relative to the foot midpoint, and onset foot separation.
- Subject mass 130 lb and reported height 64 in from the subject configuration.

## Physics-informed assumptions

The model enforces `r¨ = g_proxy + a_effective`. The gravity proxy is 9.80665 m/s² opposite the standing headward axis. The effective acceleration is a learned low-complexity residual regularized for magnitude and temporal roughness. Multiplying it by subject mass produces the reported effective force.

This effective force combines unmeasured support, voluntary control, contact effects, modeling error and any true perturbation. It is not a recovered perturbation or ground-reaction force.

## Interpretation gate

This is a software/research prototype. It is useful only if held-out position error and physics residual are reported together. A low residual alone is not validation because the effective term is learned. Synthetic falls should not yet be presented as physically validated.

## Next experiment

Compare data-only and physics-informed networks under the same folds, then run loss-weight sensitivity. Only after the result is stable should the effective input be perturbed to generate candidate synthetic trajectories.
