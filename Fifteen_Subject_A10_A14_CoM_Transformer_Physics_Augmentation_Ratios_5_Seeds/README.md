# A10-A14 CoM Transformer: physics-augmentation ratios

This experiment tests whether GATE-approved direct-physics synthetic falls
improve multi-activity fall detection and which training ratio works better.
It uses one unchanged compact two-channel CoM Transformer for three controlled
conditions.

## Conditions

The batch size is 60 so the 30 fall positions support exact ratios.

| Condition | Real ADL | Real falls | Synthetic falls | Fall-source ratio |
|:--|--:|--:|--:|:--|
| `real_only` | 30 | 30 | 0 | 100:0 |
| `real60_synthetic40` | 30 | 18 | 12 | 60:40 |
| `real40_synthetic60` | 30 | 12 | 18 | 40:60 |

Every batch remains exactly 50% ADL and 50% fall. Therefore the only intended
difference is the source composition inside the fall half.

## Controls

- Same 64-frame theta/x windows, Transformer architecture, optimizer, schedule,
  five subject folds, and seeds 11/22/33/44/55.
- Model initialization is hashed and recorded for every run.
- Normalization is fitted only from real training ADL and real training falls,
  making the scaler identical across the three conditions for a fold.
- Synthetic samples are training-only and inherit their real source subject.
- Validation and test contain only unseen real ADL and real A10-A14 falls.
- Real and synthetic fall draws are activity-balanced within one count.
- Synthetic sampling selects a source-trial family first and then one approved
  generator variant, preventing trials with eight variants from dominating.
- Repaired real frames are excluded through `observed_mask`.

## Required layout

```text
PINN-FallDetection-Init/
├── Fifteen_Subject_A10_A14_Fall_Detector_Data_Preparation/
│   └── outputs/
└── Fifteen_Subject_A10_A14_CoM_Transformer_Physics_Augmentation_Ratios_5_Seeds/
```

## MacBook MPS run

```bash
cd Fifteen_Subject_A10_A14_CoM_Transformer_Physics_Augmentation_Ratios_5_Seeds
chmod +x run.sh run_on_mac.sh

./run_on_mac.sh setup       # optional if dependencies already exist
./run_on_mac.sh test
./run_on_mac.sh smoke --device mps
./run_on_mac.sh validate
./run_on_mac.sh train --device mps
./run_on_mac.sh compare
./run_on_mac.sh package-results
```

Training is resumable: completed fold/seed runs are skipped. A small diagnostic
run is available:

```bash
./run_on_mac.sh train --device mps --conditions real_only --folds 1 --seeds 11 --max-epochs 1 --steps-per-epoch 1
```

Do not leave that diagnostic result in the final output. Rerun the same setting
with `--overwrite` and the full schedule.

## Outputs

Each condition produces 25 runs (5 folds × 5 seeds), for 75 total. The
comparison reports trial/window metrics, false-positive events per ADL minute,
and A10-A14 sensitivity. Statistical comparisons use five seed-averaged fold
pairs with two-sided Wilcoxon tests and Holm adjustment.

```text
outputs/
├── real_only/fold_*/seed_*/...
├── real60_synthetic40/fold_*/seed_*/...
├── real40_synthetic60/fold_*/seed_*/...
└── comparison/
    ├── all_run_metrics.csv
    ├── fold_seed_averaged_metrics.csv
    ├── condition_summary.csv
    ├── paired_wilcoxon_holm.csv
    ├── comparison_summary.json
    ├── condition_metric_boxplots.png
    ├── per_activity_sensitivity_boxplots.png
    └── COMPARISON.md
```

Share the packaged results ZIP for final analysis and README/FINDINGS updates.
