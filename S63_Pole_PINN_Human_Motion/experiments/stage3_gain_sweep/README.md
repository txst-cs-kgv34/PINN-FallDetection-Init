# S63 Stage 3 fixed-gain sweep

This completed experiment repeats the controlled S43 gain-chunk study for Subject 63 A11 front-fall data. It keeps the existing S63 pole-PINN architecture, equations, losses, data, seed, and Stage 1 checkpoint unchanged. Only the four controller gains supplied to Stage 3 change. All 11 requested chunks completed successfully.

## Experimental question

For each manually supplied gain tuple, how closely does the Stage 3 forward block reconstruct the five measured S63 CoM trajectories?

Each chunk independently:

1. rebuilds the unchanged conditional pole PINN;
2. restores the same S63 Stage 1 checkpoint;
3. fixes one `Kp_theta, Kd_theta, Kp_x, Kd_x` tuple;
4. keeps `Pi = 3.628571 deg` and `tau = 0.23 s` fixed;
5. resets the same random seed;
6. runs the original Stage 3 training for 5,000 epochs; and
7. produces five matched forward simulations, one from each real trial's initial state.

Stages 1 and 2 are not rerun. The earlier set of 100 random-initial-angle trajectories is also not regenerated; this experiment needs matched real/synthetic simulations so that trajectory MSE is meaningful.

## Gain chunks

Chunks 1-10 are equally spaced between the S63-identified gains and the Subject B paper gains. Chunk 11 is the exact Subject A paper Kp/Kd comparison used in the revised S43 experiment.

| Chunk | Kp_theta | Kd_theta | Kp_x | Kd_x | Meaning |
|---:|---:|---:|---:|---:|---|
| 1 | 145.109024 | 15.048624 | 14.932888 | 15.048451 | S63-identified endpoint |
| 2 | 155.652466 | 16.709888 | 14.718123 | 16.709734 | S63 to Subject B interpolation |
| 3 | 166.195908 | 18.371152 | 14.503357 | 18.371017 | S63 to Subject B interpolation |
| 4 | 176.739349 | 20.032416 | 14.288592 | 20.032301 | S63 to Subject B interpolation |
| 5 | 187.282791 | 21.693680 | 14.073827 | 21.693584 | S63 to Subject B interpolation |
| 6 | 197.826233 | 23.354944 | 13.859061 | 23.354867 | S63 to Subject B interpolation |
| 7 | 208.369675 | 25.016208 | 13.644296 | 25.016150 | S63 to Subject B interpolation |
| 8 | 218.913116 | 26.677472 | 13.429531 | 26.677434 | S63 to Subject B interpolation |
| 9 | 229.456558 | 28.338736 | 13.214765 | 28.338717 | S63 to Subject B interpolation |
| 10 | 240.000000 | 30.000000 | 13.000000 | 30.000000 | Subject B paper endpoint |
| 11 | 120.000000 | 28.000000 | 14.000000 | 19.000000 | Exact Subject A paper Kp/Kd |

The paper's reported Pi values are provenance only. They are not assigned because this controlled experiment varies only Kp/Kd. This means the sweep tests gain sensitivity; it is not a new joint parameter-identification run.

## Completed results

The primary ranking metric is pooled normalized MSE over the same 412 measured samples from T01-T05. Lower is better. Chunk 6 is the numerical winner, but chunks 6, 7, and 11 are separated by only 0.54%, so a single deterministic run cannot establish that their ordering is robust.

| Combined rank | Chunk | Kp_theta | Kd_theta | Kp_x | Kd_x | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta pooled W1 (deg) | x pooled W1 (cm) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6 | 197.83 | 23.35 | 13.86 | 23.35 | **0.103263** | 36.790 | **27.749** | 0.492 | 0.663 |
| 2 | 7 | 208.37 | 25.02 | 13.64 | 25.02 | 0.103304 | 34.603 | 29.962 | **0.490** | 0.632 |
| 3 | 11 | 120.00 | 28.00 | 14.00 | 19.00 | 0.103816 | 37.051 | 27.835 | 0.498 | 0.513 |
| 4 | 10 | 240.00 | 30.00 | 13.00 | 30.00 | 0.105267 | 36.003 | 29.788 | 0.498 | 0.462 |
| 5 | 5 | 187.28 | 21.69 | 14.07 | 21.69 | 0.105910 | 35.566 | 30.627 | 0.494 | 0.664 |
| 6 | 8 | 218.91 | 26.68 | 13.43 | 26.68 | 0.106734 | 34.525 | 32.184 | 0.501 | 0.446 |
| 7 | 9 | 229.46 | 28.34 | 13.21 | 28.34 | 0.107154 | 36.428 | 30.543 | 0.505 | 0.497 |
| 8 | 3 | 166.20 | 18.37 | 14.50 | 18.37 | 0.108744 | 35.356 | 32.609 | 0.498 | 0.672 |
| 9 | 2 | 155.65 | 16.71 | 14.72 | 16.71 | 0.109965 | 36.367 | 32.362 | 0.496 | 0.680 |
| 10 | 4 | 176.74 | 20.03 | 14.29 | 20.03 | 0.114410 | 36.364 | 35.143 | 0.502 | 0.627 |
| 11 | 1 | 145.11 | 15.05 | 14.93 | 15.05 | 0.127258 | **30.677** | 48.859 | 0.507 | **0.371** |

