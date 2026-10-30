# S62 full-run checkpoint and synthetic-trajectory audit

## Checkpoint reconstruction comparison

Both saved checkpoints were evaluated deterministically on the same pooled set of **1,290 measured samples** from S62A11T01, S62A11T02, S62A11T03, S62A11T04, S62A11T05, S63A11T01, S63A11T02, S63A11T03, S63A11T04, S63A11T05. The calculation uses the unchanged source's `data_loss` definition:

`mean(((theta_pred-theta_true)/25 deg)^2) + mean(((x_pred-x_true)/0.25 m)^2)`

| Checkpoint | Normalized reconstruction loss | theta RMSE (deg) | x RMSE (cm) |
|---|---:|---:|---:|
| Stage 1 best | 0.008429097 | 1.397914 | 1.820446 |
| After Stage 3 | 0.565339267 | 7.030476 | 17.432998 |

The Stage-3-to-Stage-1 normalized-loss ratio is `0.565339267 / 0.008429097 = 67.070`. Values above 1 mean physics refinement increased reconstruction error; values below 1 mean it reduced it. This checkpoint-level comparison is stronger evidence than comparing stochastic mini-batch losses printed during training.

`stage3_best.weights.h5` and `conditional_forward_pinn.weights.h5` are byte-identical, so the Stage 3 checkpoint is also the final model used to generate the trajectories. SHA-256 provenance is recorded in `evaluation_summary.json`.

## Synthetic trajectories

- 100 files were found; each contains 3001 rows over 30 s.
- All saved values are finite.
- Across the complete extrapolation, theta spans -280.725 to 366.196 deg and x spans -37.783 to 29.761 m.
- 100 of 100 trajectories cross |theta| = 20 deg; their first crossings occur between 4.04 and 4.17 s (median 4.09 s).

The short-horizon figure is a qualitative overlay, not a held-out predictive validation: the synthetic curves use randomized initial angles and zero initial velocities, whereas each real trial has its own measured initial conditions. The 30-second envelope is extrapolation far beyond the 0.23-2.96 s measured pre-cutoff windows and must not be interpreted as validated human biomechanics.

## Reproduce

```bash
python analysis/evaluate_full_run.py
python analysis/visualize_trajectories.py --horizon 5
python analysis/visualize_trajectories.py --horizon 30 --count 20
```
