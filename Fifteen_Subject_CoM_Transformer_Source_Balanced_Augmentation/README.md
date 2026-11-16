# Fifteen-Subject CoM Transformer: Source-Balanced Augmentation

This is a **new sibling experiment**, not a replacement for the original
three-scenario detector. It preserves the original 75 runs and adds one controlled
condition: equal real and synthetic representation within the fall half of every
training batch.

## Completed result

The full experiment completed successfully: 25 new source-balanced runs were
combined with the 75 prior runs, giving 100 matched scenario runs.

| Training scenario | Balanced accuracy | F1 | AUPRC | FP events/ADL min ↓ |
|---|---:|---:|---:|---:|
| **Real falls + real ADL** | **0.943** | **0.881** | **0.960** | **0.170** |
| Synthetic falls + real ADL | 0.878 | 0.714 | 0.825 | 0.463 |
| Original combined + real ADL | 0.886 | 0.740 | 0.870 | 0.417 |
| **Source-balanced 1:1 + real ADL** | **0.904** | **0.804** | **0.897** | **0.276** |

Real-only training is the full-data winner. Source balancing improved the original
combined condition by 1.77 balanced-accuracy points, 6.33 F1 points, and reduced
false-positive events by 33.9%, but it remained 3.96 balanced-accuracy points below
real-only training. No comparison was significant after Holm correction; with
only five fold-level pairs, the exact two-sided Wilcoxon test has insufficient
resolution to reach p < 0.05 even when all five differences share one direction.

See `FINDINGS.md` for the complete statistical, fold-level, and error analysis.

## Why this is a separate directory

The original combined condition drew from 70 real and 226 approved synthetic fall
trajectories. Uniform sampling from that combined positive pool made synthetic
falls much more likely to appear. This experiment tests whether that source
imbalance explains the combined condition's result, while keeping the previous
results unchanged and directly comparable.

Only 25 new runs are trained: five subject-disjoint folds times five fixed seeds.
The comparison step reads the completed 75-run table from the original detector
and produces a four-condition analysis.

## Batch design

For the default batch size of 64, every training batch contains:

| Source | Label | Samples | Batch share |
|---|---:|---:|---:|
| Real ADL | 0 | 32 | 50% |
| Real A11 falls | 1 | 16 | 25% |
| Approved synthetic A11 falls | 1 | 16 | 25% |

Thus the class balance is 32 ADL : 32 falls, and the fall-source balance is
16 real : 16 synthetic. Sampling is with replacement only when a source pool is
smaller than its required quota. The 1:1 source ratio is fixed before evaluation;
it is not selected from test performance.

`subject_balanced_within_source` is `false` by default so this experiment changes
only source quotas. Within each source pool, trajectory windows are sampled using
the same uniform policy as the earlier experiment.

Validation and test sets contain only real ADL and real A11 falls. Synthetic falls
are used for training only. Normalization is fitted on each fold's training data,
the decision threshold is selected from validation subjects, and held-out test
subjects remain untouched until final evaluation.

## Required repository layout

```text
PINN-FallDetection-Init/
├── Fifteen_Subject_CoM_Transformer_Fall_Detector/
│   ├── detector_core.py
│   ├── model.py
│   ├── train_scenario.py
│   └── outputs/comparison/combined_run_metrics.csv
├── Fifteen_Subject_CoM_Transformer_Source_Balanced_Augmentation/
├── Fifteen_Subject_Fall_Detector_Data_Preparation/
│   └── outputs/dataset_manifest.csv
└── ...
```

Do not delete or rerun the original detector outputs. This directory imports its
architecture and data utilities and reads its comparison table, but writes only to
its own `outputs/` directory.

## Environment

The launcher uses your existing home-directory environment at `~/.venv`. It does
not create a new environment. To use a different existing environment:

```bash
export FALL_DETECTOR_VENV=/absolute/path/to/your/venv
```

Install dependencies in that environment if needed:

```bash
~/.venv/bin/python -m pip install -r requirements.txt
```

## Before the full run

From this directory:

```bash
chmod +x run.sh
./run.sh test
./run.sh smoke
./run.sh validate
```

The smoke test checks exact 32/16/16 batch composition and one model
forward/backward pass. It intentionally creates no persistent experiment files.
Validation checks the prepared trajectories, all subject splits, absence of
synthetic validation/test leakage, exact source quotas, and the availability of
all 75 prior runs.

