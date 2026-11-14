# Fifteen-subject CoM Transformer fall detector

This directory trains and compares the three A11 front-fall experiments:

1. Real A11 falls + real ADL.
2. Quality-approved synthetic A11 falls + real ADL.
3. Real and quality-approved synthetic A11 falls + real ADL.

The detector uses the compact temporal-attention idea from the skeleton teacher in RightFeatKD, adapted for two center-of-mass (CoM) signals instead of a 32-joint skeleton. It does **not** use the RightFeatKD accelerometer student or knowledge-distillation loss.

The code reads the manifest and `.npz` trajectories created by `Fifteen_Subject_Fall_Detector_Data_Preparation`. It does not copy or regenerate the prepared trajectories.

## Required repository layout

Place this directory beside the data-preparation directory:

```text
PINN-FallDetection-Init/
├── Fifteen_Subject_Fall_Detector_Data_Preparation/
│   └── outputs/
│       ├── dataset_manifest.csv
│       └── trials/
│           ├── real_adl/*.npz
│           ├── real_fall/*.npz
│           └── synthetic_fall/*.npz
└── Fifteen_Subject_CoM_Transformer_Fall_Detector/
```

The verified prepared-data totals are:

| Source | Label | Trajectories |
|---|---:|---:|
| Real ADL | 0 | 545 |
| Phase-marked real A11 falls | 1 | 70 |
| Quality-approved synthetic A11 falls | 1 | 226 |
| **Total** |  | **841** |

Run the preparation pipeline first if its `outputs` directory does not exist.

## Python environment and hardware

`run.sh` uses the existing virtual environment in your home directory:

```text
~/.venv/bin/python
```

It does not create a virtual environment. Install the dependencies once:

```bash
~/.venv/bin/python -m pip install -r requirements.txt
```

If your existing environment is elsewhere, set:

```bash
export FALL_DETECTOR_VENV=/absolute/path/to/your/.venv
```

The default `--device auto` selection order is:

1. NVIDIA CUDA, when available;
2. Apple MPS, when available;
3. CPU.

You can explicitly select a device with `--device cpu`, `--device mps`, or `--device cuda`.

## Model architecture

Each fixed-length input is shaped `[batch, 64 frames, 2 channels]` with channels:

- `theta_rad`: body/CoM angle in radians;
- `x_m`: forward CoM displacement in metres.

The model is:

```text
theta(t), x(t)
    ↓
training-subject normalization
    ↓
temporal Conv1D projection (2 → 32 features)
    ↓
learned time-position embedding
    ↓
two temporal Transformer encoder blocks
    ↓
padding-aware mean pooling
    ↓
linear layer → one fall logit
```

Default architecture settings:

| Setting | Value |
|---|---:|
| Window length | 64 frames = 2.13 s at 30 Hz |
| Embedding dimension | 32 |
| Attention heads | 4 |
| Transformer layers | 2 |
| Feed-forward dimension | 128 |
| Dropout | 0.2 |
| Output | One binary logit |
| Optimizer | AdamW |
| Training loss | `BCEWithLogitsLoss` |

Training uses exactly balanced mini-batches: half fall windows and half ADL windows. Therefore, the loss does not also apply `pos_weight`; doing both would double-correct the imbalance.

## Window construction

- Every fall trajectory contributes one terminal/contact-aligned 64-frame window.
- A fall shorter than 64 frames is left-padded and supplied with a padding mask.
- ADL recordings use 64-frame sliding windows with a 32-frame stride.
- The last ADL window is always included so the end of the recording is covered.
- Training limits each ADL trial to four evenly spaced windows so long trials cannot dominate.
- Validation and test retain all ADL windows.

This is an **event-classification benchmark**, not yet a causal early-warning detector. A future real-time experiment should use causal windows and labels defined relative to fall onset.

## Leakage-free cross-validation

The configuration defines five subject-disjoint folds. For fold `k`:

- fold `k` is the real test set;
- the next fold is the real validation set;
- the remaining three folds are the training set.

Each subject appears in the test set exactly once. S31 and S59 form one logical split group because S31 supplies the ADL recordings associated with the missing S59 ADL data. They can never appear on opposite sides of a split.

Important rules enforced in code:

- subject assignment occurs before windowing;
- synthetic trajectories are used only in training;
- validation and test always contain real A11 falls and real ADLs;
- a synthetic trajectory remains grouped with its source subject;
- normalization mean and standard deviation are fitted only on training-subject trajectories;
- the same real validation and test partitions are used for all three scenarios.

