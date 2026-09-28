# Reproducible skeleton audit and evidence figures

Use this toolkit for a new subject by changing JSON configuration and the input path. It audits recordings, estimates a **segment-mass CoM proxy**, and generates the evidence figures and a findings report. It does not train a PINN or generate synthetic falls.

## Start here: current S43 inspection

The team confirmed on 2026-09-28 that these are original Azure Kinect joint positions with leading/trailing trimming only. No normalization, retargeting, rescaling or padding was reported. All young participants are adults older than 20. Original videos, timestamps, tracking confidence and camera/floor calibration are unavailable. These confirmations are stored in `configs/collection_metadata.json`; earlier audit snapshots retain their historical metadata.

Open **`inspections/S43_candidates/INSPECT.html`** directly in a browser. It is self-contained and works offline without a server or FFmpeg. The included inspection contains 24 trials / 5,898 frames and enforces the S43A10T01 exclusion. It includes a 1.5 Hz filtering comparison following the main shared notebook; this is an exploratory setting, not a selected fall-model preprocessor. Raw is the initial display mode.

Controls provide trial selection, frame stepping/scrubbing, nominal-speed playback, three camera projections, raw/filtered overlays, jumps to original audit flags, and provisional phase-note export. The data remain in the camera frame. The foot connection and midpoint are landmark geometry, not a support polygon or confirmed contact. Phase notes are held only in page memory: export them before closing the page. Save exported JSON alongside your run's research notes; no annotation is treated as ground truth automatically.

## Main files and their tasks

The main scripts follow a clear order: load/validate inputs, calculate, then export. Command-line entry points use `main()`; reusable functions contain the task logic. Historical `findings/*/code/` folders preserve their earlier versions and should not be used for new analyses.

| Main file | Task |
|---|---|
| `scripts/run_audit.py` | Run a complete new audit, evidence generation and report |
| `scripts/audit_data.py` | Read/validate recordings and export data-quality measurements |
| `scripts/skeleton_model.py` | Define Kinect joints, segment masses, CoM and model sensitivity |
| `scripts/make_evidence.py` | Regenerate all evidence figures for a saved audit |
| `scripts/plot_evidence.py` | Draw CoM traces, tracking diagnostics and pose snapshots |
| `scripts/temporal_diagnostics.py` | Locate exact repeated-pose intervals and shared limb-scale patterns |
| `scripts/build_report.py` | Assemble generated findings, figures and research notes |
| `scripts/add_finding.py` | Append a dated observation/evidence/interpretation/question |
| `scripts/inspect_trials.py` | Apply candidate selection and prepare geometry, filtering comparison and player |
| `scripts/foot_geometry.py` | Calculate foot midpoint/separation and CoM relative to the midpoint |
| `scripts/filter_motion.py` | Apply optional offline filtering with parameter/short-clip guards |
| `scripts/build_viewer.py` | Build a portable HTML player from prepared inspection data |
| `scripts/phase_annotations.py` | Validate exported manual phase marks and create ordered trial windows |
| `scripts/merge_phase_notes.py` | Merge annotation exports under explicit per-trial eligibility decisions |
| `scripts/build_phase_baseline.py` | Build raw onset-to-apparent-contact trajectories and a leave-one-trial-out reference baseline |
| `viewer/inspection.html`, `inspection.js`, `inspection.css` | Player layout, interactions and appearance |
| `scripts/verify.py` | Check audit and male/female CoM regression behavior |
| `scripts/verify_inspection.py` | Check geometry, filtering, candidate selection and S43 inspection exports |
| `scripts/verify_phase_baseline.py` | Check phase validation, alignment, outputs and S43 regression counts |

`core.py` remains only as a compatibility import layer for older scripts. New code imports the task-specific modules. No additional CoM model was introduced during this organization change.

## Reproduce the inspection

The inspection uses an existing audit and an explicit subject-matched candidate list. It rejects candidates also present in the exclusion list, changed raw-file hashes, absent/invalid trials, and existing output directories.

```bash
# Optional filtering dependency; the raw-only inspection does not require SciPy.
python -m pip install -r requirements-inspection.txt

# Raw and filtered comparison (all original frames and flags retained).
python scripts/inspect_trials.py \
  --run findings/S43_audit \
  --selection configs/S43_modeling_selection.json \
  --metadata configs/collection_metadata.json \
  --cutoff-hz 1.5 \
  --output inspections/S43_new_comparison

# Omit --cutoff-hz for raw-only inspection.
python scripts/inspect_trials.py \
  --run findings/S43_audit \
  --selection configs/S43_modeling_selection.json \
  --metadata configs/collection_metadata.json \
  --output inspections/S43_new_raw

# Rebuild just the portable player from existing derived data.
python scripts/build_viewer.py \
  --data inspections/S43_candidates/inspection_data.json \
  --output inspections/S43_candidates/INSPECT.html

python scripts/verify.py
python scripts/verify_inspection.py
python scripts/verify_phase_baseline.py
```