## Full experiment

The supplied results package already contains all 25 completed runs. The commands
below are retained for reproducibility or deliberate retraining.

Choose the device available on your machine:

```bash
# Apple Silicon
./run.sh train --device mps

# NVIDIA CUDA
./run.sh train --device cuda

# CPU
./run.sh train --device cpu
```

The command runs all five folds and five seeds (25 runs). Existing completed runs
are skipped, so it is safe to resume. Use `--overwrite` only when you intentionally
want to retrain existing balanced runs.

After training, compare with the original 75 runs:

```bash
./run.sh compare
```

Or train and compare in one command:

```bash
./run.sh all --device mps
```

A small diagnostic run is possible with:

```bash
./run.sh train --device cpu --folds 1 --seeds 11 --max-epochs 1 --steps-per-epoch 1
```

Keep a diagnostic run out of the final output, or rerun that setting with
`--overwrite` and the full configuration before comparison.

## Outputs

```text
outputs/
├── source_balanced_1to1/
│   ├── fold_01/seed_00011/
│   │   ├── best_model.pt
│   │   ├── metrics.json
│   │   ├── history.csv
│   │   └── *_predictions.csv
│   ├── run_summary.csv
│   └── experiment_summary.json
├── comparison_with_prior/
    ├── four_scenario_run_metrics.csv
    ├── four_scenario_fold_seed_averaged_metrics.csv
    ├── four_scenario_summary.csv
    ├── source_balanced_vs_prior_wilcoxon_holm.csv
    ├── COMPARISON.md
    └── *.png
└── error_analysis/
    ├── ERROR_ANALYSIS.md
    ├── activity_error_summary.csv
    ├── subject_error_summary.csv
    ├── trial_error_frequency.csv
    ├── scenario_trial_transitions.csv
    ├── fold_calibration_summary.csv
    └── *.png
```

The comparison includes:

1. real falls + real ADL;
2. synthetic falls + real ADL;
3. original combined falls + real ADL;
4. new source-balanced 1:1 combined falls + real ADL.

Seeds are averaged within each fold before inferential testing. The new condition
is paired with each prior condition by the same five held-out folds. For each
metric, three two-sided Wilcoxon signed-rank tests are performed, then Holm
correction is applied across those three comparisons. The analysis also reports
fold-paired differences and four figures; a p-value alone should not determine the
conclusion because there are only five folds.

## Share results

Package outputs without the large model checkpoints:

```bash
./run.sh package-results
```

Include checkpoints only if needed:

```bash
./run.sh package-results --include-models
```

Share the resulting ZIP when an independently rerun result needs to be reviewed.

## Completed activity- and subject-level error analysis

The post-hoc error analysis covers 12,300 held-out trial-seed predictions from all
100 completed runs. It requires no retraining. The main findings are:

- Balanced 1:1 made 111 ADL false-positive decisions; A02 Pick Up Object, A05
  Sweeping Floor, and A08 TUG/Walking produced 105 of them (94.6%).
- Source balancing reduced the original combined model from 170 to 111 ADL false
  positives and from 56 to 52 real-fall false negatives.
- Real-only remained better with 61 ADL false positives and 30 fall false
  negatives.
- S44, S30, S49, and S32 account for most repeatedly missed real A11 falls.
- Fold 5 has unstable validation thresholds and the largest false-positive burden.

The complete report is `outputs/error_analysis/ERROR_ANALYSIS.md`. Reproduce it
after all four scenario outputs are available with:

```bash
~/.venv/bin/python error_analysis.py
```

The script reads existing predictions only and does not change model outputs.

## Recommended next stage

Do not generate more samples from the same synthetic distribution yet. The next
recommended controlled experiment is a **low-real-data augmentation study**:

1. retain fixed fractions such as 25% and 50% of the real training falls;
2. compare reduced-real-only training with the same reduced real subset plus
   source-balanced synthetic falls;
3. keep validation and test data entirely real and subject-disjoint;
4. choose any augmentation setting using validation subjects only.

This tests the most defensible use of synthetic data: whether it can recover
performance when real falls are scarce. The completed error report shows that
hard-negative sampling should remain a separate later ablation; adding it to the
low-real study would confound the effect of synthetic augmentation. The current
real-only condition remains the primary full-data detector result.
