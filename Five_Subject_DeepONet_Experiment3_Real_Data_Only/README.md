# Experiment 3 — Model A: real data-only DeepONet

## Purpose

This is the non-physics control for the four-model comparison. It trains the
shared neural-operator backbone only on real trajectories from the three
training subjects in each fold.

It asks:

> How well does a four-window subject-conditioned DeepONet generalize when it
> receives no synthetic data, no teacher gains, and no physics residual?

The direct comparison is Experiment 2 / Model B. A and B use the same real
training subjects, preprocessing, folds, four-window encoder, branch/trunk
dimensions, optimizer, validation rule, and real test subjects. The intended
difference is that B adds physical gain semantics and the cart-pole residual.

## Architecture

For each real trajectory:

1. The first 0.40 seconds are divided into four 0.10-second windows.
2. The convolutional context encoder produces a context embedding.
3. A four-dimensional latent vector `z=[z0,z1,z2,z3]` is inferred.
4. The branch network receives z, the initial state, demographics, and fixed
   auxiliary constants.
5. The Fourier-time trunk receives the query time.
6. The forward operator predicts theta and forward x with hard initial position
   and velocity constraints.

The four latent values are deliberately not called gains. Without gain labels
or a physics equation, they are ordinary learned features and are not
physically identifiable.

## Data-only loss

The only optimized scientific loss is the normalized real-trajectory forecast
error after the 0.40-second context:

```text
L_A = L_real_forecast
```

This experiment contains:

- no subject-PINN checkpoints;
- no synthetic trajectories;
- no teacher control parameters;
- no delayed cart-pole residual; and
- no gain NLL or gain-consistency loss.

The hard initial-condition form is retained because it is part of the common
DeepONet architecture, not a residual physics penalty.

## Balanced subject folds

| Fold | Real training subjects | Real validation subject | Real test subject |
|---:|:---|:---:|:---:|
| 1 | S55, S57, S62 | S63 | S43 |
| 2 | S43, S57, S62 | S55 | S63 |
| 3 | S43, S63, S62 | S57 | S55 |
| 4 | S43, S63, S55 | S62 | S57 |
| 5 | S63, S55, S57 | S43 | S62 |

The test subject is untouched until the real validation subject has selected
the best checkpoint.

## Required placement

```text
PINN-FallDetection-Init/
├── S43_Pole_PINN_Human_Motion/
├── S63_Pole_PINN_Human_Motion/
├── S55_Pole_PINN_Human_Motion/
├── S57_Pole_PINN_Human_Motion/
├── S62_Pole_PINN_Human_Motion/
└── Five_Subject_DeepONet_Experiment3_Real_Data_Only/
```

Only the A11 pole-compatible real TSV files are read from the subject
directories. Subject checkpoints and gain-sweep results are not accessed.

## Step-by-step run

### 1. Install into the existing home environment

```bash
cd Five_Subject_DeepONet_Experiment3_Real_Data_Only
chmod +x run_on_mac.sh
./run_on_mac.sh setup
```

The runner uses:

```bash
source ~/.venv/bin/activate
```

### 2. Validate inputs and subject isolation

```bash
./run_on_mac.sh validate
```

This confirms that training, validation, and test subjects do not overlap and
that the configuration is strictly real-only and physics-free.

### 3. Run unit and syntax tests

```bash
./run_on_mac.sh test
```

### 4. Run the three-epoch smoke test

```bash
./run_on_mac.sh smoke
```

The smoke run verifies real preprocessing, model shapes, MPS/CPU execution,
validation-only checkpoint selection, real test evaluation, and plotting. It is
not used in the final analysis.

### 5. Prepare the full real dataset

```bash
./run_on_mac.sh prepare
```

The preprocessing exactly matches the other experiments: warm-up removal,
250-to-100 Hz resampling, x centering, the pre-20-degree cutoff, 3-second padded
storage, and a mask that prevents padding from becoming a training target.

### 6. Optionally run one full fold

```bash
./run_on_mac.sh fold 1
```

### 7. Run the complete experiment

```bash
./run_on_mac.sh full
```

The complete run trains five new models. Each fold trains on the three real
training subjects, selects the checkpoint on the real validation subject, and
evaluates the unseen real test subject. It then creates:

```text
Five_Subject_DeepONet_Experiment3_Results.zip
```

Logs are displayed in the terminal through `tee` and retained in
`results/logs/`.

## MPS support

Automatic device order is MPS, CUDA, then CPU. MPS fallback is enabled. A CPU
diagnostic fold can be run with:

```bash
source ~/.venv/bin/activate
python -u train_fold.py --mode full --fold 1 --device cpu
```

## Results to return

Please return:

```text
Five_Subject_DeepONet_Experiment3_Results.zip
```

The archive includes all code, configuration, manifests, logs, model states,
test trajectories, metrics, and aggregate plots, but omits prepared arrays by
default.

## Completed full-run result

All five real-only folds completed on MPS. Across the five equally weighted
held-out subjects, Model A produced:

| Metric | Mean ± subject SD |
|:---|---:|
| Normalized MSE | 0.408 ± 0.249 |
| Theta RMSE (deg) | 7.636 ± 2.861 |
| Theta MAE (deg) | 6.050 ± 2.524 |
| x RMSE (cm) | 13.362 ± 3.804 |
| x MAE (cm) | 10.742 ± 3.563 |
| Theta W1 (deg) | 4.499 ± 3.353 |
| x W1 (cm) | 7.475 ± 4.895 |

The real data-only operator outperformed the synthetic-only Model C on every
subject-averaged metric, but the direct-physics Model B improved over Model A by
42.73% in normalized MSE, 10.38% in theta RMSE, and 26.60% in x RMSE. This makes
Model A a useful control: real data alone transfers better than synthetic-only
distillation, while explicit physics adds a further and more consistent gain.

S43 was the main Model A failure case, with normalized MSE 0.802 and x RMSE
18.660 cm. Detailed fold results and the complete four-model interpretation are
in `FINDINGS.md`.

## How this result will be used

- A versus B: whether explicit pole-balancing physics improves direct real
  multi-subject training.
- A versus C: the complete subject-PINN pipeline versus a real-only data model;
  this comparison changes both training source and physics supervision.
- A versus D: whether combining real data with synthetic physics-informed data
  improves over real data alone.
