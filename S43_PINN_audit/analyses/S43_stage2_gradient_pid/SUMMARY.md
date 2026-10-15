# Revised Stage 2: gradient-based PID identification

## Method

The exact retained Stage-1 fold/seed checkpoints are loaded and frozen. Only Kp, Kd, Ki and continuous response delay are optimized. The loss is the normalized Stage-1 governing-equation residual. The effective-torque branch is not a fitting target. Perturbation torque is fixed to zero, and no nuisance torque or torque saturation is used.

## Synthetic recovery check

| Parameter | True | Estimated | Error |
|---|---:|---:|---:|
| alpha Kp | 1.400000 | 1.404851 | 0.347% |
| beta Kd | 0.450000 | 0.412325 | 8.372% |
| kappa Ki | 0.120000 | 0.121546 | 1.288% |
| Delay | 0.100000 s | 0.091807 s | 8.193 ms |

## Held-out CoM results

Values are means over four held-out trials and two frozen Stage-1 seeds.

| Activity | Gradient PID | Frozen Stage 1 | Constant velocity |
|---|---:|---:|---:|
| A11 | 0.2767 m | 0.2520 m | 0.4028 m |
| A13 | 0.3981 m | 0.4467 m | 0.3791 m |

## Effective parameter summary

| Activity | alpha Kp mean [range] | beta Kd mean [range] | kappa Ki mean [range] | Delay mean [range] |
|---|---:|---:|---:|---:|
| A11 | 0.9733 [0.8864, 1.0356] | 0.1064 [0.0000, 0.2838] | 0.0158 [0.0000, 0.1261] | 0.2000 [0.2000, 0.2000] s |
| A13 | 0.6539 [0.0000, 0.8891] | 0.4296 [0.3532, 0.5670] | 0.4142 [0.0014, 1.5555] | 0.2000 [0.2000, 0.2000] s |

## Interpretation

- 16/16 held-out forward simulations remained finite.
- These estimates are effective zero-perturbation model parameters, not physiological measurements.
- Progress to Stage 3 should depend on synthetic recovery, cross-start convergence, held-out prediction, and parameter consistency—not training physics loss alone.
- Superseded least-squares, nuisance-torque, saturation, and torque-limit branches are excluded from the cleaned codebase.

