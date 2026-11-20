# S49 PINN audit: repaired findings and manual A11 review package

This directory audits the supplied Azure Kinect skeleton fall trials and stops before PINN or DeepONet training. S49 is recorded as female, 165 lb, 4 ft 11 in.

## Start here

- `findings/S49_audit_repaired/FINDINGS.md`: numeric audit findings.
- `REPAIR_ASSESSMENT.md`: missing trials, gap repairs, and modeling recommendations.
- `inspections/S49_candidates_repaired/INSPECT.html`: offline repair-aware skeleton player.
- `repaired_data/S49/repair_manifest.json`: exact gap and boundary records.
- `analysis_inputs/S49_phase_notes_manual.json`: user-supplied manual A11 phase marks.
- `analysis_inputs/S49_automatic_A11_phase_suggestions_repaired.json`: provisional A11 candidates, not labels.
- `analysis_inputs/S49_phase_notes_template.json`: file to populate with manual phase marks.
- `analysis_inputs/FRONTFALL_PHASE_STATUS.md`: A11 availability and repair warnings.

## Audit status

- Expected trials: 25.
- Numeric trials: 23.
- Empty trials: 0.
- Missing trials: 2.
- Invalid trials: 0.
- Analyzed frames: 3027.
- Repaired blank frames: 55 across 14 gaps.
- Manually phase-marked A11 trials: 3.

Original source archives were not modified. A complete missing or empty trial was never fabricated.

## Manual A11 phases

Manual phase notes were received for 3 A11 trial(s) and saved as `analysis_inputs/S49_phase_notes_manual.json`. Strict phase validation status: **pass**. Automatic phase suggestions remain only as historical review aids and are superseded by the manual notes.

Modeling recommendation: Exclude A11T01 and the absent A11T03. Use only the three strictly validated marked trials: T02, T04, and T05.

See `analysis_inputs/FRONTFALL_PHASE_STATUS.md` and `analysis_inputs/S49_manual_A11_annotation.json` for phase-specific repair intersections, exclusions, and camera-axis interpretation.

## Reproduce

```bash
python -m pip install -r requirements.txt
python scripts/repair_blank_rows.py --input ../upload/S49_FallSamples.zip --subject S49 --short-gap-max 3 --output repaired_data/S49_rerun
python scripts/run_audit.py --input repaired_data/S49_rerun --config configs/S49.json --output findings/S49_audit_repaired_rerun
python scripts/inspect_trials.py --run findings/S49_audit_repaired_rerun --selection configs/S49_repaired_selection.json --metadata configs/collection_metadata.json --cutoff-hz 1.5 --filter-order 6 --repair-mask repaired_data/S49_rerun/repaired_frames.csv --output inspections/S49_candidates_repaired_rerun
```

## Scientific boundary

The audit assumes the established Azure Kinect 32-joint XYZ/mm/30-FPS format. Original timestamps, tracking confidence, videos, and camera-to-floor calibration are unavailable. Repairs, review flags, and automatic phase suggestions support inspection; they are not validated fall labels.

<!-- MULTIACTIVITY_PHASE_UPDATE_START -->
## Multi-activity manual phase update

A10, A12, A13, and A14 manual phase notes were reconciled with this audit; the previously reviewed A11 annotations were retained. The trial manifest separates manual fall validity from repair quality and preserves unavailable or incomplete trials as explicit exclusions.

| Activity | Numeric | Detection-ready | Manual exclusions | Unavailable |
|:--|--:|--:|--:|--:|
| A10 | 5 | 4 | 1 | 0 |
| A11 | 4 | 3 | 1 | 1 |
| A12 | 4 | 1 | 3 | 1 |
| A13 | 5 | 4 | 1 | 0 |
| A14 | 5 | 4 | 1 | 0 |

Machine-readable files: `analysis_inputs/S49_real_fall_trial_manifest.csv` and `analysis_inputs/S49_all_fall_phase_annotations.json`.

A14 may end on either camera side after rotation. Use the per-trial X–Z fall direction rather than an activity-wide sign. Apparent contact remains skeleton-observed.

### Excluded or unavailable trial slots

- `S49A10T01` — Manually confirmed incomplete fall.
- `S49A11T01` — Manually confirmed incomplete fall.
- `S49A11T03` — Expected trial has no numeric CoM output in the audit (missing or empty source).
- `S49A12T01` — Expected trial has no numeric CoM output in the audit (missing or empty source).
- `S49A12T02` — Only T03 was manually confirmed as a valid A12 trial.
- `S49A12T04` — Only T03 was manually confirmed as a valid A12 trial.
- `S49A12T05` — Only T03 was manually confirmed as a valid A12 trial.
- `S49A13T03` — Manually confirmed incomplete fall.
- `S49A14T01` — Manually confirmed incomplete fall.
<!-- MULTIACTIVITY_PHASE_UPDATE_END -->
