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

## Package the completed results

After the run prints that ten chunks were aggregated:

```bash
bash experiments/stage3_gain_sweep/package_results.sh
```

Upload `S43_Stage3_Gain_Sweep_Results.zip` for interpretation. It includes the exact gain table, per-trial and pooled metrics, all real-versus-synthetic CoM CSV files, the revised mean-and-distance figures, aggregate MSE/Wasserstein graphs, the report, and the ten saved Stage 3 checkpoints.

## Scope

The synthetic curves in this experiment are matched forward simulations used for controller-sensitivity evaluation. They are different from the earlier set of 100 trajectories generated from random initial angles. This pairing is necessary for a meaningful trajectory MSE.