For another subject, use its audit and a selection JSON with `subject_id`, `remaining_candidate_trials`, and `excluded_trials` (a trial-to-reason mapping). Optional collection metadata accompanies the historical audit; it does not silently replace coordinate units, model parameters or sampling rate. Rerun an audit if those computational inputs change.

Each inspection stores geometry CSVs, trial summaries, selection, collection confirmations, the exact segment model, source hashes, code/assets and an HTML player. For a reproducible historical player rebuild, run the copied `scripts/build_viewer.py` within that inspection directory so it uses the adjacent frozen `viewer/` assets.

### Geometry definitions

All calculations use metres and keep the original frame order:

- Foot midpoint: `(FOOT_LEFT + FOOT_RIGHT) / 2` in camera XYZ.
- Foot separation in camera X/Z: Euclidean distance after selecting X and Z.
- Foot separation in camera X: absolute X-coordinate difference.
- Relative CoM: `CoM - foot_midpoint` in camera XYZ.

CSV names explicitly identify the camera axes. The viewer negates Y only for the labeled `Camera −Y` display. It uses a fixed initial-pelvis origin and equal spatial scaling for skeleton drawing, preserving translation within each trial. There is no floor estimate, contact classifier, MoS threshold or automatic fall label. Nominal time is frame0/30; original timestamps and trimmed start offsets are unknown.

### Filtering and evidence

Filtering is optional and runs independently on joint XYZ coordinates using Butterworth second-order sections with forward-backward filtering. The default order is 6 per pass; a cutoff must be explicitly requested. SciPy settings and padding length are recorded. Short clips that cannot support padding retain their raw view and report `skipped_short_clip`. Filters do not interpolate, delete, deduplicate or retime rows. Raw audit flags and repeated-row indicators remain visible regardless of display mode. Filtered CoM uses the same anatomical proxy model on the filtered coordinates. Smoothing can alter motion and limb geometry and uses future samples; it is not validated for prospective prediction.

Confirmed trimming-only provenance does not remove the observed repeat and common limb-length patterns. They are retained as data-quality observations with an unknown cause, not evidence of unreported preprocessing. The next work is phase inspection and reconstruction sensitivity analysis under the available-data constraints, with any later dynamics/contact assumptions stated explicitly.

## Build a phase-aligned real-trial baseline

The S43 viewer annotations are stored with the derived analysis in
`analyses/S43_phase_baseline/S43_phase_notes.json`. They contain 80 manual,
provisional skeleton observations: five ordered phase marks for each of 16
trials. The validator checks the subject, nominal FPS, candidate list, frame
bounds, phase completeness and phase order. It does not promote an
`apparent_contact` mark to measured ground contact.

```bash
python scripts/build_phase_baseline.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analyses/S43_phase_baseline/S43_phase_notes.json \
  --output analyses/S43_phase_baseline_new
```

The script uses raw coordinates converted to metres and the documented female
segment-mass CoM proxy. It extracts each inclusive `fall_onset` to
`apparent_contact` window, expresses CoM as displacement from the onset frame,
and interpolates the window to 101 normalized phase points. Normalization makes
trajectory shapes comparable but removes absolute duration; the original
nominal durations are retained in `phase_windows.csv`.

For each trial, the leave-one-out reference is the mean trajectory of the other
annotated trials with the same activity code. This is a simple real-data
benchmark, not a trained model and not synthetic data. `trial_priority.csv`
ranks annotated trials only by transparent screening burden inside the dynamics
window: the fraction of existing audit flags plus the fraction of exact repeated
transitions. A lower rank is a practical review priority, not proof of physical
validity. Keep whole trials together in every later train/validation/test split.

### A13 completion review

The follow-up A13 export confirms that S43A13T04 is truncated: its final marked
descent is also the recording's final frame, and no apparent-contact or post-fall
mark exists. It is excluded from onset-to-contact modeling. S43A13T05 contains
fall onset, descent and apparent-contact marks but no post-fall movement. Because
the pilot dynamics window ends at apparent contact, T05 is included for that
window only. These decisions and the user's reasons are stored in
`configs/S43_phase_eligibility.json`; the excluded T04 marks remain in the merge
provenance rather than being discarded.

