# Next steps — A10–A13 physics DeepONet, A14, and synthetic data

## Decision from the completed A11 calibration

The current A11 experiment shows that reducing a CartPole residual is not
sufficient to improve unseen-subject forecasting. The next planar experiment
must change the physical representation and validation design, not merely try
more values of the same global loss.

Use these current references:

- A11 strict-primary forecasting reference: matched λ=0.
- A10–A13 current reference: the completed unified no-physics model.
- A14 current reference: the completed separate rotation/yaw physics model.

## Experiment 1 — unified A10–A13 activity-specific physics V2

Use all 257 strict-primary planar trials:

| Activity | Trials | Physical axis |
|:--|--:|:--|
| A10 backfall | 58 | signed sagittal, backward-positive convention |
| A11 frontfall | 64 | signed sagittal, forward-positive convention |
| A12 leftfall | 68 | signed frontal, left-positive convention |
| A13 rightfall | 67 | signed frontal, right-positive convention |

### Architecture

- One shared context encoder, demographic conditioning block, branch, and time
  trunk across A10–A13.
- Four activity-specific controller/residual heads.
- Each head receives its activity-defined signed coordinate; do not compute
  direction from future onset-to-contact samples.
- Keep the delayed CartPole residual family.
- Normalize angular and horizontal residuals separately by `g/l` and `g`.
- Average losses equally by activity before averaging trials so A12/A13 do not
  dominate A10 merely because they contain more trials.
- Log every residual head, forecast loss, and physics/data gradient ratio.

### Splits and selection

Retain five outer test folds with three held-out subjects each. Replace the
current 11-train/1-validation/3-test arrangement with
10-train/2-validation/3-test inside each outer fold. Select hyperparameters on
the subject-balanced, activity-balanced mean of both validation subjects.

Train these matched-from-scratch arms per fold and seed:

`λglobal = {0, 1e-4, 1e-3, 1e-2}`

For nonzero arms, λ multiplies the equal mean of the four normalized
activity-specific residual heads. This first experiment intentionally uses one
global magnitude to avoid an unmanageable `4^4` search. All arms must share
the same initialization, batch order, optimizer, schedule, minimum epochs,
patience, and checkpoint rule.

Run seed 1 as a pilot. Continue to five seeds only if nonzero physics improves
validation without a large activity-specific penalty. The final decision must
use held-out subjects after five-seed averaging, not residual reduction alone.

## Experiment 2 — activity-head ablation

If Experiment 1 finds a useful nonzero global magnitude, train the following
matched configurations at that magnitude:

1. no physics;
2. all four heads;
3. A10 head only;
4. A11 head only;
5. A12 head only; and
6. A13 head only.

This identifies helpful and harmful activities with six interpretable arms
instead of searching 256 λ combinations. Construct the final unified physics
configuration by enabling only heads that improve their activity and do not
materially harm the other activities through the shared representation. Then
confirm that locked configuration over all five seeds.

The A11 head must be allowed to remain zero. The completed A11 result gives no
reason to force physics onto A11 merely for architectural symmetry.

## A14 decision

Do **not** repeat the completed A14 physics-versus-no-physics experiment. The
separate A14 CartPole-plus-yaw model is still the best current rotation
formulation:

- normalized MSE improved 10.1%;
- theta RMSE improved 3.0%;
- CoM-x RMSE improved 4.3%;
- yaw RMSE improved 5.9%;
- horizontal residual RMSE improved 85.5%; and
- yaw residual RMSE improved 17.5%.

Those trajectory improvements were exploratory rather than statistically
significant, so describe A14 as the best current candidate, not a proven
superior model.

For synthetic generation, **do train a final production A14 generator**, but
this is a refit rather than a new ablation: lock the validated architecture and
hyperparameters, then train on all 49 eligible A14 trials. Retraining is also
needed if the A10–A13 work changes shared preprocessing, conditioning fields,
or the saved-model interface. Otherwise there is no reason to redo the 50-model
A14 comparison.

## Final production generators

Cross-validation checkpoints are evaluation models; they intentionally omit
test subjects. After the A10–A13 and A14 configurations are locked:

1. choose a fixed training duration from the median validation-selected epoch
   of the completed folds;
2. refit A10–A13 on all 257 eligible planar trials;
3. refit A14 on all 49 eligible rotation trials;
4. train five production seeds with the fixed duration;
5. retain the five models as an ensemble rather than selecting one using the
   former test subjects; and
6. use between-seed spread as a synthetic-trajectory uncertainty signal.

These all-data refits are for generation only and must not be reported as new
held-out accuracy estimates.

## Synthetic-data generation and quality gates

DeepONet currently generates CoM-level trajectories—theta, signed horizontal
CoM displacement, and yaw for A14—not a complete 32-joint skeleton. Use these
outputs directly only when the detector consumes the same CoM features. If the
fall detector requires raw skeleton sequences, add and validate a separate
kinematic/skeleton decoder before calling the output synthetic skeleton data.

Generate candidates by conditioning on real training-range demographics,
activity, context, initial state, and direction label. Perturb controller or
latent variables only within empirically observed ranges. Reject samples that
fail any of these gates:

- finite values and strictly increasing time;
- exact initial-state construction;
- activity-appropriate direction and phase order;
- real-data bounds for duration, angle, displacement, velocity, and yaw;
- smoothness/acceleration limits;
- per-head residual thresholds derived from real validation trajectories;
- plausible contact endpoint;
- minimum distance from exact training trajectories to prevent copies; and
- ensemble agreement or an explicitly retained uncertainty label.

## Prevent leakage in the fall-detection study

For unbiased cross-subject detector evaluation, synthetic samples used in a
detector fold must come from a generator trained only on that fold's real
training subjects. An all-subject production generator may be used for
exploratory augmentation or deployment, but not to augment training in a study
whose test subjects were included in that generator.

Compare at least:

- real-only detector baseline;
- 40:60 real-to-synthetic falls;
- 60:40 real-to-synthetic falls; and
- optionally the earlier 50:50 reference.

Keep non-fall data, detector splits, initialization seeds, batch sizes, and
decision thresholds paired. Report sensitivity/recall, specificity, F1,
precision, AUROC/AUPRC, false alarms, and subject-level paired uncertainty.

## Recommended implementation order

1. Build and audit activity-defined A10–A13 coordinates.
2. Implement the shared model with four residual/controller heads.
3. Run the four-arm global-λ seed-1 pilot with two validation subjects.
4. Review activity-wise forecast/residual/gradient diagnostics.
5. Run five seeds only if the pilot gate passes.
6. Run the six-arm head ablation if global physics is promising.
7. Lock A10–A13 and A14 configurations.
8. Train final five-seed production ensembles.
9. Generate and quality-filter synthetic CoM trajectories.
10. Run leakage-free detector source-ratio experiments.

Suggested experiment folders:

- `Fifteen_Subject_DeepONet_A10_A13_Activity_Specific_Physics_V2_5_Seeds`
- `Fifteen_Subject_DeepONet_A10_A13_Activity_Head_Ablation_5_Seeds`
- `Fifteen_Subject_DeepONet_Final_Synthetic_Generators`
