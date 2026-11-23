# Fifteen-subject A10-A14 fall-detector data preparation

This is the multi-activity successor to the earlier A11-only
`Fifteen_Subject_Fall_Detector_Data_Preparation` folder. It creates
architecture-neutral 30 Hz trajectories for the downstream binary fall
detector while preserving the exact source-subject and synthetic-generator
provenance needed for leakage-safe experiments.

The folder prepares data; it does not train a detector or fix a window length.

## Reviewed input scope

| Source | Label | Reviewed count |
|:--|--:|--:|
| Real ADL | 0 | 545 |
| Detection-ready real A10-A14 falls | 1 | 322 |
| GATE-approved synthetic A10-A14 falls | 1 | 1,380 |
| **Total** |  | **2,247** |

Real falls come from `include_detection_training == true` in the authoritative
physics-ready manifest. This deliberately includes all 322 manually valid
detection trials, not only the stricter 306-trial physics-training subset.

Synthetic falls come only from
`final_approved_synthetic_manifest.json`. The 1,380 approved variants represent
249 strict real source trials and all 15 subjects.

## Required repository layout

```text
PINN-FallDetection-Init/
├── Fifteen_Subject_A10_A14_Fall_Detector_Data_Preparation/
├── Fifteen_Subject_DeepONet_A10_A14_Physics_Synthetic_Fall_Study_GATED/
│   └── outputs/{synthetic_trajectories,trajectory_quality}/...
├── data/processed/Fifteen_Subject_Real_Fall_Physics_Ready/
├── S30_PINN_audit/ ... S63_PINN_audit/
├── ADLSamples/
├── human_subjects_demographics.csv
└── Activity_Types.md
```

The synthetic-study folder must contain the `outputs` extracted or produced by
the completed GATE run. The detector preparer will not read rejected synthetic
files.

## Run on the MacBook home venv

```bash
cd Fifteen_Subject_A10_A14_Fall_Detector_Data_Preparation
chmod +x run.sh run_on_mac.sh

./run_on_mac.sh setup       # optional if numpy is already installed
./run_on_mac.sh test
./run_on_mac.sh all --overwrite
./run_on_mac.sh package
```

If the home environment is not `~/.venv`:

```bash
export FALL_DETECTOR_VENV=/absolute/path/to/your/venv
```

For nonstandard input locations:

```bash
./run_on_mac.sh all \
  --project-root "/path/to/PINN-FallDetection-Init" \
  --physics-ready-root "/path/to/Fifteen_Subject_Real_Fall_Physics_Ready" \
  --synthetic-results-root "/path/to/Fifteen_Subject_DeepONet_A10_A14_Physics_Synthetic_Fall_Study_GATED" \
  --overwrite
```

The reviewed counts are enforced by default. `--allow-count-drift` exists only
for a deliberately changed input dataset; do not use it to bypass an unexplained
count mismatch.

## Coordinate construction

Real falls are recomputed from the audited skeletons using the same fixed
standing-body frame and adult segment-mass CoM model used for DeepONet:

- A10 uses the signed backward subject axis.
- A11 uses the signed forward subject axis.
- A12 uses the signed left subject axis.
- A13 uses the signed right subject axis.
- A14 uses its trial-specific onset-to-contact direction.
- Each real fall ends at its manually marked apparent-contact frame.

Synthetic theta/x signals are resampled from 100 Hz to 30 Hz through their
source-conditioned endpoint. A14 yaw is retained. Planar synthetic trajectories
do not have a generated yaw signal, so their `yaw_available_mask` is zero;
zero-filled yaw must never be interpreted as measured rotation.

The canonical all-activity detector inputs are `theta_rad` and `x_m`. Yaw is an
optional future ablation.

## Output

```text
outputs/
├── dataset_manifest.csv
├── dataset_manifest.json
├── dataset_summary.csv
├── fall_mixture_policies.json
├── subject_activity_coverage.csv
├── analysis_summary.json
├── integrity_report.json
├── excluded_samples.csv              # only when an ADL source is excluded
└── trials/
    ├── real_adl/*.npz
    ├── real_fall/*.npz
    └── synthetic_fall/*.npz
```

Each `.npz` contains `time_s`, `theta_rad`, `x_m`, `yaw_rad`, `valid_mask`,
`observed_mask`, `yaw_available_mask`, the label/activity, demographics, and
the 30 Hz sample rate. Files remain variable length; windowing belongs in the
later detector-training folder.

## Planned comparisons

`sampling_policy.json` and the generated `fall_mixture_policies.json` define:

| Condition | Real falls per 10 fall samples | Synthetic falls per 10 fall samples |
|:--|--:|--:|
| Real-only control | 10 | 0 |
| Real 60 : synthetic 40 | 6 | 4 |
| Real 40 : synthetic 60 | 4 | 6 |

These are ratios within the **fall portion** of a training batch. Fall-versus-ADL
class balance is a separate control and must remain identical across conditions.

## Leakage and multiplicity rules

1. Split by `split_group`/source subject before windowing or sampling.
2. Synthetic samples are permitted only for training subjects.
3. Validation and test contain real ADL and real falls only.
4. Fit normalization on training subjects only.
5. Stratify the fall mixture by activity when possible.
6. Select `synthetic_family_id` first and then select one accepted model variant.

The final rule is essential: a represented real source trial has one to eight
approved variants. Sampling synthetic files uniformly would over-weight source
trials with more accepted generators.

After the local run, share
`Fifteen_Subject_A10_A14_Fall_Detector_Data_Preparation_Results.zip`. The next
folder can then implement the detector architecture, subject folds, windowing,
and the three controlled training conditions.
