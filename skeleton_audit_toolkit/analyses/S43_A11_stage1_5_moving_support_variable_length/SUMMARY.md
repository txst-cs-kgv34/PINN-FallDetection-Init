# S43 A11 Stage-1.5 relaxed-mechanics ablation

Mechanics: **measured moving-support diagnostic + predicted l(t)**.

| Metric | Value |
|---|---:|
| Matched data-only XY RMSE | 0.3151 m |
| Best nonzero physics weight | 1 |
| Best relaxed PINN XY RMSE | 0.3176 m |
| Change vs matched data-only | 0.8% worse |
| Matched fold/seed PINN wins | 3 / 8 |
| Physics residual reduction | 13.7% |
| Best PINN physics-angle RMSE | 16.70 degrees |
| Best PINN radius RMSE | 0.1555 m |

## Equation

The angular residual uses `m*l(t)^2*theta_ddot + 2*m*l(t)*l_dot(t)*theta_dot = m*g*l(t)*sin(theta) + tau_effective - b*theta_dot - m*l(t)*pivot_ddot dot e_theta`.
The predicted trajectory defines `l(t)`; the true held-out CoM radius is not supplied to the model.

## Interpretation boundary

This is a diagnostic ceiling, not a standalone forecast. It uses the held-out trial's filtered left/right FOOT midpoint displacement and acceleration as an observed exogenous support proxy. It does not use held-out CoM after onset, but the support trajectory would be unavailable for prospective simulation and must eventually be predicted or replaced by measured CoP/contact data.
The proxy is not center of pressure and no foot-contact labels are available.

## Data and controls

- Trials: S43A11T02, S43A11T03, S43A11T04, S43A11T05.
- Horizontal direction: anterior-posterior (subject-forward).
- Four whole-trial leave-one-out folds, two seeds, and 300 epochs.
- Physics weights: 0, 0.01, 0.1, 1, 10.
- Same trajectory and torque architectures as Stage 1.
- Same constant-velocity and uncontrolled-pendulum reference controls are retained.
