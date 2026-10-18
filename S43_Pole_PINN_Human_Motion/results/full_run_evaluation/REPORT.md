# S43 full-run checkpoint and synthetic-trajectory audit

## Evidence for the approximately 305x statement

Both saved checkpoints were evaluated deterministically on the same pooled set of **1,522 measured samples** from T02-T05. The calculation uses the unchanged source's `data_loss` definition:

`mean(((theta_pred-theta_true)/25 deg)^2) + mean(((x_pred-x_true)/0.25 m)^2)`

| Checkpoint | Normalized reconstruction loss | theta RMSE (deg) | x RMSE (cm) |
|---|---:|---:|---:|
| Stage 1 best | 0.004233117 | 1.314333 | 0.958241 |
| After Stage 3 | 1.289735317 | 14.687387 | 24.297432 |

The ratio is `1.289735317 / 0.004233117 = 304.677`, hence **approximately 305x**. This checkpoint-level result is stronger evidence than comparing stochastic mini-batch losses printed during training.

`stage3_best.weights.h5` and `conditional_forward_pinn.weights.h5` are byte-identical, so the Stage 3 checkpoint is also the final model used to generate the trajectories. SHA-256 provenance is recorded in `evaluation_summary.json`.

## Synthetic trajectories

- 100 files were found; each contains 3001 rows over 30 s.
- All saved values are finite.
- Across the complete extrapolation, theta spans -163.516 to 27.303 deg and x spans -3.501 to 3.909 m.
- All 100 trajectories cross |theta| = 20 deg between 14.24 and 25.33 s (median 25.23 s).

The short-horizon figure is a qualitative overlay, not a held-out predictive validation: the synthetic curves use randomized initial angles and zero initial velocities, whereas each real trial has its own measured initial conditions. The 30-second envelope is extrapolation far beyond the 2.69-5.01 s measured windows and becomes physically implausible for human CoM.

## Reproduce

```bash
python analysis/evaluate_full_run.py
python analysis/visualize_trajectories.py --horizon 5
python analysis/visualize_trajectories.py --horizon 30 --count 20
```
