# Findings and design decisions

## Why this is a new folder

The earlier detector-data folder was an A11-only study built around 70 real and
226 approved synthetic front falls. Editing it in place would obscure that
experiment's provenance. This new folder is explicitly A10-A14 and consumes the
new direct-physics GATE result.

## Data decision

- Use all **322** manually valid real falls marked
  `include_detection_training`, including repair-sensitive trials with an
  explicit `observed_mask`.
- Use only the **1,380** GATE-approved synthetic variants.
- Retain the **545** reviewed real ADL trajectories as negatives.
- Keep variable-length trials and postpone windowing and normalization.

## Synthetic result interpretation

The approved synthetic pool is sufficient for both mixture experiments. A10
has the lowest approval rate, but its main limitation is kinematic consistency,
not physics-residual failure. A14 has 259 accepted trajectories and does not
need retraining before this detector study.

There are no approved synthetic samples for S56-A11 or S57-A13. Therefore the
40:60 and 60:40 ratios should be enforced globally over each training fall pool,
with activity stratification when available, rather than independently inside
every subject/activity cell.

## Experimental boundary

This preparation package does not yet claim that synthetic data improve fall
detection. The next training experiment must compare the real-only, 60:40, and
40:60 conditions under identical subject folds, ADL/fall balance, optimizer,
windowing, normalization, and random seeds. All reported validation/test
metrics must use unseen real data only.

## Completed preparation result

- Integrity status: **PASS**
- Total trajectories: **2,247**
- Real ADL: **545** (four unusable ADL files excluded and documented)
- Real A10-A14 falls: **322**
- GATE-approved synthetic A10-A14 falls: **1,380**
- Approved synthetic source families: **249**
- Maximum accepted variants per family: **8**
- Synthetic source subjects: **15/15**
- Duplicate sample identifiers: **0**

| Activity | Real falls | Synthetic variants |
|:--|--:|--:|
| A10 | 60 | 209 |
| A11 | 70 | 284 |
| A12 | 69 | 338 |
| A13 | 68 | 290 |
| A14 | 55 | 259 |

The four excluded ADL trials were one empty recording and three recordings with
blank-row runs longer than the three-frame repair limit. Excluding them is the
correct outcome; no threshold should be relaxed.

## Next experiment decision

Proceed with the same compact theta/x CoM Transformer and the same five subject
folds and five seeds used in the earlier detector work. Use a batch size of 60
so the 30 fall positions support exact conditions:

- real-only: 30 real falls;
- real 60 : synthetic 40: 18 real + 12 synthetic falls;
- real 40 : synthetic 60: 12 real + 18 synthetic falls.

Each batch also contains 30 real ADL windows. Normalize all three conditions
from real training data only, select synthetic families before generator
variants, balance fall activities within each source quota, and keep validation
and testing entirely real.
