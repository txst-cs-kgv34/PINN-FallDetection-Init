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

The returned ZIP has now been analyzed against the matched Physics run. See
`FINDINGS.md` for the interpretation and `comparison/` for the reproducible
paired analysis, tables, and figures.

## Completed no-physics results

All 25 models completed: five folds by five optimization seeds. The results
contain 75 held-out subject-seed evaluations and 350 held-out trial-seed
evaluations, representing 15 independent subjects and 70 accepted trials.

Subject-balanced held-out means across the five seeds are:

| Metric | B-no-physics mean | Across-seed SD | 95% t CI over five seeds |
|:---|---:|---:|:---|
| Normalized forecast MSE | 3.7831 | 0.5413 | 3.1109 to 4.4552 |
| Theta RMSE | 22.7223° | 0.8252° | 21.6976° to 23.7470° |
| CoM x RMSE | 30.9527 cm | 1.2103 cm | 29.4500 to 32.4555 cm |

These across-seed intervals describe optimization variability; they are not
population confidence intervals over humans.

## Matched Physics comparison

The Physics and no-physics outputs match exactly on subject, optimization
seed, and accepted trial: 75 subject-seed pairs and 350 trial-seed pairs. For
the main inference, each subject is first averaged over its five seeds, leaving
15 independent paired subject values.

| Metric | Physics | No physics | Physics reduction | Subjects favoring Physics |
|:---|---:|---:|---:|---:|
| Normalized forecast RMSE | 1.5883 | 1.7292 | 8.15% | 12/15 |
| Theta RMSE | 21.4843° | 22.7223° | 5.45% | 12/15 |
| CoM x RMSE | 28.4642 cm | 30.9527 cm | 8.04% | 12/15 |

The descriptive result consistently favors Physics. Two-sided subject-level
Wilcoxon tests were below 0.05 before multiple-metric correction for normalized
RMSE (`p=0.0256`) and CoM x RMSE (`p=0.0215`), but their Holm-adjusted values
are both `p=0.0646`. Theta RMSE is `p=0.1354`. Therefore, the correct claim is
that Physics produced lower average errors in this experiment, not that the
ablation establishes a statistically significant benefit at family-wise
`alpha=0.05` across all three metrics.

The five points in each box in the comparison figure are the five optimization
seeds, not five different subjects or trials. Trial-level plots are included as
exploratory diagnostics because multiple trials from one person are correlated.

Post-hoc physics residuals are excluded from the primary comparison. In the
no-physics model, the four positive context coordinates are unsupervised latent
features rather than physically identified controller gains, so its residuals
are not a fair trajectory-accuracy endpoint.

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
