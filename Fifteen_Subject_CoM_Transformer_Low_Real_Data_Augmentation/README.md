# Fifteen-Subject CoM Transformer: Low-Real-Data Augmentation Study

This sibling experiment tests the question that the full-data study could not answer:

> When only 25% or 50% of the real front-fall training trajectories are available, does adding the approved synthetic front-fall set recover fall-detection performance?

It reuses the verified CoM temporal-transformer architecture, subject-disjoint folds, real-only validation/test sets, validation-selected thresholds, and five training seeds from the earlier detector studies. It does **not** rerun the completed 100%-data experiments.

## Place the directory here

```text
PINN-FallDetection-Init/
├── Fifteen_Subject_CoM_Transformer_Fall_Detector/
├── Fifteen_Subject_CoM_Transformer_Source_Balanced_Augmentation/
│   └── outputs/comparison_with_prior/four_scenario_run_metrics.csv
├── Fifteen_Subject_CoM_Transformer_Low_Real_Data_Augmentation/   # this directory
├── Fifteen_Subject_Fall_Detector_Data_Preparation/
│   └── outputs/dataset_manifest.csv
└── ...
```

The source-balanced sibling must contain the completed `four_scenario_run_metrics.csv`; it supplies the frozen 100%-real and 100%-real-plus-synthetic reference results.

## Four new conditions

| Condition | Real falls retained | Synthetic falls | Training batch |
|---|---:|---|---|
| `real_25pct_real_adl` | 25% | No | 32 real ADL + 32 real falls |
| `real_25pct_balanced_synthetic_real_adl` | Same 25% | Yes | 32 real ADL + 16 real falls + 16 synthetic falls |
| `real_50pct_real_adl` | 50% | No | 32 real ADL + 32 real falls |
| `real_50pct_balanced_synthetic_real_adl` | Same 50% | Yes | 32 real ADL + 16 real falls + 16 synthetic falls |

Every condition uses all available real ADL trajectories in the training subjects. Only quality-approved synthetic trajectories are eligible. Synthetic data are never used for validation or testing.

The full study is 4 conditions × 5 folds × 5 seeds = **100 new training runs**. The comparison adds 50 frozen reference runs (25 full-real and 25 full-data source-balanced runs) without retraining them.

## Fixed real-fall subset policy

The subset is chosen from the **training subjects only**, independently inside each fold.

- `subset_seed = 20261115` fixes a stable hash ranking; model seeds do not change data membership.
- Selection is stratified by logical subject group, including the configured S31/S59 pairing.
- Every training subject group contributes at least one real fall.
- The global target is the nearest integer to 25% or 50% of available training real falls, subject to group coverage.
- Allocation is deterministic and nested: every trajectory in the 25% subset is also in that fold's 50% subset.
- The paired real-only and augmented conditions at a fraction use exactly the same selected real falls.

`outputs/real_fall_subset_audit.csv` records every eligible training fall and its 25%/50% membership for every fold. Each run also stores the selected IDs and a SHA-256 membership digest.

This design isolates the effect of synthetic augmentation. A different subset per training seed would mix subset variability with model-initialization variability and weaken the paired comparison.

## Model and evaluation

The experiment imports the existing model and data-window code from `../Fifteen_Subject_CoM_Transformer_Fall_Detector`:

- input: 64 frames of CoM angle and horizontal CoM displacement;
- sampling rate: 30 Hz;
- compact 2-layer temporal Transformer (`d_model=32`, 4 attention heads);
- binary cross-entropy training with AdamW;
- early stopping on validation balanced binary cross-entropy;
- decision threshold selected using validation subjects only;
- final evaluation on real falls and real ADLs from held-out test subjects.

The augmented condition keeps the fall half of every batch exactly 1:1 by source. Thus the much larger synthetic pool cannot crowd out the limited real falls.

## Environment

`run.sh` uses the existing home-directory environment at `~/.venv`. It does not create or modify an environment. To use another existing environment:

```bash
export FALL_DETECTOR_VENV=/absolute/path/to/venv
```

