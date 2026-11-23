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
