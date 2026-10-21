# Stage 3 fixed-gain sweep

This experiment tests the sensitivity of the unchanged pole-PINN Stage 3 forward block to ten manually supplied controller-gain sets for the same S43 A11 subject data.

## Controlled design

- Same four S43 A11 trials: T02-T05.
- Same human-to-pole adapter inputs.
- Same saved Stage 1 checkpoint for every chunk.
- Same original Stage 3 architecture, equations, losses, 5,000 epochs, batch size, and seed.
- Fixed `Pi = 3.6066 deg` and `tau = 0.23 s`.
- Only `kp_theta`, `kd_theta`, `kp_x`, and `kd_x` vary.
- The ten gain sets linearly interpolate between the controller previously identified from S43 and the Subject A values printed as the paper reference in the original pole code.

Each chunk is independent. Before every Stage 3 run, the script rebuilds the model, reloads the same `results/full_run/stage1_best.weights.h5`, assigns one gain set, and resets all random seeds.

## Completed results

All 10 chunks completed. The primary ranking metric is pooled normalized MSE on the same 1,522 measured samples from T02-T05. Lower is better for every metric in this table.

| Chunk | Kp_theta | Kd_theta | Kp_x | Kd_x | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta pooled W1 (deg) | x pooled W1 (cm) | Takeaway |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| 1 | 145.14 | 15.03 | 5.04 | 15.05 | **1.2380** | 212.64 | 561.12 | 3.600 | 6.247 | **Best combined MSE**; S43-identified endpoint. |
| 2 | 155.68 | 16.70 | 5.93 | 16.71 | 1.2619 | 211.11 | 577.59 | 3.616 | 6.693 | Fourth overall; second-lowest theta MSE, but largest pooled W1 in both outputs. |
| 3 | 166.22 | 18.36 | 6.81 | 18.37 | 1.2693 | 213.77 | 579.58 | 3.529 | 6.453 | Mid-ranked; no metric minimum. |
| 4 | 176.76 | 20.02 | 7.70 | 20.03 | 1.2751 | 221.24 | 575.69 | **3.423** | 5.992 | Best theta W1 but worst theta MSE, showing that distribution match and paired trajectory error differ. |
| 5 | 187.30 | 21.69 | 8.58 | 21.69 | **1.2461** | 217.83 | **560.96** | 3.455 | 5.931 | **Second overall and best x MSE**; strongest alternative to chunk 1. |
| 6 | 197.84 | 23.35 | 9.46 | 23.35 | 1.2608 | 215.27 | 572.76 | 3.593 | 5.984 | Third overall; reasonably balanced, without a single-metric win. |
| 7 | 208.38 | 25.01 | 10.35 | 25.02 | 1.3041 | **209.26** | 605.79 | 3.610 | 6.668 | Best theta MSE but worst combined and x MSE; clear angle-versus-translation tradeoff. |
| 8 | 218.92 | 26.67 | 11.23 | 26.68 | 1.2752 | 216.41 | 580.56 | 3.551 | **5.914** | Best pooled x W1, but only seventh by paired normalized MSE. |
| 9 | 229.46 | 28.34 | 12.12 | 28.34 | 1.2955 | 215.39 | 594.29 | 3.603 | 6.040 | Ninth overall; the higher x error drives the poor combined rank. |
| 10 | 240.00 | 30.00 | 13.00 | 30.00 | 1.2782 | 214.63 | 584.22 | 3.531 | 5.933 | Subject A paper endpoint; eighth overall and 3.24% above chunk 1 in normalized MSE. |

### Main interpretation

- The S43-identified gains in chunk 1 gave the lowest combined reconstruction error. The Subject A paper gains in chunk 10 did not improve this subject's paired reconstruction.
- The sweep is not monotonic. Chunk 5 nearly matches chunk 1 overall and has the lowest forward-CoM MSE, while chunk 7 improves angle MSE at a substantial cost to forward-CoM accuracy.
- The full normalized-MSE spread is only 5.34% from best to worst, so the gain choice matters, but none of these ten settings fixes the larger reconstruction mismatch.
- T03 dominates the pooled result: although it contains 440 of 1,522 samples, it contributes 94.29-94.55% of theta squared error and 94.65-96.01% of x squared error across the sweep.
- W1 is a distribution metric, not a paired trajectory metric. Chunk 4 has the best theta W1 while having the worst theta MSE; chunk 8 has the best pooled x W1 while chunk 5 has the best x MSE.

See [`FINDINGS.md`](FINDINGS.md) for the ranked comparisons, trial-level interpretation, metric definitions, limitations, and recommended next experiment.

## Full run

Activate the same virtual environment that worked for the completed S43 run. From the repository root on macOS, run:

```bash
bash experiments/stage3_gain_sweep/run_on_mac.sh
```

The launcher uses `caffeinate`, runs all ten chunks sequentially, and keeps the original 5,000 Stage 3 epochs and batch size of 4,096. The command is resumable. Existing chunks with a `result.json` file are skipped; an interrupted chunk is rerun from the common Stage 1 checkpoint.

To run a particular subset manually:

```bash
python experiments/stage3_gain_sweep/run_gain_sweep.py \
  --chunks 1,2,3 \
  --epochs 5000 \
  --batch-size 4096
```

## What is compared

For each gain set, the final Stage 3 model receives each real trial's measured initial conditions. This creates four matched synthetic forward simulations. The script reports per-trial and pooled:

- angle MSE in squared degrees;
- forward-CoM MSE in squared centimeters;
- RMSE and MAE;
- the pole code's combined normalized MSE;
- pooled and time-resolved Wasserstein-1 distance.

The common distribution window ends at the shortest real trial. At every time point, Wasserstein distance compares the four real values with the four matched synthetic values.

## Figures

Each chunk contains:

- `real_vs_synthetic_com_by_trial.png`
- `real_vs_synthetic_means_and_distances.png`
- `mse_by_trial.csv`
- `time_resolved_means_and_distances.csv`
- `synthetic_com/` with the four matched trajectories

The revised means-and-distances figure shows:

1. real and synthetic means directly;
2. the full range across the four trajectories;
3. time-resolved W1 distribution distance;
4. absolute distance between the real and synthetic means; and
5. an explicitly labeled average W1 reference line.

Aggregate outputs compare all completed chunks in `results/mse_by_gain_chunk.png`, `results/wasserstein_by_gain_chunk.png`, and `results/gain_sweep_metrics.csv`.

The aggregate MSE figure should be used for matched trajectory accuracy. The W1 figure should be used to describe distribution similarity only. The per-chunk means-and-distances figures show why those rankings can differ: a synthetic distribution can overlap the real distribution while following the wrong trial-specific trajectory.

## Package the completed results

After the run prints that ten chunks were aggregated:

```bash
bash experiments/stage3_gain_sweep/package_results.sh
```

Upload `S43_Stage3_Gain_Sweep_Results.zip` for interpretation. It includes the exact gain table, per-trial and pooled metrics, all real-versus-synthetic CoM CSV files, the revised mean-and-distance figures, aggregate MSE/Wasserstein graphs, the report, and the ten saved Stage 3 checkpoints.

## Scope

The synthetic curves in this experiment are matched forward simulations used for controller-sensitivity evaluation. They are different from the earlier set of 100 trajectories generated from random initial angles. This pairing is necessary for a meaningful trajectory MSE.
