# Findings — completed A11 physics calibration V2 seed-1 pilot

## Executive finding

The warm-start calibration did not pass its gate for seeds 2–5. All five folds
selected the unchanged no-physics checkpoint (`λ=0`, epoch 0). Every nonzero
candidate—`1e-4`, `1e-3`, and `1e-2`—also had its best validation value at epoch
0 in every fold.

The selected V2 policy is therefore exactly the existing seed-1 no-physics
model, not a new physics-improved model. Do not run the remaining four seeds for
this warm-start design.

## Completion and protocol audit

- 15/15 planned nonzero candidate fine-tunes completed: three weights by five
  folds.
- 5/5 validation-only weight selections completed.
- 64 held-out trial predictions were produced after selection.
- All five folds selected `λ=0` before test evaluation.
- Candidate folders contain training and validation histories but no candidate
  test metrics.
- Selected test targets matched the existing no-physics targets exactly.
- The archive contains all 15 training histories, selections, and final
  candidate states.

The selection protocol worked as intended: when physics did not improve the
validation subject, it protected the test evaluation by retaining the baseline.

## Selected-policy comparison

Because every fold selected the existing baseline, all held-out results tie
exactly.

| Seed-1 endpoint | Selected V2 | Existing no physics | Difference |
|:--|--:|--:|--:|
| Normalized forecast MSE | 3.4014 | 3.4014 | 0.0000 |
| Theta RMSE | 21.4531° | 21.4531° | 0.0000° |
| CoM-x RMSE | 30.4418 cm | 30.4418 cm | 0.0000 cm |

The 15 subject ties and p-values of 1.0 are mechanical consequences of using
the same checkpoints. They are not evidence that two independently trained
models are statistically equivalent.

## Candidate validation behavior

| Target weight | Folds improving over epoch 0 | Mean best epoch | Mean final validation MSE | Final change from warm start |
|--:|--:|--:|--:|--:|
| `1e-4` | 0/5 | 0 | 2.5852 | +96.2% |
| `1e-3` | 0/5 | 0 | 2.5344 | +92.3% |
| `1e-2` | 0/5 | 0 | 2.3717 | +80.0% |

The mean warm-start validation MSE was 1.3176. After only one fine-tune epoch,
it increased to approximately 1.6132 (+22.4%) for all three candidates. Their
effective weights at that point were only `1e-6`, `1e-5`, and `1e-4`, and their
validation changes were nearly identical. This shows that the immediate loss of
generalization came mainly from restarting training from a checkpoint already
selected at its validation minimum, rather than from a large physics term.

## Residual and gradient diagnostics

The weight ramp behaved as configured and reached each target by epoch 100.
The mean effective physics/data gradient ratio remained weight-dependent:

| Target weight | Median effective gradient ratio | Maximum effective gradient ratio |
|--:|--:|--:|
| `1e-4` | 0.0009 | 0.0132 |
| `1e-3` | 0.0081 | 0.1068 |
| `1e-2` | 0.0544 | 0.5879 |

For `λ=0.01`, the mean normalized horizontal residual loss fell from 16.0828
to 5.8737 (-63.5%), while the angular component fell from 0.3844 to 0.3536
(-8.0%). Thus normalized physics was active and reduced equation residuals,
but no later checkpoint recovered the warm-start validation forecast.

This repeats the central observation from the earlier diagnostic: lower
CartPole residual does not automatically imply better held-out trajectory
prediction.

## What this pilot can and cannot conclude

The pilot validly concludes that **adding further training to the already
validation-selected no-physics checkpoint is not useful under this schedule**.
It does not isolate the causal effect of the physics residual from the effect of
resuming data optimization with a fresh AdamW state. There was no matched
continued-training `λ=0` arm, and the frozen baseline began at the validation
minimum by construction.

Therefore:

- do not interpret the 5/5 `λ=0` selections as definitive proof that CartPole
  physics cannot help A11;
- do not run seeds 2–5 merely to reproduce the same warm-start confound; and
- do not choose a nonzero weight by examining held-out test performance.

## Recommended next experiment

Replace the warm-start design with a from-scratch matched calibration:

1. Create the same initial model state for `λ=0`, `1e-4`, `1e-3`, and `1e-2`
   within each fold and seed.
2. Use the same optimizer, learning rate, batches, maximum epochs, and patience
   for every weight.
3. Preserve residual normalization (`rθ/(g/l)` and `rx/g`) and the 100-epoch
   ramp for nonzero weights.
4. Select the weight using only the validation subject, then evaluate test
   subjects once.
5. Run seed 1 as a new pilot before authorizing seeds 2–5.

The existing no-physics result may remain the external reference, but the new
pilot should also train a matched `λ=0` arm so optimizer continuation and
initialization are controlled exactly.

Only after this corrected A11 calibration should we decide whether to proceed
to the activity-defined, activity-specific A10–A13 V2 model.

## Recommended report statement

> In the seed-1 warm-start calibration, validation selected the unchanged
> no-physics checkpoint in all five subject folds. No nonzero physics candidate
> improved validation forecast MSE beyond epoch 0, although `λ=0.01` reduced the
> normalized horizontal residual loss by 63.5%. Because resuming optimization
> from an already validation-selected checkpoint immediately degraded
> validation performance almost identically across weights, the pilot does not
> cleanly isolate the physics effect. The remaining seeds were not authorized;
> the next calibration will train all weights from matched initial states.

