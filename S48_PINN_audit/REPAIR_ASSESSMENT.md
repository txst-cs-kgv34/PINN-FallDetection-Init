# S48 repair and availability assessment

The supplied archive contains 24 numeric trials out of 25 expected. The derived repair layer replaced 329 fully blank frames across 40 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

## Repaired trials

| Trial | Frames | Repaired | Fraction | Gaps | Boundary carry | Recommendation |
|:---|---:|---:|---:|---:|:---:|:---|
| S48A11T05 | 130 | 57 | 43.8% | 2 | yes | exclude_primary_modeling |
| S48A11T01 | 186 | 58 | 31.2% | 2 | no | exclude_primary_modeling |
| S48A10T01 | 166 | 49 | 29.5% | 6 | yes | exclude_primary_modeling |
| S48A11T02 | 170 | 50 | 29.4% | 5 | no | exclude_primary_modeling |
| S48A10T05 | 142 | 35 | 24.6% | 7 | no | exclude_primary_modeling |
| S48A12T02 | 96 | 16 | 16.7% | 3 | yes | sensitivity_check_required |
| S48A11T04 | 138 | 21 | 15.2% | 1 | no | sensitivity_check_required |
| S48A14T01 | 158 | 14 | 8.9% | 5 | no | sensitivity_check_required |
| S48A14T03 | 185 | 10 | 5.4% | 2 | no | sensitivity_check_required |
| S48A11T03 | 148 | 7 | 4.7% | 1 | no | minor_repair_review |
| S48A10T04 | 191 | 6 | 3.1% | 1 | no | minor_repair_review |
| S48A12T05 | 163 | 3 | 1.8% | 2 | no | minor_repair_review |
| S48A12T03 | 173 | 3 | 1.7% | 3 | no | minor_repair_review |

## Missing, empty, or invalid trials

- S48A14T04: Audit input check failed: Expected at least two frames and 96 columns, got (1, 96)

## Interpretation thresholds

- `exclude_primary_modeling`: at least 20% of frames repaired.
- `sensitivity_check_required`: 5% to less than 20% repaired.
- `manual_review_boundary_repair`: a smaller boundary carry that cannot be two-sidedly interpolated.
- `minor_repair_review`: less than 5% repaired without a boundary carry.

These are conservative audit recommendations, not validated fall labels. Manual inspection can impose stricter exclusions.