The requirements are listed in `requirements.txt`. Your environment needs PyTorch, NumPy, pandas, SciPy, scikit-learn, and Matplotlib.

## Validate and test first

From this directory:

```bash
chmod +x run.sh
./run.sh validate
./run.sh test
./run.sh smoke
```

- `validate` checks all inputs, split leakage, nested subset membership, subject coverage, and the 50 frozen reference runs.
- `test` checks deterministic nested selection and exact batch quotas.
- `smoke` performs in-memory subset, sampler, model forward, and backward checks on CPU. It intentionally creates no experiment output files.

## Run on an Apple-silicon Mac

Use `--device mps` explicitly:

```bash
./run.sh train --device mps
./run.sh compare
```

`PYTORCH_ENABLE_MPS_FALLBACK=1` is set by `run.sh` for operations that PyTorch must execute on CPU. If MPS is unavailable in your installed PyTorch build, use `--device cpu`.

For CUDA or automatic selection:

```bash
./run.sh train --device cuda
# or
./run.sh train --device auto
```

Existing completed `metrics.json` files are skipped, so the command can be resumed safely. Use `--overwrite` only if you intentionally want to rerun and replace completed runs.

## Run conditions individually

You can run the four conditions separately:

```bash
./run.sh real-25 --device mps
./run.sh augmented-25 --device mps
./run.sh real-50 --device mps
./run.sh augmented-50 --device mps
./run.sh compare
```

For a quick one-run integration check that does write output:

```bash
./run.sh real-25 --device mps --folds 1 --seeds 11 --max-epochs 2 --steps-per-epoch 2
```

Delete that run directory or use `--overwrite` when starting the full experiment, because a short run still creates a valid-looking `metrics.json`.

## Comparison outputs

After all 100 new runs finish, `./run.sh compare` writes `outputs/comparison/` containing:

| File | Meaning |
|---|---|
| `all_six_condition_run_metrics.csv` | 100 new runs plus 50 frozen full-data reference runs |
| `six_condition_fold_seed_averaged_metrics.csv` | seeds averaged within each held-out fold |
| `six_condition_summary.csv` | run-level and fold-level means/SDs |
| `augmentation_vs_real_only_wilcoxon_holm.csv` | paired 25% and 50% augmentation tests |
| `augmentation_recovery_by_fold.csv` | descriptive fraction of the gap to 100%-real recovered |
| `COMPARISON.md` | automatically generated result summary |
| `augmentation_recovery_curves.png` | real-data fraction versus balanced accuracy and F1 |
| `six_condition_performance_overview.png` | overview of all trial-level metrics |
| `foldwise_augmentation_gain.png` | paired augmentation gain for each held-out fold |
| `false_positive_burden.png` | false-positive events per ADL minute |

For statistical tests, the five model seeds are first averaged within each fold. A two-sided paired Wilcoxon signed-rank test compares augmented versus real-only performance at 25% and 50%. Holm correction is applied across those two fraction comparisons separately for each metric. Because there are only five independent folds, p-values are exploratory; foldwise consistency and effect size remain important.

The recovery percentage is descriptive:

```text
(augmented − reduced-real) / (100%-real − reduced-real) × 100
```

for higher-is-better metrics. The direction is reversed for false-positive burden. It can be negative (augmentation hurt), exceed 100% (augmentation surpassed full-real), or be undefined when the reduced-real condition did not trail the full-real reference.

## Package results to send back

```bash
./run.sh package-results
```

This creates `Fifteen_Subject_CoM_Transformer_Low_Real_Data_Augmentation_Results.zip` without model checkpoints. To include the `.pt` files:

```bash
./run.sh package-results --include-models
```

The checkpoint-free archive is normally sufficient for updating `README.md`, `FINDINGS.md`, interpreting the winner, and choosing the next controlled experiment.

## Scope of the conclusion

This study tests whether the already-approved synthetic A11 front-fall set helps when real A11 training data are scarce. It does not test other fall directions, activity-aware hard-negative sampling, alternative architectures, or synthetic data selected using test performance. Those should remain separate experiments.
