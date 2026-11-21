# Findings — completed A11 current-data physics diagnostic

## Executive finding

Removing A10, A12, and A13 from training did **not** restore the earlier A11
physics advantage. On the same 64 strict-primary A11 trials, the model trained
with the fixed CartPole weight `0.01` had higher mean held-out error than the
paired no-physics model on all three primary endpoints:

- normalized forecast MSE was 5.62% higher;
- theta RMSE was 5.75% higher; and
- direction-aligned CoM-x RMSE was 7.03% higher.

None of the subject-level comparisons was statistically significant after
Holm correction. The correct diagnostic conclusion is therefore not that
CartPole physics is invalid. It is that multi-activity pooling alone does not
explain the reversal, and that the present coordinate/conditioning pipeline,
fixed physics weight, and optimization schedule must be calibrated before the
full V2 experiment.

## Completion and pairing audit

- 25 trained models per condition: five subject folds by five optimization
  seeds.
- 50 completed full models in total.
- 15 independent held-out subjects.
- 64 unique strict-primary A11 trials.
- 75 paired subject-seed evaluations and 320 paired trial-seed evaluations.
- All 320 paired targets matched exactly for time, theta, and x; maximum
  absolute target difference was zero.
- Folds, seeds, architecture, preprocessing, targets, and checkpoint-selection
  rule were paired. The intended training difference was present:
  `Lforecast + 0.01 × LCartPole` versus `Lforecast`.

The primary analysis first averages the five matched seeds within each subject,
leaving 15 independent paired subject values. Seeds are not treated as 75
independent people.

## Primary paired results

Positive improvement means `no physics − physics`; negative values favor no
physics.

| Held-out endpoint | Physics | No physics | Physics improvement | Relative | Subject wins P/N | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.4861 | 3.3006 | -0.1856 | -5.62% | 7/8 | 0.7788 |
| Theta RMSE | 22.8186° | 21.5777° | -1.2409° | -5.75% | 7/8 | 0.7788 |
| CoM-x RMSE | 31.9421 cm | 29.8429 cm | -2.0992 cm | -7.03% | 5/10 | 0.3210 |

The subject-bootstrap 95% intervals for mean physics improvement all included
zero: `[-0.5583, 0.1869]` for normalized MSE, `[-3.2696°, 0.6473°]` for theta
RMSE, and `[-4.3944 cm, 0.1441 cm]` for x RMSE. Thus the data do not establish a
population-level advantage for either condition, although every mean endpoint
favored no physics.

## Seed and optimization stability

Physics was more seed-sensitive than no physics.

| Endpoint | Physics across-seed SD | No-physics across-seed SD | Seeds favoring Physics |
|:--|--:|--:|--:|
| Normalized MSE | 0.6387 | 0.2548 | 3/5 |
| Theta RMSE | 2.0852° | 0.8723° | 1/5 |
| CoM-x RMSE | 2.8677 cm | 0.8871 cm | 0/5 |

The validation-selected epoch was earlier and less stable with physics:

| Selection diagnostic | Physics | No physics |
|:--|--:|--:|
| Best epoch, range | 1–294 | 29–400 |
| Best epoch, median | 77 | 114 |
| Best epoch, mean | 108.68 | 148.68 |
| Models selected at epoch 10 or earlier | 4/25 | 0/25 |
| Mean best validation forecast MSE | 1.4545 | 1.2684 |

At the selected physics checkpoints, the mean unweighted CartPole loss was
18.18 and the mean data loss was 1.88. With weight `0.01`, the physics term
contributed about 0.182 to the scalar objective, roughly 9.7% of the data-loss
magnitude. This does not reveal gradient dominance, because the residual uses
second derivatives; V2 should log per-loss gradient norms.

## Residual agreement is not forecast improvement

