# Synthetic generator selection and next steps

## Recommended model family

Keep two generator families:

1. One unified A10-A13 DeepONet with shared trajectory representation and
   activity-specific controller heads.
2. One separate A14 rotation DeepONet with the previously selected rotational
   physics formulation.

Do not split A10-A13 into four independent trajectory models. The available
data are limited, and the shared representation is still the more defensible
way to pool subjects and activities.

## Provisional activity policy

| Activity | Direct physics loss in the unified model | Evidence |
|:--|:--:|:--|
| A10 backfall | Off | +0.2% to +0.3% aggregate changes are practically neutral |
| A11 frontfall | Off | Selected V2 is worse on all three activity endpoints |
| A12 leftfall | On | +2.0% to +3.0% aggregate improvement across endpoints |
| A13 rightfall | On | +4.76% normalized-MSE and smaller component gains |
| A14 rotatefall | Separate model | Requires rotational dynamics and already has a selected model family |

This is a policy to confirm, not yet a production lock. Activity rows come from
a unified model with one globally selected lambda per fold, so a masked run is
needed to isolate the effect of removing direct A10/A11 physics penalties.

## Immediate confirmation experiment

Add an activity mask to the existing unified loss:

```text
physics_active = activity in {A12, A13}
```

Preserve every other choice: subject folds, stored initializations, data order,
optimizer, schedule, residual scaling, validation metric, early stopping, and
test timing.

Reuse existing work:

- comparator 1: matched lambda=0 candidates already trained;
- comparator 2: validation-selected all-head V2 already evaluated;
- new work: masked lambda `{1e-4, 1e-3, 1e-2}` for 5 seeds x 5 folds = 75
  candidates, followed by 25 validation-selected masked evaluations.

The masked condition should be preferred only if it improves overall forecast
metrics relative to lambda=0, does not introduce a meaningful A10/A11 penalty,
and is at least as good as all-head V2 on the prespecified primary endpoints.
Residual outcomes remain secondary quality evidence.

## Locking a production configuration

After the masked comparison:

1. Lock one activity mask.
2. Lock one global lambda using aggregate cross-validation **validation**
   performance only; do not choose it from held-out test performance.
3. Lock the epoch budget from the distribution of validation-selected epochs.
4. Refit five production seeds and preserve all five checkpoints as an
   ensemble rather than selecting the luckiest seed after generation.

The current all-head validation table slightly favors lambda=1e-3 on mean
validation MSE (2.1282), but lambda=1e-2 is nearly identical (2.1287) and the
per-fold selections are unstable. These numbers are not sufficient to lock the
masked model's lambda in advance.

## Refit rules by study purpose

### Unbiased subject-held-out detector experiment

For each detector split, train/refit the DeepONet generator using only the real
fall subjects in that detector split's training set. Generate synthetic
detector-training examples only from that generator. The generator must never
see detector validation or test trajectories.

### Final all-data generator

After all comparative detector experiments are complete, refit:

- the locked A10-A13 model on all 257 eligible planar trials; and
- the locked A14 rotation model on all 49 eligible A14 trials.

This all-data refit is appropriate for final synthesis/deployment but not for
an unbiased detector evaluation whose test subjects are among those 15 people.

## Does A14 need to be trained again?

Do not repeat the A14 physics-versus-no-physics comparison. Do train a new A14
**production refit** after its architecture and physics settings are locked:
either once per detector training fold for leakage-safe evaluation or on all 49
trials for the final all-data generator. Existing cross-validation checkpoints
remain evidence models, not the final production ensemble.

## Generation and acceptance checks

Generate multiple candidates per conditioning vector with the five-seed
ensemble. Retain samples only if they satisfy all of the following:

- finite values and strictly increasing time;
- activity-appropriate direction and phase order;
- plausible theta and CoM displacement ranges relative to real training data;
- smooth velocity and acceleration without isolated spikes;
- endpoint/contact plausibility;
- activity-appropriate physics residual threshold;
- agreement across ensemble members or an explicit uncertainty ceiling;
- no near-duplicate of a real training trajectory or another accepted sample.

Record the generating checkpoint, conditioning variables, acceptance metrics,
and random seed for every synthetic sequence.

## Downstream augmentation study

Within each leakage-safe detector fold, compare at minimum:

- real-only training;
- 40% real / 60% synthetic;
- 60% real / 40% synthetic.

Keep the detector initialization, optimizer, schedule, and number of update
steps matched. Report subject-level detection metrics and activity-stratified
results. A generator that improves residuals but does not improve detector
generalization should not be called beneficial for fall detection.

The present DeepONet predicts CoM trajectory variables. If the detector expects
complete joint skeletons, first validate a kinematic decoder and audit its bone
lengths, joint limits, foot-floor contact, and temporal smoothness.

