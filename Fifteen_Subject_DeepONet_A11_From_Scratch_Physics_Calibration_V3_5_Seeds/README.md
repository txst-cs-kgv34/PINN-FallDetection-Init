# Fifteen-subject A11 matched from-scratch physics calibration V3

This experiment is the controlled follow-up to the A11 warm-start calibration
pilot. It trains four CartPole-loss weights from the same original model state
inside every seed-fold:

`λ = {0, 1e-4, 1e-3, 1e-2}`

The four arms have the same A11 data, model, initialization, batch order,
AdamW optimizer, learning rate, maximum epochs, minimum training period,
patience, validation subject, and checkpoint rule. Only the target physics
weight differs. Nonzero weights ramp linearly over the first 100 epochs; all
arms have the same 100-epoch minimum training period.

## Final five-seed result

The complete matched experiment does **not** establish a forecasting advantage
for CartPole physics on the current 64-trial A11 Physics-Ready pipeline.

| Endpoint | Selected V3 | Matched λ=0 | Relative physics improvement | Subject wins V3/N | Holm p |
|:--|--:|--:|--:|--:|--:|
| Normalized forecast MSE | 3.4892 | 3.3313 | -4.74% | 7/8 | 1.0000 |
| Theta RMSE | 21.9119° | 21.6521° | -1.20% | 10/5 | 1.0000 |
| CoM-x RMSE | 30.3129 cm | 29.8412 cm | -1.58% | 8/7 | 1.0000 |

Positive improvement would favor selected V3; all three mean improvements are
negative. Validation nevertheless selected nonzero physics in 17/25 fold-seed
models (`1e-4`: 3, `1e-3`: 7, `1e-2`: 7), showing that preference on one
validation subject did not reliably transfer to three unseen test subjects.

Physics reduced horizontal residual RMSE by 41.2%, but angular residual RMSE
worsened by 6.0%. Equation agreement and trajectory generalization therefore
remain separate outcomes. The matched λ=0 model is the A11 forecasting
reference for the current pipeline.

## Why this experiment is required

The earlier full-fall Model B result and the current Physics-Ready A11 result
are not exact replications:

| Item | Earlier favorable Model B | Current calibration |
|:--|:--|:--|
| A11 trials | 70 accepted trials | 64 strict-primary trials |
| Input construction | Mixed legacy-pole and audit conversion | Unified Physics-Ready pipeline |
| Conditioning | Earlier Model B inputs | Adds current activity/direction conditioning |
| Question | Physics vs matched no physics in the earlier pipeline | Does CartPole regularization help the current pipeline? |

The earlier comparison found lower descriptive errors for physics on 12 of 15
subjects for all three primary outcomes. That finding is valid for its stated
pipeline. Its Holm-adjusted subject-level p-values were above 0.05, so it
should be described as a promising descriptive advantage, not proof that
physics must win after every data or architecture change.

The failed V2 warm-start pilot also did not establish that physics loses. Its
λ=0 arm was a frozen validation-optimal checkpoint, while every nonzero arm
resumed data training with a fresh optimizer. Every candidate degraded at the
first epoch, when the ramped physics weights were only 1e-6 to 1e-4. V3 removes
that continuation confound.

## Protocol

- 64 strict-primary A11 front-fall trials.
- Five grouped subject folds: 11 train, 1 validation, 3 test.
- Five deterministic optimization seeds.
- Model B DeepONet and the same delayed CartPole residual family.
- Angular residual divided by `g/l`; horizontal residual divided by `g`.
- 800 maximum epochs, AdamW, learning rate `5e-4`, weight decay `1e-6`.
- Validation-only checkpoint and λ selection; smaller λ wins an exact tie.
- Test subjects are accessed only after λ selection.
- Selected V3 is compared with the newly trained, matched λ=0 arm.

Each candidate manifest stores an SHA-256 digest of the initial state. Selection
fails if the four digests or their pre-training validation predictions differ.

## MacBook MPS commands

Place this directory beside:

- `data/processed/Fifteen_Subject_Real_Fall_Physics_Ready`
- all 15 updated `S##_PINN_audit` directories

The experiment is complete. For reproduction, run:

```bash
cd Fifteen_Subject_DeepONet_A11_From_Scratch_Physics_Calibration_V3_5_Seeds
chmod +x run.sh run_on_mac.sh
./run_on_mac.sh setup
./run_on_mac.sh validate
./run_on_mac.sh smoke mps
./run_on_mac.sh pilot mps
```

The full experiment trains 100 candidates: four λ arms × five folds × five
seeds, then evaluates the validation-selected and matched λ=0 checkpoints:

```bash
./run_on_mac.sh full mps
```

Resume/status helpers:

```bash
./run_on_mac.sh status
./run_on_mac.sh fold 3 mps 1
./run_on_mac.sh seed 1 mps
```

Completed models are skipped. Use `FORCE=1` only when intentionally replacing
an existing candidate.

## Final decision

- Do not use this A11 selected-physics V3 as evidence of improved forecasting.
- Retain matched λ=0 as the current strict-primary A11 forecasting reference.
- Retain the CartPole residual as a useful consistency constraint, not as a
  demonstrated generalization benefit in this pipeline.
- Proceed to A10–A13 only with activity-defined coordinates, activity-specific
  residual/controller heads, and validation averaged across multiple subjects
  and activities.
- Do not reuse the single-validation-subject selection rule for the next model.

## Interpretation boundaries

V3 answers whether validation-selected CartPole regularization helps the
current 64-trial A11 pipeline under a matched from-scratch design: it does not
on the predefined held-out forecast endpoints. This does not invalidate the
earlier 70-trial result, which used a different data and preprocessing pipeline.
It also does not answer whether activity-defined axes and activity-specific
residual heads help the 257-trial unified A10–A13 model.

See `NEXT_STEPS_A10_A14_SYNTHETIC.md` for the recommended unified-model and
synthetic-generation plan.
