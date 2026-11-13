# Fifteen-subject fall-detector data preparation

This directory creates architecture-neutral, trial-level center-of-mass (CoM) data for the downstream binary fall detector.

- Label `0`: real activities of daily living (ADL).
- Label `1`: real or approved synthetic A11 front falls.
- Sampling rate: 30 Hz.
- Signals: `theta_rad` and `x_m`.
- Current real-fall scope: phase-marked A11 front falls from the subject audit directories.

The current DeepONet was trained on A11 front falls, and the approved synthetic trajectories are also A11 front falls. Therefore, the default detector-preparation workflow uses only real A11 front falls. A10 and A12-A14 are not included in the current experiment.

This stage prepares data only. It does not choose the detector architecture, create fixed-length windows, normalize features, balance classes, or assign train/validation/test subjects.

## Required repository layout

Place this directory inside `PINN-FallDetection-Init`:

```text
PINN-FallDetection-Init/
├── Fifteen_Subject_DeepONet_ModelB_Direct_Unified_Physics_Full_Fall_5_Seeds/
├── Fifteen_Subject_Fall_Detector_Data_Preparation/
├── Fifteen_Subject_DeepONet_Synthetic_Fall_Study/
├── S30_PINN_audit/
├── S32_PINN_audit/
├── ...
├── S63_PINN_audit/
├── Activity_Types.md
├── human_subjects_demographics.csv
├── ADLSamples/
│   ├── S30_ADLSamples/*.csv
│   ├── S31_ADLSamples/*.csv
│   ├── ...
│   └── S59_ADLSamples/       # optional; if present, it must be empty
└── FallSamples/              # not used by the default A11 workflow
```

The default command automatically discovers these paths from the parent `PINN-FallDetection-Init` directory. No absolute paths are required with this layout.

## Data sources used by the current A11 workflow

| Input | Purpose |
|---|---|
| `ADLSamples` | Raw 32-joint ADL skeleton CSV files |
| `S##_PINN_audit` | Audited A11 skeleton data, subject configuration, and manual A11 phase marks |
| `Fifteen_Subject_DeepONet_Synthetic_Fall_Study` | Final quality-approved, continuity-corrected synthetic A11 trajectories |
| `human_subjects_demographics.csv` | Sex, mass, and height used by the adult segment-mass CoM model |
| `Activity_Types.md` | Activity names and labels |

Only trajectories listed in the synthetic study's `final_approved_synthetic_manifest.json` are included. Rejected synthetic candidates are not copied.

## Python environment

`run.sh` uses the existing virtual environment in your home directory:

```text
~/.venv/bin/python
```

It does not create or activate another environment. Install the dependency into the existing environment once:

```bash
~/.venv/bin/python -m pip install -r requirements.txt
```

If the existing environment is stored somewhere other than `~/.venv`, set:

```bash
export FALL_DETECTOR_VENV=/absolute/path/to/your/.venv
```

`run.sh` will then use `$FALL_DETECTOR_VENV/bin/python`.

## Run the complete A11 preparation pipeline

From `Fifteen_Subject_Fall_Detector_Data_Preparation`:

```bash
./run.sh test
./run.sh all --overwrite
```

Because `a11` is the default real-fall scope, this is equivalent to:

```bash
./run.sh all --real-fall-scope a11 --overwrite
```

The complete command:

1. Creates 30 Hz ADL CoM trajectories under `outputs/trials/real_adl`.
2. Reads phase-marked A11 skeleton data from the `S##_PINN_audit` directories.
3. Keeps only A11 trials with a complete manual phase sequence.
4. Creates real A11 CoM trajectories through apparent contact under `outputs/trials/real_fall`.
5. Resamples the approved synthetic A11 trajectories from 100 Hz to 30 Hz under `outputs/trials/synthetic_fall`.
6. Writes labels, demographics, provenance, phase frames, and leakage groups.
7. Validates every generated trajectory and runs the summary analysis.

With the previously verified input set, the expected prepared counts are:

| Source | Label | Expected trials |
|---|---:|---:|
| Real ADL | 0 | 545 |
| Phase-marked real A11 front falls | 1 | 70 |
| Approved synthetic A11 front falls | 1 | 226 |
| **Total** |  | **841** |

