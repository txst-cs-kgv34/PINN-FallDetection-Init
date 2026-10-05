# Reproducible skeleton audit and evidence figures

Use this toolkit for a new subject by changing JSON configuration and the input path. It audits recordings, estimates a **segment-mass CoM proxy**, generates evidence figures, and includes explicitly limited reconstruction/PINN research pilots. It does not generate validated synthetic falls.

## Start here: current S43 inspection

The team confirmed on 2026-09-28 that these are original Azure Kinect joint positions with leading/trailing trimming only. No normalization, retargeting, rescaling or padding was reported. All young participants are adults older than 20. Original videos, timestamps, tracking confidence and camera/floor calibration are unavailable. These confirmations are stored in `configs/collection_metadata.json`; earlier audit snapshots retain their historical metadata.

Open **`inspections/S43_candidates/INSPECT.html`** directly in a browser. It is self-contained and works offline without a server or FFmpeg. The included inspection contains 24 trials / 5,898 frames and enforces the S43A10T01 exclusion. It includes a 1.5 Hz filtering comparison following the main shared notebook; raw remains the initial inspection mode. The later Stage-1 experiment explicitly selects the same offline filter and reports that choice separately.

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
| `scripts/subject_frame.py` | Define a fixed standing-body coordinate frame without claiming floor calibration |
| `scripts/run_reconstruction_pilot.py` | Run fixed whole-trial A13 reconstruction folds and export predictions, errors and plots |
| `scripts/pinn_autograd.py` | Define the differentiable CoM network, derivatives and effective-residual loss |
| `scripts/run_pinn_pilot.py` | Train and evaluate the physical-time A13 PINN in four whole-trial folds |
| `scripts/pinn_torch.py` | Define the controlled PyTorch trajectory/residual networks and dimensionless physics losses |
| `scripts/run_physics_weight_experiment.py` | Compare data-only and physics-informed networks under matched folds, seeds and loss weights |
| `scripts/inverted_pendulum_pinn.py` | Define the Stage-1 horizontal/vertical CoM network, angle derivatives, torque and inverted-pendulum loss |
| `scripts/run_stage1_inverted_pendulum.py` | Run the framework-aligned A13 Stage-1 experiment with non-averaged controls |
| `viewer/inspection.html`, `inspection.js`, `inspection.css` | Player layout, interactions and appearance |
| `scripts/verify.py` | Check audit and male/female CoM regression behavior |
| `scripts/verify_inspection.py` | Check geometry, filtering, candidate selection and S43 inspection exports |
| `scripts/verify_phase_baseline.py` | Check phase validation, alignment, outputs and S43 regression counts |
| `scripts/verify_reconstruction_pilot.py` | Check body-frame geometry and the four A13 reconstruction folds |
| `scripts/verify_pinn_pilot.py` | Check automatic derivatives, hard initial conditions and the four-fold PINN workflow |
| `scripts/verify_physics_weight_experiment.py` | Check the PyTorch controls, gravity sanity baseline, exports and four-fold comparison workflow |
| `scripts/verify_stage1_inverted_pendulum.py` | Check CoM-to-angle geometry, hard onset constraints, controls and the Stage-1 four-fold workflow |

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
python scripts/verify_reconstruction_pilot.py
python scripts/verify_pinn_pilot.py
python scripts/verify_physics_weight_experiment.py
python scripts/verify_stage1_inverted_pendulum.py
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

The current consolidated S43 annotations are stored in
`analysis_inputs/S43_phase_notes_with_A13_eligibility.json`. This input combines
the initial manual phase marks with the later A13 completion review and records
the merge provenance. The validator checks the subject, nominal FPS, candidate
list, frame bounds, phase completeness and phase order. It does not promote an
`apparent_contact` mark to measured ground contact.

