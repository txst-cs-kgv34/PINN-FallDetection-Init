# S63 full-run checkpoint and synthetic-trajectory audit

## Checkpoint reconstruction comparison

Both saved checkpoints were evaluated deterministically on the same pooled set of **412 measured samples** from T01-T05. The calculation uses the unchanged source's `data_loss` definition:

`mean(((theta_pred-theta_true)/25 deg)^2) + mean(((x_pred-x_true)/0.25 m)^2)`

| Checkpoint | Normalized reconstruction loss | theta RMSE (deg) | x RMSE (cm) |
|---|---:|---:|---:|
| Stage 1 best | 0.000629546 | 0.337198 | 0.528927 |
| After Stage 3 | 0.113098592 | 5.902940 | 5.986812 |

The Stage-3-to-Stage-1 normalized-loss ratio is `0.113098592 / 0.000629546 = 179.651`. Values above 1 mean physics refinement increased reconstruction error; values below 1 mean it reduced it. This checkpoint-level comparison is stronger evidence than comparing stochastic mini-batch losses printed during training.

`stage3_best.weights.h5` and `conditional_forward_pinn.weights.h5` are byte-identical, so the Stage 3 checkpoint is also the final model used to generate the trajectories. SHA-256 provenance is recorded in `evaluation_summary.json`.

## Synthetic trajectories

- 100 files were found; each contains 3001 rows over 30 s.
- All saved values are finite.
- Across the complete extrapolation, theta spans -340.365 to 292.949 deg and x spans -26.684 to 48.161 m.
- 100 of 100 trajectories cross |theta| = 20 deg; their first crossings occur between 4.04 and 4.22 s (median 4.11 s).

The short-horizon figure is a qualitative overlay, not a held-out predictive validation: the synthetic curves use randomized initial angles and zero initial velocities, whereas each real trial has its own measured initial conditions. The 30-second envelope is extrapolation far beyond the 0.33-1.22 s measured pre-cutoff windows and must not be interpreted as validated human biomechanics.

## Reproduce

```bash
python analysis/evaluate_full_run.py
python analysis/visualize_trajectories.py --horizon 5
python analysis/visualize_trajectories.py --horizon 30 --count 20
```
