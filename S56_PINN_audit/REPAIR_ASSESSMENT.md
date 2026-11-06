# S56 repair and availability assessment

The supplied archive contains 24 numeric trials out of 25 expected. The derived repair layer replaced 391 fully blank frames across 50 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

## Repaired trials

| Trial | Frames | Repaired | Fraction | Gaps | Boundary carry | Recommendation |
|:---|---:|---:|---:|---:|:---:|:---|
| S56A11T04 | 176 | 78 | 44.3% | 4 | no | exclude_primary_modeling |
| S56A14T05 | 134 | 58 | 43.3% | 3 | no | exclude_primary_modeling |
| S56A11T01 | 191 | 57 | 29.8% | 14 | no | exclude_primary_modeling |
| S56A10T05 | 178 | 49 | 27.5% | 5 | no | exclude_primary_modeling |
| S56A10T04 | 154 | 33 | 21.4% | 5 | no | exclude_primary_modeling |
| S56A11T03 | 192 | 40 | 20.8% | 3 | no | exclude_primary_modeling |
| S56A14T04 | 160 | 30 | 18.8% | 2 | no | sensitivity_check_required |
| S56A11T02 | 156 | 14 | 9.0% | 2 | no | sensitivity_check_required |
| S56A11T05 | 197 | 13 | 6.6% | 1 | no | sensitivity_check_required |
| S56A10T03 | 141 | 5 | 3.5% | 2 | yes | manual_review_boundary_repair |
| S56A12T05 | 220 | 5 | 2.3% | 1 | no | minor_repair_review |
| S56A12T01 | 221 | 4 | 1.8% | 3 | no | minor_repair_review |
| S56A10T01 | 97 | 1 | 1.0% | 1 | no | minor_repair_review |
| S56A14T01 | 193 | 1 | 0.5% | 1 | no | minor_repair_review |
| S56A12T02 | 214 | 1 | 0.5% | 1 | no | minor_repair_review |
| S56A12T03 | 220 | 1 | 0.5% | 1 | no | minor_repair_review |
| S56A12T04 | 230 | 1 | 0.4% | 1 | no | minor_repair_review |

## Missing, empty, or invalid trials

- S56A10T02: Source CSV is empty and no complete trial was synthesized.

## Interpretation thresholds

- `exclude_primary_modeling`: at least 20% of frames repaired.
- `sensitivity_check_required`: 5% to less than 20% repaired.
- `manual_review_boundary_repair`: a smaller boundary carry that cannot be two-sidedly interpolated.
- `minor_repair_review`: less than 5% repaired without a boundary carry.

These are conservative audit recommendations, not validated fall labels. Manual inspection can impose stricter exclusions.

<!-- MANUAL_A11_REPAIR_UPDATE_START -->
## Phase-aware repair interpretation

All A11 trials were phase marked. Repairs between fall onset and apparent contact were judged acceptable during manual review; T05 has more visible repair involvement but a trajectory consistent with the other trials and is retained.

| Trial | Phase order | Onset-contact repaired | Contact repaired | Post-fall repaired |
|:---|:---:|---:|:---:|:---:|
| S56A11T01 | pass | 5/41 (12.2%) | no | no |
| S56A11T02 | pass | 11/32 (34.4%) | no | no |
| S56A11T03 | pass | 9/43 (20.9%) | no | no |
| S56A11T04 | pass | 6/44 (13.6%) | no | no |
| S56A11T05 | pass | 13/69 (18.8%) | no | no |

**Decision:** `usable_with_repair_sensitivity_check`. Retain all five trials with repair masks. Report a sensitivity analysis because some onset-to-contact intervals contain repaired rows; retain T05 as requested rather than excluding it solely for repair count.
<!-- MANUAL_A11_REPAIR_UPDATE_END -->
