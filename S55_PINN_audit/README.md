# S55 PINN audit: repaired findings and manual inspection package

This directory audits 25 S55 Azure Kinect skeleton trials and stops before PINN
training. S55 is recorded as male, 145 lb, 5 ft 5 in. The original audit is
retained; the repaired audit and inspection are the preferred review path.

## Start here

- `findings/S55_audit_repaired/FINDINGS.md`: findings from the repaired numeric data.
- `inspections/S55_candidates_repaired/INSPECT.html`: offline, repair-aware skeleton player.
- `repaired_data/S55/repair_manifest.json`: exact gaps, methods, and boundary frames.
- `repaired_data/S55/repaired_frames.csv`: frame-level repair mask.
- `analysis_inputs/S55_automatic_phase_suggestions_repaired.json`: provisional candidates, not labels.
- `analysis_inputs/S55_phase_notes.json`: user-supplied manual A11 annotations.
- `analysis_inputs/S55_A11_phase_windows.json`: five validated model-input windows.
- `analysis_inputs/FRONTFALL_PHASE_STATUS.md`: validation and quality-flag summary.

The player marks repaired frames in purple and raw audit flags in peach. Short
fully blank gaps of at most 3 frames (0.10 s at 30 Hz) were forward-filled from
the previous valid row. Longer internal gaps were linearly interpolated for each
coordinate. Original files were not modified.

## Important repair findings

Eighty frames in 11 gaps were repaired. S55A10T01 has 26 repaired frames
(24.8%) and S55A14T01 has 48 (22.6%); treat both as low-confidence and exclude
them from primary parameter estimation unless manual inspection supports a
sensitivity analysis. S55A10T02 has 5 repaired frames and S55A13T01 has 1.

## Manual phases

Manual A11 phases are complete for T01–T05 and pass phase-order validation.
Four selected phase frames overlap raw audit review flags; these are documented
in `analysis_inputs/S55_A11_phase_quality_flags.csv` and are not automatic
exclusions. Apparent contact is a skeleton observation, not force-confirmed contact.

## Reproduce the repaired workflow

```bash
python -m pip install -r requirements.txt
python scripts/repair_blank_rows.py --input findings/S55_audit/raw --subject S55 --short-gap-max 3 --output repaired_data/S55_rerun
python scripts/run_audit.py --input repaired_data/S55_rerun --config configs/S55.json --output findings/S55_audit_repaired_rerun
python scripts/inspect_trials.py --run findings/S55_audit_repaired_rerun --selection configs/S55_repaired_selection.json --metadata configs/collection_metadata.json --cutoff-hz 1.5 --filter-order 6 --repair-mask repaired_data/S55_rerun/repaired_frames.csv --output inspections/S55_candidates_repaired_rerun
```

## Scientific boundary

The audit assumes the established Azure Kinect 32-joint XYZ/mm/30-FPS format.
Original timestamps, tracking confidence, videos, and camera-to-floor
calibration are unavailable. Repair masks, review flags, and automatic phase
suggestions support inspection; they are not validated fall labels.
