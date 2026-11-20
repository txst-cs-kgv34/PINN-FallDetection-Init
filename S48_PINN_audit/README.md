# S48 PINN audit: repaired findings and manual A11 review package

This directory audits the supplied Azure Kinect skeleton fall trials and stops before PINN or DeepONet training. S48 is recorded as male, 188 lb, 5 ft 8 in.

## Start here

- `findings/S48_audit_repaired/FINDINGS.md`: numeric audit findings.
- `REPAIR_ASSESSMENT.md`: missing trials, gap repairs, and modeling recommendations.
- `inspections/S48_candidates_repaired/INSPECT.html`: offline repair-aware skeleton player.
- `repaired_data/S48/repair_manifest.json`: exact gap and boundary records.
- `analysis_inputs/S48_phase_notes_manual.json`: user-supplied manual A11 phase marks.
- `analysis_inputs/S48_automatic_A11_phase_suggestions_repaired.json`: provisional A11 candidates, not labels.
- `analysis_inputs/S48_phase_notes_template.json`: file to populate with manual phase marks.
- `analysis_inputs/FRONTFALL_PHASE_STATUS.md`: A11 availability and repair warnings.

## Audit status

- Expected trials: 25.
- Numeric trials: 24.
- Empty trials: 0.
- Missing trials: 0.
- Invalid trials: 1.
- Analyzed frames: 3463.
- Repaired blank frames: 329 across 40 gaps.
- Manually phase-marked A11 trials: 5.

Original source archives were not modified. A complete missing or empty trial was never fabricated.

## Manual A11 phases

Manual phase notes were received for 5 A11 trial(s) and saved as `analysis_inputs/S48_phase_notes_manual.json`. Strict phase validation status: **pass**. Automatic phase suggestions remain only as historical review aids and are superseded by the manual notes.

Modeling recommendation: Use the observed onset-through-apparent-contact interval. Mask repaired post-contact frames and do not use them as measured post-fall supervision.

See `analysis_inputs/FRONTFALL_PHASE_STATUS.md` and `analysis_inputs/S48_manual_A11_annotation.json` for phase-specific repair intersections, exclusions, and camera-axis interpretation.

## Reproduce

```bash
python -m pip install -r requirements.txt
python scripts/repair_blank_rows.py --input ../upload/S48_FallSamples.zip --subject S48 --short-gap-max 3 --output repaired_data/S48_rerun
python scripts/run_audit.py --input repaired_data/S48_rerun --config configs/S48.json --output findings/S48_audit_repaired_rerun
python scripts/inspect_trials.py --run findings/S48_audit_repaired_rerun --selection configs/S48_repaired_selection.json --metadata configs/collection_metadata.json --cutoff-hz 1.5 --filter-order 6 --repair-mask repaired_data/S48_rerun/repaired_frames.csv --output inspections/S48_candidates_repaired_rerun
```

## Scientific boundary

The audit assumes the established Azure Kinect 32-joint XYZ/mm/30-FPS format. Original timestamps, tracking confidence, videos, and camera-to-floor calibration are unavailable. Repairs, review flags, and automatic phase suggestions support inspection; they are not validated fall labels.

<!-- MULTIACTIVITY_PHASE_UPDATE_START -->
## Multi-activity manual phase update

A10, A12, A13, and A14 manual phase notes were reconciled with this audit; the previously reviewed A11 annotations were retained. The trial manifest separates manual fall validity from repair quality and preserves unavailable or incomplete trials as explicit exclusions.

| Activity | Numeric | Detection-ready | Manual exclusions | Unavailable |
|:--|--:|--:|--:|--:|
| A10 | 5 | 1 | 4 | 0 |
| A11 | 5 | 5 | 0 | 0 |
| A12 | 5 | 4 | 1 | 0 |
| A13 | 5 | 2 | 3 | 0 |
| A14 | 4 | 4 | 0 | 1 |

Machine-readable files: `analysis_inputs/S48_real_fall_trial_manifest.csv` and `analysis_inputs/S48_all_fall_phase_annotations.json`.

A14 may end on either camera side after rotation. Use the per-trial X–Z fall direction rather than an activity-wide sign. Apparent contact remains skeleton-observed.

### Excluded or unavailable trial slots

- `S48A10T01` — Only T04 was manually confirmed as a valid A10 trial.
- `S48A10T02` — Only T04 was manually confirmed as a valid A10 trial.
- `S48A10T03` — Only T04 was manually confirmed as a valid A10 trial.
- `S48A10T05` — Only T04 was manually confirmed as a valid A10 trial.
- `S48A12T01` — Manually confirmed incomplete fall.
- `S48A13T02` — Manually confirmed incomplete fall.
- `S48A13T03` — Manually confirmed incomplete fall.
- `S48A13T05` — Manually confirmed incomplete fall.
- `S48A14T04` — Expected trial has no numeric CoM output in the audit (missing or empty source).
<!-- MULTIACTIVITY_PHASE_UPDATE_END -->