```bash
python scripts/build_phase_baseline.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analysis_inputs/S43_phase_notes_with_A13_eligibility.json \
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

The retained checkpoint is `analyses/S43_phase_baseline_v2`. It has 17 eligible
annotated trials overall and four A13 onset-to-contact trials. Reproduce the
baseline from the consolidated input with:

```bash
python scripts/build_phase_baseline.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analysis_inputs/S43_phase_notes_with_A13_eligibility.json \
  --output analyses/S43_phase_baseline_new
```

The four A13 trials support a small four-fold leave-one-trial-out pilot. They do
not provide a strong independent train/validation/test study: any fixed split
would leave only two training trials after reserving validation and test trials.

## Run the A13 kinematic reconstruction pilot

```bash
python scripts/run_reconstruction_pilot.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analysis_inputs/S43_phase_notes_with_A13_eligibility.json \
  --activity A13 \
  --output analyses/S43_A13_reconstruction_pilot_new
```

The pilot fixes a coordinate frame from a five-frame median around each manual
initial-standing mark. Its axes are left-hip to right-hip, foot-midpoint to head,
and an orthogonal forward proxy oriented toward the nose. This makes trials
comparable in a subject-relative frame; it does not estimate the floor or a
measured gravity vector.

Each fold trains on three complete A13 dynamics windows and evaluates the fourth
without frame leakage. Two pre-specified baselines are exported: the mean of the
three training trajectories and a degree-5 ridge-polynomial shape constrained to
zero onset displacement. Both use 101 normalized phase points. Duration is
predicted separately as the median training duration, because normalized phase
hides physical-time variation.

For S43, the polynomial and mean-template results are nearly identical: mean 3D
RMSE 0.1963 m versus 0.1968 m. S43A13T02 is the largest-error fold and has a
1.033 s duration error. These are preliminary subject/activity-specific
benchmarks, not evidence of cross-subject generalization.

## Run the first physical-time PINN pilot

Install the small automatic-differentiation dependency and run the fixed
experiment:

```bash
python -m pip install -r requirements-pinn.txt

python scripts/run_pinn_pilot.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analysis_inputs/S43_phase_notes_with_A13_eligibility.json \
  --activity A13 \
  --epochs 500 \
  --output analyses/S43_A13_pinn_pilot_new
```

The retained fixed-run checkpoint is `analyses/S43_A13_pinn_pilot_v2`. It adds
the held-out condition-distance diagnostic and updated interpretation to the
initial run while keeping the same model settings.

The network consumes physical time plus pre-onset CoM velocity, onset CoM
relative to the foot midpoint and onset foot separation. Position is constructed
as `r(t) = v0*t + t^2*f(t, condition)`, which fixes onset position and velocity.
Automatic differentiation supplies velocity and acceleration. The physics loss
uses `r_ddot = g_proxy + a_effective`, where the gravity proxy follows the
standing headward axis. The effective acceleration is regularized for magnitude
and temporal roughness; multiplying it by subject mass produces an effective
force in newtons.

That force is not a recovered perturbation or ground-reaction force. It combines
all unmeasured support, voluntary control, contact, model error and any true
perturbation. The standing vertical is also a proxy rather than calibrated
gravity.

The delivered fixed run converges on its three training trials but generalizes
poorly: mean held-out 3D RMSE is 0.5010 m versus 0.1961 m for the training-mean
baseline, and it improves zero of four folds. T02 is strongly outside the tiny
training condition range (maximum 21.0 training standard deviations). This is a
negative pilot result: do not generate or claim validated synthetic falls from
this model. The next experiment must compare a data-only network against this
PINN and perform training-only loss-weight/conditioning sensitivity.

## Run the controlled physics-weight experiment

Install PyTorch plus the existing lightweight dependencies, then run the fixed
data-only/PINN comparison:

```bash
python -m pip install -r requirements-pinn-comparison.txt

python scripts/run_physics_weight_experiment.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analysis_inputs/S43_phase_notes_with_A13_eligibility.json \
  --activity A13 \
  --epochs 300 \
  --physics-weights 0,0.01,0.1,1,10 \
  --seeds 43013,43014 \
  --output analyses/S43_A13_physics_weight_experiment_new
