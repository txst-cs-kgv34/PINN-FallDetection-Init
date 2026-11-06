# S44 PINN audit: repaired findings and manual A11 review package

This directory audits the supplied Azure Kinect skeleton fall trials and stops before PINN or DeepONet training. S44 is recorded as male, 180 lb, 6 ft 1 in.

## Start here

- `findings/S44_audit_repaired/FINDINGS.md`: numeric audit findings.
- `REPAIR_ASSESSMENT.md`: missing trials, gap repairs, and modeling recommendations.
- `inspections/S44_candidates_repaired/INSPECT.html`: offline repair-aware skeleton player.
- `repaired_data/S44/repair_manifest.json`: exact gap and boundary records.
- `analysis_inputs/S44_automatic_A11_phase_suggestions_repaired.json`: provisional A11 candidates, not labels.
- `analysis_inputs/S44_phase_notes_template.json`: file to populate with manual phase marks.
- `analysis_inputs/FRONTFALL_PHASE_STATUS.md`: A11 availability and repair warnings.

## Audit status

- Expected trials: 25.
- Numeric trials: 25.
- Empty trials: 0.
- Missing trials: 0.
- Invalid trials: 0.
- Analyzed frames: 7322.
- Repaired blank frames: 0 across 0 gaps.
- A11 trials available for manual review: 5.

Original source archives were not modified. A complete missing or empty trial was never fabricated.

## Manual A11 phases

Open the inspection player and provide five ordered frames for each usable A11 trial: initial standing, fall onset, descent, apparent contact, and post-fall. Purple frames were repaired; peach frames carry raw audit review flags. Update `analysis_inputs/S44_phase_notes_template.json` or send the phase frames back for validation.

## Reproduce

```bash
python -m pip install -r requirements.txt
python scripts/repair_blank_rows.py --input ../upload/S44_FallSamples.zip --subject S44 --short-gap-max 3 --output repaired_data/S44_rerun
python scripts/run_audit.py --input repaired_data/S44_rerun --config configs/S44.json --output findings/S44_audit_repaired_rerun
python scripts/inspect_trials.py --run findings/S44_audit_repaired_rerun --selection configs/S44_repaired_selection.json --metadata configs/collection_metadata.json --cutoff-hz 1.5 --filter-order 6 --repair-mask repaired_data/S44_rerun/repaired_frames.csv --output inspections/S44_candidates_repaired_rerun
```

## Scientific boundary

The audit assumes the established Azure Kinect 32-joint XYZ/mm/30-FPS format. Original timestamps, tracking confidence, videos, and camera-to-floor calibration are unavailable. Repairs, review flags, and automatic phase suggestions support inspection; they are not validated fall labels.
