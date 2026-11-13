# Fifteen-subject fall-detector data preparation

This directory contains architecture-neutral, trial-level CoM trajectories for the downstream binary fall-detection study. It prepares the data but does not choose or train a detector architecture.

## Labels and scope

- Detector label `0`: real activities of daily living (ADL).
- Detector label `1`: real or synthetic falls.
- Canonical sampling rate: 30 Hz.
- Canonical input signals: `theta_rad` and `x_m`.
- No fixed-length windows, train/validation/test assignments, normalization statistics, or class-balancing operations have been applied yet.

The initial controlled fall comparison uses A11 Frontfall only because the approved Physics generator produces A11 trajectories. The audit inventory contains 360 available real files across A10–A14, listed in `outputs/available_real_fall_inventory.csv`, but A10 and A12–A14 are held for a later multi-fall-type study after the detector design is agreed upon.

## Prepared dataset

| Source | Label | Trials | Subjects |
|---|---:|---:|---:|
| Real ADL | 0 | 545 | 15 |
| Real A11 falls | 1 | 70 | 15 |
| Quality-approved synthetic Physics A11 falls | 1 | 226 | 15 source subjects |
| Total | — | 841 | — |

The three requested study conditions are already encoded in `outputs/study_membership.csv`:

| Study condition | Samples | Composition |
|---|---:|---|
| Real falls + real ADL | 615 | 545 ADL + 70 real falls |
| Synthetic Physics falls + real ADL | 771 | 545 ADL + 226 synthetic falls |
| Real and synthetic falls + real ADL | 841 | 545 ADL + 70 real + 226 synthetic falls |

## ADL activities

The prepared ADL set includes A01–A03 and A05–A09. As expected for the supplied young-adult recordings, A04 is absent. A08 is retained as walking.

| Code | Activity | Prepared trials |
|---|---|---:|
| A01 | Drinking Water | 69 |
| A02 | Pick Up Object | 72 |
| A03 | Put On and Take Off Jacket | 66 |
| A05 | Sweeping Floor | 70 |
| A06 | Washing Hand | 66 |
| A07 | Waving Hand | 69 |
| A08 | TUG Test/Walking | 64 |
| A09 | Sit/Stand | 69 |

S59 has no ADL recording. S31 is included as the replacement ADL source using S31's own identifier and demographics. S31 is never relabeled as S59. This distinction is retained in `replacement_for_missing_adl_subject` and `split_group`.

## CoM representation

Real skeleton files use the same adult male/female segment-mass model used by the fall audits. Camera orientation is removed with a fixed anatomical body frame defined from the beginning of an ADL trial or the manually marked initial-standing frame of a real A11 fall.

For ADL:

- the body frame and foot pivot are estimated from the first 0.5 seconds;
- the complete recording is retained;
- `x_m` is the forward CoM displacement relative to the initial foot pivot and centered over the first 0.5 seconds;
- `theta_rad = atan2(forward CoM displacement, vertical CoM displacement)`.

For real A11 falls:

- the fixed body frame uses the manually marked initial-standing neighborhood;
- the pivot is the foot midpoint at the manually marked fall onset;
- the trajectory ends at apparent contact;
- only trials with a complete manual phase sequence are included.

Approved synthetic falls retain the generator's continuity-corrected `theta` and `x` signals and are linearly resampled from 100 Hz to 30 Hz.

## Output files

```text
outputs/
├── dataset_manifest.csv
├── dataset_manifest.json
├── dataset_summary.csv
├── study_membership.csv
├── available_real_fall_inventory.csv
├── excluded_samples.csv
├── repaired_rows.csv
├── integrity_report.json
├── analysis_summary.json
├── trajectory_range_by_sample.csv
├── trajectory_range_summary.csv
├── real_synthetic_context_alignment.csv
└── trials/
    ├── real_adl/*.npz
    ├── real_fall/*.npz
    └── synthetic_fall/*.npz
```

Each trial `.npz` contains:

- `time_s`
- `theta_rad`
- `x_m`
- `valid_mask`
- `label`
- `activity_id`
- `sample_rate_hz`
- `mass_kg`
- `height_m`

Files are variable length and contain only valid samples. Window generation should occur later, after the detector architecture and required observation length are chosen.

## Leakage control

The `split_group` field is the actual or source subject identifier:

- real ADL stays with its recorded subject;
- real falls stay with their recorded subject;
- every synthetic trajectory stays with the subject and real trial that conditioned its generator input.

The detector split must be assigned by `split_group` before windowing, oversampling, or augmentation. Random trial-level or window-level splitting is prohibited because it can place synthetic variants or overlapping windows from the same person in both training and evaluation sets.

## Data-quality handling

- One empty ADL file was excluded: `S48A02T05`.
- ADL files with blank runs longer than three frames were excluded: `S49A03T01`, `S56A03T03`, and `S57A02T03`.
- Five isolated blank rows were linearly repaired across `S57A03T02` and `S63A02T04`; every repaired frame is listed in `outputs/repaired_rows.csv`.
- Four real A11 files without a complete manual phase sequence were excluded: `S43A11T01`, `S49A11T01`, `S57A11T01`, and `S57A11T02`.
- Demographic values were checked against every audit configuration.
- All 841 prepared files passed label, finite-value, 30 Hz timing, required-array, and split-group validation.

## Commands

Run unit tests:

```bash
./run.sh test
```

Validate the included prepared outputs:

```bash
./run.sh validate
```

Recompute the range and context-alignment analysis:

```bash
./run.sh analyze
```

To regenerate the dataset from source locations:

```bash
./run.sh prepare \
  --adl-root /path/to/ADLSamples \
  --audit-root /path/to/extracted/audit/directories \
  --synthetic-results-root /path/to/Fifteen_Subject_DeepONet_Synthetic_Fall_Study_Results \
  --demographics /path/to/human_subjects_demographics.csv \
  --activity-types /path/to/Activity_Types.md \
  --overwrite
```

## Next decision

After the advisor selects the detector architecture, the next code stage should define subject-disjoint folds, window duration/stride, training-only normalization, class balancing, and evaluation metrics. No additional synthetic generation is needed before that experiment.
