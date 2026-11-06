# S30 PINN audit: repaired findings and manual A11 review package

This directory audits the supplied Azure Kinect skeleton fall trials and stops before PINN or DeepONet training. S30 is recorded as female, 190 lb, 5 ft 6 in.

S30 is the replacement candidate for retired subject S58 in the active Model B generalization cohort. No S58 samples should be carried into the new training or evaluation runs.

## Start here

- `findings/S30_audit_repaired/FINDINGS.md`: numeric audit findings.
- `REPAIR_ASSESSMENT.md`: missing trials, gap repairs, and modeling recommendations.
- `inspections/S30_candidates_repaired/INSPECT.html`: offline repair-aware skeleton player.
- `repaired_data/S30/repair_manifest.json`: exact gap and boundary records.
- `analysis_inputs/S30_phase_notes_manual.json`: validated user-supplied A11 phase marks.
- `analysis_inputs/S30_automatic_A11_phase_suggestions_repaired.json`: provisional A11 candidates, not labels.
- `analysis_inputs/S30_phase_notes_template.json`: file to populate with manual phase marks.
- `analysis_inputs/FRONTFALL_PHASE_STATUS.md`: A11 availability and repair warnings.

## Audit status

- Expected trials: 25.
- Numeric trials: 25.
- Empty trials: 0.
- Missing trials: 0.
- Invalid trials: 0.
- Analyzed frames: 5571.
- Repaired blank frames: 0 across 0 gaps.
- Manually phase-marked A11 trials: 5.

Original source archives were not modified. A complete missing or empty trial was never fabricated.

## Manual A11 phases

All five A11 trials have complete, strictly ordered manual phase marks in `analysis_inputs/S30_phase_notes_manual.json`. The derived windows are in `analysis_inputs/S30_manual_A11_phase_windows.json` and `.csv`.

All A11 trials were phase marked. Front-fall motion is slightly tilted toward the camera, so it has a camera-Z component in addition to camera X. Use S30 after aligning the subject-specific horizontal fall direction with Model B's progression coordinate (for example, an X-Z rotation or projection onto the observed horizontal fall direction). Do not treat the Z component as generalization error.

See `analysis_inputs/FRONTFALL_PHASE_STATUS.md` for the validated zero-based phase frames.

## Reproduce

```bash
python -m pip install -r requirements.txt
python scripts/repair_blank_rows.py --input ../upload/S30_FallSamples.zip --subject S30 --short-gap-max 3 --output repaired_data/S30_rerun
python scripts/run_audit.py --input repaired_data/S30_rerun --config configs/S30.json --output findings/S30_audit_repaired_rerun
python scripts/inspect_trials.py --run findings/S30_audit_repaired_rerun --selection configs/S30_repaired_selection.json --metadata configs/collection_metadata.json --cutoff-hz 1.5 --filter-order 6 --repair-mask repaired_data/S30_rerun/repaired_frames.csv --output inspections/S30_candidates_repaired_rerun
```

## Scientific boundary

The audit assumes the established Azure Kinect 32-joint XYZ/mm/30-FPS format. Original timestamps, tracking confidence, videos, and camera-to-floor calibration are unavailable. Repairs, review flags, and automatic phase suggestions support inspection; they are not validated fall labels.
