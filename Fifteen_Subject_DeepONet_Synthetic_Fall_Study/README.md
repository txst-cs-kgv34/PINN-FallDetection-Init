# Fifteen-subject DeepONet synthetic-fall study

This directory is intentionally separate from:

- `Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds`
- all `S##_PINN_audit` directories

The study now contains three stages:

1. Leakage-free generator selection.
2. Conditional synthetic trajectory generation from training-subject contexts.
3. Real-real versus synthetic-real quality verification using RMSE, DTW, duration, displacement, velocity, and acceleration.

## Expected sibling layout

```text
PINN-FallDetection-Init/
├── Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds/
│   └── results/full/seed_*/fold_*/
├── S30_PINN_audit/
├── S32_PINN_audit/
├── ...
└── Fifteen_Subject_DeepONet_Synthetic_Fall_Study/
```

The study reads the 25 model runs and `outputs/real_data_full` from the sibling Physics directory. It does not modify the Physics or audit directories.

## Selection rule

For each of the five folds:

1. Validate all five seed-specific runs.
2. Read only `best_validation_value` from `training_selection.json`.
3. Rank lower validation normalized MSE as better.
4. Select the top two checkpoints.
5. Never use `test_*` errors for ranking or tie-breaking.

Each seed-specific run has already selected its best epoch using that fold's one real validation subject. This script performs the second selection level: choosing the top two seeds within the fold.

## Run

```bash
cd Fifteen_Subject_DeepONet_Synthetic_Fall_Study
chmod +x run.sh run_on_mac.sh

./run.sh setup       # only if the Physics Python environment is unavailable
./run.sh test
./run.sh smoke
./run.sh validate
./run.sh select
./run.sh generate auto
./run.sh quality
./run.sh package
```

`validate` writes ranking tables without copying checkpoints. `select` also copies the ten selected checkpoints into this study directory.

To run the complete workflow:

```bash
./run.sh pipeline auto
```

Use `cuda`, `mps`, or `cpu` instead of `auto` when you want to force a device:

```bash
./run.sh generate mps
```

If the Physics results are somewhere else:

```bash
./run.sh select \
  --results-dir "/absolute/path/to/results/full"
```

If you want a different number of retained seeds:

```bash
./run.sh select --top-k 3
```

## Outputs

```text
outputs/generator_selection/
├── all_generator_rankings.csv
├── selected_generators.csv
├── generator_selection.json
├── SELECTION_SUMMARY.md
└── selected_generators/
    ├── fold_01/
    │   ├── rank_01_seed_.../
    │   └── rank_02_seed_.../
    └── ...
```

Each selected generator folder contains:

- `final_best_model_state.pt`
- `training_selection.json`
- `generator_manifest.json`
- SHA-256 checkpoint provenance in the manifest

Generation outputs:

```text
outputs/synthetic_trajectories/
├── synthetic_manifest.csv
├── synthetic_manifest.json
├── fold_01/
│   ├── rank_01_seed_.../*.npz
│   └── rank_02_seed_.../*.npz
└── ...
```

Each `.npz` contains the observed context, predicted forecast, raw model output, validity masks, inferred controller coordinates, and physical-gain values. Generation uses only the 11 training subjects belonging to that fold. Validation and test subject contexts are rejected.

Quality outputs:

```text
outputs/trajectory_quality/
├── QUALITY_REPORT.md
├── quality_summary.json
├── real_real_distances.csv
├── synthetic_real_distances.csv
├── selected_generator_diversity.csv
├── quality_thresholds_by_fold.csv
├── quality_decisions.csv
├── generator_quality_summary.csv
├── real_real_vs_synthetic_real.png
└── generator_quality_pass_rates.png
```

## Quality-verification protocol

For every fold:

1. Use only its 11 training subjects.
2. Pair different real trials within the same subject to establish natural real-real variability.
3. Compare every conditional synthetic trajectory with its source real trajectory.
4. Phase-normalize forecast segments to 101 points for normalized RMSE, theta RMSE, x RMSE, and DTW.
5. Calculate displacement, peak velocity, and peak acceleration on the original 100 Hz timing after identical Savitzky–Golay smoothing.
6. Define per-fold thresholds from the 95th percentile of training real-real distances.

The default automatic gate requires:

- normalized RMSE and normalized DTW both within their real-real thresholds; and
- at least 75% of the displacement, velocity, and acceleration distances within their real-real thresholds.

All raw measurements and per-metric thresholds are saved, so this gate can be revised transparently after advisor review.

### Duration limitation

DeepONet predicts theta and x but does not predict contact time. The synthetic trajectory therefore inherits the apparent-contact endpoint and valid duration of its source trial. Duration differences are saved for transparency but are excluded from automatic pass/fail decisions. The generated data should be described as **conditionally generated synthetic falls**, not completely de novo falls.

## Safety checks

The selector stops if:

- any of the 25 fold/seed runs is missing;
- a checkpoint is absent or empty;
- the validation loss is non-finite;
- the saved selection metric is not validation forecast normalized MSE;
- a run indicates that a test subject was used for selection;
- the train, validation, or test subjects overlap;
- subject splits change across seeds;
- any subject is tested in more than one fold.

Generation and quality verification additionally stop if a validation or test subject appears in a generation context, source trial, or threshold-construction set.

The next project stage will train the real-only, synthetic-only, and real-plus-synthetic fall detectors. Only quality-approved synthetic trajectories should enter that downstream experiment.

After the full run, the file to return for review is:

```text
Fifteen_Subject_DeepONet_Synthetic_Fall_Study_Results.zip
```

The results archive includes the generated trajectories, manifests, quality tables, plots, and report. It excludes copied `.pt` checkpoints because those model files already exist in the Physics results.
