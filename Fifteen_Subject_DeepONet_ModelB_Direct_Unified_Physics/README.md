# Model B — 15-subject direct unified physics DeepONet (five seeds)

This repository extends the exact earlier **Model B** condition to 15 subjects:

`S43, S55, S57, S62, S63, S59, S56, S49, S48, S46, S45, S44, S34, S32, S30`

It runs the same five-fold experiment with **five optimization seeds**. It
trains on real phase-marked CoM trajectories with the differentiable delayed
cart-pole biomechanics residual. It does **not** train on Pole-PINN synthetic
trajectories, teacher checkpoints, or gain-sweep targets.

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
- Optimizer: AdamW, learning rate `5e-4`, weight decay `1e-6`, batch size 4,
  maximum 800 epochs, patience 100, gradient clip 5.
- Fixed physics: `m=0.0138 kg`, `m0=1 kg`, `l=0.57 m`, `g=9.81 m/s²`,
  `tau=0.23 s`, `Pi=0.0635 rad`, dead-zone sharpness 50.

The inferred gains are effective model parameters, not measured physiological
control gains.

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
and physics weight remain fixed across seeds. A seed initializes the Python,
NumPy, and PyTorch random-number generators. It changes:

- initial neural-network weights and biases in the context encoder, controller
  head, DeepONet branch, and Fourier trunk;
- the shuffled order of training trajectories in every epoch; and therefore
- the gradient path, validation-loss history, early-stopping epoch, final
  checkpoint, generated trajectories, and four inferred controller outputs.

It does **not** change the real trajectories, repaired rows, phase marks,
demographics, train/validation/test subjects, architecture, loss equation,
physics coefficient, learning rate, batch size, maximum epochs, or test metric
definitions. The stored test time and target theta/x arrays were verified to
be exactly identical for all 66 trials across all five seeds.

For seed index `i` with base seed `b`, fold `f` uses the effective random seed:

```text
effective_fold_seed = b + f
```

Because the five consecutive base seeds are shifted by fold ID, the same
numeric effective seed can occur for a different fold in an adjacent repeat.
Those are still different training problems because their training,
validation, and test subjects differ. The later no-physics ablation must use
this exact seed matrix so physics and no-physics remain paired. A future
standalone repetition could use widely spaced base seeds to avoid numeric
overlap across different folds.

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
└── Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics/
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
cd Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics
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
always regenerates the deterministic audit inputs before training.

## Synthetic outputs and real comparison

At test time, the model receives only the unseen subject trial's first 0.40 s,
initial state, demographics, fixed auxiliaries, and query times. Its predicted
theta and forward-x continuation is a model-generated—or synthetic—CoM
trajectory in the experiment's reduced coordinates.

For every held-out trial the repository saves:

- `test_predictions/<trial>.npz`: time, real theta/x, predicted theta/x, and
  inferred effective gains;
- `test_predictions/<trial>.png`: overlaid real-versus-synthetic trajectories;
- `test_metrics_by_trial.csv` and `test_metrics_by_subject.csv`;
- theta/x RMSE and MAE, normalized MSE, Wasserstein-1 distances, and 10-degree
  crossing-time error;
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
- `multi_seed_fold_heatmaps.png`: direct seed-by-fold error comparison; and
- `seed_variability_summary.csv`: mean, standard deviation, coefficient of
  variation, interval, and best/worst observed seed for each metric.

The primary summary first averages equally over the 15 held-out subjects within
each seed and then summarizes the five seed-level means. It does not treat 75
subject-seed rows as 75 independent people.

The packaged file is:

```text
Fifteen_Subject_ModelB_Direct_Unified_Physics_5_Seeds_Results.zip
```

Please return that ZIP for analysis. Raw prepared arrays are omitted from it by
default, while provenance manifests, predictions, plots, metrics, logs, and
model states are retained.

## Completed five-seed results

All 25 seed-fold models completed. Every seed evaluated the same 15 held-out
subjects and 66 eligible trials, giving 75 subject-seed evaluations and 330
trial-seed evaluations. Subject means—not individual trials—remain the primary
unit within each seed.

| Held-out metric | Five-seed mean | SD across seed means | Descriptive 95% t interval | CV |
|:---|---:|---:|---:|---:|
| Normalized MSE | 0.2143 | 0.0383 | [0.1667, 0.2619] | 17.9% |
| Angle RMSE | 5.103° | 0.420° | [4.582°, 5.625°] | 8.2% |
| CoM displacement RMSE | 7.772 cm | 0.574 cm | [7.059, 8.484] cm | 7.4% |

Seed 5 has the lowest observed mean on all three metrics, but it must not be
reported alone as a post-hoc “best model.” The five-seed mean and variability
are the appropriate result. Seed 3 has the largest normalized MSE, while Seed
1 has the largest angle and displacement RMSE.

The strongest persistent subject difficulty is S45: normalized MSE is 1.126 ±
0.565 across seeds. S48 and S32 are the next-highest and are also seed
sensitive. At the fold level, Fold 3 is consistently hardest and most variable;
Fold 5 is the most stable and lowest-error fold.

The validation-selected checkpoint epoch ranges from 12 to 396 (median 83),
showing that the seed changes not only the final prediction but also where
early stopping selects the model. See [FINDINGS.md](FINDINGS.md) for the full
interpretation and the updated comparison figures in `results/full/`.

## Interpretation limits

- Apparent contact is based on skeleton/video marking, not force-plate contact.
- Five seeds measure optimization variability; they do not increase the number
  of independent human subjects beyond 15.
- With only five seeds, across-seed confidence intervals remain descriptive and
  relatively imprecise.
- Model predictions should be called synthetic only as a provenance label.
  They should not be used to train a future fall detector until their fidelity,
  diversity, leakage risk, and downstream utility have been evaluated.
