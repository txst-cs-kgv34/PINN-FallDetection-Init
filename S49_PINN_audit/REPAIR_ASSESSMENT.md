# S49 repair and availability assessment

The supplied archive contains 23 numeric trials out of 25 expected. The derived repair layer replaced 55 fully blank frames across 14 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

## Repaired trials

| Trial | Frames | Repaired | Fraction | Gaps | Boundary carry | Recommendation |
|:---|---:|---:|---:|---:|:---:|:---|
| S49A11T01 | 101 | 41 | 40.6% | 4 | yes | exclude_primary_modeling |
| S49A13T01 | 99 | 5 | 5.1% | 4 | no | sensitivity_check_required |
| S49A11T05 | 189 | 5 | 2.6% | 3 | no | minor_repair_review |
| S49A11T04 | 180 | 2 | 1.1% | 1 | no | minor_repair_review |
| S49A14T02 | 104 | 1 | 1.0% | 1 | no | minor_repair_review |
| S49A14T03 | 116 | 1 | 0.9% | 1 | no | minor_repair_review |

## Missing, empty, or invalid trials

- S49A11T03: Trial is absent from the supplied archive.
- S49A12T01: Trial is absent from the supplied archive.

## Interpretation thresholds

- `exclude_primary_modeling`: at least 20% of frames repaired.
- `sensitivity_check_required`: 5% to less than 20% repaired.
- `manual_review_boundary_repair`: a smaller boundary carry that cannot be two-sidedly interpolated.
- `minor_repair_review`: less than 5% repaired without a boundary carry.

These are conservative audit recommendations, not validated fall labels. Manual inspection can impose stricter exclusions.

<!-- MANUAL_A11_REPAIR_UPDATE_START -->
## Phase-aware repair interpretation

A11T01 is an incomplete fall and should be ignored. A11T03 is absent. A11T02, A11T04, and A11T05 were phase marked.

| Trial | Phase order | Onset-contact repaired | Contact repaired | Post-fall repaired |
|:---|:---:|---:|:---:|:---:|
| S49A11T02 | pass | 0/49 (0.0%) | no | no |
| S49A11T04 | pass | 2/34 (5.9%) | no | no |
| S49A11T05 | pass | 3/45 (6.7%) | no | no |

**Decision:** `three_trials_usable`. Exclude A11T01 and the absent A11T03. Use only the three strictly validated marked trials: T02, T04, and T05.
<!-- MANUAL_A11_REPAIR_UPDATE_END -->
