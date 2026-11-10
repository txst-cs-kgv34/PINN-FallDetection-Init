# Model B — 15-subject full-fall unified physics DeepONet (five seeds)

This repository extends the exact earlier **Model B** condition to 15 subjects:

`S43, S55, S57, S62, S63, S59, S56, S49, S48, S46, S45, S44, S34, S32, S30`

It runs the same five-fold experiment with **five optimization seeds**, now over
the complete standing-to-apparent-contact CoM interval. It trains on real
phase-marked trajectories with the differentiable delayed cart-pole
biomechanics residual. It does **not** train on Pole-PINN synthetic trajectories,
teacher checkpoints, or gain-sweep targets.

This full-fall version removes the earlier pre-20-degree truncation. The real
trajectory loss remains active from the end of the 0.40-s context through the
marked apparent-contact endpoint. Physics is enforced over the pre-contact
trajectory, excluding only the final 0.03 s to avoid applying the smooth
cart-pole equations to the impact boundary.

The five base seeds are:

```text
20261101, 20261102, 20261103, 20261104, 20261105
```

These exact seeds must also be used for the no-physics experiment so every
physics run has a paired no-physics run.

## Do Pole_PINN_Human_Motion or Sweep Gain need to be rerun?

**No.** This Model B condition has `requires_teachers=false`,
`gain_weight=0`, and `synthetic_source_weight=0`. Pole-PINN checkpoints and
selected sweep gains do not enter its loss or inputs.

The five earlier subjects still need their already-created pole-compatible TSV
files. If those TSVs are missing on a new machine, rerun only the deterministic
data-conversion step from the earlier subject repository—not Pole-PINN training
and not the gain sweep. The ten new audit subjects are converted by this
repository's deterministic adapter.

## Exact preserved Model B condition

- Context: first 0.40 s, split into four 0.10-s windows.
- Context channels: theta, forward x, both velocities, and local time.
- Encoder: `Conv1d(5,32) → Conv1d(32,64) → adaptive average pool → 96`.
- Positive controller head: Softplus outputs
  `[Kp_theta, Kd_theta, Kp_x, Kd_x]`.
- DeepONet branch: gains + initial state + demographics + two fixed auxiliaries;
  hidden width 160 and output width `2 × 96`.
- Fourier-time trunk: 12 modes, hidden width 160, latent width 96.
- Hard initial conditions:
  `q(t) = q0 + qdot0*t + t²*f(t)` for theta and x.
- Objective: `L_real_forecast + 0.01 × L_cart_pole_physics`.
- Data interval: complete source clip through apparent contact; no 20-degree
  cutoff and no silent horizon truncation.
- Physics interval: valid trajectory except the final 0.03 s at contact.
- Optimizer: AdamW, learning rate `5e-4`, weight decay `1e-6`, batch size 4,
  maximum 800 epochs, patience 100, gradient clip 5.
- Fixed physics: `m=0.0138 kg`, `m0=1 kg`, `l=0.57 m`, `g=9.81 m/s²`,
  `tau=0.23 s`, `Pi=0.0635 rad`, dead-zone sharpness 50.

The inferred gains are effective model parameters, not measured physiological
control gains.

## Full-fall endpoint requirement

Every pole-compatible source TSV must end at the manually marked apparent
contact frame. The ten audit subjects satisfy this automatically because
`prepare_audit_inputs.py` slices each repaired skeleton trajectory at
`apparent_contact`. The five legacy subject TSV directories must contain their
previously phase-clipped standing-to-contact files; do not supply untrimmed
post-fall recordings.

`prepare_real_data.py` now:

- keeps all resampled samples through the source endpoint;
- decodes angle with `atan2(marker_dx, marker_dy)`, preserving the descent near
  and beyond 90 degrees instead of using the earlier ambiguous `arcsin` decoder;
- refuses to silently truncate a trajectory that exceeds `data.horizon_s`;
- stores a data-valid mask through contact;
- stores a separate physics mask that excludes the final 0.03 s; and
- records endpoint angle, maximum angle, duration, and mask counts in the real
  manifest.

The supplied configuration uses an 8-s grid, which contains every accepted
trial in this dataset (the longest marked interval is 6.09 s). If a future
trial exceeds the configured grid, increase `data.horizon_s` and rerun
preparation. Do not restore the 20-degree cutoff or silently truncate it.

## Five-fold generalization protocol

With 15 subjects and exactly five folds, each fold holds out three unseen test
subjects. This lets every subject contribute once to the final test result while
retaining one separate real validation subject for checkpoint selection.

| Fold | 11 real training subjects | Real validation | 3 unseen real test subjects |
|---:|:---|:---:|:---|
| 1 | S43, S55, S62, S59, S56, S49, S48, S45, S44, S34, S32 | S63 | S57, S46, S30 |
| 2 | S57, S63, S59, S56, S49, S46, S45, S44, S34, S32, S30 | S62 | S55, S48, S43 |
| 3 | S43, S55, S62, S63, S49, S48, S46, S44, S34, S32, S30 | S57 | S45, S59, S56 |
| 4 | S43, S57, S62, S63, S59, S56, S48, S46, S45, S44, S30 | S55 | S34, S32, S49 |
| 5 | S55, S57, S59, S56, S49, S48, S46, S45, S34, S32, S30 | S43 | S44, S62, S63 |

