# Fifteen-subject DeepONet synthetic-fall study

This directory is intentionally separate from:

- `Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds`
- all `S##_PINN_audit` directories

The first stage performs leakage-free generator selection. A later update will add synthetic trajectory generation and comparison with real samples for RMSE, DTW, phase duration, displacement, velocity, and acceleration.

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

The selector reads the 25 full-run folders. It does not modify the Physics or audit directories.

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

./run.sh test
./run.sh smoke
./run.sh validate
./run.sh select
```

`validate` writes ranking tables without copying checkpoints. `select` also copies the ten selected checkpoints into this study directory.

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

## Planned quality-check extension

The next stage will reuse the selected generator manifests and access the sibling real-data/audit directories without copying or modifying them. Quality thresholds will be calculated from training-subject real-real variability only. Test-subject trajectories will remain untouched until the final downstream fall-detector evaluation.
