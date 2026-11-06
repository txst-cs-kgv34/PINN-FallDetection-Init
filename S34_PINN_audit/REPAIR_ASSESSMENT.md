# S34 repair and availability assessment

The supplied archive contains 21 numeric trials out of 25 expected. The derived repair layer replaced 0 fully blank frames across 0 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

## Repaired trials

| Trial | Frames | Repaired | Fraction | Gaps | Boundary carry | Recommendation |
|:---|---:|---:|---:|---:|:---:|:---|
| None | — | 0 | 0.0% | 0 | no | no blank-row repair required |

## Missing, empty, or invalid trials

- S34A14T01: Trial is absent from the supplied archive.
- S34A14T02: Trial is absent from the supplied archive.
- S34A14T03: Trial is absent from the supplied archive.
- S34A14T05: Trial is absent from the supplied archive.

## Interpretation thresholds

- `exclude_primary_modeling`: at least 20% of frames repaired.
- `sensitivity_check_required`: 5% to less than 20% repaired.
- `manual_review_boundary_repair`: a smaller boundary carry that cannot be two-sidedly interpolated.
- `minor_repair_review`: less than 5% repaired without a boundary carry.

These are conservative audit recommendations, not validated fall labels. Manual inspection can impose stricter exclusions.

<!-- MANUAL_A11_REPAIR_UPDATE_START -->
## Phase-aware repair interpretation

All A11 trials were phase marked. Front-fall progression is toward the camera, primarily along camera Z rather than camera X.

| Trial | Phase order | Onset-contact repaired | Contact repaired | Post-fall repaired |
|:---|:---:|---:|:---:|:---:|
| S34A11T01 | pass | 0/44 (0.0%) | no | no |
| S34A11T02 | pass | 0/42 (0.0%) | no | no |
| S34A11T03 | pass | 0/40 (0.0%) | no | no |
| S34A11T04 | pass | 0/40 (0.0%) | no | no |
| S34A11T05 | pass | 0/39 (0.0%) | no | no |

**Decision:** `usable_after_axis_alignment`. Use after mapping the subject-specific horizontal fall direction to the Model B progression coordinate; do not interpret fixed camera X as the sagittal fall coordinate.
<!-- MANUAL_A11_REPAIR_UPDATE_END -->
