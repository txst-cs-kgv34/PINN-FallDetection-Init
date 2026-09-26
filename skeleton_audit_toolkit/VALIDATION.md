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

No real female subject recording was supplied for this update; anatomical accuracy in women remains unvalidated.
