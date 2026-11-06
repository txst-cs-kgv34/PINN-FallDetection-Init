# S30 repair and availability assessment

The supplied archive contains 25 numeric trials out of 25 expected. The derived repair layer replaced 0 fully blank frames across 0 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

## Repaired trials

| Trial | Frames | Repaired | Fraction | Gaps | Boundary carry | Recommendation |
|:---|---:|---:|---:|---:|:---:|:---|
| None | — | 0 | 0.0% | 0 | no | no blank-row repair required |

## Missing, empty, or invalid trials

- None; all 25 expected trials are present and numeric.

## Interpretation thresholds

- `exclude_primary_modeling`: at least 20% of frames repaired.
- `sensitivity_check_required`: 5% to less than 20% repaired.
- `manual_review_boundary_repair`: a smaller boundary carry that cannot be two-sidedly interpolated.
- `minor_repair_review`: less than 5% repaired without a boundary carry.

These are conservative audit recommendations, not validated fall labels. Manual inspection can impose stricter exclusions.

<!-- MANUAL_A11_REPAIR_UPDATE_START -->
## Phase-aware repair interpretation

All five manually marked A11 trials contain zero repaired frames. All A11 trials were phase marked. Front-fall motion is slightly tilted toward the camera, so it has a camera-Z component in addition to camera X.

**Decision:** `usable_after_axis_alignment`. Use S30 after aligning the subject-specific horizontal fall direction with Model B's progression coordinate (for example, an X-Z rotation or projection onto the observed horizontal fall direction). Do not treat the Z component as generalization error.
<!-- MANUAL_A11_REPAIR_UPDATE_END -->