### Main interpretation

- Chunk 6 gives the lowest combined error and lowest forward-x MSE. Its normalized MSE is 18.86% below the S63-identified endpoint in chunk 1.
- Chunk 7 is only 0.04% above chunk 6 and gives the best theta W1. These two chunks are effectively tied until repeated across multiple seeds.
- The exact Subject A gains in chunk 11 rank third, only 0.54% above chunk 6 and 1.38% better than the Subject B endpoint in chunk 10.
- Chunk 1 is best for theta MSE and early pooled x W1, yet worst for combined MSE because its full-trajectory x MSE is 76.1% above chunk 6. W1 over the common 0.33 s window and paired MSE over complete trials answer different questions.
- T02 drives the pooled ranking: it contains 29.9% of the samples but contributes about 70% of theta squared error and 41-83% of x squared error, depending on the chunk.
- The smallest Stage 3 training objective occurs in chunk 1, not chunk 6. The physics-weighted Stage 3 objective must not be interpreted as reconstruction MSE.

See `FINDINGS.md` for the trial-level analysis, endpoint comparisons, Wasserstein interpretation, limitations, and advisor-ready conclusion.

## Where to place this code

Unzip the supplied code package into the root of your existing `S63_Pole_PINN_Human_Motion` directory. After extraction, this file should be located at:

```text
S63_Pole_PINN_Human_Motion/
  experiments/
    stage3_gain_sweep/
      run_gain_sweep.py
```

The experiment expects these existing S63 files:

- `source/pinn_pole_synthetic_data_generation.py`
- `CORE_PIPELINE_LOCK.json`
- `data/pole_compatible/A11/SubjectB_S63A11T01.tsv` through `T05.tsv`
- `results/full_run/stage1_best.weights.h5`
- `results/full_run/identified_parameters.json`
- `config/S63_runtime_overrides.json`

The `SubjectB_` filename prefix is only the unchanged loader contract; the files contain S63 data.

The runner reapplies the documented S63 `minimum_trial_seconds = 0.25` eligibility override. Without it, the unchanged source default of two seconds would reject every short S63 trial. This is the same disclosed wrapper setting used for the completed S63 full run; it does not modify the pole source or network architecture.

## Reproduce on the MacBook

From the root of `S63_Pole_PINN_Human_Motion`:

```bash
source .venv/bin/activate
chmod +x experiments/stage3_gain_sweep/run_on_mac.sh
chmod +x experiments/stage3_gain_sweep/package_results.sh
python experiments/stage3_gain_sweep/check_setup.py
bash experiments/stage3_gain_sweep/run_on_mac.sh
```

`run_on_mac.sh` validates the setup and then runs all 11 chunks at 5,000 Stage 3 epochs with batch size 4,096. On macOS it uses `caffeinate` automatically to prevent sleep.

The run is resumable. A chunk with a completed `result.json` is skipped. To resume manually:

```bash
python experiments/stage3_gain_sweep/run_gain_sweep.py \
  --chunks all \
  --epochs 5000 \
  --batch-size 4096
```

To test one chunk first:

```bash
python experiments/stage3_gain_sweep/run_gain_sweep.py \
  --chunks 1 \
  --epochs 20 \
  --batch-size 4096 \
  --output experiments/stage3_gain_sweep/smoke_results
```

The short command is an execution check only. Do not mix `smoke_results` with the full scientific results.

## Metrics and figures

Every chunk reports trial-wise and pooled:

- theta MSE, RMSE, and MAE in degrees;
- forward-x MSE, RMSE, and MAE in centimeters;
- combined normalized MSE;
- pooled and time-resolved Wasserstein-1 distances;
- absolute differences between real and synthetic means; and
- the Stage 3 loss history and best objective.

Every chunk also creates:

- `real_vs_synthetic_com_by_trial.png`;
- `real_vs_synthetic_means_and_distances.png`;
- `mse_by_trial.csv`;
- `time_resolved_means_and_distances.csv`;
- five `synthetic_com/*.csv` matched-trajectory tables; and
- Stage 3 best/final weight files.

The mean-and-distance figure places real and synthetic means/ranges beside W1 and the absolute mean difference. For S63, the common W1 window is expected to end near 0.33 s because T05 is the shortest accepted trial. Therefore, use MSE for paired trajectory accuracy and W1 only for early marginal-distribution similarity.

Aggregate files include:

- `gain_sets.csv`;
- `gain_sweep_metrics.csv`;
- `summary.json`;
- `REPORT.md`;
- `mse_by_gain_chunk.png`;
- `wasserstein_by_gain_chunk.png`; and
- `best_chunk_real_vs_synthetic_means_and_distances.png`.

## Package reproduced results

After all 11 chunks finish:

```bash
bash experiments/stage3_gain_sweep/package_results.sh
```

This creates `S63_Stage3_Gain_Sweep_Results.zip` in the project root. It contains the exact experiment code, gain table, all per-trial and pooled metrics, matched trajectory CSVs, plots, and saved Stage 3 checkpoints.

## Interpretation boundary

The gains are manually fixed effective parameters of the preserved cart-pole model. A low MSE identifies the best tested gain tuple for reconstructing these five short S63 trials; it does not prove that the tuple is a directly measured human neuromuscular controller.