```

The comparison uses a three-layer, 32-unit `tanh` trajectory network and a
smaller two-layer, 16-unit effective-residual network. Both data-only and PINN
fits use the same physical-time input, hard onset position/velocity constraint,
trial conditions, folds, optimizer, epochs and seeds. Condition statistics are
computed from the three training trials in each fold. The data-only control is
the zero physics-weight run. The gravity-only curve is untrained and is included
only to demonstrate that unsupported ballistic motion is not a suitable fall
reconstruction model.

The retained result is `analyses/S43_A13_physics_weight_experiment`. Among the
tested weights, λ=0.1 is best: mean held-out 3D RMSE decreases from 0.4618 m for
the matched data-only network to 0.2975 m, and six of eight matched fold/seed
runs improve. This is useful evidence that a moderate physics penalty regularizes
the neural network. It is not sufficient validation: the simple training-mean
baseline remains better at 0.1961 m, only four of eight best-PINN runs beat that
baseline, and T02 remains strongly outside the training-condition range. The
selected weight was chosen using these same four folds, not an independent
validation set. Synthetic generation therefore remains gated.

## Run Framework Stage 1 with inverted-pendulum physics

This is the retained framework-aligned experiment. It follows the shared
`skeleton_analysis_v4.ipynb` preprocessing choices where they are applicable:
order-6, 1.5 Hz zero-phase Butterworth filtering of each complete trial and the
female De Leva segment-weighted CoM. It then transforms the filtered motion to
the fixed standing-subject frame used by this toolkit.

```bash
python -m pip install -r requirements-stage1.txt

python scripts/run_stage1_inverted_pendulum.py \
  --run findings/S43_audit \
  --config configs/S43.json \
  --selection configs/S43_modeling_selection.json \
  --phase-notes analysis_inputs/S43_phase_notes_with_A13_eligibility.json \
  --activity A13 \
  --epochs 300 \
  --physics-weights 0,0.01,0.1,1,10 \
  --seeds 43013,43014 \
  --output analyses/S43_A13_stage1_inverted_pendulum_new
```

For A13, horizontal is the subject-relative lateral direction and vertical is
the standing headward direction. Both are measured relative to the foot
midpoint fixed at marked fall onset. The angular state is derived rather than
renaming a coordinate:

```text
theta(t) = atan2(horizontal_CoM(t), vertical_CoM(t))
```

The PINN enforces the reduced equation
`I*theta_ddot = m*g*l*sin(theta) + tau_effective - b*theta_dot`, with the
point-mass approximation `I=m*l^2` and `b=0` in this feasibility run. The
horizontal/vertical state construction hard-enforces measured onset position
and velocity. `tau_effective` remains an unidentified sum of human control,
external perturbation, support/contact behavior and model error.

The experiment deliberately does not use an averaged trial as a quantitative
baseline. Its controls are the identical data-only network, constant-velocity
extrapolation and a zero-torque inverted pendulum. The marked contact duration
is not supplied as a condition, avoiding that future endpoint as an input.

The retained checkpoint is
`analyses/S43_A13_stage1_inverted_pendulum`. The full run contains 40 fits:
four held-out trials, five physics weights and two seeds. No nonzero physics
weight improved aggregate held-out accuracy. The least harmful nonzero weight,
lambda=0.01, produced 0.4467 m horizontal/vertical CoM RMSE versus 0.4121 m for
the data-only network and improved only two of eight matched runs. It reduced
the angular-equation residual by 31.4%, but worsened trajectory RMSE by 8.4%.
The constant-velocity control was strongest in aggregate at 0.3791 m. T02 again
dominated failure because its 1.8 s trajectory substantially exceeds the
shorter training trials.

This negative result is scientifically useful: satisfying the reduced angular
equation more closely does not yet improve held-out fall reconstruction. The
observed CoM-to-pivot radius changes by 0.159--0.316 m within the selected
windows, so the rigid single-link assumption is visibly violated. Stage 2 and
synthetic generation remain gated.

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
