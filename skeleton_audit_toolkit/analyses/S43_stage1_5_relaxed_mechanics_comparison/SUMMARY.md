# S43 Stage-1.5 relaxed-mechanics comparison

## Decision

Neither predicted time-varying length nor the observed moving-support diagnostic improved on the original data-only network in both activities. Do not replace the current Stage-1 pipeline with either relaxed model, and do not interpret lower equation residual as validated fall prediction.

| Activity | Model | Best lambda | XY RMSE | Change vs original data-only | Residual reduction vs matched data-only |
|---|---|---:|---:|---:|---:|
| A11 | Original fixed pivot + fixed length | 0.01 | 0.2520 m | +3.7% | 33.9% |
| A11 | Fixed pivot + predicted l(t) | 0.01 | 0.2500 m | +2.9% | 32.4% |
| A11 | Measured moving support + predicted l(t) | 1 | 0.3176 m | +30.7% | 13.7% |
| A13 | Original fixed pivot + fixed length | 0.01 | 0.4467 m | +8.4% | 31.4% |
| A13 | Fixed pivot + predicted l(t) | 0.01 | 0.4857 m | +17.8% | 6.2% |
| A13 | Measured moving support + predicted l(t) | 1 | 0.4955 m | +20.2% | 57.6% |

Original data-only RMSE was 0.2430 m for A11 and 0.4121 m for A13.

## Interpretation

- Fixed pivot plus predicted `l(t)` slightly improved the A11 PINN from 0.2520 to 0.2500 m, but remained 2.9% worse than data-only. For A13 it worsened the PINN from 0.4467 to 0.4857 m and remained dominated by the long T02 extrapolation.
- The measured moving-support diagnostic did not improve A11 and produced 0.3176 m RMSE. For A13 it improved strongly relative to its own poorly generalizing moving-coordinate data-only model, but its 0.4955 m RMSE was still 20.2% worse than the original data-only network.
- A13 support displacement ranged from 0.048 to 0.499 m, with the largest movement in the difficult T02 trial. This confirms that support motion is real, but a raw FOOT midpoint is not a sufficiently stable support-state representation.
- Variable length corrected one violated assumption, but the effective-torque branch and single-link planar model still absorb articulation, contact, out-of-plane motion, and measurement error.

## Recommendation before Stage 2

Close Stage 1.5 as a negative ablation and proceed to the framework's Stage-2 parameter-recovery benchmark in simulation. Generate trajectories with known `Kp`, `Kd`, response delay, torque limit, damping, and perturbation input; freeze the simulated plant; then test whether inverse optimization recovers those known values under noise. Do not first interpret controller gains inferred from S43 falls as physiological quantities, because force, CoP, contact state, and perturbation input remain unavailable.

The S43 Stage-1 models can still be retained as descriptive trajectory and residual diagnostics. If moving support is revisited later, use measured CoP/contact data or a separately validated support-state model rather than the observed FOOT midpoint as an inference-time input.
