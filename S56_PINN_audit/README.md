# S56 PINN audit: repaired findings and manual A11 review package

This directory audits the supplied Azure Kinect skeleton fall trials and stops before PINN or DeepONet training. S56 is recorded as male, 165 lb, 5 ft 10 in.

## Start here

- `findings/S56_audit_repaired/FINDINGS.md`: numeric audit findings.
- `REPAIR_ASSESSMENT.md`: missing trials, gap repairs, and modeling recommendations.
- `inspections/S56_candidates_repaired/INSPECT.html`: offline repair-aware skeleton player.
- `repaired_data/S56/repair_manifest.json`: exact gap and boundary records.
- `analysis_inputs/S56_automatic_A11_phase_suggestions_repaired.json`: provisional A11 candidates, not labels.
- `analysis_inputs/S56_phase_notes_template.json`: file to populate with manual phase marks.
- `analysis_inputs/FRONTFALL_PHASE_STATUS.md`: A11 availability and repair warnings.

## Audit status

- Expected trials: 25.
- Numeric trials: 24.
- Empty trials: 1.
- Missing trials: 0.
- Invalid trials: 0.
- Analyzed frames: 4337.
- Repaired blank frames: 391 across 50 gaps.
- A11 trials available for manual review: 5.

Original source archives were not modified. A complete missing or empty trial was never fabricated.

## Manual A11 phases

Open the inspection player and provide five ordered frames for each usable A11 trial: initial standing, fall onset, descent, apparent contact, and post-fall. Purple frames were repaired; peach frames carry raw audit review flags. Update `analysis_inputs/S56_phase_notes_template.json` or send the phase frames back for validation.

## Reproduce

```bash
python -m pip install -r requirements.txt
python scripts/repair_blank_rows.py --input ../upload/S56_FallSamples.zip --subject S56 --short-gap-max 3 --output repaired_data/S56_rerun
python scripts/run_audit.py --input repaired_data/S56_rerun --config configs/S56.json --output findings/S56_audit_repaired_rerun
python scripts/inspect_trials.py --run findings/S56_audit_repaired_rerun --selection configs/S56_repaired_selection.json --metadata configs/collection_metadata.json --cutoff-hz 1.5 --filter-order 6 --repair-mask repaired_data/S56_rerun/repaired_frames.csv --output inspections/S56_candidates_repaired_rerun
```

## Scientific boundary

The audit assumes the established Azure Kinect 32-joint XYZ/mm/30-FPS format. Original timestamps, tracking confidence, videos, and camera-to-floor calibration are unavailable. Repairs, review flags, and automatic phase suggestions support inspection; they are not validated fall labels.