The split is reproducible from seed 220. A test subject is excluded from both
gradient training and validation selection in its fold. Aggregate means and
standard deviations are computed with equal weight across the 15 held-out
subjects, rather than weighting subjects with more trials more heavily.
The five original Model B subjects serve once each as validation anchors; they
are also tested once in different folds, exactly like the ten added subjects.

## Five-seed repetition protocol

The subject folds, prepared trajectories, architecture, optimizer settings,
and physics weight remain fixed across seeds. Only stochastic initialization
and training order change.

For seed index `i` with base seed `b`, fold `f` uses the effective random seed:

```text
effective_fold_seed = b + f
```

The complete experiment therefore trains `5 seeds × 5 folds = 25` models.
Each seed evaluates all 15 held-out subjects exactly once, producing 75
subject-seed evaluations while retaining only 15 unique human subjects.

Outputs are isolated by seed so checkpoints cannot overwrite one another:

```text
results/full/
├── seed_01_20261101/fold_01 ... fold_05
├── seed_02_20261102/fold_01 ... fold_05
├── seed_03_20261103/fold_01 ... fold_05
├── seed_04_20261104/fold_01 ... fold_05
└── seed_05_20261105/fold_01 ... fold_05
```

## Data placement

Unzip this repository beside the subject directories:

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
└── Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds/
```

For the ten new subjects, `prepare_audit_inputs.py` reads the repaired skeleton
CSV files, demographics, and manual A11 phase notes. It computes sex-specific
segment-mass CoM, defines a fixed standing anatomical frame, uses the foot
midpoint at marked fall onset as the pivot, and derives:

```text
theta = atan2(subject-forward CoM, subject-vertical CoM)
x     = subject-forward CoM relative to the fixed onset pivot
```

This removes camera X/Z orientation before training. It also records every
repaired frame used before apparent contact in the adapter manifest. S49 A11T01
is naturally omitted because it is absent from the accepted phase notes. S58 is
not configured anywhere in this experiment.

## Running locally

Python 3.10+ is recommended. `./run.sh setup` creates or reuses the shared
environment at `~/.venv` (override with `PINN_VENV_DIR`). `auto` chooses CUDA,
then Apple MPS, then CPU.

```bash
cd Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds
chmod +x run.sh run_on_mac.sh
./run.sh setup
./run.sh validate
./run.sh test
./run.sh smoke auto
./run.sh full auto
```

Explicit device examples:

```bash
./run.sh smoke cpu
./run.sh fold 1 cuda 3
./run.sh seed 3 cuda
./run.sh full cuda
./run.sh full cpu
```

`fold 1 cuda 3` means Fold 1 using seed index 3 (`20261103`). Omitting the
seed index defaults to seed index 1. `seed 3 cuda` runs all five folds for seed
index 3 and aggregates that seed. `full cuda` runs all 25 models, performs the
five-seed aggregation, and packages the result.

Completed fold summaries are skipped automatically, so an interrupted run can
resume with the same command. Set `FORCE=1` only when you intentionally want to
overwrite a completed fold:

```bash
FORCE=1 ./run.sh fold 1 cuda 3
```

Check progress without starting training:

```bash
./run.sh status
```

`run_on_mac.sh` remains as a compatibility wrapper and accepts the same modes.

Usage:

```text
./run.sh setup
./run.sh validate
./run.sh prepare
./run.sh smoke [auto|cuda|mps|cpu]
./run.sh fold FOLD_ID [auto|cuda|mps|cpu] [SEED_INDEX]
./run.sh seed SEED_INDEX [auto|cuda|mps|cpu]
./run.sh full [auto|cuda|mps|cpu]
./run.sh aggregate
./run.sh package
./run.sh status
./run.sh test
```

The smoke run uses three epochs and is only an end-to-end check. The full run
always regenerates the deterministic audit inputs and runs
`validate_prepared_full_fall.py` before training. See `FULL_FALL_CHANGES.md` for
the exact differences from the earlier pre-20-degree experiment.

## Synthetic outputs and real comparison

At test time, the model receives only the unseen subject trial's first 0.40 s,
initial state, demographics, fixed auxiliaries, and query times. Its predicted
theta and forward-x continuation is a model-generated—or synthetic—CoM
trajectory in the experiment's reduced coordinates.

For every held-out trial the repository saves:

- `test_predictions/<trial>.npz`: full forecast time, real/predicted theta/x,
  inferred effective gains, time-aligned angular/horizontal residuals, and the
  residual-valid mask;
- `test_predictions/<trial>.png`: overlaid real-versus-synthetic trajectories;
- `test_predictions/<trial>_physics_residuals.png`: separate angular and
  horizontal residuals over time;
- `test_metrics_by_trial.csv` and `test_metrics_by_subject.csv`;
- theta/x RMSE and MAE, normalized MSE, Wasserstein-1 distances, and 10-degree
  crossing-time error, plus separate residual RMSE/MAE diagnostics;
- the validation-selected checkpoint and complete training history.

Within each seed, `cross_subject_metrics.csv`, `cross_trial_metrics.csv`, and
`aggregate_summary.json` summarize its five folds. After all seeds, the root
`results/full/` directory contains:

- `multi_seed_subject_metrics.csv`: 75 rows (15 held-out subjects × 5 seeds);
- `multi_seed_trial_metrics.csv`: every eligible held-out trial for every seed;
- `multi_seed_fold_metrics.csv`: 25 trained fold models;
- `multi_seed_summary.json`: seed-level means, across-seed standard deviations,
  descriptive 95% t intervals, and per-subject seed distributions;
- `multi_seed_subject_boxplots.png`: five seed-specific values per subject; and
- `multi_seed_seed_means.png`: the held-out-subject mean for each seed.

The primary summary first averages equally over the 15 held-out subjects within
each seed and then summarizes the five seed-level means. It does not treat 75
subject-seed rows as 75 independent people.

The packaged file is:

```text
Fifteen_Subject_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds_Results.zip
```

Please return that ZIP for analysis. Raw prepared arrays are omitted from it by
default, while provenance manifests, predictions, plots, metrics, logs, and
model states are retained.

## Completed five-seed full-fall results

The returned run passed the full-fall integrity checks:

- 25/25 fold-seed models and fold summaries are present;
- all 15 subjects are evaluated once per seed (75 subject-seed evaluations);
- 70 unique accepted trials are evaluated for every seed (350 trial-seed
  evaluations); and
- all 70 trials retain their complete marked standing-to-contact interval.

The primary aggregate first averages trials within each held-out subject,
averages the 15 subjects equally within each seed, and then summarizes the five
seed means.

| Held-out metric | Five-seed mean | Seed SD | Descriptive 95% t interval |
|:---|---:|---:|:---|
| Normalized forecast MSE | 3.1852 | 0.3292 | 2.7764–3.5940 |
| Angle RMSE | 21.484° | 0.901° | 20.365–22.603° |
| CoM displacement RMSE | 28.464 cm | 1.473 cm | 26.635–30.294 cm |
| Angle MAE | 17.152° | 0.792° | 16.169–18.136° |
| CoM displacement MAE | 22.978 cm | 1.279 cm | 21.389–24.566 cm |

For the advisor-facing subject boxplot, normalized forecast RMSE is calculated
for each subject-seed point as `sqrt(normalized_mse)`. Theta RMSE remains in
degrees and CoM x RMSE remains in centimetres; these are trajectory errors, not
physics-equation residuals.

Seed 1 has the lowest mean normalized MSE (2.7734), while Seed 2 has the
highest (3.6769). This optimization variation is modest compared with subject
variation. S45 is the hardest held-out subject (mean normalized MSE 14.7969,
angle RMSE 50.847°, displacement RMSE 69.126 cm), followed by S49 (9.0833,
39.376°, 43.491 cm). Most other subjects have mean normalized MSE between
0.6810 and 2.8133.

Across subjects and seeds, angular physics-residual RMSE is 12.1061 ± 0.3949
and horizontal physics-residual RMSE is 17.5184 ± 3.3120. These residuals are
diagnostics of equation consistency, not trajectory-error metrics, and their
units/scales are not directly comparable to normalized MSE, degrees, or
centimetres. S49 has an especially large horizontal-residual RMSE (80.95),
which is concentrated in the difficult short T04 fall.

See `FINDINGS.md` for the subject/trial analysis and interpretation.
`results/full/full_fall_physics_residuals_by_subject.png` now shows normalized
forecast RMSE, theta RMSE (degrees), and CoM x RMSE (centimetres) as five-seed
boxplots by subject. The clearer alias
`results/full/full_fall_primary_errors_by_subject.png` contains the same plot.
Angular and horizontal residuals remain available in the CSV and per-trial NPZ
outputs for equation-specific diagnostics.

## Interpretation limits

- Apparent contact is based on skeleton/video marking, not force-plate contact.
- The cart-pole residual is not applied to the final 0.03-s contact boundary;
  the real trajectory loss still includes those samples.
- Five seeds measure optimization variability; they do not increase the number
  of independent human subjects beyond 15.
- With only five seeds, across-seed confidence intervals remain descriptive and
  relatively imprecise.
- Model predictions should be called synthetic only as a provenance label.
  They should not be used to train a future fall detector until their fidelity,
  diversity, leakage risk, and downstream utility have been evaluated.
- The full-fall results are not directly comparable with the earlier pre-20°
  experiment: the target interval, angle decoder, grid length, and difficulty
  changed. A physics-versus-no-physics claim requires rerunning the matched
  no-physics ablation with this same full-fall preparation and five seeds.
