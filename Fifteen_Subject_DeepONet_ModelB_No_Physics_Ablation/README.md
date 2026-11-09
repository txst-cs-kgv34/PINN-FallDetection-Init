# Model B-no-physics — 15-subject DeepONet ablation

This repository is the controlled no-physics ablation of the completed
15-subject **Model B — Direct Unified Physics DeepONet** experiment.

It uses the same 15 subjects:

`S43, S55, S57, S62, S63, S59, S56, S49, S48, S46, S45, S44, S34, S32, S30`

The purpose is to answer one question:

> Does the cart-pole biomechanics residual improve held-out-subject trajectory
> prediction when the data, model, folds, seed, and training settings are held
> constant?

## Controlled ablation

Only the biomechanics residual is removed.

| Component | Model B with physics | This ablation |
|:---|:---:|:---:|
| Real forecast normalized-MSE loss | Enabled | Enabled |
| Cart-pole biomechanics residual | Enabled | **Disabled** |
| Physics loss weight | 0.01 | **0.0** |
| Context encoder architecture | Same | Same |
| Positive four-control head | Same | Same |
| Branch and Fourier trunk | Same | Same |
| Hard initial position/velocity constraints | Same | Same |
| Five subject folds | Same | Same |
| Data preparation and exclusions | Same | Same |
| Seed and randomized subject order | Same | Same |
| Optimizer, learning rate, epochs, and patience | Same | Same |
| Validation checkpoint selection | Same | Same |
| Test metrics and box plots | Same | Same |

The ablation objective is therefore:

```text
L_B-no-physics = L_real_forecast
```

compared with the physics model:

```text
L_B = L_real_forecast + 0.01 * L_cart_pole_biomechanics
```

`operator_core.py` retains the shared physics-residual function so the source
and architecture remain directly comparable, but `use_physics=false` prevents
the training path from calculating it and `physics_weight=0.0` gives it no
contribution to the objective.

The fixed Pi/tau auxiliary input slots and the positive four-control head are
also preserved to avoid changing Model B's branch dimensions. In this
no-physics condition, those four outputs are unsupervised conditioning
variables and must not be interpreted as recovered biomechanical gains.

## Preserved Model B architecture

- First 0.40 s divided into four 0.10-s context windows.
- Context channels: theta, forward x, both velocities, and local time.
- Encoder: `Conv1d(5,32) → Conv1d(32,64) → adaptive average pool → 96`.
- Positive controller head with four Softplus outputs.
- Branch: controls + initial state + demographics + fixed auxiliaries; hidden
  width 160 and output width `2 × 96`.
- Fourier-time trunk: 12 modes, hidden width 160, latent width 96.
- Hard initial conditions:
  `q(t) = q0 + qdot0*t + t²*f(t)` for theta and x.
- AdamW, learning rate `5e-4`, weight decay `1e-6`, batch size 4, maximum
  800 epochs, early-stopping patience 100, and gradient clip 5.

No teacher checkpoint, gain-sweep target, or Pole-PINN synthetic trajectory is
used.

## Five-fold protocol

Every subject is tested exactly once. Each fold trains on 11 real subjects,
selects its checkpoint using one separate real validation subject, and tests
three unseen subjects.

| Fold | 11 real training subjects | Validation | 3 unseen test subjects |
|---:|:---|:---:|:---|
| 1 | S43, S55, S62, S59, S56, S49, S48, S45, S44, S34, S32 | S63 | S57, S46, S30 |
| 2 | S57, S63, S59, S56, S49, S46, S45, S44, S34, S32, S30 | S62 | S55, S48, S43 |
| 3 | S43, S55, S62, S63, S49, S48, S46, S44, S34, S32, S30 | S57 | S45, S59, S56 |
| 4 | S43, S57, S62, S63, S59, S56, S48, S46, S45, S44, S30 | S55 | S34, S32, S49 |
| 5 | S55, S57, S59, S56, S49, S48, S46, S45, S34, S32, S30 | S43 | S44, S62, S63 |

The split seed is 220 and the optimization seed is 20261101, exactly matching
the physics experiment. Test subjects are excluded from gradient training and
checkpoint selection.

## Required directory placement

Place this repository beside the same subject directories used by the physics
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
└── Fifteen_Subject_DeepONet_ModelB_No_Physics_Ablation/
```

The ten audit subjects are converted deterministically from repaired,
phase-marked skeleton data into the same anatomical-frame theta/forward-x
representation used by the physics experiment. S58 remains excluded.

You do **not** need to rerun Pole_PINN_Human_Motion training or Sweep Gain. If
the five older pole-compatible TSV directories are already present, this
repository uses them directly.

## Run locally

Python 3.10+ is recommended. The runner uses the shared environment at
`~/.venv`. Device `auto` selects CUDA, then Apple MPS, then CPU.

```bash
cd Fifteen_Subject_DeepONet_ModelB_No_Physics_Ablation
chmod +x run.sh run_on_mac.sh

./run.sh setup
./run.sh validate
./run.sh test
./run.sh smoke auto
./run.sh full auto
```

Explicit device examples:

```bash
./run.sh full cuda
./run.sh full mps
./run.sh full cpu
```

To run one fold:

```bash
./run.sh fold 1 cuda
```

Usage:

```text
./run.sh setup
./run.sh validate
./run.sh prepare
./run.sh smoke [auto|cuda|mps|cpu]
./run.sh fold FOLD_ID [auto|cuda|mps|cpu]
./run.sh full [auto|cuda|mps|cpu]
./run.sh aggregate
./run.sh package
./run.sh test
```

The smoke run uses only three epochs and is not a scientific result. The full
run regenerates the audit inputs, prepares the real trajectories, trains all
five folds, aggregates all 15 held-out subjects, creates subject-wise trial
error box plots, and packages the results.

## Saved results

For each held-out trial:

- `test_predictions/<trial>.npz` stores time, real theta/x, predicted theta/x,
  and the four inferred positive controller variables;
- `test_predictions/<trial>.png` overlays the real and generated trajectories;
- `test_metrics_by_trial.csv` stores normalized MSE, theta/x RMSE and MAE,
  Wasserstein distances, crossing-time information, and controller outputs.

Each fold also stores its validation-selected checkpoint, training history,
subject metrics, and fold summary. `cross_subject_results.png` contains box
plots over the held-out trials for each subject, with individual trial points,
the trial median, and subject mean.

The final archive is:

```text
Fifteen_Subject_ModelB_No_Physics_Ablation_Results.zip
```

Please return that ZIP. The comparison with the physics result will use the
same subject-level and trial-level metrics and will report both absolute and
paired error differences.

## Interpretation rules

- This experiment isolates the contribution of the physics residual; it is not
  a new architecture.
- Lower held-out normalized MSE, theta RMSE, or forward-x RMSE indicates better
  trajectory generalization.
- A useful physics contribution requires Model B with physics to outperform
  this ablation consistently across subjects or trials, not merely in the
  overall mean.
- The four inferred controller outputs remain effective internal variables,
  especially here where no physics equation constrains them.
- One seed remains a pilot; repeated seeds are required for formal uncertainty
  estimates.
