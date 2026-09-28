# Validation performed

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

No floor/contact calibration, physical stability validation or PINN training is claimed by these checks.
