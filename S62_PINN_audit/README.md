# S62 PINN audit: repaired findings and manual inspection package

This directory audits 25 S62 Azure Kinect skeleton trials and stops before PINN
training. S62 is recorded as male, 155 lb, 5 ft 4 in. The original audit is
retained; the repaired audit and inspection are the preferred review path.

## Start here

- `findings/S62_audit_repaired/FINDINGS.md`: findings from the repaired numeric data.
- `inspections/S62_candidates_repaired/INSPECT.html`: offline, repair-aware skeleton player.
- `repaired_data/S62/repair_manifest.json`: exact gaps, methods, and boundary frames.
- `repaired_data/S62/repaired_frames.csv`: frame-level repair mask.
- `analysis_inputs/S62_automatic_phase_suggestions_repaired.json`: provisional candidates, not labels.
- `analysis_inputs/S62_phase_notes_template.json`: template for manual phase review.

The player marks repaired frames in purple and raw audit flags in peach. Short
fully blank gaps of at most 3 frames (0.10 s at 30 Hz) were forward-filled from
the previous valid row. Longer internal gaps were linearly interpolated for each
coordinate. Original files were not modified.

## Important repair findings

One hundred nine frames in 11 gaps were repaired. The five A10 trials contain
7.5%–16.7% repaired frames; use A10-derived results only with a repair-exclusion
or leave-one-trial-out sensitivity analysis. S62A12T04 has 4 repaired frames
(2.6%) and S62A14T04 has 2 (1.1%).

## Manual phases

Open `inspections/S62_candidates_repaired/INSPECT.html`. For each retained
trial, mark `initial_standing`, `fall_onset`, `descent`, `apparent_contact`, and
`post_fall`, then export the notes. Apparent contact is a skeleton observation,
not force-plate-confirmed contact.

## Reproduce the repaired workflow

```bash
python -m pip install -r requirements.txt
python scripts/repair_blank_rows.py --input findings/S62_audit/raw --subject S62 --short-gap-max 3 --output repaired_data/S62_rerun
python scripts/run_audit.py --input repaired_data/S62_rerun --config configs/S62.json --output findings/S62_audit_repaired_rerun
python scripts/inspect_trials.py --run findings/S62_audit_repaired_rerun --selection configs/S62_repaired_selection.json --metadata configs/collection_metadata.json --cutoff-hz 1.5 --filter-order 6 --repair-mask repaired_data/S62_rerun/repaired_frames.csv --output inspections/S62_candidates_repaired_rerun
```

## Scientific boundary

The audit assumes the established Azure Kinect 32-joint XYZ/mm/30-FPS format.
Original timestamps, tracking confidence, videos, and camera-to-floor
calibration are unavailable. Repair masks, review flags, and automatic phase
suggestions support inspection; they are not validated fall labels.
