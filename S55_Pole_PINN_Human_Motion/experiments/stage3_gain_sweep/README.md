# S55 Stage-3 fixed-gain sweep

This experiment retrains Stage 3 independently for 11 fixed controller-gain sets while preserving the original pole-PINN architecture, equations, training function, S55 Stage-1 checkpoint, `Pi = 3.625025 deg`, and `tau = 0.23 s`.

Chunks 1-10 linearly interpolate all four gains from the S55-identified endpoint to `(240, 30, 13, 30)`. Chunk 11 uses the comparison gains `(120, 28, 14, 19)`. Every chunk resets seed 1234, trains for 5,000 epochs with batch size 4,096, and restores its best checkpoint before evaluation.

## Result

All 11 chunks completed. Pooled normalized MSE selects chunk 5:

| Rank | Chunk | `Kp_theta` | `Kd_theta` | `Kp_x` | `Kd_x` | Normalized MSE |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 187.303 | 21.696 | 8.589 | 21.696 | **0.430774** |
| 2 | 10 | 240.000 | 30.000 | 13.000 | 30.000 | 0.433449 |
| 3 | 8 | 218.921 | 26.678 | 11.235 | 26.678 | 0.438054 |

Chunk 5 also gives the lowest pooled x MSE. Chunk 11 gives the lowest theta MSE and training objective but ranks last on combined reconstruction because it has the highest x MSE. No setting wins both angle and translation.

The 0.62% normalized-MSE difference between chunks 5 and 10 is small compared with the run-to-run variation observed when the same chunk-1 gains were trained in the full run and sweep. Treat chunk 5 and chunk 10 as a leading region until they are repeated across multiple seeds. See `FINDINGS.md` for the complete ranked table and interpretation.

## Run

From the project root:

```bash
./run_on_mac.sh gain-sweep
./run_on_mac.sh gain-sweep-package
```

The launcher activates `~/.venv/bin/activate`, streams output to the terminal, and saves the same log under `experiments/stage3_gain_sweep/results/`.

The sweep reports time-aligned MSE/RMSE/MAE, normalized paired MSE, pooled and time-resolved Wasserstein-1 distances over the common 0.52 s support, and the minimum Stage-3 objective. The primary combined ranking is pooled normalized MSE; Wasserstein distance and the training objective answer different questions and can select different chunks.
