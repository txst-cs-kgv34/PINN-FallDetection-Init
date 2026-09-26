# Reproducible skeleton audit and evidence figures

Use this toolkit for a new subject by changing JSON configuration and the input path. It audits recordings, estimates a **segment-mass CoM proxy**, and generates the evidence figures and a findings report. It does not train a PINN or generate synthetic falls.

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
- Subject measurements, FPS and activity descriptions were supplied by the user. Unit and joint-order assumptions remain provisional until confirmed against the export.
