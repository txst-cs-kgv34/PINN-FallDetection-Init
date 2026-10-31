# Stage 3 fixed-gain sweep

This experiment measures how the unchanged pole-PINN Stage 3 responds to eleven controller-gain settings for the current subject. It is adapted from the S43 experiment, but it reads the current subject's gains, Pi, and tau from the corrected `results/full_run/identified_parameters.json`; no S43 constants are copied.

## Required clean baseline

The sweep intentionally refuses to start unless:

- `data/pole_compatible/A11` contains exactly the trials listed in the subject's experiment scope;
- `results/full_run/run_mode.json` records a subject-only validated inventory;
- the clean full run produced `stage1_best.weights.h5` and `identified_parameters.json`.

This guard matters because the first returned S57/S62 runs accidentally included five stale S63 TSV files. Those checkpoints must not be reused.

## Controlled design

- Every chunk rebuilds the same architecture and reloads the same clean Stage-1 checkpoint.
- Every chunk resets Python, NumPy, and TensorFlow to seed `1234`.
- Pi and tau stay fixed at the current subject's identified values.
- Only `kp_theta`, `kd_theta`, `kp_x`, and `kd_x` change.
- Chunks 1–10 are equally spaced between the subject-identified gains and the Subject B paper gains `(240, 30, 13, 30)`.
- Chunk 11 uses the Subject A paper gains `(120, 28, 14, 19)`.
- Each chunk uses the original Stage-3 training function, 5,000 epochs, and batch size 4,096.

The matched simulations use each measured trial's initial conditions. They are for controller sensitivity and paired reconstruction error; they are not another set of 100 random-initial-condition falls.

## Run locally

The launcher activates `~/.venv/bin/activate`, validates the clean baseline, prevents macOS sleep with `caffeinate`, and runs all eleven chunks. Progress is shown in Terminal and also saved to `results/gain_sweep.log`:

```bash
bash experiments/stage3_gain_sweep/run_on_mac.sh
```

The run is resumable. A chunk with a completed `result.json` is skipped. To run selected chunks directly:

```bash
source ~/.venv/bin/activate
PYTHONUNBUFFERED=1 python experiments/stage3_gain_sweep/run_gain_sweep.py \
  --chunks 1,5,11 \
  --epochs 5000 \
  --batch-size 4096
```

Use `--force` only when you intentionally want to replace completed selected chunks. Use `--analyze-only` to rebuild aggregate tables and plots from existing chunk results.

## Metrics and outputs

For every trial and pooled across trials, the experiment reports:

- theta MSE/RMSE/MAE in degrees;
- forward-CoM x MSE/RMSE/MAE in centimeters;
- combined normalized MSE using the source output scales;
- pooled and time-resolved one-dimensional Wasserstein-1 distances;
- real and synthetic means and their absolute difference.

The primary ranking is pooled normalized MSE because it preserves matched trial/time reconstruction. Wasserstein distance is a complementary marginal-distribution measure and may select a different chunk.

Each `results/chunk_XX/` directory contains the Stage-3 checkpoint, loss history, per-trial CSV files, paired metrics, and figures. Aggregate outputs include `gain_sets.csv`, `gain_sweep_metrics.csv`, `summary.json`, `REPORT.md`, and cross-chunk MSE/Wasserstein plots.

## Completed S62 result

All 11 chunks completed on the clean five-trial S62 inventory. The primary pooled normalized-MSE ranking selects chunk 11:

| Chunk | Gain set | Normalized MSE | Theta RMSE | x RMSE |
|---:|---|---:|---:|---:|
| 1 | Identified S62 endpoint | 0.236283 | 8.152 deg | 9.012 cm |
| 10 | Subject-B endpoint `(240, 30, 13, 30)` | 0.377634 | **7.329 deg** | 13.502 cm |
| 11 | Subject-A comparison `(120, 28, 14, 19)` | **0.212552** | 7.698 deg | **8.578 cm** |

Chunk 11 reduces normalized MSE by 10.0%, theta MSE by 10.8%, x MSE by 9.4%, and the best Stage-3 objective by 13.1% relative to chunk 1. It is the best balanced S62 candidate under the current protocol. However, T02 restricts all-trial Wasserstein comparisons to 0.23 s, so those W1 values cannot validate later fall behavior.

This sweep produces matched simulations and checkpoints, not 100 new random-condition falls. A new 100-trajectory generation pass is required if chunk 11 is selected as a teacher.

## Package results

After all eleven chunks finish:

```bash
bash experiments/stage3_gain_sweep/package_results.sh
```

Return `<SUBJECT>_Stage3_Gain_Sweep_Results.zip` for analysis.
