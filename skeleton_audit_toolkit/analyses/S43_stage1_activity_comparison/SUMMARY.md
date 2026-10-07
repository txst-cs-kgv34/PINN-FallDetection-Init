# S43 Stage-1 cross-activity comparison

## Controlled result

A11 and A13 used the same Stage-1 architecture, losses, optimizer, physics weights, seeds and whole-trial validation. A11 used anterior-posterior CoM; A13 used medial-lateral CoM.

| Activity | Data-only RMSE | Best PINN RMSE | PINN trajectory change | Residual reduction | Matched PINN wins |
|---|---:|---:|---:|---:|---:|
| A11 | 0.2430 m | 0.2520 m | +3.7% | 33.9% | 4 / 8 |
| A13 | 0.4121 m | 0.4467 m | +8.4% | 31.4% | 2 / 8 |

Positive trajectory change means the PINN was worse than the identical data-only network.

## Interpretation

- The best nonzero setting was lambda=0.01 for both activities.
- In both activities, physics substantially reduced the angular-equation residual but did not improve aggregate held-out CoM accuracy.
- A11 was the more stable prediction problem: the data-only network achieved 0.2430 m and beat both simple controls. Its best PINN was 3.7% worse in CoM RMSE, although angle RMSE changed by -5.1%.
- A13 remained dominated by its long T02 extrapolation fold: the data-only network achieved 0.4121 m, and the best PINN was 8.4% worse.
- The repeated pattern across two fall directions strengthens the conclusion that lower residual alone is not evidence of more accurate motion.
- RMSE magnitudes across A11 and A13 are descriptive rather than a formal activity ranking because the modeled horizontal direction, trial windows and individual trajectories differ.
- Both activities show large pivot-to-CoM radius changes, so the rigid constant-length single-link assumption remains violated.

## Decision

Retain the Stage-1 inverted-pendulum equation as an interpretable auxiliary constraint and diagnostic, but do not increase its weight or use it yet for synthetic fall generation. The next mechanics experiment should relax the fixed-length/fixed-pivot assumption and be tested against the same data-only controls.