The current combined checkpoint is `analyses/S43_phase_baseline_v2`. It has 17
eligible annotated trials overall and four A13 onset-to-contact trials. Reproduce
the merged input and baseline with:

```bash
python scripts/merge_phase_notes.py \
  --base analyses/S43_phase_baseline/S43_phase_notes.json \
  --supplement /path/to/S43_A13_phase_notes.json \
  --eligibility configs/S43_phase_eligibility.json \
  --output analysis_inputs/S43_phase_notes_with_A13_eligibility.json

python scripts/build_phase_baseline.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analysis_inputs/S43_phase_notes_with_A13_eligibility.json \
  --output analyses/S43_phase_baseline_v2
```

The four A13 trials support a small four-fold leave-one-trial-out pilot. They do
not provide a strong independent train/validation/test study: any fixed split
would leave only two training trials after reserving validation and test trials.

## Quick start

Python 3.10+ is recommended. From this folder:

```bash
python -m pip install -r requirements.txt
python scripts/run_audit.py --input /path/to/S50_FallSamples.zip --config configs/S50.json --output findings/S50_new_run
```

Open `findings/S50_new_run/REPORT.html`. Keep its sibling folders with it: the HTML loads local PNGs and works offline. The included `findings/S50_initial` contains the reproduced S50 audit; `findings/S06_check` demonstrates a different subject, activity and directory input. Use a new output directory for every audit: existing runs cannot be overwritten.

For your next subject, copy `configs/subject_template.json`. Set `subject_id` (for example S51), `mass_lb`, `height_in`, `fps`, and `coordinate_units` (`mm` or `m`). Replace the metadata status notes when confirmed. Set activity descriptions, or leave `activities` empty to discover activity codes. Optional `expected_trials` maps each activity to trial strings such as `["T01", "T02"]`; only specified expected trials can be reported as missing. Extra discovered trials are still audited. No expected-trial list means completeness is unknown, not complete.

```bash
python scripts/run_audit.py --input /path/to/new_subject_folder --config configs/my_subject.json --output findings/my_subject_first_audit
```

Inputs must be headerless numeric CSV, one frame per row, 96 columns in standard Azure Kinect 32-joint XYZ order, named `S<number>A<number>T<number>.csv`. ZIP members may be in subfolders; directory inputs are recursive. Names with longer subject numbers work. Nonmatching names, other subjects and macOS resource files are recorded in `ignored_members.json`. Duplicate trial basenames stop processing rather than silently overwrite data. A different CSV schema requires a reviewed reader/mapping change.

The toolkit supports **adult male and adult female** anthropometric coefficient sets. Set `"sex": "male"` or `"sex": "female"`; unknown/missing values are rejected rather than defaulted. Use `configs/subject_template_female.json` for women and fill in the subject ID and measurements before running. This field selects the published sex-specific anthropometric model; it does not infer gender from skeleton data. Child or other custom anthropometry still requires an appropriate model.

Existing example runs retain their original frozen code and male results. Run new audits using `scripts/run_audit.py` at the toolkit root, not historical `findings/*/code/` snapshots.

## Reproduce each image and log findings

```bash
python scripts/make_evidence.py --run findings/S50_initial
python scripts/build_report.py --run findings/S50_initial
python scripts/add_finding.py --run findings/S50_initial --observation "Visible jump between frames" --evidence "results/review_events.csv; trial and frame numbers" --interpretation "Possible tracking or export issue; unconfirmed" --question "Can we inspect the original Kinect export?"
```

`run_audit.py` runs analysis, figures and report together. `make_evidence.py` regenerates all pictures from saved raw CSVs, CoM scale outputs and frozen configuration. For exact historical code, use the copies in each run's `code/` directory. Do not edit an existing run's raw files or configuration; start a new run instead.

| Evidence file | What is plotted |
|---|---|
| `real_CoM_comparison.png` | All valid trials, one row per activity; camera X, negative Y and Z CoM displacement from the first frame |
| `tracking_diagnostics.png` | Median normalized limb scale and maximum adjacent-frame joint displacement; configured displacement review threshold |
| `<activity>_skeleton_snapshots.png` | Four evenly spaced frame indices per valid trial; camera X/negative-Y projection; red CoM, blue left side, orange right side |

Time is frame index/FPS, not recorded timestamps. No onset alignment, time normalization, smoothing or interpolation is applied. Snapshots subtract a single initial-pelvis origin for each trial and retain translation within that trial. Plot limits are fixed within a trial, not necessarily identical between trials. Repeated colors are possible beyond five trials; legends identify trials. Zero-valid-trial activities remain in tables; there are no fabricated pose pictures.

