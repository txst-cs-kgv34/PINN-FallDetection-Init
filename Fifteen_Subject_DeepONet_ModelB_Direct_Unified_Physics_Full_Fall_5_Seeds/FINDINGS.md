# Findings — Model B full-fall unified physics, five seeds

## Executive result

The full standing-to-apparent-contact experiment completed successfully. All
25 models (five folds × five seeds) are present, with 75 held-out
subject-seed evaluations and 350 held-out trial-seed evaluations. The prepared
manifest contains 70 unique accepted trials, and every trial passes the
complete-source-interval check. Physics is evaluated only on pre-contact
samples, excluding the final 0.03 s; the real forecast loss and test metrics
still cover the marked contact endpoint.

The five-seed held-out result is:

| Metric | Mean of five seed-level subject means | Seed SD | Descriptive 95% t interval |
|:---|---:|---:|:---|
| Normalized forecast MSE | 3.1852 | 0.3292 | 2.7764–3.5940 |
| Angle RMSE | 21.484° | 0.901° | 20.365–22.603° |
| Angle MAE | 17.152° | 0.792° | 16.169–18.136° |
| CoM displacement RMSE | 28.464 cm | 1.473 cm | 26.635–30.294 cm |
| CoM displacement MAE | 22.978 cm | 1.279 cm | 21.389–24.566 cm |
| Angle Wasserstein-1 | 16.562° | 0.703° | — |
| CoM displacement Wasserstein-1 | 22.126 cm | 1.132 cm | — |

The advisor-facing subject figure uses three directly interpretable trajectory
errors: normalized forecast RMSE, theta RMSE in degrees, and CoM x RMSE in
centimetres. Each normalized-RMSE point is computed as the square root of that
subject-seed's normalized MSE before constructing the five-seed boxplot. The
angular and horizontal equation residuals are intentionally excluded from this
comparison figure and remain reported separately below.

These are subject-balanced statistics: trials are averaged within each held-out
subject, the 15 subjects are averaged equally within a seed, and only then are
the five seed means summarized. The 75 subject-seed rows are repeated
optimization evaluations, not 75 independent people.

## Seed stability

| Seed index | Base seed | Normalized MSE | Angle RMSE | CoM RMSE |
|---:|---:|---:|---:|---:|
| 1 | 20261101 | 2.7734 | 20.638° | 27.161 cm |
| 2 | 20261102 | 3.6769 | 22.940° | 30.874 cm |
| 3 | 20261103 | 3.0475 | 20.956° | 27.792 cm |
| 4 | 20261104 | 3.2422 | 21.190° | 27.686 cm |
| 5 | 20261105 | 3.1858 | 21.698° | 28.809 cm |

Seed 1 performs best and Seed 2 performs worst on all three primary RMSE
summaries. Nevertheless, seed SD is only 0.329 normalized-MSE units, 0.901°,
and 1.473 cm. Subject identity has a substantially larger effect than the
optimization seed.

The validation-selected epochs range from 14 to 290 (median 43, mean 97.2).
All histories and checkpoints are finite; no model, metric file, or fold
summary is missing.

## Held-out subjects

The values below are means across the five seeds.

| Subject | Trials | Normalized MSE | Angle RMSE | CoM RMSE | Angular residual RMSE | Horizontal residual RMSE |
|:---|---:|---:|---:|---:|---:|---:|
| S30 | 5 | 0.6810 | 7.165° | 18.113 cm | 17.927 | 27.130 |
| S32 | 5 | 1.7133 | 16.338° | 26.014 cm | 16.036 | 45.668 |
| S34 | 5 | 1.0119 | 15.681° | 18.158 cm | 11.532 | 18.281 |
| S43 | 4 | 4.5152 | 26.425° | 38.530 cm | 13.227 | 3.133 |
| S44 | 5 | 2.1690 | 18.679° | 26.706 cm | 12.560 | 5.881 |
| S45 | 5 | 14.7969 | 50.847° | 69.126 cm | 17.917 | 33.108 |
| S46 | 5 | 1.6487 | 18.042° | 24.763 cm | 10.389 | 7.471 |
| S48 | 5 | 2.5291 | 19.312° | 30.296 cm | 11.099 | 10.241 |
| S49 | 3 | 9.0833 | 39.376° | 43.491 cm | 13.760 | 80.950 |
| S55 | 5 | 1.1667 | 14.617° | 20.664 cm | 12.806 | 5.957 |
| S56 | 5 | 1.2699 | 12.971° | 23.680 cm | 11.841 | 6.292 |
| S57 | 3 | 1.5495 | 18.544° | 23.930 cm | 8.864 | 5.908 |
| S59 | 5 | 2.8133 | 21.889° | 26.653 cm | 9.296 | 3.085 |
| S62 | 5 | 1.6999 | 22.922° | 21.040 cm | 6.761 | 4.643 |
| S63 | 5 | 1.1300 | 19.455° | 15.799 cm | 7.578 | 5.030 |

