# Validation performed

## Phase-aligned S43 real-trial baseline (2026-09-28)

`python scripts/verify_phase_baseline.py` rebuilds the phase baseline in a
temporary directory and checks the supplied S43 annotation regression counts:
84 included marks, 17 dynamics-complete trials, five fall types, 101 normalized
points per trial, 17 leave-one-out comparisons, exclusion of S43A10T01 and
incomplete S43A13T04, inclusion of the onset-to-contact-only S43A13T05, zero onset
displacement and five generated plots. The full audit and inspection regression
checks were rerun after adding this workflow and also passed.

This test validates annotation handling, phase-window extraction, interpolation
and table/figure generation. It does not validate manual phase accuracy,
physical contact, anatomical CoM accuracy or model suitability.

## A13 reconstruction pilot (2026-09-28)

`python scripts/verify_reconstruction_pilot.py` checks a constructed identity
standing-body frame, orthonormal axes and point transformation. It then rebuilds
the A13 pilot in a temporary directory and verifies four held-out trials, two
fixed methods per fold, 404 prediction rows, zero onset displacement and four
plots. All earlier audit, inspection and phase-baseline checks also pass.

This verifies software behavior and whole-trial separation. It does not validate
the standing-body axes as world gravity/floor coordinates, the CoM proxy as
anatomical truth, or the reconstruction as a clinical/physical fall model.

## First physical-time PINN pilot (2026-09-28/29)

`python scripts/verify_pinn_pilot.py` checks finite automatic derivatives and the
hard onset position/velocity construction on an independent numerical example.
It then runs a two-epoch workflow smoke test and verifies four held-out trials,
finite metrics, zero onset displacement, histories and four plots. The delivered
500-epoch run was also executed end to end with fixed settings.

Training objectives decreased substantially, but held-out performance was worse
than the training-mean baseline in all four folds. This negative result is
retained. Software execution does not validate the gravity proxy, effective
force, loss weights, perturbations or synthetic trajectories.

## Controlled PyTorch physics-weight experiment (2026-09-28)

`python scripts/verify_physics_weight_experiment.py` checks the hard onset
position/velocity constraint and finite automatic derivatives on an independent
network instance, verifies the analytical gravity-only sanity curve, and runs a
two-epoch four-fold workflow with data-only and nonzero-physics branches. It
checks all expected trial/weight runs, finite metrics, zero onset displacement,
histories, exported predictions, six plots and the force-interpretation warning.

The delivered experiment ran 40 fits: four whole-trial folds, five physics
weights and two base seeds, each for 300 epochs. The best tested nonzero weight
was 0.1. Its mean held-out 3D CoM RMSE was 0.2975 m versus 0.4618 m for the
matched data-only network; six of eight matched fold/seed runs improved and the
mean held-out physics residual was 3.0733 m/s². However, the training-mean
baseline remained better at 0.1961 m, only four of eight best-PINN runs beat it,
and S43A13T02 remained the dominant error and was 21.0 training standard
deviations outside at least one conditioning range.

This verifies the controlled software comparison and shows a regularization
benefit at moderate physics weight. It is not independent hyperparameter
validation, force identification, cross-subject validation, clinical validation
or permission to generate physically validated synthetic falls.

## Framework Stage-1 inverted-pendulum experiments (2026-10-02/05)

`python scripts/verify_stage1_inverted_pendulum.py` checks the conversion from
horizontal/vertical CoM to `theta=atan2(horizontal, vertical)`, the hard onset
position and velocity construction, finite first/second automatic derivatives,
constant-velocity and uncontrolled-pendulum controls, and a two-epoch
four-fold workflows for A13 lateral and A11 anterior-posterior motion. It verifies all expected trials and branches, finite
metrics, exact onset states, exported histories/predictions, six plots, absence
of an averaged-trial baseline, and the effective-torque interpretation warning.

The retained 300-epoch experiment ran 40 fits: four whole-trial folds, five
physics weights and two seeds. The best tested nonzero setting by aggregate XY
RMSE was lambda=0.01, but it was 8.4% worse than the identical data-only network
(0.4467 m versus 0.4121 m) and improved only two of eight matched runs. It
reduced the angular-equation residual from 336.87 to 231.18 N*m (31.4%) while
worsening held-out trajectory accuracy. The constant-velocity control was best
in aggregate at 0.3791 m; the uncontrolled zero-torque pendulum was 0.4882 m.
T02 remained the dominant failure.

This verifies the executable Stage-1 formulation and demonstrates that lower
physics residual is not sufficient evidence of better held-out motion. The
fixed onset foot midpoint is not measured center of pressure, the point-mass
inertia and rigid link are approximations, and the learned effective torque is
not separately identifiable as human control or external perturbation. The
experiment does not validate Stage 2, synthetic falls, cross-subject behavior,
or clinical fall detection.

The retained A11 experiment also ran 40 fits using the user-reviewed T02--T05
phase windows and the same architecture, weights, seeds, epochs, optimizer and
loss terms as A13. Its horizontal state is subject-forward CoM and its support
span proxy uses the anterior-posterior projections of the left/right ANKLE and
FOOT landmarks. The data-only network achieved 0.2430 m mean held-out XY RMSE.
The best nonzero setting, lambda=0.01, achieved 0.2520 m: 3.7% worse in
trajectory RMSE, despite reducing the angular-equation residual by 33.9%. It
improved four of eight matched fold/seed runs and improved angle RMSE by 5.1%.
The software verifier checks automatic A11-to-forward and A13-to-lateral axis
selection. The cross-activity export checks that the two activities are
compared descriptively without pooling their different horizontal directions.

## Stage-1.5 relaxed-mechanics validation (2026-10-07)

