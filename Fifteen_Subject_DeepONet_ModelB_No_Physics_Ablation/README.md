# Model B-no-physics — 15-subject DeepONet ablation (five seeds)

This repository is the paired five-seed no-physics ablation of the completed
**Model B — Direct Unified Physics DeepONet** experiment.

It uses the same 15 subjects:

`S43, S55, S57, S62, S63, S59, S56, S49, S48, S46, S45, S44, S34, S32, S30`

The experiment answers one controlled question:

> Does the cart-pole biomechanics residual improve held-out-subject trajectory
> prediction when the data, folds, architecture, optimizer, and five
> optimization seeds are held fixed?

## Controlled ablation

Only the biomechanics residual is removed.

| Component | Unified Physics | This no-physics ablation |
|:---|:---:|:---:|
| Real forecast normalized-MSE loss | Enabled | Enabled |
| Cart-pole biomechanics residual | Enabled | **Disabled** |
| Physics weight | 0.01 | **0.0** |
| Context encoder and DeepONet architecture | Same | Same |
| Positive four-control head | Same | Same |
| Hard initial position/velocity constraints | Same | Same |
| Real trajectory preparation and exclusions | Same | Same |
| Five subject folds and validation subjects | Same | Same |
| Five base seeds and fold seed offsets | Same | Same |
| Optimizer, epochs, patience, and metrics | Same | Same |

The paired objectives are:

```text
Unified Physics:
L_B = L_real_forecast + 0.01 * L_cart_pole_biomechanics

No physics:
L_B-no-physics = L_real_forecast
```

`operator_core.py` retains the shared residual implementation so both
repositories keep the same architecture and code path. In this repository,
`use_physics=false` prevents it from contributing and
`physics_weight=0.0` gives it zero weight.

The fixed Pi/tau auxiliary slots and positive four-output head are preserved so
the input and branch dimensions remain identical. Without the physics equation,
the four outputs are unsupervised latent conditioning variables. They must not
be described as recovered biomechanical control parameters.

## Exact five-seed pairing

The base optimization seeds are:

```text
20261101, 20261102, 20261103, 20261104, 20261105
```

For seed index `i` with base seed `b`, fold `f` uses:

```text
effective_fold_seed = b + f
```

This is exactly the same matrix used by Unified Physics. A seed changes initial
network weights, epoch shuffle order, gradient path, validation history,
early-stopping checkpoint, predictions, and the four internal controller
outputs. It does not change subjects, trials, phase markings, repaired rows,
demographics, fold membership, architecture, optimizer settings, or metric
definitions.

Because consecutive base seeds are shifted by fold ID, a numeric effective seed
can appear on a different fold in an adjacent repetition. This is retained
intentionally for a strict paired comparison with the completed physics run.

The full experiment trains:

```text
5 seeds × 5 folds = 25 models
```

Each seed tests all 15 subjects exactly once, producing 75 subject-seed
evaluations. These are repeated model evaluations of 15 people, not 75
independent human subjects.

## Preserved architecture and training settings

- Context: first 0.40 s, divided into four 0.10-s windows.
- Context channels: theta, forward x, both velocities, and local time.
- Encoder: `Conv1d(5,32) → Conv1d(32,64) → adaptive average pool → 96`.
- Four positive Softplus controller outputs.
- DeepONet branch: controller outputs, initial state, demographics, and fixed
  auxiliaries; hidden width 160 and output width `2 × 96`.
- Fourier-time trunk: 12 modes, hidden width 160, latent width 96.
- Hard initial conditions:
  `q(t) = q0 + qdot0*t + t²*f(t)` for theta and x.
- AdamW, learning rate `5e-4`, weight decay `1e-6`, real batch size 4,
  maximum 800 epochs, early-stopping patience 100, gradient clip 5.
- Real data only: no teacher checkpoints, gain labels, gain sweep, or
  Pole-PINN synthetic trajectories.

## Five-fold protocol

Each fold trains on 11 real subjects, selects its checkpoint with one separate
real validation subject, and evaluates three unseen subjects.

| Fold | 11 training subjects | Validation | 3 unseen test subjects |
|---:|:---|:---:|:---|
| 1 | S43, S55, S62, S59, S56, S49, S48, S45, S44, S34, S32 | S63 | S57, S46, S30 |
| 2 | S57, S63, S59, S56, S49, S46, S45, S44, S34, S32, S30 | S62 | S55, S48, S43 |
| 3 | S43, S55, S57, S62, S63, S48, S46, S44, S34, S32, S30 | S49 | S45, S59, S56 |
| 4 | S43, S57, S62, S63, S59, S56, S48, S46, S45, S44, S30 | S55 | S34, S32, S49 |
| 5 | S55, S57, S59, S56, S49, S48, S46, S45, S34, S32, S30 | S43 | S44, S62, S63 |