S45 is the dominant error outlier on every primary trajectory metric. S49 is
the second-largest outlier and has a uniquely large horizontal physics
residual. S43 is a smaller third outlier. The remaining 12 subjects have
normalized MSE between 0.6810 and 2.8133. Aggregate performance should
therefore always be reported together with subject-level distributions; the
overall mean alone hides this heterogeneity.

## Trial-level diagnosis

The largest trial errors after averaging each trial over five seeds are:

| Rank | Trial | Forecast duration after context | Normalized MSE | Angle RMSE | CoM RMSE |
|---:|:---|---:|---:|---:|---:|
| 1 | S45A11T02 | 4.12 s | 31.896 | 83.715° | 112.738 cm |
| 2 | S49A11T04 | 0.72 s | 24.758 | 75.581° | 97.875 cm |
| 3 | S45A11T04 | 3.52 s | 24.708 | 71.795° | 100.762 cm |
| 4 | S43A11T02 | 5.32 s | 12.302 | 46.718° | 71.162 cm |
| 5 | S45A11T03 | 5.06 s | 11.190 | 43.383° | 64.244 cm |

Duration has only a modest correlation with trial error (Pearson r = 0.281 for
normalized MSE, 0.325 for angle RMSE, and 0.364 for displacement RMSE). Longer
falls are somewhat harder, but duration does not explain the very large error
of the short S49A11T04 trial. That trial should be visually reviewed against
its phase marking and subject-forward coordinate construction before changing
the architecture.

The easiest seed-averaged trials include S48A11T04 (normalized MSE 0.088),
S30A11T01 (0.276), and S56A11T01 (0.344). This confirms that the model can
produce close full-fall continuations for some unseen trials; the limitation is
cross-subject/trial robustness rather than universal failure.

## Physics diagnostics

| Residual diagnostic | Five-seed mean | Seed SD | Descriptive 95% t interval |
|:---|---:|---:|:---|
| Angular residual RMSE | 12.1061 | 0.3949 | 11.6158–12.5965 |
| Angular residual MAE | 9.8056 | 0.2197 | 9.5328–10.0783 |
| Horizontal residual RMSE | 17.5184 | 3.3120 | 13.4060–21.6308 |
| Horizontal residual MAE | 13.3648 | 2.3278 | — |

These quantities measure the two cart-pole equations separately. They are not
forecast errors and should not be added together or compared numerically with
degrees or centimetres. The saved NPZ files and residual plots make it possible
to locate whether a violation is angular or horizontal and whether it occurs
during early descent, late descent, or immediately before the contact
exclusion window.

S49's horizontal-residual RMSE of 80.95 is the clearest equation-specific
outlier, followed by S32 (45.67), S45 (33.11), and S30 (27.13). By contrast,
S49's angular residual is not extreme. This separation would be hidden by a
single combined physics-loss value.

## Effective control parameters

The four context-encoder outputs are saved per trial in
`multi_seed_trial_metrics.csv` and each prediction NPZ:
`inferred_kp_theta`, `inferred_kd_theta`, `inferred_kp_x`, and
`inferred_kd_x`. Across the 350 trial-seed evaluations, their distributions are
highly right-skewed:

| Parameter | Mean | Median | Maximum |
|:---|---:|---:|---:|
| Kp_theta | 2.400 | 0.019 | 337.1 |
| Kd_theta | 1.170 | 0.200 | 47.63 |
| Kp_x | 33.98 | 16.63 | 480.18 |
| Kd_x | 0.977 | 0.179 | 15.68 |

These are effective latent controller parameters jointly fitted with the
operator. They are not identified physiological measurements. The extreme
upper tails also warn against interpreting an individual gain without checking
its trial prediction and residuals.

## Scientific interpretation and next comparison

The earlier pre-20° experiment and this full-fall experiment answer different
questions. The full-fall run predicts a longer, more nonlinear descent,
preserves angles near/beyond 90° with `atan2`, and includes the endpoint in the
trajectory loss. Its larger errors therefore must not be presented as a fair
regression relative to the earlier truncated task.

Likewise, the existing early-fall no-physics results are not a valid ablation
for this run. To determine whether the biomechanics residual helps full-fall
generalization, rerun B-no-physics with the identical 8-s preparation,
full-contact masks, `atan2` decoder, folds, seeds, architecture, and checkpoint
selection, changing only the physics weight to zero. Then compare paired
subject-seed and trial-seed errors. Until that matched ablation is complete,
the present results establish full-fall feasibility and diagnostics—not a
causal benefit from physics.
