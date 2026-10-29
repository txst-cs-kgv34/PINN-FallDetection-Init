# S55 PINN audit: findings and manual inspection package

This directory audits the 25 attached S55 Azure Kinect skeleton trials and
stops before PINN training. S55 is recorded as male, 145 lb, 5 ft 5 in.

## Delivered workflow

- `findings/S55_audit/FINDINGS.md`: audit findings and evidence figures.
- `findings/S55_audit/REPORT.html`: portable findings report.
- `inspections/S55_candidates/INSPECT.html`: offline skeleton player for phase marking.
- `analysis_inputs/S55_phase_notes_template.json`: placeholder for manually reviewed notes.
- `analysis_inputs/S55_automatic_phase_suggestions.json`: optional signal-derived candidates; never treat them as ground truth.
- `scripts/`: reusable audit, inspection, phase-validation, and verification code.

## Inspect and export phases

Open `inspections/S55_candidates/INSPECT.html` in a browser. For each retained
trial, mark `initial_standing`, `fall_onset`, `descent`, `apparent_contact`, and
`post_fall`, then click **Export notes**. Apparent contact is a visual skeleton
label, not force-plate-confirmed contact.

## Reproduce

Run from this directory:

```bash
python -m pip install -r requirements.txt
python scripts/run_audit.py --input ../upload/S55_FallSamples.zip --config configs/S55.json --output findings/S55_audit_rerun
python scripts/inspect_trials.py --run findings/S55_audit_rerun --selection configs/S55_inspection_selection.json --metadata configs/collection_metadata.json --cutoff-hz 1.5 --filter-order 6 --output inspections/S55_candidates_rerun
python scripts/suggest_phases.py --run findings/S55_audit_rerun --selection configs/S55_inspection_selection.json --output analysis_inputs/S55_automatic_phase_suggestions_rerun.json
```

Verification commands for the delivered run are recorded in `VALIDATION.md`.

## Scientific boundary

The audit assumes the same Azure Kinect 32-joint XYZ/mm/30-FPS format used by
the established project workflow. Original timestamps, body-tracking
confidence, videos, and camera-to-floor calibration are unavailable. Review
flags and automatic phase suggestions support inspection; they are not labels,
repairs, or automatic exclusions.
