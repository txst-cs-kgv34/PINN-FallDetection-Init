# S58 repair and availability assessment

The supplied archive contains 24 numeric trials out of 25 expected. The derived repair layer replaced 2087 fully blank frames across 57 gaps. Original files were not modified. Short gaps of 1–3 frames use the preceding valid row; longer internal gaps use per-coordinate linear interpolation; boundary gaps use the nearest valid row. Entire missing or empty trials are never synthesized.

## Repaired trials

| Trial | Frames | Repaired | Fraction | Gaps | Boundary carry | Recommendation |
|:---|---:|---:|---:|---:|:---:|:---|
| S58A13T04 | 137 | 119 | 86.9% | 3 | yes | exclude_primary_modeling |
| S58A10T02 | 129 | 102 | 79.1% | 1 | yes | exclude_primary_modeling |
| S58A11T05 | 149 | 112 | 75.2% | 2 | yes | exclude_primary_modeling |
| S58A10T04 | 223 | 164 | 73.5% | 2 | yes | exclude_primary_modeling |
| S58A10T01 | 134 | 97 | 72.4% | 2 | yes | exclude_primary_modeling |
| S58A12T01 | 134 | 92 | 68.7% | 1 | yes | exclude_primary_modeling |
| S58A11T01 | 159 | 108 | 67.9% | 1 | yes | exclude_primary_modeling |
| S58A11T03 | 161 | 107 | 66.5% | 2 | yes | exclude_primary_modeling |
| S58A12T02 | 171 | 109 | 63.7% | 2 | yes | exclude_primary_modeling |
| S58A14T03 | 179 | 113 | 63.1% | 1 | yes | exclude_primary_modeling |
| S58A11T02 | 210 | 121 | 57.6% | 1 | yes | exclude_primary_modeling |
| S58A11T04 | 190 | 107 | 56.3% | 2 | yes | exclude_primary_modeling |
| S58A14T02 | 185 | 104 | 56.2% | 2 | yes | exclude_primary_modeling |
| S58A10T03 | 200 | 108 | 54.0% | 1 | yes | exclude_primary_modeling |
| S58A14T04 | 213 | 104 | 48.8% | 1 | yes | exclude_primary_modeling |
| S58A14T01 | 182 | 86 | 47.3% | 3 | yes | exclude_primary_modeling |
| S58A14T05 | 169 | 72 | 42.6% | 6 | yes | exclude_primary_modeling |
| S58A12T03 | 185 | 62 | 33.5% | 2 | no | exclude_primary_modeling |
| S58A12T04 | 228 | 72 | 31.6% | 5 | no | exclude_primary_modeling |
| S58A13T03 | 161 | 46 | 28.6% | 3 | no | exclude_primary_modeling |
| S58A13T01 | 154 | 23 | 14.9% | 2 | no | sensitivity_check_required |
| S58A13T02 | 221 | 26 | 11.8% | 6 | no | sensitivity_check_required |
| S58A13T05 | 241 | 26 | 10.8% | 5 | no | sensitivity_check_required |
| S58A12T05 | 166 | 7 | 4.2% | 1 | no | minor_repair_review |

## Missing, empty, or invalid trials

- S58A10T05: Trial is absent from the supplied archive.

## Interpretation thresholds

- `exclude_primary_modeling`: at least 20% of frames repaired.
- `sensitivity_check_required`: 5% to less than 20% repaired.
- `manual_review_boundary_repair`: a smaller boundary carry that cannot be two-sidedly interpolated.
- `minor_repair_review`: less than 5% repaired without a boundary carry.

These are conservative audit recommendations, not validated fall labels. Manual inspection can impose stricter exclusions.