`python scripts/verify_stage1_relaxed_mechanics.py` checks that the new
variable-length residual reduces exactly to the original Stage-1 residual when
`l_dot=0` and pivot acceleration is zero. It also runs independent two-epoch
four-fold workflows for the fixed-pivot variable-length and measured moving-
support variants. The check verifies finite metrics, both physics branches,
exact onset position, expected trial counts, exported predictions, and the
moving-support interpretation warning.

Four full experiments were then run with the original Stage-1 training budget:
four whole-trial folds, five physics weights, two seeds, 300 epochs, 24
collocation points, and the same neural architectures and optimizer.

- A11 fixed-pivot variable length: 0.2500 m best PINN RMSE, 2.9% worse than
  original data-only and 32.4% lower residual than its matched data-only run.
- A13 fixed-pivot variable length: 0.4857 m, 17.8% worse than original
  data-only and 6.2% lower residual.
- A11 moving-support diagnostic: 0.3176 m, 30.7% worse than original data-only.
- A13 moving-support diagnostic: 0.4955 m, 20.2% worse than original data-only,
  although it reduced residual by 57.6% relative to its matched moving-frame
  data-only model.

The moving-support workflow uses the held-out filtered FOOT midpoint trajectory
as an observed exogenous diagnostic, so it is not a deployable forecast. It
does not use held-out CoM after onset, but its support input would not be known
for virtual perturbation simulation. These checks validate software behavior
and the controlled comparison; they do not validate the support proxy,
controller identification, synthetic falls, or clinical prediction.

- Reproduced S50: 19 analyzed clips, 6 empty files, 895 frames.
- Compared 582 shared numeric trial metrics to the previous S50 audit, with relative and absolute tolerance 1e-12; all matched.
- Used a separate subject configuration and directory input for S06: 5 clips, 1,011 frames, activity A08.
- Verified segment mass fractions sum to one and CoM responds correctly to translation and uniform coordinate scaling.
- Verified hashes of retained raw files.
- Tested an alternate subject ID S123 with an empty CSV, wrong-column CSV, nonfinite CSV and absent expected trial; all statuses were logged correctly with zero analyzed frames.
- Visually inspected the regenerated S06 pose-snapshot figure for layout, frame labels and CoM markers.

The delivered scripts support all-empty/invalid datasets without inventing plots. These checks are software verification, not biomechanical or clinical validation. Reproduction can differ in raster styling across Matplotlib versions; provenance records versions and script hashes for each run.

## Adult female model update

- Checked all female mass and segment-position coefficients against the Visual3D source table (accessed 2026-09-26).
- Female rounded source mass fractions sum to 0.9999; normalized weights sum to one and segment masses sum to the supplied subject mass.
- Confirmed sex selection changes CoM for the same numerical coordinates, and unsupported selections raise errors.
- Checked female CoM against a separately calculated weighted sum and affine transformations.
- Ran the full female pipeline on a deterministic fabricated numerical fixture, including three evidence PNGs, CoM CSV/JSON outputs, model metadata and HTML report. The fixture is a software test, not a recorded woman or a synthetic fall experiment.
- Recomputed every CoM frame in the included S50 and S06 recordings with the updated male model; all matched prior exported values at absolute tolerance 1e-12 m.
- Original example runs and their frozen code remain unchanged. Female support is in the top-level scripts for new runs.

At the female-model implementation stage, no real female subject recording had been supplied. S43 was subsequently audited below; anatomical accuracy remains unvalidated.

## S43 audit update (2026-09-26)

- Ran all 25 uploaded S43 CSV files through the female model: 6,080 frames; zero empty, missing or invalid files.
- Verified hashes and recomputed every exported female CoM frame directly from saved raw coordinates.
- Confirmed 1,390 exact consecutive repeated transitions and the S43A10T01 interval of 180 identical rows at frames 0–179.
- Verified duplicate-run interval boundary logic on independent constructed sequences.
- Verified all nine evidence figures exist; inspected the montage and A10 pose figure for layout and interpretation.
- Confirmed report regeneration preserves research_notes.md.
- All previous male/female calculation and malformed-input regression tests passed.

These tests verify computation and provenance. Repeated coordinates and common scale changes still limit physical interpretation.

## Inspection and code organization update (2026-09-28)

- Split the former core into skeleton_model.py, audit_data.py and plot_evidence.py, retaining compatibility imports. Main scripts now use clear formatting, task functions and main() entry points. Previous audit/model tests passed after the refactor; stored historical code remains unchanged.
- Verified exact raw-coordinate preservation, nominal 30 FPS, 24 selected trials / 5,898 frames, 800 raw review flags and 1,211 repeated transitions in the inspection export.
- Verified geometry against independent known-coordinate examples and translation invariance.
- Checked optional filtering preserves source arrays and row counts, rejects invalid cutoffs, and skips unsupported short clips explicitly. Raw-only inspection was also exercised.
- Verified candidate/exclusion conflicts fail before creating output.
- Tested the delivered HTML in headless Chromium: trial selection, raw/filtered/overlay modes, all camera projections, frame-to-time conversion, review-flag jumps, playback end/restart behavior, manual-note export and narrow-screen layout. No page JavaScript errors or HTTP(S) requests occurred. Desktop screenshot was inspected.
- Browser test source is tests/verify_viewer.cjs. It requires Playwright and its Chromium installation; optional PLAYWRIGHT_CHROMIUM_EXECUTABLE points to an existing compatible binary. This is a development-only check, not a requirement to open the player.
- Filtering is exploratory: maximum CoM displacement from raw at the delivered 1.5 Hz setting is 0.273900453 m in S43A10T03. This is sensitivity to filtering, not an error estimate.

No floor/contact calibration, physical stability validation, recovered external
force or physically validated synthetic-fall generation is claimed by these checks.
