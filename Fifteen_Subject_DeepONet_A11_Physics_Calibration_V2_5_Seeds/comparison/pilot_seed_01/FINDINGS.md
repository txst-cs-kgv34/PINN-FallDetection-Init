# A11 physics calibration V2 — one-seed pilot

Positive improvement means `existing no physics − selected V2`; positive values favor V2.

| Metric | Selected V2 | Existing no physics | V2 improvement | Relative | Subject wins V2/N | Holm p |
|:--|--:|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.4014 | 3.4014 | +0.0000 | +0.00% | 0/0 | 1.0000 |
| Theta RMSE (degrees) | 21.4531° | 21.4531° | +0.0000° | +0.00% | 0/0 | 1.0000 |
| CoM-x RMSE (cm) | 30.4418 cm | 30.4418 cm | +0.0000 cm | +0.00% | 0/0 | 1.0000 |

Selected weight counts across fold-seed models: `{'0.0': 5}`.

Weights and checkpoints were selected only from the validation subject. Test subjects were evaluated after selection.

The λ=0 option is the already completed no-physics checkpoint; it was not retrained.

## Interpretation

This is not evidence that the selected V2 and no-physics models are two
independently equivalent models. They are the same five no-physics checkpoints:
all folds selected `λ=0`, so all 15 held-out subject metrics tie exactly and the
reported p-values of 1.0 are mechanical.

Every nonzero weight (`1e-4`, `1e-3`, and `1e-2`) retained epoch 0—the warm
start—as its best validation checkpoint in all five folds. The first fine-tune
epoch increased mean validation MSE from 1.3176 to approximately 1.6132
(+22.4%), with almost identical changes across weights. At that first epoch the
effective ramped weights were only `1e-6`, `1e-5`, and `1e-4`; therefore the
immediate degradation is dominated by restarting data optimization, not by a
large physics gradient.

At epoch 180, `λ=0.01` reduced mean normalized horizontal residual loss from
16.0828 to 5.8737 (-63.5%) and angular residual loss from 0.3844 to 0.3536
(-8.0%). Its mean validation MSE nevertheless rose to 2.3717 (+80.0% from the
warm start). The residual was active, but no post-warm-start checkpoint
improved validation forecasting.

## Decision

Do not run seeds 2–5 for this warm-start design. The next controlled pilot
should initialize `λ=0` and all nonzero normalized/ramped candidates from the
same original random model state and train them under the same schedule. That
removes the confound created by continuing from an already
validation-selected no-physics checkpoint.