## Initial checks

From this detector directory:

```bash
chmod +x run.sh
./run.sh test
./run.sh smoke --device mps
./run.sh validate
```

`test` runs unit tests and compilation checks. `smoke` creates a temporary miniature dataset and trains all three scenarios for two CPU epochs. It does not use or modify the real dataset. `validate` checks the real manifest, NPZ files, source counts, folds, labels, sampling rate, and leakage policy.

## Run the experiments individually

Run scenario 1:

```bash
./run.sh real --device mps
```

Run scenario 2:

```bash
./run.sh synthetic --device mps
```

Run scenario 3:

```bash
./run.sh combined --device mps
```

Each command runs five folds and five random seeds by default. Completed fold/seed runs are skipped, so an interrupted experiment can be resumed with the same command.

To deliberately replace existing results for that scenario:

```bash
./run.sh real --overwrite
```

`--overwrite` removes only the matching detector run directory before rebuilding it. It does not change the prepared trajectories.

For a quick real-data check before the full experiment:

```bash
./run.sh real --folds 1 --seeds 11 --max-epochs 2 --steps-per-epoch 2
```

Remove that quick run or rerun the same fold/seed with `--overwrite` before collecting final results.

## Run everything and compare

To run all three scenarios sequentially and generate the final comparison:

```bash
./run.sh all
```

If the scenarios were run individually, create or refresh the comparison with:

```bash
./run.sh compare
```

The training budget is controlled by a fixed number of balanced optimizer steps per epoch. Thus, the combined-data scenario does not receive more optimizer updates merely because it has more trajectories.

## Checkpoint and threshold selection

For every fold and seed:

1. The checkpoint with the lowest balanced validation loss is retained.
2. The probability threshold that maximizes trial-level balanced accuracy is selected on the real validation subjects.
3. That checkpoint and threshold are frozen.
4. Metrics are then calculated once on the real test subjects.

No seed is chosen using test performance. All configured seeds are reported and compared. Test data are not used for checkpoint selection, threshold selection, normalization, or generator selection.

## Evaluation outputs

Each fold/seed directory contains:

```text
outputs/<scenario>/fold_XX/seed_XXXXX/
├── best_model.pt
├── scaler.json
├── run_configuration.json
├── history.csv
├── training_history.png
├── validation_window_predictions.csv
├── validation_trial_predictions.csv
├── test_window_predictions.csv
├── test_trial_predictions.csv
└── metrics.json
```

Trial probabilities are the maximum window probability within each trajectory. The principal reported metrics are:

- sensitivity/recall;
- specificity;
- precision and F1;
- balanced accuracy;
- AUROC from probabilities;
- AUPRC from probabilities;
- false-positive detection events per ADL minute.

The final comparison is written to `outputs/comparison`:

```text
outputs/comparison/
├── COMPARISON.md
├── scenario_summary.csv
├── combined_run_metrics.csv
├── fold_seed_averaged_metrics.csv
├── paired_wilcoxon_holm.csv
├── comparison_metadata.json
└── scenario_metric_boxplots.png
```

The Wilcoxon analysis first averages seeds inside each fold, then performs the three paired scenario comparisons across folds. Holm correction is applied separately within each metric. With five folds, these p-values are exploratory; effect sizes and consistency across folds should be emphasized.

## Package results to share

After all experiments and the comparison finish:

```bash
./run.sh package-results
```

This creates:

```text
Fifteen_Subject_CoM_Transformer_Fall_Detector_Results.zip
```

Model checkpoints are excluded by default to keep the archive small. To include them:

```bash
./run.sh package-results --include-models
```

Share the results archive for review. The CSV predictions and metrics are sufficient to audit the comparison even when model checkpoints are excluded.

## Main files

| File | Purpose |
|---|---|
| `config.json` | Architecture, folds, seeds, paths, and training settings |
| `model.py` | CoM Temporal Transformer |
| `detector_core.py` | Manifest loading, splitting, normalization, windowing, and metrics |
| `train_scenario.py` | One-scenario cross-validation trainer |
| `compare_scenarios.py` | Three-scenario descriptive and paired comparison |
| `validate_setup.py` | Real prepared-data validation |
| `smoke_test.py` | Temporary end-to-end CPU smoke test |
| `package_results.py` | Results archive creation |
| `run.sh` | Commands using the existing home-directory virtual environment |

