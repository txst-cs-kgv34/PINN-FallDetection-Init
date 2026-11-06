# S59 repair and availability assessment

The supplied archive contains 21 numeric trials out of 25 expected. The derived repair layer replaced 9 fully blank frames across 4 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

## Repaired trials

| Trial | Frames | Repaired | Fraction | Gaps | Boundary carry | Recommendation |
|:---|---:|---:|---:|---:|:---:|:---|
| S59A10T01 | 189 | 4 | 2.1% | 1 | no | minor_repair_review |
| S59A10T03 | 231 | 3 | 1.3% | 1 | no | minor_repair_review |
| S59A13T01 | 171 | 1 | 0.6% | 1 | no | minor_repair_review |
| S59A10T02 | 224 | 1 | 0.4% | 1 | no | minor_repair_review |

## Missing, empty, or invalid trials

- S59A14T02: Trial is absent from the supplied archive.
- S59A14T03: Trial is absent from the supplied archive.
- S59A14T04: Trial is absent from the supplied archive.
- S59A14T05: Trial is absent from the supplied archive.

## Interpretation thresholds

- `exclude_primary_modeling`: at least 20% of frames repaired.
- `sensitivity_check_required`: 5% to less than 20% repaired.
- `manual_review_boundary_repair`: a smaller boundary carry that cannot be two-sidedly interpolated.
- `minor_repair_review`: less than 5% repaired without a boundary carry.

These are conservative audit recommendations, not validated fall labels. Manual inspection can impose stricter exclusions.

<!-- MANUAL_A11_REPAIR_UPDATE_START -->
## Phase-aware repair interpretation

All A11 trials were phase marked.

| Trial | Phase order | Onset-contact repaired | Contact repaired | Post-fall repaired |
|:---|:---:|---:|:---:|:---:|
| S59A11T01 | pass | 0/37 (0.0%) | no | no |
| S59A11T02 | pass | 0/42 (0.0%) | no | no |
| S59A11T03 | pass | 0/35 (0.0%) | no | no |
| S59A11T04 | pass | 0/41 (0.0%) | no | no |
| S59A11T05 | pass | 0/41 (0.0%) | no | no |

**Decision:** `usable`. Usable for the planned A11 analysis, subject to the existing audit flags and the provisional nature of skeleton-observed contact.
<!-- MANUAL_A11_REPAIR_UPDATE_END -->
