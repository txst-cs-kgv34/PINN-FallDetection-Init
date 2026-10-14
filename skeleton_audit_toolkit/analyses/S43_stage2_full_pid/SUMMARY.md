# Complete Stage 2 frozen-dynamics delayed-PID identification

## Design

The retained Stage-1 lambda=0.01 architecture is retrained and saved independently inside each whole-trial fold, then frozen. Stage 2 optimizes only Kp, Kd, Ki, delay and torque saturation. The primary model fixes perturbation torque to zero; a regularized three-component nuisance torque is reported only as sensitivity.

## Held-out results

| Activity | PID zero XY RMSE | PD zero XY RMSE | PID nuisance XY RMSE | Stage-1 PINN | Constant velocity |
|---|---:|---:|---:|---:|---:|
| A11 | 0.2408 m | 0.2406 m | 0.2430 m | 0.2520 m | 0.4028 m |
| A13 | 0.4518 m | 0.4240 m | 0.4665 m | 0.4467 m | 0.3791 m |

## Interpretation

On A11, the PID integral coefficient collapses to approximately zero and PID
does not improve over nested PD. On A13, full PID is worse than PD; the nonzero
mean Ki is driven by the unstable S43A13T02 fold rather than consistent
recovery. The nuisance-torque branch worsens mean held-out error for both
activities.

These are assumption-dependent effective controller fits. The skeleton
recordings contain no measured perturbation, ground-reaction force or center of
pressure. Trajectory agreement therefore cannot validate physiological gains.
Damping remains fixed at the Stage-1 value b=0 rather than being re-estimated
after freezing Stage 1.
