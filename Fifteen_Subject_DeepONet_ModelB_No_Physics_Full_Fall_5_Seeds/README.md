# B-no-physics — matched 15-subject full-fall DeepONet, five seeds

This directory is the matched no-physics ablation for:

```text
Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds
```

It predicts the complete standing-to-apparent-contact CoM trajectory for the
same 15 subjects:

```text
S43, S55, S57, S62, S63, S59, S56, S49, S48, S46,
S45, S44, S34, S32, S30
```

The comparison changes one training factor only:

```text
Physics:     L = L_real_forecast + 0.01 × L_cart_pole_physics
No physics:  L = L_real_forecast
```

The cart-pole residual is not evaluated during training and cannot affect
gradients or validation checkpoint selection. Angular and horizontal residuals
are still calculated after training on held-out predictions as post-hoc
diagnostics, which keeps the result schema directly comparable.

## Matched experimental condition

The following are identical to the full-fall Physics run:

- all 15 subjects and accepted A11 trials;
- deterministic audit-to-pole conversion and repaired rows;
- complete standing-to-apparent-contact interval;
- 8.0-s grid at 100 Hz, with no pre-20° cutoff or silent truncation;
- `atan2(marker_dx, marker_dy)` angle decoding;
- first 0.40 s as context, divided into four 0.10-s windows;
- context channels: theta, forward x, both velocities, and local time;
- context encoder, positive four-coordinate head, DeepONet branch and trunk;
- hard initial conditions for theta and x;
- the same five subject folds and one real validation subject per fold;
- the same five base optimization seeds and `base_seed + fold_id` rule;
- AdamW settings, batch size, epoch limit, patience, and gradient clipping;
- validation-subject normalized forecast MSE for checkpoint selection; and
- subject-balanced aggregation across the 15 held-out subjects.

Only these two configuration values differ:

| Setting | Physics | Matched no physics |
|:---|---:|---:|
| `training.use_physics` | `true` | `false` |
| `training.physics_weight` | `0.01` | `0.0` |

The four positive encoder outputs and their original scales are retained to
keep the architecture exact. Without physics supervision, however, they are
latent conditioning coordinates and must not be interpreted as identified
physiological controller gains. CSV column names remain unchanged for paired
analysis compatibility.

## Five folds

| Fold | Validation | Unseen test subjects |
|---:|:---:|:---|
| 1 | S63 | S57, S46, S30 |
| 2 | S62 | S55, S48, S43 |
| 3 | S57 | S45, S59, S56 |
| 4 | S55 | S34, S32, S49 |
| 5 | S43 | S44, S62, S63 |

The other 11 subjects in each fold are used for training. Test subjects are
excluded from both gradient training and validation selection.

## Five seeds

```text
20261101, 20261102, 20261103, 20261104, 20261105
```

Fold `f` uses `base_seed + f`, exactly as in the Physics run. The experiment
therefore trains 25 models and produces 75 held-out subject-seed evaluations.

## Data placement

Unzip this directory beside the same subject directories used by the Physics
run:

```text
PINN-FallDetection-Init/
├── S43_Pole_PINN_Human_Motion/
├── S55_Pole_PINN_Human_Motion/
├── S57_Pole_PINN_Human_Motion/
├── S62_Pole_PINN_Human_Motion/
├── S63_Pole_PINN_Human_Motion/
├── S59_PINN_audit/
├── S56_PINN_audit/
├── S49_PINN_audit/
├── S48_PINN_audit/
├── S46_PINN_audit/
├── S45_PINN_audit/
├── S44_PINN_audit/
├── S34_PINN_audit/
├── S32_PINN_audit/
├── S30_PINN_audit/
└── Fifteen_Subject_DeepONet_ModelB_No_Physics_Full_Fall_5_Seeds/
```

Pole-PINN training and sweep-gain experiments are not required. The five
legacy pole-compatible TSV directories must already exist, as in the Physics
run. The ten audit subjects are converted deterministically by this directory.

## Run locally

Python 3.10+ is recommended. The setup command creates or reuses the shared
environment at `~/.venv`; set `PINN_VENV_DIR` to override it. `auto` selects
CUDA, then Apple MPS, then CPU.

```bash
cd Fifteen_Subject_DeepONet_ModelB_No_Physics_Full_Fall_5_Seeds
chmod +x run.sh run_on_mac.sh
./run.sh setup
./run.sh validate
./run.sh test
./run.sh smoke auto
./run.sh full auto
```

Device-specific examples:

```bash
./run.sh smoke cpu
./run.sh fold 1 cuda 3
./run.sh seed 3 cuda
./run.sh full cuda
./run.sh full mps
```

`fold 1 cuda 3` runs Fold 1 with seed index 3 (`20261103`). Completed fold
summaries are skipped, so `./run.sh full ...` can resume an interrupted run.
Use `FORCE=1` only to intentionally rerun completed folds.

```bash
./run.sh status
FORCE=1 ./run.sh fold 1 cuda 3
```

Usage:

```text
./run.sh setup
./run.sh validate
./run.sh prepare
./run.sh smoke [auto|cuda|mps|cpu] [SEED_INDEX]
./run.sh fold FOLD_ID [auto|cuda|mps|cpu] [SEED_INDEX]
./run.sh seed SEED_INDEX [auto|cuda|mps|cpu]
./run.sh full [auto|cuda|mps|cpu]
./run.sh aggregate
./run.sh package
./run.sh status
./run.sh test
```

## Outputs

For every held-out trial, the run saves:

- real and predicted theta/x trajectories;
- normalized MSE, RMSE, MAE, and Wasserstein-1 metrics;
- the four architecture-matched context coordinates;
- post-hoc angular and horizontal residuals by time;
- prediction and residual plots; and
- the validation-selected checkpoint and training history.

After all 25 models finish, the root `results/full/` directory contains the
five-seed subject, trial, fold, and seed summaries plus the boxplots. The run
packages:

```text
Fifteen_Subject_ModelB_No_Physics_Full_Fall_5_Seeds_Results.zip
```

Please send that ZIP back for the paired Physics-versus-no-physics analysis.
The primary comparison will pair the same subject and seed, with trial-level
paired analysis added where the accepted trial sets match.

## Interpretation limits

- This is a matched ablation, not a new architecture.
- Five seeds measure optimization variability but do not create more than 15
  independent human subjects.
- Apparent contact is visually/skeleton marked rather than force-plate
  confirmed.
- Post-hoc residuals do not mean that the no-physics model was trained with
  biomechanics.
- The four positive context coordinates are not identified physical gains in
  this condition.

See `MATCHED_ABLATION.md` for the exact change audit.
