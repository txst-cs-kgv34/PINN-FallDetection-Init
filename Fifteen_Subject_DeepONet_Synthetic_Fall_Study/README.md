# Fifteen-subject DeepONet synthetic-fall results

This archive contains the leakage-free generator selection, 516 conditionally generated full-fall trajectories, and real-real versus synthetic-real quality verification for the five-fold Physics DeepONet experiment.

## Executive summary

| Item | Result |
|---|---:|
| Original Physics models | 25: five folds × five optimization seeds |
| Validation-selected generators | 10: top two seeds per fold |
| Unique real source contexts | 70 |
| Generated conditional trajectories | 516 |
| Training-subject real-real reference pairs | 489 |
| Synthetic-real quality comparisons | 516 |
| Passed RMSE and DTW shape gate | 461/516 (89.3%) |
| Passed kinematic gate | 281/516 (54.5%) |
| Passed the complete predefined gate | 257/516 (49.8%) |

The 257 passing trajectories should be treated as **provisionally quality-approved**, not as 257 fully independent falls. They originate from 70 real contexts and use two closely related generator outputs per context within each fold.

## Identifier convention

Synthetic identifiers use:

```text
F<fold>_R<generator-rank>_S<seed-index>_<source-trial>
```

For example, `F01_R01_S03_S43A11T02` means:

| Component | Meaning |
|---|---|
| `F01` | Fold 1 |
| `R01` | Validation rank 1 within Fold 1—not round 1 |
| `S03` | Optimization-seed index 3, corresponding to base seed 20261103 |
| `S43A11T02` | Real training-subject context trial used to condition generation |

The `R` field is a rank determined from validation-subject normalized forecast MSE. It is not a training round or epoch.

## Generator selection

Test-subject performance was not used for generator selection. Each fold retained the two seeds with the lowest validation-subject loss:

| Fold | Validation subject | Rank 1 | Rank 2 |
|---:|---|---|---|
| 1 | S63 | Seed index 3 | Seed index 1 |
| 2 | S62 | Seed index 5 | Seed index 2 |
| 3 | S57 | Seed index 4 | Seed index 5 |
| 4 | S55 | Seed index 3 | Seed index 5 |
| 5 | S43 | Seed index 3 | Seed index 4 |

## Quality protocol

For each fold:

1. Only its 11 training subjects were used for generation and threshold construction.
2. Different real trials from the same subject established natural real-real variability.
3. Synthetic-real shape was measured using phase-normalized normalized RMSE, theta RMSE, CoM x RMSE, and DTW.
4. Displacement, velocity, and acceleration were computed on the original 100 Hz time grid after identical Savitzky–Golay smoothing.
5. Per-fold limits were the 95th percentiles of training-subject real-real distances.
6. A trajectory passed when normalized RMSE and DTW both passed and at least 75% of six displacement/velocity/acceleration metrics passed.

## Results by fold

| Fold | Candidates | Complete passes | Pass rate | Mean normalized RMSE | Mean DTW | Mean theta RMSE | Mean x RMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 104 | 40 | 38.5% | 1.1606 | 0.2524 | 17.314° | 22.996 cm |
| 2 | 102 | 62 | 60.8% | 0.6420 | 0.1570 | 9.779° | 12.484 cm |
| 3 | 104 | 67 | 64.4% | 0.8794 | 0.1646 | 13.451° | 17.148 cm |
| 4 | 104 | 67 | 64.4% | 1.1066 | 0.1935 | 15.810° | 22.412 cm |
| 5 | 102 | 21 | 20.6% | 1.2837 | 0.2996 | 19.033° | 25.596 cm |
| **Total** | **516** | **257** | **49.8%** | **1.0149** | **0.2133** | **15.083°** | **20.135 cm** |

Fold 5 is the principal bottleneck. Its two generators produced only 21 passing trajectories, partly because Fold 5's training real-real reference distribution produced stricter DTW and displacement thresholds.

## Real-real versus synthetic-real distance

| Metric | Real-real mean | Synthetic-real mean | Real-real median | Synthetic-real median |
|---|---:|---:|---:|---:|
| Normalized RMSE | 0.7818 | 1.0149 | 0.5741 | 0.9695 |
| Normalized DTW | 0.1709 | 0.2133 | 0.1139 | 0.1718 |
| Theta RMSE | 11.829° | 15.083° | 8.273° | 14.595° |
| CoM x RMSE | 14.977 cm | 20.135 cm | 11.696 cm | 19.093 cm |

Synthetic-real distances are generally larger than natural real-real distances, but 89.3% of trajectories remain within their fold-specific shape thresholds. Most rejection therefore comes from kinematic mismatches rather than RMSE or DTW alone.

## Important limitations before fall-detector training

### Contact duration is conditioned, not generated

DeepONet predicts theta and x but does not predict contact time. Each synthetic trajectory inherits the apparent-contact endpoint and duration of its source trial. Duration is reported but excluded from the gate.

### Context-to-forecast boundary

The first 0.40 seconds are observed real context and the forecast begins at 0.40 seconds. The median boundary jump is 0.950° and 1.451 cm; the 95th percentiles are 4.488° and 6.788 cm. Because this discontinuity could become a classifier shortcut, the current 257 passes should remain provisional until a continuity rule or boundary correction is applied and the quality metrics are rerun.

### Diversity is limited

The two selected generators are less different from each other than separate real trials are:

| Distance | Selected-generator mean | Real-real mean |
|---|---:|---:|
| Normalized RMSE | 0.3597 | 0.7818 |
| Normalized DTW | 0.0753 | 0.1709 |

Thus, adding repeated outputs from the same contexts and deterministic checkpoints would increase file count without proportionally increasing fall diversity.

## Should more synthetic data be generated now?

**Not yet.** The current set is sufficient to prepare an initial downstream detector study after the context-to-forecast continuity issue is addressed. The immediate priority is quality refinement, not sample count.

Recommended order:

1. Add a continuity correction or explicit boundary-jump gate at 0.40 seconds.
2. Rerun quality verification and define the final accepted set.
3. Run the real-only, synthetic-only, and real-plus-synthetic detector experiments on unseen real subjects.
4. Generate more data only if the detector study shows that synthetic-data volume or diversity is limiting performance.

If more data are needed, use new training contexts or validated perturbations of initial state, controller coordinates, and demographics. Simply rerunning the same deterministic generators will reproduce the same trajectories.

## Archive contents

- `outputs/generator_selection/`: rankings and selected-generator provenance
- `outputs/synthetic_trajectories/`: 516 generated `.npz` trajectories and manifests
- `outputs/trajectory_quality/`: distance tables, thresholds, decisions, plots, and generated quality report
- `FINDINGS.md`: detailed scientific interpretation and recommendations
- `study_config.json`: exact quality-gate configuration

