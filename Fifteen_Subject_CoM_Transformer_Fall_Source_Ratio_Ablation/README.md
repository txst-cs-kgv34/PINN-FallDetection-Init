# Fifteen-Subject CoM Transformer: Fall-Source Ratio Ablation

This sibling experiment extends the completed source-balanced 50:50 detector
study with two requested real-fall-to-synthetic-fall ratios:

- 40:60 real:synthetic falls;
- 60:40 real:synthetic falls.

It preserves the architecture, subject-disjoint folds, five seeds, validation
threshold selection, preprocessing, optimizer, and total training budget from
the 50:50 experiment. Only the source composition of the fall half of the
training batch changes.

## Runs

The experiment trains **2 ratios × 5 folds × 5 seeds = 50 new runs**.

The previous 75 original-scenario runs and 25 balanced 50:50 runs are frozen
references and are not retrained.

## Batch design

Every batch still has 64 windows:

| Portion | Windows |
|---|---:|
| Real ADL | 32 |
| All falls | 32 |
| Total | 64 |

A ratio such as 40:60 cannot be represented exactly inside 32 integer fall
slots because 0.40 × 32 = 12.8. The sampler therefore alternates the two
nearest legal quotas while keeping the original batch size and 32 optimizer
steps per epoch.

| Target ratio | Per-batch real falls | Per-batch synthetic falls | Per-epoch real falls | Per-epoch synthetic falls | Effective epoch ratio |
|---|---:|---:|---:|---:|---:|
| 40:60 | 12 or 13 | 20 or 19 | 410 | 614 | 40.039% : 59.961% |
| 60:40 | 19 or 20 | 13 or 12 | 614 | 410 | 59.961% : 40.039% |

The quota order is shuffled reproducibly each epoch. The total class balance
remains 50% ADL and 50% fall. Sampling uses replacement only when a source pool
is smaller than a requested quota.

Validation and test contain only real ADL and real A11 falls. Synthetic falls
are training-only. Normalization is fitted on each fold's training data, and
the decision threshold is selected from validation subjects only.

## Required repository layout

```text
PINN-FallDetection-Init/
├── Fifteen_Subject_CoM_Transformer_Fall_Detector/
│   ├── detector_core.py
│   ├── model.py
│   ├── train_scenario.py
│   └── outputs/comparison/combined_run_metrics.csv
├── Fifteen_Subject_CoM_Transformer_Source_Balanced_Augmentation/
│   └── outputs/source_balanced_1to1/
├── Fifteen_Subject_CoM_Transformer_Fall_Source_Ratio_Ablation/
├── Fifteen_Subject_Fall_Detector_Data_Preparation/
│   └── outputs/dataset_manifest.csv
└── ...
```

Do not delete or rerun the earlier detector outputs. This directory imports the
verified detector architecture and data utilities and writes only to its own
`outputs/` directory.

## Environment

The launcher uses the existing home virtual environment at `~/.venv`. To use
a different existing environment:

```bash
export FALL_DETECTOR_VENV=/absolute/path/to/your/venv
```

Install missing dependencies if necessary:

```bash
~/.venv/bin/python -m pip install -r requirements.txt
```

## Run on Apple Silicon

From this directory:

```bash
chmod +x run.sh

./run.sh test
./run.sh smoke
./run.sh validate

./run.sh train --device mps
./run.sh compare
./run.sh package-results
```

Training is resumable. A completed `metrics.json` causes that fold/seed/ratio
run to be skipped. Use `--overwrite` only when intentionally retraining.

To train and compare in one command:

```bash
./run.sh all --device mps
```

A short diagnostic run is available:

```bash
./run.sh train --device cpu --folds 1 --seeds 11 --max-epochs 1 --steps-per-epoch 5
```

Do not mix a diagnostic run with the final results. Delete it or rerun the same
setting with `--overwrite` and the full configuration.

## Outputs

```text
outputs/
├── source_ratio_40real_60synthetic/
│   ├── fold_01/seed_00011/
│   ├── run_summary.csv
│   └── experiment_summary.json
├── source_ratio_60real_40synthetic/
│   ├── fold_01/seed_00011/
│   ├── run_summary.csv
│   └── experiment_summary.json
└── ratio_comparison/
    ├── six_scenario_run_metrics.csv
    ├── six_scenario_fold_seed_averaged_metrics.csv
    ├── six_scenario_summary.csv
    ├── ratio_paired_wilcoxon_holm.csv
    ├── COMPARISON.md
    └── *.png
```

The comparison produces:

1. a six-scenario table covering the original three scenarios, 40:60, 50:50,
   and 60:40;
2. a focused three-ratio comparison;
3. fold-wise balanced-accuracy plots;
4. paired differences relative to 50:50;
5. false-positive-event comparisons;
6. paired Wilcoxon tests after averaging seeds within each fold, with Holm
   adjustment across five planned comparisons per metric.

## Interpretation status

This is an exploratory post-hoc ratio ablation because the earlier held-out
results were already inspected before 40:60 and 60:40 were requested. It can
show whether performance trends toward more real or more synthetic fall
windows. A final claim that one ratio is optimal should select the ratio using
validation data or confirm it on new untouched subjects.

## Share the results

After the run, send:

```text
Fifteen_Subject_CoM_Transformer_Fall_Source_Ratio_Ablation_Results.zip
```

The default results package excludes `.pt` checkpoints but includes metrics,
predictions, plots, reports, and reproducibility code.
