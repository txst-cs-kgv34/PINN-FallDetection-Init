# Experiment 1: Five-subject leave-two-out DeepONet distillation

This directory implements the advisor-proposed first experiment using the five currently audited A11 front-fall subjects: S43, S63, S55, S57, and S62.

It reuses the physics-informed conditional DeepONet architecture from the S43/S63 preliminary experiment and fixes the context encoder to four motion windows. The code stays outside all subject projects and reads their selected Stage-3 checkpoints, gain metadata, and real pole-compatible trials in place. It does not copy or edit a subject checkpoint.

## Scientific question

For each fold, can one operator distilled from three subject-specific PINN teachers predict the real motion of a completely unseen test subject when a different unseen subject supplies real validation data?

The separation is strict:

- training: synthetic trajectories from three training-subject PINNs;
- model selection: real trajectories from one validation subject;
- final evaluation: real trajectories from one test subject;
- validation/test PINN outputs are never supplied to that fold's training.

## Selected primary teachers

| Subject | Teacher | Role |
|:---|:---|:---|
| S43 | chunk 1 | Subject-identified controller |
| S63 | chunk 6 | Improved non-reference controller |
| S55 | chunk 5 | Best combined non-reference controller |
| S57 | chunk 9 | Best combined setting after excluding the exact Subject-B endpoint |
| S62 | chunk 1 | Best subject-derived setting after excluding the exact Subject-A endpoint |

Exact Subject-A and Subject-B pole-reference gain tuples are not used as teachers.

## Balanced folds

| Fold | Training PINN subjects | Real validation subject | Real test subject |
|---:|:---|:---|:---|
| 1 | S55, S57, S62 | S63 | S43 |
| 2 | S43, S57, S62 | S55 | S63 |
| 3 | S43, S63, S62 | S57 | S55 |
| 4 | S43, S63, S55 | S62 | S57 |
| 5 | S63, S55, S57 | S43 | S62 |

Every subject appears in training three times, validation once, and testing once. The held-out test subject is not used for early stopping, gain averaging, `Pi`, `tau`, normalization, or checkpoint selection.

The subject order was fixed before model fitting using `split_seed = 220`; the five rows rotate the test and validation roles through that stored order. This gives the requested repeatable shuffle while guaranteeing balanced coverage, which unconstrained random draws would not guarantee with only five subjects.

## Required directory placement

Place this directory beside the five populated subject directories:

```text
PINN-FallDetection-Init/
├── S43_Pole_PINN_Human_Motion/
├── S63_Pole_PINN_Human_Motion/
├── S55_Pole_PINN_Human_Motion/
├── S57_Pole_PINN_Human_Motion/
├── S62_Pole_PINN_Human_Motion/
└── Five_Subject_DeepONet_Experiment1/
```

Each subject directory must contain:

```text
source/pinn_pole_synthetic_data_generation.py
data/pole_compatible/A11/SubjectB_<subject>A11T*.tsv
experiments/stage3_gain_sweep/results/chunk_XX/stage3_best.weights.h5
experiments/stage3_gain_sweep/results/chunk_XX/result.json
```

The exact relative paths are declared in `experiment.json`. Edit those paths only if your local directory layout differs.

## Architecture preserved from the preliminary experiment

The implementation retains:

- a shared 1-D convolutional context encoder;
- a gain head predicting `Kp_theta`, `Kd_theta`, `Kp_x`, and `Kd_x`, plus log variances;
- GELU multilayer perceptrons;
- a branch network receiving gains, initial state, demographics, `Pi`, and `tau`;
- a Fourier-time trunk network;
- branch/trunk latent multiplication to predict theta and forward x;
- the hard initial-condition form `y(t) = y0 + ydot0*t + t^2*correction(t)`;
- gain NLL, oracle teacher-trajectory loss, predicted-gain consistency loss, and delayed cart-pole physics loss.

The context affects the trajectory only through the estimated gains, as in the preliminary code.

## Four-window adaptation for the real subjects

The preliminary experiment used four 0.25-second windows over one second. Several accepted human trials are shorter than one second, especially for S63 and S62. A literal one-second context would discard most of those subjects' real validation/test evidence.

This experiment therefore retains the selected **four-window architecture** while using:

```text
four windows × 0.10 seconds = first 0.40 seconds of context
```

At 100 Hz, the windows begin at 0.00, 0.10, 0.20, and 0.30 seconds. Forecast metrics use only real samples at or after 0.40 seconds. Trials that cannot supply 0.40 seconds are excluded automatically and listed in `outputs/real_data_full/real_manifest.json`; they are never padded into fake evaluation targets.

This timing adjustment must be disclosed when comparing the result with the preliminary one-second-context study. The window duration and context region remain configurable in `experiment.json`.

## Step-by-step execution

### Step 1 — Validate the five external projects

```bash
cd Five_Subject_DeepONet_Experiment1
chmod +x run_on_mac.sh
./run_on_mac.sh validate
```

