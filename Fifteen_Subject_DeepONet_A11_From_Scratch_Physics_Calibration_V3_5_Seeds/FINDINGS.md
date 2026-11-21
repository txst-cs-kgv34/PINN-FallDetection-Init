# Findings — A11 matched from-scratch calibration V3 seed-1 pilot

## Executive decision

The controlled seed-1 pilot **passes the gate for seeds 2–5**. This is not yet
evidence of a statistically established physics advantage. It is evidence that
the matched design behaves differently from the confounded V2 warm-start run:
validation selected a nonzero CartPole weight in four of five independently
held-out validation folds.

Selected V3 slightly improved held-out theta and CoM-x RMSE. Mean normalized
MSE was 0.75% worse because S45 had a large adverse response, even though the
normalized endpoint favored V3 for nine subjects, λ=0 for three, and tied for
three. The correct next step is the predefined five-seed confirmation.

## Completion and integrity audit

- 20/20 trained candidates: four λ arms × five folds.
- 20/20 candidate manifests, histories, selections, and final checkpoints.
- 5/5 validation selections and 5/5 matched λ=0 evaluations.
- 64 selected predictions and 64 matched λ=0 predictions.
- 4,540 training-history rows; no non-finite value.
- One unique initialization SHA-256 per fold across all four arms.
- Pre-training validation-loss range across arms: exactly zero in every fold.
- All 64 paired target trajectories matched exactly for time, theta, and x.
- Test subjects were accessed only after validation-only weight selection.

## Validation selection

Positive validation improvement means `λ=0 − selected`; positive favors the
selected arm.

| Fold | Validation subject | Selected λ | λ=0 validation MSE | Selected validation MSE | Improvement |
|---:|:---|---:|---:|---:|---:|
| 1 | S63 | 0.01 | 0.244760 | 0.208731 | +14.72% |
| 2 | S62 | 0.01 | 1.159581 | 1.142194 | +1.50% |
| 3 | S57 | 0.01 | 2.156603 | 2.119644 | +1.71% |
| 4 | S55 | 0 | 1.357246 | 1.357246 | 0.00% |
| 5 | S43 | 0.001 | 1.241864 | 1.106041 | +10.94% |

Nonzero λ was selected in 4/5 folds. The average validation improvement was
5.77% and the median was 1.71%. Fold 2 was nearly tied between `0.001` and
`0.01` (difference `0.000042`), so its exact weight should not be overread.

## Held-out trajectory comparison

Positive improvement means `matched λ=0 − selected V3`; positive favors V3.

| Endpoint | Selected V3 | Matched λ=0 | Improvement | Relative | Subject wins V3/N/tie | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.6716 | 3.6441 | -0.0275 | -0.75% | 9/3/3 | 0.4738 |
| Theta RMSE | 21.5392° | 21.7734° | +0.2342° | +1.08% | 7/5/3 | 0.5303 |
| CoM-x RMSE | 30.3499 cm | 30.6641 cm | +0.3142 cm | +1.02% | 9/3/3 | 0.4738 |

All subject-bootstrap intervals included zero. The pilot is underpowered for a
final inference because it contains one optimization seed; the p-values should
not be interpreted as proof of equivalence.

## Subject and fold heterogeneity

Three nonzero-selected folds improved mean normalized MSE, theta RMSE, and
CoM-x RMSE on their held-out subjects. Fold 3 was the exception:

| Fold | Selected λ | Δ normalized MSE | Δ theta RMSE | Δ CoM-x RMSE | Interpretation |
|---:|---:|---:|---:|---:|:--|
| 1 | 0.01 | -0.0412 | -0.502° | -0.402 cm | V3 better |
| 2 | 0.01 | -0.2895 | -0.395° | -2.045 cm | V3 better |
| 3 | 0.01 | +0.5603 | +0.116° | +1.286 cm | λ=0 better in mean |
| 4 | 0 | 0 | 0 | 0 | exact tie by construction |
| 5 | 0.001 | -0.0922 | -0.390° | -0.409 cm | V3 better |

Here negative Δ means selected V3 has lower error. Fold 3 contains S45, the
dominant adverse outlier: compared with λ=0, S45 worsened by 1.928 normalized-
MSE units, 1.799°, and 4.755 cm. The other two fold-3 subjects, S56 and S59,
improved on normalized MSE. Across all subjects, the largest normalized-MSE
gains occurred for S48 (+0.595), S44 (+0.272), S46 (+0.252), and S43 (+0.189).

## Physics and optimization diagnostics

Across all 15 subjects, horizontal residual RMSE decreased from 452.17 to
392.28 (13.2%), while angular residual RMSE was essentially unchanged
(16.33 to 16.35). This overall horizontal percentage is distorted by the very
large S49 residual in the λ=0-selected fold. Restricting descriptively to the
12 subjects whose folds selected nonzero physics, horizontal residual RMSE
decreased 44.5%, while angular residual RMSE changed by only -0.11% in the
unfavorable direction.

At the selected checkpoints, the effective physics/data gradient ratios were
modest:

- λ=0.01 folds: 0.0258–0.0569 at the selected epoch; median history ratios
  0.0235–0.0307; maximum transient ratios 0.349–0.363.
- λ=0.001 fold: 0.00413 at the selected epoch; median 0.00427; maximum 0.0662.

Thus the physics term influenced optimization without persistently dominating
the forecast gradient. This is materially healthier than using an uncalibrated
fixed loss solely because it reduces equation residuals.

## Relationship to the earlier results

The pilot does not prove or disprove the earlier 70-trial Model B finding. It
does show why the V2 failure should not have been interpreted as evidence that
physics was harmful: after removing the continuation confound, validation
again preferred nonzero physics in most folds and the majority of non-tied
subjects improved on two of the three primary endpoints.

The present effect is smaller and more heterogeneous than the earlier 12/15
result. That difference remains scientifically plausible because the current
experiment uses a 64-trial strict-primary set, unified Physics-Ready processing,
and current conditioning.

## Decision for the full run

Run seeds 2–5 with no protocol changes:

```bash
./run_on_mac.sh full mps
```

The existing seed-1 models will be skipped. After completion, determine:

1. how often each λ is selected across all 25 fold-seed models;
2. whether theta and CoM-x gains remain positive after seed averaging;
3. whether the S45 penalty recurs or is seed-specific;
4. whether normalized MSE retains a majority of subject wins despite its
   sensitivity to large outliers; and
5. whether subject-level bootstrap intervals and Holm-adjusted tests support a
   stable benefit.

Do not change the weight grid, folds, ramp, or early-stopping rule between the
pilot and confirmation.

## Advisor-facing statement

> The earlier 12/15 advantage was a real descriptive result for the original
> matched pipeline, with adjusted p-values reported above 0.05. A later
> warm-start calibration was methodologically confounded. In the corrected
> matched-from-scratch pilot, initialization, optimizer, schedule, and data
> order were identical across λ values. Validation selected nonzero physics in
> four of five folds. Held-out theta and CoM-x RMSE improved by about 1%, while
> normalized MSE was 0.75% worse because of one large S45 penalty despite nine
> subject wins. We are therefore completing the planned five-seed confirmation
> before making a final claim.
