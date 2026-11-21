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

Then run:

```bash
cd Fifteen_Subject_DeepONet_A11_From_Scratch_Physics_Calibration_V3_5_Seeds
chmod +x run.sh run_on_mac.sh
./run_on_mac.sh setup
./run_on_mac.sh validate
./run_on_mac.sh smoke mps
./run_on_mac.sh pilot mps
```

The pilot trains 20 models: four λ arms × five folds for seed 1. Send back:

`Fifteen_Subject_A11_From_Scratch_Physics_Calibration_V3_Seed_01_Pilot_Results.zip`

Do not run seeds 2–5 until the seed-1 gate is reviewed. If approved:

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

## Seed-1 decision gate

Proceed to all five seeds only when:

1. all 20 candidate manifests confirm matched initialization;
2. at least one nonzero λ is selected in a meaningful number of folds;
3. selected V3 improves held-out forecast errors without severe seed/fold
   instability; and
4. residual improvement is not purchased by materially worse trajectory error.

If λ=0 is selected in all five folds, stop and diagnose coordinates/residual
heads before A10–A13 V2. If results are mixed, inspect fold histories and
gradient ratios before expanding.

## Interpretation boundaries

V3 answers whether validation-selected CartPole regularization helps the
current 64-trial A11 pipeline under a matched from-scratch design. It does not
invalidate the earlier 70-trial result, and it does not yet answer whether
activity-defined axes and activity-specific residual heads help A10–A13.