The preparation command recalculates these counts from the local inputs and records the actual values in the manifest.

`--overwrite` deletes only the generated output directory before rebuilding it. It does not modify source skeletons, audit directories, trained models, or the synthetic-study outputs.

## Run one stage at a time

```bash
./run.sh prepare --overwrite
./run.sh validate
./run.sh analyze
```

## Nonstandard repository location

If this directory is not directly inside `PINN-FallDetection-Init`, provide the repository root:

```bash
./run.sh all \
  --project-root /path/to/PINN-FallDetection-Init \
  --overwrite
```

Individual paths can also be overridden:

```bash
./run.sh all \
  --adl-root /path/to/ADLSamples \
  --audit-root /path/to/PINN-FallDetection-Init \
  --synthetic-results-root /path/to/Fifteen_Subject_DeepONet_Synthetic_Fall_Study \
  --demographics /path/to/human_subjects_demographics.csv \
  --activity-types /path/to/Activity_Types.md \
  --overwrite
```

No `--fall-root` argument is needed for the current A11 workflow.

## Generated directory

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

These folders contain prepared `.npz` files, not copies of the raw skeleton CSV files. Each `.npz` contains:

- `time_s`
- `theta_rad`
- `x_m`
- `valid_mask`
- `label`
- `activity_id`
- `sample_rate_hz`
- `mass_kg`
- `height_m`

Files remain variable length. Windowing must occur later, after the detector architecture and observation length are selected.

## CoM construction

Real skeleton data uses the same adult male/female segment-mass model used by the audits.

For ADL:

- the fixed body frame and foot pivot are estimated from the first 0.5 seconds;
- the complete recording is retained;
- `x_m` is forward CoM displacement relative to the initial foot pivot and is centered over the first 0.5 seconds;
- `theta_rad = atan2(forward CoM displacement, vertical CoM displacement)`.

For phase-marked real A11 falls:

- the fixed body frame uses the manually marked initial-standing neighborhood;
- the pivot is the foot midpoint at the manually marked fall onset;
- the trajectory ends at apparent contact;
- trials without a complete ordered phase sequence are excluded.

Approved synthetic A11 falls retain the generator's continuity-corrected `theta` and `x` signals and are linearly resampled from 100 Hz to 30 Hz.

## ADL details

The ADL set includes A01-A03 and A05-A09. A04 is absent, as expected for the supplied young-adult recordings. A08 is walking and is retained as an important hard-negative activity.

S59 has no ADL recording. The supplied S31 recordings retain S31's identifier and demographics. They are annotated as the replacement source for missing S59 ADL but are never renamed to S59.

## Data-quality rules

- Empty skeleton files are excluded.
- Partially blank rows are excluded.
- Continuous fully blank intervals of at most three frames are linearly interpolated.
- A blank interval longer than three frames is excluded.
- Non-finite values, malformed 96-column rows, duplicate identifiers, and trajectories shorter than the minimum duration are rejected.
- Every exclusion and repair is recorded in the output tables.

## Study membership

`outputs/study_membership.csv` identifies the samples used by the three activity-matched A11 conditions:

1. Real A11 falls + real ADL.
2. Synthetic Physics A11 falls + real ADL.
3. Real and synthetic A11 falls + real ADL.

## Leakage prevention

The `split_group` is always the actual or source subject:

- real ADL remains with its recorded subject;
- real A11 falls remain with their recorded subject;
- synthetic A11 trajectories remain with the subject and real trial that conditioned their generation.

Assign train/validation/test subjects by `split_group` before windowing, oversampling, or augmentation. Do not randomly split trials or windows because synthetic variants or overlapping windows from the same person could appear in both training and evaluation sets.

## Future multi-direction experiment

The code retains an optional A10-A14 mode for a later general fall detector:

```bash
./run.sh all --real-fall-scope all --overwrite
```

That future mode uses `FallSamples`. It is not the recommended command for the current A11 DeepONet/synthetic-fall study.

## Packaging after a local run

```bash
./run.sh package
```

## Next stage

After the detector architecture is confirmed, add a separate training stage that consumes `dataset_manifest.csv` and defines subject-disjoint folds, window length and stride, training-only normalization, class balancing, and real-data evaluation metrics.
