# S55 full-run checkpoint and synthetic-trajectory audit

## Checkpoint reconstruction comparison

Both saved checkpoints were evaluated deterministically on the same pooled set of **624 measured samples** from S55A11T01, S55A11T02, S55A11T03, S55A11T04, S55A11T05. The calculation uses the unchanged source's `data_loss` definition:

`mean(((theta_pred-theta_true)/25 deg)^2) + mean(((x_pred-x_true)/0.25 m)^2)`

| Checkpoint | Normalized reconstruction loss | theta RMSE (deg) | x RMSE (cm) |
|---|---:|---:|---:|
| Stage 1 best | 0.002986566 | 0.710799 | 1.166777 |
| After Stage 3 | 0.483573973 | 9.618655 | 14.481546 |

The Stage-3-to-Stage-1 normalized-loss ratio is `0.483573973 / 0.002986566 = 161.916`. Values above 1 mean physics refinement increased reconstruction error; values below 1 mean it reduced it. This checkpoint-level comparison is stronger evidence than comparing stochastic mini-batch losses printed during training.

`stage3_best.weights.h5` and `conditional_forward_pinn.weights.h5` are byte-identical, so the Stage 3 checkpoint is also the final model used to generate the trajectories. SHA-256 provenance is recorded in `evaluation_summary.json`.

## Synthetic trajectories

- 100 files were found; each contains 3001 rows over 30 s.
- All saved values are finite.
- Across the complete extrapolation, theta spans -159.409 to 279.160 deg and x spans -108.289 to 50.471 m.
- 100 of 100 trajectories cross |theta| = 20 deg; their first crossings occur between 4.84 and 5.15 s (median 4.92 s).

The short-horizon figure is a qualitative overlay, not a held-out predictive validation: the synthetic curves use randomized initial angles and zero initial velocities, whereas each real trial has its own measured initial conditions. The 30-second envelope is extrapolation far beyond the 0.53-1.52 s measured pre-cutoff windows and must not be interpreted as validated human biomechanics.

## Reproduce

```bash
python analysis/evaluate_full_run.py
python analysis/visualize_trajectories.py --horizon 5
python analysis/visualize_trajectories.py --horizon 30 --count 20
```
