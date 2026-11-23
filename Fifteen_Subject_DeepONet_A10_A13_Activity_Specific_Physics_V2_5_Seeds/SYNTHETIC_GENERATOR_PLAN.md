# Synthetic generator selection and next steps

## Locked model-family decision

Keep two generator families:

1. One unified A10-A13 DeepONet with direct CartPole physics active for A10,
   A11, A12, and A13, using the four activity-specific controller heads.
2. One separate A14 rotation DeepONet with the previously selected rotational
   physics formulation.

There is no A10/A11 physics exception, no A12+A13-only physics mask, and no plan
to split A10-A13 into four independent trajectory networks. The matched
no-physics models remain scientific comparators only.

The activity-stratified forecast findings remain part of the report: A10 was
neutral, A11 descriptively favored lambda=0, and A12/A13 favored selected V2 in
aggregate. The production choice retains direct physics for all four planar
activities because the goal is to generate physically constrained candidates
and then enforce quality with a strict post-generation gate. This operational
choice should not be described as proof that physics improved A11 forecasting.

## Top-two validation selection

The generator pool must contain only unified all-head models with nonzero
physics weight. Select the two best models using validation performance only:

1. Rank by `validation_subject_activity_balanced_forecast_mse`.
2. Exclude lambda=0 from the synthesis pool.
3. Never use held-out test performance, detector results, or post-generation
   visual preference to select the two models.
4. Preserve both selected checkpoints and their validation scores in the
   generation manifest.

Raw validation MSE is affected by which subjects are in the validation set.
Therefore, top-two candidates must either share the same validation split or
be ranked through a predefined fold-balanced aggregation. Do not simply take
the two lowest numbers across different folds.

For a subject-held-out detector experiment, perform this selection separately
inside each detector fold using only that fold's training and validation
subjects. For a final all-data generator, use a fixed production validation
protocol and then refit the selected configurations on the intended real-data
scope.

## Generation with the two selected models

Generate candidates from both validation-selected models. Retain the source
model identifier, lambda, seed, conditioning vector, and sampling seed for
every candidate. The two models can be used to:

- contribute separate accepted trajectories, increasing diversity; and
- provide an agreement/uncertainty signal when generated with matched
  conditioning variables.

Do not average trajectories automatically. Averaging can blur fall onset,
contact, and directional dynamics. Keep model outputs separate unless a later
validation study explicitly supports trajectory averaging.

## Trajectory-quality gate

Apply the established gate before a synthetic sequence is admitted to detector
training. A candidate must pass all relevant checks:

- finite values and strictly increasing time;
- valid activity label and activity-appropriate fall direction;
- valid standing, onset, descent, contact, and post-fall phase order;
- theta and CoM displacement within robust ranges learned only from the real
  training data;
- plausible duration, peak velocity, and peak acceleration;
- smooth velocities and accelerations without isolated spikes;
- plausible contact/end state;
- activity-appropriate normalized CartPole residual threshold for A10-A13;
- rotational residual threshold for A14;
- no near-duplicate of a real training trajectory or another accepted sample;
- acceptable disagreement between the two selected generators for matched
  conditioning, or an explicitly justified uncertainty threshold.

Quality thresholds must be estimated from training/validation data only, not
from detector test subjects. Save pass/fail reasons and all gate metrics so the
accepted dataset is auditable.

## Refit rules by study purpose

### Unbiased subject-held-out detector experiment

For each detector split, train/select the DeepONet generators using only the
real fall subjects assigned to detector training and validation. Generate
synthetic detector-training examples only from those models. A generator must
never see detector-test trajectories.

### Final all-data generator

After comparative detector experiments are complete, the selected all-head
A10-A13 configuration may be refit on all 257 eligible planar trials. The A14
rotation configuration may be refit separately on all 49 eligible A14 trials.
This all-data refit is suitable for final synthesis or deployment, but not for
an unbiased evaluation whose test subjects occur in those data.

## A14 decision

Do not repeat the A14 physics-versus-no-physics comparison. Do perform the A14
production training/refit needed for the chosen detector fold or final all-data
scope. Select its two best eligible physics models using the corresponding
validation-only rule and apply the rotation-specific quality gate.

## Downstream augmentation study

Within each leakage-safe detector fold, compare at minimum:

- real-only training;
- 40% real / 60% synthetic;
- 60% real / 40% synthetic.

Keep detector initialization, optimizer, schedule, and number of update steps
matched. Report subject-level and activity-stratified detection metrics. Also
report how many generated trajectories were rejected by each quality-gate
criterion.

The present DeepONet predicts CoM trajectory variables. If the detector expects
complete joint skeletons, first validate the kinematic decoder and audit bone
lengths, joint limits, foot-floor contact, and temporal smoothness.

