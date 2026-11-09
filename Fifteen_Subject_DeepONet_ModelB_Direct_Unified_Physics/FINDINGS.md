# Findings — Model B 15-subject direct unified physics DeepONet

## Executive conclusion

The experiment demonstrates **partial but meaningful cross-subject
generalization**. Model B generated plausible held-out theta and forward-x CoM
continuations for most subjects, including several subjects whose recordings
were newly converted from phase-marked skeleton audits. Performance was not
uniform: S45 and S32 were clear failures, and S48 was a weaker case.

Across the 15 held-out subjects:

- mean normalized MSE was **0.2584 ± 0.3068**;
- median normalized MSE was **0.1642**;
- mean theta RMSE was **5.70 ± 2.84 degrees**;
- mean forward-x RMSE was **8.87 ± 4.67 cm**;
- 10/15 subjects had normalized MSE below 0.20;
- 13/15 subjects had normalized MSE below 0.50.

The large standard deviations and the gap between mean and median show that a
few poor subjects dominate the overall mean. The correct conclusion is not
that Model B generalizes equally to all people; it is that it transfers well to
many unseen subjects while retaining identifiable out-of-distribution failure
cases.

## Held-out subject results

Each row is the mean across that subject's held-out trials. The final aggregate
weights every subject equally, regardless of trial count.

The accompanying `cross_subject_results.png` uses one box per subject for each
metric. Boxes summarize the subject's held-out trial distribution, individual
trial values are overlaid as black points, the blue line marks the median, and
the orange diamond marks the subject mean. With only 2–5 trials per subject,
the points should be inspected together with the quartiles rather than treating
the boxes as high-sample population estimates.

| Rank | Subject | Fold | Trials | Normalized MSE | Theta RMSE (deg) | Forward-x RMSE (cm) |
|---:|:---:|---:|---:|---:|---:|---:|
| 1 | S30 | 1 | 5 | 0.0151 | 1.24 | 2.79 |
| 2 | S59 | 3 | 5 | 0.0688 | 3.97 | 5.15 |
| 3 | S56 | 3 | 4 | 0.0936 | 3.87 | 6.30 |
| 4 | S46 | 1 | 5 | 0.0971 | 3.92 | 6.43 |
| 5 | S44 | 5 | 5 | 0.0984 | 2.90 | 6.38 |
| 6 | S62 | 5 | 4 | 0.1097 | 5.57 | 6.04 |
| 7 | S43 | 2 | 4 | 0.1184 | 4.19 | 7.24 |
| 8 | S63 | 5 | 4 | 0.1642 | 5.79 | 8.25 |
| 9 | S55 | 2 | 5 | 0.1666 | 5.30 | 8.09 |
| 10 | S57 | 1 | 3 | 0.1771 | 4.95 | 8.79 |
| 11 | S49 | 4 | 2 | 0.2020 | 5.63 | 7.73 |
| 12 | S34 | 4 | 5 | 0.2142 | 7.03 | 8.92 |
| 13 | S48 | 2 | 5 | 0.4658 | 8.48 | 13.23 |
| 14 | S32 | 4 | 5 | 0.7267 | 11.41 | 17.21 |
| 15 | S45 | 3 | 5 | 1.1588 | 11.22 | 20.46 |

S30 has the lowest numerical error, but its mean forecast region is only about
0.26 s after the 0.40-s context. Its result should therefore not be compared
directly with subjects that retain forecasts of roughly 2.5–2.6 s. S44 and S59
are particularly useful positive examples because both remain accurate over
long forecast regions. S45 is the strongest negative example: its predicted
theta and x diverge substantially from the real path across multiple trials.

## Fold-level results and checkpoint selection

Fold metrics below are pooled over the forecast samples in the three test
subjects, so they are not the equal-subject aggregate reported above.

| Fold | Validation subject | Test subjects | Best epoch | Validation nMSE | Pooled test nMSE | Theta RMSE (deg) | Forward-x RMSE (cm) |
|---:|:---:|:---|---:|---:|---:|---:|---:|
| 1 | S63 | S57, S46, S30 | 64 | 0.0281 | 0.1156 | 4.18 | 7.40 |
| 2 | S62 | S55, S48, S43 | 86 | 0.1098 | 0.2131 | 6.01 | 9.85 |
| 3 | S57 | S45, S59, S56 | 405 | 0.1628 | 0.5545 | 9.13 | 16.22 |
| 4 | S55 | S34, S32, S49 | 26 | 0.1043 | 0.3929 | 8.89 | 12.90 |
| 5 | S43 | S44, S62, S63 | 37 | 0.0433 | 0.1072 | 4.22 | 7.02 |

