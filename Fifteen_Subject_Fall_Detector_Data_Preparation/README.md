# Fifteen-subject fall-detector data preparation

This directory creates architecture-neutral, trial-level center-of-mass (CoM) data for the downstream binary fall detector.

- Label `0`: real activities of daily living (ADL).
- Label `1`: real or approved synthetic falls.
- Sampling rate: 30 Hz.
- Signals: `theta_rad` and `x_m`.
- Default real-fall scope: all available A10-A14 recordings.

This stage prepares data only. It does not choose the detector architecture, create fixed-length windows, normalize features, balance classes, or assign train/validation/test subjects.

## Required repository layout

Place this directory inside `PINN-FallDetection-Init` with the source folders shown below:

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
│   └── S59_ADLSamples/        # optional; if present, expected to be empty
└── FallSamples/
    ├── S30_FallSamples/*.csv
    ├── S32_FallSamples/*.csv
    ├── ...
    └── S63_FallSamples/*.csv
```

`ADLSamples` and `FallSamples` may remain ignored by Git. They are input data and are never modified by this code.

The default command automatically discovers every path from the parent `PINN-FallDetection-Init` directory. No absolute paths are required when the repository follows this layout.

## Input responsibilities

| Input | Purpose |
|---|---|
| `ADLSamples` | Raw 32-joint ADL skeleton CSV files |
| `FallSamples` | Raw 32-joint A10-A14 fall skeleton CSV files |
| `S##_PINN_audit` | Subject configuration and demographic consistency checks; also supplies manual A11 phases for the optional A11-only run |
| `Fifteen_Subject_DeepONet_Synthetic_Fall_Study` | Final quality-approved synthetic manifest and continuity-corrected synthetic trajectories |
| `human_subjects_demographics.csv` | Sex, mass, and height used by the adult segment-mass CoM model |
| `Activity_Types.md` | Activity names for A01-A14 |

Only trajectories listed in the synthetic study's `final_approved_synthetic_manifest.json` are included. Rejected synthetic candidates are not copied.

## Environment setup

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Run the complete preparation pipeline

Run the unit tests first:

```bash
./run.sh test
```

Then create the three prepared folders, validate them, and run the summary analysis:

```bash
./run.sh all --overwrite
```

The command performs these operations in order:

1. Converts ADL skeletons into 30 Hz CoM trajectories under `outputs/trials/real_adl`.
2. Converts all valid A10-A14 real-fall skeletons into 30 Hz CoM trajectories under `outputs/trials/real_fall`.
3. Converts the approved synthetic A11 trajectories from 100 Hz to 30 Hz under `outputs/trials/synthetic_fall`.
4. Writes labels, demographics, activity metadata, provenance, and leakage groups to the manifests.
5. Validates every generated trajectory.
6. Produces range and real/synthetic context-alignment reports.

`--overwrite` deletes only the generated output directory before rebuilding it. It does not delete or edit any source skeleton, audit, model, or synthetic-study file.

## Run one stage at a time

The same workflow can be run separately:

```bash
./run.sh prepare --overwrite
./run.sh validate
./run.sh analyze
```

After a successful run, the preparation step prints the exact accepted and excluded counts. The expected ADL count with the supplied files is 545, and the approved synthetic count is 226. The accepted real-fall count is determined from the local `FallSamples` quality checks and is recorded in `outputs/dataset_manifest.json`.

## Real-fall scope

The default is the general detector dataset:

```bash
./run.sh all --real-fall-scope all --overwrite
```

This uses full A10 Backfall, A11 Frontfall, A12 Leftfall, A13 Rightfall, and A14 Rotatefall recordings from `FallSamples`.

To reproduce the controlled activity-matched A11-only dataset, use a separate output directory:

```bash
./run.sh all \
  --real-fall-scope a11 \
  --output-dir outputs_a11 \
  --overwrite
```

The A11-only mode reads the audited skeleton copies and manual phase notes from the `S##_PINN_audit` directories, requires a complete phase sequence, and clips each trajectory through apparent contact. Keeping it in `outputs_a11` prevents it from replacing the general A10-A14 dataset.

## Nonstandard paths

If the project is stored differently, set the project root:

```bash
./run.sh all \
  --project-root /path/to/PINN-FallDetection-Init \
  --overwrite
```

Individual locations can also be overridden:

```bash
./run.sh all \
  --adl-root /path/to/ADLSamples \
  --fall-root /path/to/FallSamples \
  --audit-root /path/to/PINN-FallDetection-Init \
  --synthetic-results-root /path/to/Fifteen_Subject_DeepONet_Synthetic_Fall_Study \
  --demographics /path/to/human_subjects_demographics.csv \
  --activity-types /path/to/Activity_Types.md \
  --overwrite
```

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

The `real_adl`, `real_fall`, and `synthetic_fall` folders contain prepared `.npz` files, not copies of the original skeleton CSV files. Each `.npz` contains:

- `time_s`
- `theta_rad`
- `x_m`
- `valid_mask`
- `label`
- `activity_id`
- `sample_rate_hz`
- `mass_kg`
- `height_m`

The files remain variable length. Windowing must be added later after the detector architecture and observation length are selected.

## CoM construction

Real skeleton data uses the same adult male/female segment-mass model used by the subject audits.

For ADL and the default A10-A14 real-fall dataset:

- the fixed anatomical body frame and foot pivot are estimated from the first 0.5 seconds;
- the complete recording is retained;
- `x_m` is forward CoM displacement relative to the initial foot pivot and is centered over the first 0.5 seconds;
- `theta_rad = atan2(forward CoM displacement, vertical CoM displacement)`.

For the optional audited A11-only dataset:

- the body frame uses the manually marked initial-standing neighborhood;
- the pivot is the foot midpoint at manually marked fall onset;
- the trajectory ends at apparent contact.

Approved synthetic falls retain the generator's continuity-corrected `theta` and `x` signals and are linearly resampled from 100 Hz to 30 Hz.

## ADL details

The ADL set includes A01-A03 and A05-A09. A04 is absent, as expected for the supplied young-adult recordings. A08 is retained as walking and is an important hard-negative activity.

S59 has no ADL recording. The supplied S31 recordings retain the subject identifier and demographics of S31. They are annotated as the replacement source for missing S59 ADL, but they are never renamed to S59.

## Data-quality rules

- Empty skeleton files are excluded.
- Partially blank rows are excluded.
- Continuous fully blank intervals of at most three frames are linearly interpolated.
- A blank interval longer than three frames is excluded instead of manufacturing a long motion segment.
- Non-finite values, malformed 96-column rows, duplicate trial identifiers, and recordings shorter than the configured minimum duration are rejected.
- Every exclusion and repair is recorded in the output tables.

## Study membership

`outputs/study_membership.csv` identifies the samples used by the three planned training conditions:

1. Real falls + real ADL.
2. Synthetic Physics falls + real ADL.
3. Real and synthetic falls + real ADL.

With the default `all` scope, the real-fall conditions contain A10-A14 while the synthetic condition contains approved A11 Physics trajectories. Use the separate `a11` run when an activity-matched real-versus-synthetic comparison is required.

## Leakage prevention

The `split_group` is always the actual or source subject:

- real ADL remains with its recorded subject;
- real falls remain with their recorded subject;
- synthetic trajectories remain with the subject and real trial that conditioned generation.

Assign train/validation/test subjects by `split_group` before windowing, oversampling, or augmentation. Do not randomly split trials or windows. Otherwise, overlapping windows or synthetic variants of the same person can appear in both training and evaluation data.

## Packaging after a local run

To package the code, reports, manifests, and generated trajectories:

```bash
./run.sh package
```

## Next stage

After the detector architecture is confirmed, add a separate training stage that consumes `dataset_manifest.csv` and defines:

- subject-disjoint folds;
- input features and observation-window length;
- window stride and event labels;
- normalization fitted on training subjects only;
- class weighting or balanced batches;
- real-only validation and testing;
- sensitivity, specificity, precision, F1, AUROC, AUPRC, and false-alarm rate.
