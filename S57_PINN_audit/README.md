# S57 PINN audit: repaired findings and manual inspection package

This directory audits 25 S57 Azure Kinect skeleton trials and stops before PINN
training. S57 is recorded as male, 180 lb, 5 ft 8 in.

## Start here

- `findings/S57_audit_repaired/FINDINGS.md`: findings from the repaired numeric data.
- `inspections/S57_candidates_repaired/INSPECT.html`: offline, repair-aware skeleton player.
- `repaired_data/S57/repair_manifest.json`: exact gaps, methods, and boundary frames.
- `repaired_data/S57/repaired_frames.csv`: frame-level repair mask.
- `analysis_inputs/S57_automatic_phase_suggestions_repaired.json`: provisional candidates, not labels.
- `analysis_inputs/S57_phase_notes.json`: user-supplied manual A11 annotations.
- `analysis_inputs/S57_A11_phase_windows.json`: three validated model-input windows.
- `analysis_inputs/FRONTFALL_PHASE_STATUS.md`: exclusions and quality-flag summary.

The player marks repaired frames in purple and raw audit flags in peach. Short
fully blank gaps of at most 3 frames (0.10 s at 30 Hz) were forward-filled from
the previous valid row. Longer internal gaps were linearly interpolated for each
coordinate. A trailing gap has no future boundary and therefore uses the last
valid row, but is explicitly marked as a boundary carry. Original files were not
modified.

## Important repair findings

One hundred thirty-nine frames in 14 gaps were repaired. Exclude S57A12T04
from modeling: 80/158 frames (50.6%) were repaired, including a 78-frame
trailing carry. Also exclude S57A13T01 from primary modeling: 38/165 frames
(23.0%) were repaired, including a 21-frame trailing carry. S57A10T03 has 12
repaired frames (6.0%) and S57A13T02 has 6 (4.9%); retain only with sensitivity
checks. All five A11 front-fall trials have zero blank-row repairs and are ready
for manual phase review, subject to the other audit flags.

## Manual phases

Manual A11 phases are complete and validated for T03–T05. The user identified
T01 and T02 as incomplete, so they are explicitly excluded from the A11
model-ready selection. Three selected phase frames overlap raw audit review
flags; see `analysis_inputs/S57_A11_phase_quality_flags.csv`. Apparent contact
is a skeleton observation, not force-confirmed contact.

## Reproduce the repaired workflow

```bash
python -m pip install -r requirements.txt
python scripts/repair_blank_rows.py --input ../upload/S57_FallSamples.zip --subject S57 --short-gap-max 3 --output repaired_data/S57_rerun
python scripts/run_audit.py --input repaired_data/S57_rerun --config configs/S57.json --output findings/S57_audit_repaired_rerun
python scripts/inspect_trials.py --run findings/S57_audit_repaired_rerun --selection configs/S57_repaired_selection.json --metadata configs/collection_metadata.json --cutoff-hz 1.5 --filter-order 6 --repair-mask repaired_data/S57_rerun/repaired_frames.csv --output inspections/S57_candidates_repaired_rerun
```

## Scientific boundary

The audit assumes the established Azure Kinect 32-joint XYZ/mm/30-FPS format.
Original timestamps, tracking confidence, videos, and camera-to-floor
calibration are unavailable. Repair masks, review flags, and automatic phase
suggestions support inspection; they are not validated fall labels.

<!-- MULTIACTIVITY_PHASE_UPDATE_START -->
## Multi-activity manual phase update

A10, A12, A13, and A14 manual phase notes were reconciled with this audit; the previously reviewed A11 annotations were retained. The trial manifest separates manual fall validity from repair quality and preserves unavailable or incomplete trials as explicit exclusions.

| Activity | Numeric | Detection-ready | Manual exclusions | Unavailable |
|:--|--:|--:|--:|--:|
| A10 | 5 | 3 | 2 | 0 |
| A11 | 5 | 3 | 2 | 0 |
| A12 | 5 | 5 | 0 | 0 |
| A13 | 5 | 5 | 0 | 0 |
| A14 | 5 | 5 | 0 | 0 |

Machine-readable files: `analysis_inputs/S57_real_fall_trial_manifest.csv` and `analysis_inputs/S57_all_fall_phase_annotations.json`.

A14 may end on either camera side after rotation. Use the per-trial X–Z fall direction rather than an activity-wide sign. Apparent contact remains skeleton-observed.

### Excluded or unavailable trial slots

- `S57A10T01` — Manually confirmed incomplete fall.
- `S57A10T04` — Manually confirmed incomplete fall.
- `S57A11T01` — Manually confirmed incomplete fall in the existing A11 review.
- `S57A11T02` — Manually confirmed incomplete fall in the existing A11 review.
<!-- MULTIACTIVITY_PHASE_UPDATE_END -->