All findings live under `findings/<run>/`: generated `FINDINGS.md`, offline `REPORT.html`, append-only-by-script `research_notes.md`, data tables, raw copies, configuration, code snapshot and environment/hash provenance. Manual notes are never overwritten by report regeneration. Edit notes directly or use `add_finding.py`; keep observation distinct from interpretation and open questions.

## How mass is distributed and CoM is calculated

Joints are landmarks, not anatomical point masses. We model 14 segments. For each segment s, its proximal and distal endpoints A_s and B_s are a joint or the mean of listed joints. Its position is:

`r_s(t) = (1 - alpha_s) A_s(t) + alpha_s B_s(t)`

`m_s = w_s M`, where `M = mass_lb * 0.45359237` kg.

`CoM(t) = sum_s [m_s r_s(t)] / sum_s m_s = sum_s [w_s r_s(t)]`

The last equality holds because the mass fractions sum to one. Thus changing total body mass alone changes segment masses, but **does not change estimated CoM position** for fixed coordinates and fractions. It will matter for a later dynamics model.

| Segment | Male source mass fraction | Female source mass fraction | Male alpha | Female alpha | Endpoint mapping |
|---|---:|---:|---:|---:|---|
| Head | 0.0694 | 0.0668 | 0 | 0 | HEAD point proxy |
| Trunk | 0.4346 | 0.4257 | 0.5138 | 0.4964 | NECK to midpoint of hips |
| Upper arm, each | 0.0271 | 0.0255 | 0.5772 | 0.5754 | Shoulder to elbow |
| Forearm, each | 0.0162 | 0.0138 | 0.4574 | 0.4559 | Elbow to wrist |
| Hand, each | 0.0061 | 0.0056 | 0 | 0 | HAND point proxy |
| Thigh, each | 0.1416 | 0.1478 | 0.4095 | 0.3612 | Hip to knee |
| Shank, each | 0.0433 | 0.0481 | 0.4395 | 0.4352 | Knee to ankle |
| Foot, each | 0.0137 | 0.0129 | 0.5 | 0.5 | ANKLE/FOOT midpoint proxy |

The head and trunk are counted once; all other rows twice. Male source fractions sum to 1.0. Rounded female source fractions sum to **0.9999**, so each is divided by 0.9999 before use; the effective fractions sum to 1.0 and preserve the supplied total body mass. Exports retain both `reported_mass_fraction` and effective `mass_fraction`, plus the selected sex/model ID. These effective fractions are the `w_s` in the equations above. For S50, total mass is 74.84274105 kg and reported stature is 1.7018 m. Exact per-segment kg values and joint-index/name mappings are exported in `segment_model.json` and `results/segment_mass_model.csv` for every subject.

Fractions and limb/trunk alpha values follow the sex-specific Visual3D implementation table of adjusted Zatsiorsky–Seluyanov/de Leva parameters. HEAD and HAND points, NECK and ANKLE/FOOT midpoint are explicitly **SDK landmark approximations**, not the original anatomical definitions. Foot alpha 0.5 is our proxy, not the published anatomical foot coefficient. The trunk's large mass fraction makes its mapping especially consequential. These population-average coefficients do not establish subject-specific anatomical accuracy.

The cited implementation lists male shank alpha 0.4395; the 0.4459 alternative is included in `landmark_sensitivity.csv`, for male runs only, alongside alternative trunk, head and foot mappings. Female runs use shank alpha 0.4352 and omit that male-specific alternative; the three landmark sensitivity checks remain available. Those comparisons are sensitivities, not measured errors or confidence intervals. The equal-joint centroid is exported only as a comparison; assigning equal mass to every landmark overweights regions with many tracking points.

Height is converted with `height_in * 0.0254`. It is retained for the ratio of eye-to-furthest-foot distance to reported stature. That pose-dependent span omits head/sole offsets and is not an independent stature measurement. No per-frame or per-trial rescaling to height is performed.

## Missing data and screening

Empty files, absent expected files and invalid files are distinct manifest statuses. Invalid means a parse error, nonfinite values, wrong column count, fewer than two frames, a zero-length diagnostic limb, or an undefined head-to-ankle direction. Entire invalid trials are withheld from derived calculations, and their original bytes and reason are retained. This is conservative trial-level exclusion, not missing-data repair. Finite zero values alone are counted but not treated as missing; confidence fields are unavailable. Files labeled `numeric` passed these input checks, not a biomechanical validity test.