Validation checks:

- all five exact checkpoint and `result.json` pairs;
- all five pipeline source files;
- all real A11 TSV inventories;
- selected chunk numbers and gain fields;
- exclusion of the exact pole-reference gain tuples; and
- balanced, non-overlapping subject roles in all five folds.

### Step 2 — Generate matched teacher trajectories

```bash
./run_on_mac.sh prepare
```

For every selected checkpoint, `export_teacher_data.py` generates 100 trajectories at 100 Hz for three seconds. All five teachers receive the same 100 initial conditions, so differences come from checkpoint behavior rather than different random inputs.

The five datasets are generated once. During a fold, the loader selects only the three training subjects and ignores the two held-out teacher datasets.

### Step 3 — Prepare real validation and test targets

`prepare_real_data.py`, invoked by `prepare`, reproduces the original pole loader's preprocessing:

1. remove the 1,024 warm-up rows;
2. decode theta and forward x;
3. resample from 250 Hz to 100 Hz;
4. center x using the initial half-second median;
5. stop before the 20-degree threshold using the original 0.08-second margin; and
6. create a validity mask rather than treating padding as measured data.

This keeps held-out real evaluation consistent with the data used in the subject-specific PINN experiments.

### Step 4 — Train one operator per fold

Each fold starts a new DeepONet from a deterministic seed. It trains on 300 synthetic trajectories:

```text
3 training subjects × 100 teacher trajectories
```

The best epoch is selected only by forecast normalized MSE on the real validation subject. The test subject remains untouched until that checkpoint has been restored.

To run one fold:

```bash
./run_on_mac.sh fold 1
```

### Step 5 — Evaluate the unseen test subject

For each eligible real test trial, the saved best model:

1. encodes four early real-motion windows;
2. estimates the four gains;
3. generates theta and x at the real query times; and
4. compares the forecast region with the measured trajectory.

Reported metrics include:

- normalized MSE;
- theta RMSE/MAE and Wasserstein-1 distance;
- x RMSE/MAE and Wasserstein-1 distance;
- estimated gains and exploratory uncertainty;
- 10-degree instability crossing-time error when both curves cross; and
- a training-subject mean-gain baseline.

The test subject's own fitted gains are not supplied to the model or used as an oracle.

### Step 6 — Repeat all five folds and aggregate by test subject

```bash
./run_on_mac.sh full
```

The aggregate report gives every test subject equal weight and reports the mean and sample standard deviation across the five held-out subjects. It does not hide subject variation by pooling all samples into one large score.

## MacBook environment and MPS

All bash modes use the existing home environment exactly as requested:

```bash
source ~/.venv/bin/activate
```

Install/update dependencies with:

```bash
./run_on_mac.sh setup
```

PyTorch device selection is:

1. Apple MPS when available;
2. CUDA when available on another system;
3. CPU fallback.

`PYTORCH_ENABLE_MPS_FALLBACK=1` is enabled for individual operations that PyTorch cannot execute on MPS. TensorFlow is used only to load the Keras teacher checkpoints and export their trajectories. If `tensorflow-metal` is already installed, TensorFlow may use it automatically; it is not required by the experiment.

To force CPU for a diagnostic fold:

```bash
source ~/.venv/bin/activate
python -u train_fold.py --mode full --fold 1 --device cpu
```

## Recommended run order

```bash
./run_on_mac.sh setup
./run_on_mac.sh validate
./run_on_mac.sh test
./run_on_mac.sh smoke
./run_on_mac.sh prepare
./run_on_mac.sh full
```

The smoke run uses four trajectories per training teacher, a 0.8-second horizon, and three training epochs. It verifies checkpoint loading, tensor shapes, real-data masking, MPS/CPU execution, validation-only checkpoint selection, evaluation, and plotting. It is not a scientific result.

All long-running commands stream logs to the terminal with `tee` and save the same text under `results/logs/`.

## Results to return

After `./run_on_mac.sh full`, please send back:

```text
Five_Subject_DeepONet_Experiment1_Results.zip
```

The default package contains code, provenance manifests, preprocessing exclusions, logs, fold checkpoints, per-trial metrics, plots, and the cross-fold summary. It omits the generated teacher arrays to keep the ZIP smaller. If raw exported arrays are needed later, run:

```bash
source ~/.venv/bin/activate
python package_results.py --include-teacher-data \
  --output Five_Subject_DeepONet_Experiment1_Results_with_data.zip
```

## Interpretation limits

- Five subjects make this a pilot unseen-subject study, not a population-level conclusion.
- The operator trains on PINN-generated theta/x trajectories, not additional measured falls or complete 32-joint skeleton motion.
- Validation and testing are real, but trial counts and durations differ by subject.
- The three-second teacher horizon is model extrapolation and does not establish three-second human validity.
- This directory implements Experiment 1 only. The direct-real, data-only, and unified-physics ablations belong to Experiment 2 and are intentionally not mixed into this run.
