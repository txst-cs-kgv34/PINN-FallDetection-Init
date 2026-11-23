# Full five-seed audit record

## Completion

| Item | Expected | Found | Status |
|:--|--:|--:|:--|
| Full candidate models | 100 | 100 | PASS |
| Validation-selected evaluations | 25 | 25 | PASS |
| Matched lambda=0 evaluations | 25 | 25 | PASS |
| Candidate training histories | 100 | 100 | PASS |
| Paired selected prediction archives | 1,285 | 1,285 | PASS |
| Paired lambda=0 prediction archives | 1,285 | 1,285 | PASS |

The 100 candidates are four lambda arms x five folds x five optimization
seeds. The held-out evaluations cover 257 trials per seed and 336,380 forecast
samples across the five seeds.

## Matched-arm checks

- All four lambda arms have one identical initialization SHA-256 within each
  of the 25 seed-fold groups.
- Random-initialization validation forecast MSE is exactly identical across the
  four arms within each seed-fold.
- Candidate manifests report from-scratch training and no test access.
- Training, validation, and test subject sets are mutually disjoint in every
  candidate manifest.
- Each selection file chooses the lowest validation forecast MSE, with the
  predefined smaller-lambda tie break.
- All selected summaries report validation-only weight/checkpoint selection
  and no test access before selection.

## Numerical checks

- Total candidate-history rows: 21,864.
- Candidate history length range: 200-420 rows.
- Nonfinite numeric history entries: 0.
- Target arrays compared: `time_s`, `target_theta_rad`, and `target_x_m` in all
  1,285 selected/matched trial pairs.
- Maximum absolute selected-versus-matched target difference: 0.0.

## Selected weights

| Seed | lambda=0 | lambda=1e-4 | lambda=1e-3 | lambda=1e-2 |
|:--|--:|--:|--:|--:|
| 1 | 2 | 1 | 1 | 1 |
| 2 | 1 | 0 | 0 | 4 |
| 3 | 4 | 0 | 0 | 1 |
| 4 | 0 | 0 | 3 | 2 |
| 5 | 2 | 1 | 1 | 1 |
| **Total** | **9** | **2** | **5** | **9** |

The distribution confirms that nonzero physics is often useful but that lambda
is not stable enough to lock by modal frequency.

## Validation-to-test transfer

Among the 16 seed-folds that selected nonzero lambda, held-out normalized MSE
improved in 9 and worsened in 7. The mean held-out improvement was +1.63%, but
the median was +0.06%. The Pearson association between validation and held-out
percentage improvement was `r=0.61`. This is directionally reassuring but not
reliable enough to lock one lambda from fold frequency alone. The chosen
synthetic-data procedure therefore retains the best two eligible all-head
nonzero-physics models ranked by validation performance, followed by the
trajectory-quality gate.

## Audit boundary

This audit establishes that the result package is complete, matched, finite,
and consistent with the documented subject-level protocol. It does not prove
that CartPole physics is the uniquely correct biomechanical model, and it does
not convert a descriptive forecast advantage into statistical confirmation.

