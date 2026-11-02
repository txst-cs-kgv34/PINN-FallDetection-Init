# Experiment 2 — Model B: direct unified physics DeepONet

## Purpose

This experiment trains one physics-informed neural operator directly on the
real trajectories of three subjects in each fold. It does not train on
subject-PINN synthetic trajectories and does not read subject-PINN checkpoints.

The question is:

> Can a shared DeepONet learn controller-conditioned balance dynamics directly
> from multi-subject real motion when the delayed cart-pole equations are
> included in its training loss?

Experiment 2 is compared primarily with:

- Experiment 3 / Model A to measure the value of explicit physics; and
- Experiment 1 / Model C to compare direct real physics training with
  subject-PINN synthetic distillation.

## Inputs and outputs

For every real training trial:

1. The first 0.40 seconds are divided into four 0.10-second windows.
2. The context encoder reads theta, forward x, their velocities, and local time.
3. The controller head infers four positive effective gains:
   `[Kp_theta, Kd_theta, Kp_x, Kd_x]`.
4. The DeepONet branch receives the normalized gains, initial state,
   demographics, and fixed controller auxiliaries.
5. The Fourier-time trunk receives the query time.
6. The forward operator predicts theta and forward x for the complete query
   grid, with the initial position and velocity imposed exactly.

The inferred gains are effective model parameters. They are not measured human
control gains and there is no real-subject gain RMSE target.

## Explicit physics loss

The delayed cart-pole residual is implemented in `physics_residual_loss()` in
`operator_core.py`. It is calculated from the DeepONet-predicted theta and x,
their finite-difference velocities and accelerations, and the inferred gains.

The training objective is:

```text
L_B = L_real_forecast + 0.01 * L_cart_pole_physics
```

The residual uses only valid, non-padded real samples. The delay and dead-zone
threshold are fixed global modeling assumptions:

```text
tau = 0.23 s
Pi  = 0.0635 rad
```

No teacher checkpoint, teacher gain, or synthetic trajectory is used. Physics
is therefore carried by an explicit differentiable loss function, not
indirectly through synthetic data.

## Balanced subject folds

| Fold | Real training subjects | Real validation subject | Real test subject |
|---:|:---|:---:|:---:|
| 1 | S55, S57, S62 | S63 | S43 |
| 2 | S43, S57, S62 | S55 | S63 |
| 3 | S43, S63, S62 | S57 | S55 |
| 4 | S43, S63, S55 | S62 | S57 |
| 5 | S63, S55, S57 | S43 | S62 |

Each subject is used for training in three folds, validation once, and testing
once. The validation and test subjects are never used for gradient training.

## Required placement

Place this directory beside the five subject directories:

```text
PINN-FallDetection-Init/
├── S43_Pole_PINN_Human_Motion/
├── S63_Pole_PINN_Human_Motion/
├── S55_Pole_PINN_Human_Motion/
├── S57_Pole_PINN_Human_Motion/
├── S62_Pole_PINN_Human_Motion/
└── Five_Subject_DeepONet_Experiment2_Direct_Unified_Physics/
```

Only these real-data paths are required:

```text
S*_Pole_PINN_Human_Motion/data/pole_compatible/A11/SubjectB_S*A11T*.tsv
```

## Step-by-step run

### 1. Activate/install the shared Mac environment

Every command uses the existing home environment:

```bash
source ~/.venv/bin/activate
```

Install the dependencies once:

```bash
cd Five_Subject_DeepONet_Experiment2_Direct_Unified_Physics
chmod +x run_on_mac.sh
./run_on_mac.sh setup
```

### 2. Validate the five-subject protocol

```bash
./run_on_mac.sh validate
```

This checks all real-data globs, the balanced folds, the four-window context,
the real-only training regime, and the absence of subject overlap.

### 3. Run unit and syntax tests

```bash
./run_on_mac.sh test
```

The tests verify the split, model tensor shapes, and differentiability of the
cart-pole residual.

### 4. Run the smoke test

```bash
./run_on_mac.sh smoke
```

The smoke run prepares a 0.8-second real dataset and trains fold 1 for three
epochs. It verifies MPS/CPU execution, masking, physics gradients, validation
checkpointing, test evaluation, and plotting. It is not a scientific result.

### 5. Prepare the full real dataset

```bash
./run_on_mac.sh prepare
```

Real preprocessing reproduces the pole pipeline: remove 1,024 warm-up rows,
decode theta/forward x, resample 250 Hz to 100 Hz, center x, stop before the
20-degree threshold with the original margin, and retain a validity mask.

### 6. Run one fold if desired

```bash
./run_on_mac.sh fold 1
```

### 7. Run all five folds

```bash
./run_on_mac.sh full
```

For each fold the script:

1. trains on real trials from the three training subjects;
2. selects the best epoch using real validation-subject forecast normalized MSE;
3. restores the selected checkpoint;
4. evaluates the unseen real test subject;
5. saves per-trial trajectories, inferred effective gains, plots, and metrics;
6. aggregates the five test subjects with equal subject weight; and
7. creates `Five_Subject_DeepONet_Experiment2_Results.zip`.

All logs stream to the terminal and are also saved under `results/logs/`.

## MPS support

Device selection is Apple MPS, then CUDA, then CPU. The runner exports
`PYTORCH_ENABLE_MPS_FALLBACK=1` for operations not implemented natively on MPS.

To diagnose a fold on CPU:

```bash
source ~/.venv/bin/activate
python -u train_fold.py --mode full --fold 1 --device cpu
```

## Results to return

Please return:

```text
Five_Subject_DeepONet_Experiment2_Results.zip
```

It contains configuration, provenance manifests, logs, validation-selected
states, training histories, test predictions, per-trial metrics, fold summaries,
and the cross-fold aggregate. Raw prepared arrays are omitted by default.

## Interpretation

- Compare B with A to determine whether the explicit physics loss helps real
  unified training.
- Compare B with C to determine whether direct real training or subject-PINN
  distillation transfers better to unseen subjects.
- Do not interpret the inferred gains as measured physiology.
- Five subjects and one seed per fold remain a pilot; repeated seeds are needed
  before a statistical claim.
