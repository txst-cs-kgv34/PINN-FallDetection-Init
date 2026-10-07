# S43 A13 Stage-1.5 relaxed-mechanics ablation

Mechanics: **measured moving-support diagnostic + predicted l(t)**.

| Metric | Value |
|---|---:|
| Matched data-only XY RMSE | 0.7008 m |
| Best nonzero physics weight | 1 |
| Best relaxed PINN XY RMSE | 0.4955 m |
| Change vs matched data-only | 29.3% better |
| Matched fold/seed PINN wins | 4 / 8 |
| Physics residual reduction | 57.6% |
| Best PINN physics-angle RMSE | 12.72 degrees |
| Best PINN radius RMSE | 0.4050 m |

## Equation

The angular residual uses `m*l(t)^2*theta_ddot + 2*m*l(t)*l_dot(t)*theta_dot = m*g*l(t)*sin(theta) + tau_effective - b*theta_dot - m*l(t)*pivot_ddot dot e_theta`.
The predicted trajectory defines `l(t)`; the true held-out CoM radius is not supplied to the model.

## Interpretation boundary

This is a diagnostic ceiling, not a standalone forecast. It uses the held-out trial's filtered left/right FOOT midpoint displacement and acceleration as an observed exogenous support proxy. It does not use held-out CoM after onset, but the support trajectory would be unavailable for prospective simulation and must eventually be predicted or replaced by measured CoP/contact data.
The proxy is not center of pressure and no foot-contact labels are available.

## Data and controls

- Trials: S43A13T01, S43A13T02, S43A13T03, S43A13T05.
- Horizontal direction: medial-lateral.
- Four whole-trial leave-one-out folds, two seeds, and 300 epochs.
- Physics weights: 0, 0.01, 0.1, 1, 10.
- Same trajectory and torque architectures as Stage 1.
- Same constant-velocity and uncontrolled-pendulum reference controls are retained.