All checkpoints were selected only from the real validation subject. Test data
were not used for selection. The physics loss was active and nonzero at the
selected epochs in every fold. Fold 3 required substantially longer training
and remained the weakest fold because of S45, while folds 1 and 5 generalized
best overall.

## Four inferred context-controller parameters

The context pathway does save the four inferred positive controls:

1. `Kp_theta`
2. `Kd_theta`
3. `Kp_x`
4. `Kd_x`

The context encoder first embeds four 0.10-s windows from the first 0.40 s. The
controller head combines that embedding with demographics and emits one
four-value vector **per trial**. Consequently, a fold does not have just one
control vector; it has one inferred vector for each trial processed by that
fold's model.

Saved locations:

- `results/full/fold_##/test_metrics_by_trial.csv` contains four explicitly
  named `inferred_*` columns.
- `results/full/fold_##/test_predictions/<trial>.npz` contains
  `inferred_controller` ordered as
  `[Kp_theta, Kd_theta, Kp_x, Kd_x]`.

Mean held-out trial outputs by fold are:

| Fold | Kp_theta | Kd_theta | Kp_x | Kd_x |
|---:|---:|---:|---:|---:|
| 1 | 0.6033 | 0.2688 | 34.4122 | 0.5789 |
| 2 | 0.000015 | 0.0017 | 0.0258 | 0.0156 |
| 3 | 0.3423 | 0.0030 | 1.8303 | 2.1500 |
| 4 | approximately 0 | 0.0175 | 0.0358 | 0.0066 |
| 5 | 10.5026 | 12.3071 | 8.7677 | 1.4762 |

These fold-to-fold differences are too large to interpret as reliable human
controller estimates. Folds 2 and 4 collapse several controls close to zero,
whereas fold 5 learns much larger theta controls. Because the controls have no
measured target or gain-supervision loss, the DeepONet branch can compensate
for different controller representations while still fitting trajectories.

Therefore:

- **Yes**, the four parameters are saved and can be audited.
- **No**, they should not yet be described as measured or recovered human
  biomechanical gains.
- For scientific control-parameter claims, add identifiability constraints,
  repeated-seed stability analysis, and independent parameter validation.

The controller uncertainty head was not trained in this condition, so the NPZ
files do not contain calibrated uncertainty for these four values.

## Motion- and data-quality observations

- The standing anatomical frame was sufficient to obtain strong performance
  for tilted/camera-facing subjects S30 and S44, so camera-axis alignment alone
  does not prevent transfer.
- S32, also camera-facing, remained a major failure. Its result indicates a
  motion-pattern mismatch or subject-specific trajectory problem beyond simple
  camera orientation.
- S56 retained repaired frames before apparent contact but still achieved good
  held-out performance (normalized MSE 0.0936). For S48, repaired frames were
  after apparent contact and were not used by the adapter; its weaker result
  therefore cannot be attributed directly to those unused repaired rows.
- S49 contributes only two eligible trials. S49A11T01 was intentionally
  ignored, and S49A11T04 was too short after preprocessing.
- Four trials were excluded because fewer than 41 samples (0.40 s context plus
  the initial sample) remained: S62A11T02, S63A11T05, S56A11T02, and
  S49A11T04.

## Event-timing metric caution

A real 10-degree theta crossing exists in 55 of 66 evaluated trials, but the
prediction crosses 10 degrees in only 14 trials. Crossing-time error is defined
for both trajectories in only 12 trials. Its mean over those 12 cases is about
0.091 s, but this is a conditional result and should not be reported as the
overall timing accuracy. The low predicted-crossing coverage indicates that
many trajectories underpredict the eventual angular excursion.

## Recommended next experiment

1. Repeat all five folds with at least three optimization seeds and report
   subject-level mean and uncertainty.
2. Compare these results against the existing B-no-physics condition using the
   identical 15-subject splits. This isolates the contribution of the
   cart-pole biomechanics residual.
3. Report error at fixed horizons such as 0.25, 0.50, 1.0, and 2.0 s in addition
   to the current variable-length forecast metric.
4. Investigate S45, S32, and S48 separately with context/target overlays and
   coordinate-sign checks before adding more subjects.
5. Treat the synthetic trajectories as candidates for later fall-detector
   augmentation only after subject-wise quality filtering and downstream
   ablation testing.

The immediate scientific takeaway is that Model B can synthesize useful
held-out CoM trajectories for many subjects, but the current run does not yet
support a claim of universal subject generalization or physiologically valid
controller recovery.
