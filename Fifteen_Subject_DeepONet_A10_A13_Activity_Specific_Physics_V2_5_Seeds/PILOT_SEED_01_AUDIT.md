# Seed-1 audit record

## Completion

- Candidate models: 20/20.
- Validation-selected fold models: 5/5.
- Matched lambda=0 fold models: 5/5.
- Held-out subjects: 15.
- Held-out trials: 257.
- Training-history rows: 4,591.
- Nonfinite training-history values: 0.

## Matched-arm checks

For each fold, all four lambda arms have one identical initialization SHA-256
and exactly equal pre-training validation forecast loss. Selected V2 and
matched lambda=0 evaluations have exactly equal `time_s`, `target_theta_rad`,
and `target_x_m` arrays for every held-out trial.

## Selected weights

| Fold | Validation subjects | Selected lambda | Best epoch |
|:--|:--|--:|--:|
| 1 | S44, S62 | 1e-4 | 320 |
| 2 | S57, S46 | 1e-2 | 124 |
| 3 | S55, S48 | 1e-3 | 121 |
| 4 | S45, S59 | 0 | 39 |
| 5 | S34, S32 | 0 | 62 |

## Interpretation boundary

This audit establishes protocol execution and pairing integrity. It does not
establish that physics improves prediction. Seed 1 is exploratory; the full
five-seed result is required for the planned conclusion.