Eight diagnostic limb lengths are divided by their within-trial medians; their framewise median is the common scale. Scale range is `100 * (max(scale)/min(scale) - 1)`. The review flag marks a destination frame when **any joint displacement exceeds the configured metres threshold OR the absolute relative common-scale change exceeds its threshold**. Defaults are 0.2 m and 3%; these are exploratory screening settings, not physical limits. All valid-trial frames, including flagged and repeated frames, remain in outputs. Constant limb series have undefined correlations, exported as null. Exact duplicate comparisons do not detect approximate duplicates.

Camera X and Z are not verified ground-horizontal axes, and negative Y is not calibrated vertical. Absolute height above the floor and true horizontal coordinates are deliberately blank. The toolkit does not infer floor, contacts, BoS, forces, joint torques, perturbations or recovery capability. Metadata fields for ground/gravity are descriptive only; this version does not apply calibration transforms.

## Verification and interpretation

```bash
python scripts/verify.py
```

Verification also checks female coefficients, normalization, model selection, invalid selections, mass conservation, per-frame CoM exports and report/plot generation on a fabricated numerical fixture (not a recorded subject). It checks original S50 count reproduction, the second-subject run, affine behavior of CoM, segment mass conservation, file hashes, and empty/invalid/missing input handling. The initial numeric output was also compared against the prior S50 audit during development. See `VALIDATION.md`. This validates software behavior, not anatomical CoM accuracy or suitability for PINN training. No automatic clinical or training acceptance label is produced.

Before PINN fitting, resolve units/order, export preprocessing, event coverage and camera calibration. Keep whole trials together when making train/test splits. Without measured force/contact/perturbation data, identifying dynamics and control requires explicit modeling assumptions and a separate validation experiment.

## Sources

- Azure Kinect joint order and positions: https://learn.microsoft.com/en-us/previous-versions/azure/kinect-dk/body-joints
- Camera coordinate convention: https://learn.microsoft.com/en-us/previous-versions/azure/kinect-dk/coordinate-systems
- Parameter implementation table: https://www.has-motion.com/wiki/doku.php?id=visual3d:documentation:definitions:adjusted_zatsiorsky-seluyanov_s_segment_inertia_parameters
- de Leva (1996): https://doi.org/10.1016/0021-9290(95)00178-6
- Subject measurements, FPS and activity descriptions were supplied by the user. S43 unit/order provenance was subsequently confirmed by the user/team; see current collection metadata. Historical snapshots preserve their earlier assumptions.

## S43 female-subject audit

S43's configuration is `configs/S43.json`: female model, 130 lb (58.9670081 kg), 64 inches (1.6256 m), and nominal 30 FPS under the previously described acquisition protocol. Adult applicability was subsequently confirmed: all young participants are older than 20.

```bash
python scripts/run_audit.py --input /path/to/S43_FallSamples.zip --config configs/S43.json --output findings/S43_new_run
```

Open `findings/S43_audit/REPORT.html` for the completed audit and research notes. All 25 files pass numeric input checks, with 6,080 frames, but this does not establish complete or physically reliable fall trajectories. There are 1,390 exact consecutive repeats, 802 review-flagged destination frames, and near-identical common scaling across the eight diagnostic limbs. S43A10T01 has only three distinct poses across 182 frames. The notes record implications and questions for the team; no PINN is trained.

New generic evidence is regenerated by `make_evidence.py` or directly:

```bash
python scripts/temporal_diagnostics.py --run findings/S43_audit
python scripts/build_report.py --run findings/S43_audit
```

`temporal_summary.csv/json` records distinct poses, repeated adjacent transitions, and longest constant-pose runs. `constant_pose_runs.csv/json` contains inclusive zero-based frame ranges. A run of N identical rows spans (N-1)/FPS nominal seconds. Repeat-transition percentages use (frames-1) as denominator; they are not percentages of missing frames. These metrics cannot determine whether repeats came from export, padding, tracking hold or another cause.

`temporal_repeats.png` compares repeats and constant spans across trials. `shared_limb_scaling.png` overlays eight normalized limb lengths for the longest constant-pose trial and largest scale-range trial, deduplicating the selection. The scripts retain every input frame. Numeric processing order is now deterministic by basename, independent of ZIP entry order. Reports include temporal results and research notes; notes remain separately editable and are not overwritten.

## Shared notebook review and S43 selection

`reviews/notebooks/REVIEW.md` explains all three shared notebooks, their CoM/BoS formulas, limitations and proposed reuse. The folder includes a reproducible CoM formula comparison on S43. `configs/S43_modeling_selection.json` records the user-directed exclusion of S43A10T01 from future modeling; all raw audit data remain preserved. This is a candidate manifest, not automatic training approval or an audit filter; the inspection runner now enforces it. No notebook BoS feature was integrated without review.