Physics training reduced the post-hoc angular residual RMSE from 15.97 to 13.16
(-17.6%) and the horizontal residual RMSE from 475.87 to 14.09 (-97.0%), while
trajectory error became worse. This is strong evidence that the optimizer can
satisfy the implemented equations without improving held-out CoM forecasts.

The no-physics controller coordinates are unsupervised latent values, so their
very large horizontal residual is not a fair physiological comparison. The
residual result is descriptive only; the trajectory endpoints above remain the
primary evidence.

## What the A11 isolation test resolved

The earlier unified current-data A11 subset favored no physics by 18.40% on
normalized MSE, 10.46% on theta RMSE, and 10.86% on x RMSE. In this A11-only
diagnostic, those gaps narrowed to 5.62%, 5.75%, and 7.03%, respectively, but
did not change sign.

The absolute physics results were similar between the unified A11 subset and
the A11-only run, while the no-physics A11-only result was weaker. Isolation
therefore mostly removed useful cross-activity transfer from the baseline; it
did not repair physics. Multi-activity sharing may contribute to the size of
the gap, but it is not the root cause.

The older full-fall A11 Model B result is not a direct replication of this
diagnostic. It used 70 accepted trials and a mixed legacy-pole/audit conversion,
whereas the current experiment uses 64 strict-primary trials from the unified
Physics-Ready pipeline. The six omitted trials are S48A11T01, S48A11T02,
S48A11T05, S56A11T01, S56A11T03, and S56A11T04. The current architecture also
adds activity and observed fall-direction conditioning. These linked changes
mean the earlier favorable result cannot be used to attribute the present
reversal to activity pooling.

## Consequence for V2

Do not run the full V2 with a fixed `0.01` residual weight. Revise it as follows:

1. **Use activity-defined physics coordinates.** Route A10/A11 through the
   signed sagittal body axis and A12/A13 through the signed frontal body axis.
   Do not condition a forecast on the observed onset-to-contact direction,
   because that vector uses future trajectory information. Use the known
   activity/direction label or infer direction only from the context window.
2. **Retain shared representation but separate physical heads.** Keep one
   A10–A13 encoder/trunk, with activity-specific controller/residual heads and
   separately logged angular and horizontal residual components. Keep A14 in
   its separate CartPole-plus-yaw model.
3. **Warm-start and ramp physics.** Train the forecast objective first, branch
   paired runs from the same validation-selected data-only checkpoint, and
   increase the residual weight gradually. This directly targets the early
   checkpoint and high seed-variance behavior seen here.
4. **Tune weight only on validation data.** Include `0`, `1e-4`, `1e-3`, and
   `1e-2` as the first coarse candidates per activity/head. Select without test
   access, then confirm the selected nonzero candidate over all five seeds.
5. **Normalize residual heads.** Use training-fold-only scales (or an
   equivalent nondimensionalization) so the angular and horizontal equations
   have controlled contributions. Log scalar loss shares and gradient norms.
6. **Preserve the 64-trial strict-primary set.** Do not re-admit excluded trials
   merely to reproduce the older positive result. Trial-set sensitivity can be
   a separate, explicitly labeled analysis.

The safest next gate is a small A11 V2 calibration on these same 64 trials. A
nonzero validation-selected weight should proceed to the five-seed confirmation
only if it improves forecast error without producing the current instability.
After that gate, run the unified A10–A13 V2 and the separate A14 rotation V2.

## Recommended report statement

> In a paired five-seed, five-fold A11-only diagnostic over 15 held-out
> subjects, the fixed-weight CartPole residual reduced equation residuals but
> did not improve trajectory forecasting. Mean normalized MSE, angular RMSE,
> and horizontal CoM RMSE were 5.62%, 5.75%, and 7.03% higher with physics,
> respectively, with no Holm-adjusted subject-level comparison below 0.05.
> Removing multi-activity pooling therefore did not recover the earlier A11
> advantage; V2 requires activity-defined coordinates, activity-specific
> physical heads, staged optimization, and validation-only weight selection.
