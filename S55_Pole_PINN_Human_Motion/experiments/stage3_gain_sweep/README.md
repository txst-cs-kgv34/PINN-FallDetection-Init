# S55 Stage-3 fixed-gain sweep

This experiment reruns Stage 3 independently for 11 fixed controller-gain sets while preserving the pole-PINN architecture and training function.

## Prerequisite

Complete the clean S55 full run first. The sweep refuses to start unless it finds:

- the S55 Stage-1 checkpoint;
- the S55 identified controller parameters;
- the full-run configuration and final checkpoint;
- exactly 100 generated trajectories; and
- `run_mode.json` proving that the full run used exactly the five declared S55 input TSVs.

This prevents a checkpoint trained with stale or mixed-subject files from becoming the gain-sweep baseline.

## Chunks

- Chunks 1–10 linearly interpolate the four gains from the clean S55-identified endpoint to the Subject-B paper endpoint `(240, 30, 13, 30)`.
- Chunk 11 uses the Subject-A comparison gains `(120, 28, 14, 19)`.
- S55's identified `Pi` and fixed `tau = 0.23 s` remain constant across chunks.
- Every chunk resets the same random seed and restores the same S55 Stage-1 checkpoint before training.

## Run

From the project root:

```bash
./run_on_mac.sh gain-sweep
./run_on_mac.sh gain-sweep-package
```

The launcher activates `~/.venv/bin/activate`, streams output to the terminal, and saves the same log to `experiments/stage3_gain_sweep/results/gain_sweep.log`.

For advanced resume/recovery runs, invoke `run_gain_sweep.py` directly with `--chunks`, `--force`, `--skip-aggregate`, or `--analyze-only`.

## Metrics and outputs

For every trial and the pooled data, the sweep reports:

- theta and x MSE, RMSE, and MAE;
- normalized paired reconstruction MSE;
- pooled Wasserstein-1 distances over the common time support;
- time-resolved mean-distribution distances; and
- the minimum Stage-3 training objective.

The primary combined ranking is pooled normalized MSE. Wasserstein distance and the Stage-3 objective are complementary metrics and may select different chunks.

Each `results/chunk_XX/` directory contains checkpoints, loss history, matched real-versus-synthetic CSVs, metrics, and figures. Aggregate outputs include `gain_sets.csv`, `gain_sweep_metrics.csv`, `summary.json`, `REPORT.md`, and cross-chunk plots.

The common Wasserstein window will be limited by the shortest accepted S55 trial, currently T02 at 0.53 seconds after the loader cutoff. This limitation should be stated in the final analysis.