The split seed is 220. Test subjects are excluded from both gradient training
and validation-based checkpoint selection.

## Data placement

Unzip this directory beside the same subject directories used for the physics
run:

```text
PINN-FallDetection-Init/
├── S43_PINN_audit/ or existing pole-compatible S43 data
├── S55_PINN_audit/ or existing pole-compatible S55 data
├── S57_PINN_audit/ or existing pole-compatible S57 data
├── S62_PINN_audit/ or existing pole-compatible S62 data
├── S63_PINN_audit/ or existing pole-compatible S63 data
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
└── Fifteen_Subject_DeepONet_ModelB_No_Physics_5_Seeds/
```

The deterministic audit adapter computes sex-specific segment-mass CoM,
constructs the standing anatomical frame, removes camera X/Z orientation, and
produces the same theta/forward-x representation used by Unified Physics. S58
is excluded. S49 A11T01 remains omitted.

You do not need to rerun Pole_PINN_Human_Motion or Sweep Gain. If the five
older pole-compatible TSVs are already present, they are reused directly.

## Run locally

Python 3.10+ is recommended. `./run.sh setup` creates or reuses
`~/.venv`. Override it with `PINN_VENV_DIR` if needed. Device `auto`
selects CUDA, then Apple MPS, then CPU.

```bash
cd Fifteen_Subject_DeepONet_ModelB_No_Physics_5_Seeds
chmod +x run.sh run_on_mac.sh

./run.sh setup
./run.sh validate
./run.sh test
./run.sh smoke auto
./run.sh full auto
```

Common alternatives:

```bash
./run.sh full cuda
./run.sh full mps
./run.sh full cpu

./run.sh fold 1 cuda 3
./run.sh seed 3 cuda
./run.sh status
```

`fold 1 cuda 3` runs Fold 1 using seed index 3, corresponding to base seed
`20261103`. `seed 3 cuda` runs all five folds for that seed. Completed fold
summaries are skipped, so an interrupted `full` run can be resumed safely.
Use `FORCE=1` only when intentionally overwriting a completed fold.

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

The smoke run uses three epochs and is not a scientific result.

## Saved outputs

Fold outputs are isolated by seed:

```text
results/full/
├── seed_01_20261101/fold_01 ... fold_05
├── seed_02_20261102/fold_01 ... fold_05
├── seed_03_20261103/fold_01 ... fold_05
├── seed_04_20261104/fold_01 ... fold_05
└── seed_05_20261105/fold_01 ... fold_05
```

For each held-out trial, the repository saves:

- `test_predictions/<trial>.npz`: time, real theta/x, predicted theta/x, and
  four internal controller outputs;
- `test_predictions/<trial>.png`: real-versus-generated trajectory overlays;
- trial and subject CSV metrics;
- normalized MSE, theta/x RMSE and MAE, Wasserstein distances, and crossing-time
  error;
- the validation-selected checkpoint and training history.

After all 25 models, `results/full/` contains:

- `multi_seed_subject_metrics.csv`;
- `multi_seed_trial_metrics.csv`;
- `multi_seed_fold_metrics.csv`;
- `multi_seed_summary.json`;
- `seed_variability_summary.csv`;
- `multi_seed_subject_boxplots.png`;
- `multi_seed_seed_means.png`; and
- `multi_seed_fold_heatmaps.png`.

The primary summary first averages equally over the 15 held-out subjects within
each seed and then summarizes the five seed-level means. It does not treat the
75 subject-seed rows as 75 independent people.

The packaged result is:

```text
Fifteen_Subject_ModelB_No_Physics_5_Seeds_Results.zip
```

Return that ZIP for the paired physics-versus-no-physics analysis.

## Planned paired comparison

The comparison will match each no-physics result to the physics result using:

```text
seed index + fold + held-out subject + trial ID
```

It will report:

- five-seed means and across-seed variability;
- paired subject- and trial-level error differences;
- physics win rates;
- per-subject and per-fold effects;
- comparison box plots and seed-paired figures; and
- whether any improvement is consistent rather than driven by one seed or
  difficult subject.

Lower held-out normalized MSE, angle RMSE, and CoM displacement RMSE indicate
better trajectory generalization. The conclusion will be based on all five
seeds, not the best observed seed.

