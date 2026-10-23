# S63 Pole-PINN full-run findings

## Executive assessment

The experiment is **computationally complete but scientifically qualified**. The unchanged four-stage pole pipeline accepted all five S63 A11 trials, identified one set of effective control parameters, and generated 100 finite trajectories. Stage 1 reconstructed the observed data very accurately. Stage 3 substantially reduced its physics objective, but it moved the network away from the measured trajectories. The generated ensemble agrees only partially with the very short observed-time distribution and becomes non-human-scale over the 30-second extrapolation.

Therefore, the run supports these claims:

1. The S43 pole-PINN software architecture can be transferred to S63 data and executed end to end.
2. The conditional network can fit the available S63 pre-fall CoM trajectories in Stage 1.
3. The inverse stage returns reproducible **effective pole-model** gains for this run.

It does **not** support claiming that the identified gains are measured human neuromuscular parameters or that the 100 long-horizon outputs are physiologically plausible human falls.

## Run integrity

| Check | Result |
|---|---|
| Core SHA-256 | `604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9` |
| Core modified | No |
| Accepted trials | S63A11T01-T05 |
| Real samples after the 20° rule | 412 |
| Stage epochs | 7,000 / 5,000 / 5,000 |
| Generated trajectories | 100 |
| Rows per trajectory | 3,001 at 100 Hz over 30 s |
| Non-finite generated values | None |
| Final model provenance | Stage 3 and final-generation weights are byte-identical |

The run used the documented `minimum_trial_seconds = 0.25` wrapper override. The source default of two seconds would have rejected every S63 trial. Available durations were T01 0.73 s, T02 1.22 s, T03 0.69 s, T04 1.10 s, and T05 0.33 s.

## Identified effective control parameters

| Parameter | Identified | Initialization | Paper reference | Change from initialization | Difference from reference |
|---|---:|---:|---:|---:|---:|
| Kp_theta | 145.109 | 150.000 | 240.000 | -3.3% | -39.5% |
| Kd_theta | 15.049 | 20.000 | 30.000 | -24.8% | -49.8% |
| Kp_x | 14.933 | 10.000 | 13.000 | +49.3% | +14.9% |
| Kd_x | 15.048 | 20.000 | 30.000 | -24.8% | -49.8% |
| Pi | 3.629° | 3.000° | 3.000° | +21.0% | +21.0% |
| tau | 0.230 s | 0.230 s | 0.230 s | fixed | fixed |

These are optimization outputs under the preserved 0.0138 kg, 0.57 m cart-pole model. They should be called **effective fitted control parameters**. `tau` was not identified from S63 because the pipeline fixes it at 0.23 s. The gains also moved largely monotonically from their starting values during Stage 2, so this single run does not establish parameter identifiability or uncertainty.

## Reconstruction performance

| Checkpoint | Normalized loss | Theta RMSE | Forward-x RMSE |
|---|---:|---:|---:|
| Stage 1 best | 0.0006295 | 0.337° | 0.529 cm |
| Stage 3 best | 0.1130986 | 5.903° | 5.987 cm |
| Stage 3 / Stage 1 | 179.65× | 17.51× | 11.32× |

Stage 1 is an excellent **in-sample** reconstruction. It uses the same five short trials for fitting and evaluation, so it is not evidence of generalization.

Stage 3 reduced its total physics-dominated objective from about `2.37e8` initially to a best value near `2.50e3`, roughly a 94,800-fold reduction. Nevertheless, the measured-data reconstruction became much worse. This is the clearest sign of a physics-data mismatch: satisfying the unchanged pole equations and frozen controller pulls the model away from S63 human CoM motion.

The Stage 3 degradation is not uniform. T02 is worst (9.116° theta RMSE and 9.024 cm x RMSE), while the very short T05 window has the smallest Stage 3 errors (1.419° and 1.154 cm). Shorter windows are easier to approximate and should not be interpreted as better trial quality.

## Real-versus-synthetic distribution comparison

The common support is only 0-0.33 s because T05 is the shortest accepted trial. The Wasserstein-1 results therefore assess the initial trajectory segment, not the full fall.

| Variable | Pooled W1 | 95% bootstrap interval | Mean time-resolved W1 | Median real-real W1 | Median synthetic split W1 | Real samples inside synthetic 5-95% |
|---|---:|---:|---:|---:|---:|---:|
| Theta | 1.530° | 0.839-3.775° | 1.953° | 5.025° | 0.340° | 61.8% |
| Forward x | 2.667 cm | 1.084-5.623 cm | 2.673 cm | 0.489 cm | 0.008 cm | 9.4% |

Interpretation:

- Theta mismatch is about 30% of the median real-to-real theta distance, so the early marginal angle distribution lies within the broad variation among the five trials.
- Forward-x mismatch is about 5.46 times the median real-to-real distance. Only 9.4% of real x samples lie in the synthetic 5-95% envelope.
- Synthetic split-half distances are far below real-to-real distances, especially for x. The generated set is internally very similar and does not reproduce the observed trial diversity.
- The x discrepancy is partly structural: generation fixes `x0 = 0` and both initial velocities to zero, whereas measured x starts vary. T05 begins near -17.9 cm, and the other measured trials also do not all begin at zero.
- Matching only the initial angle is insufficient. The initial-angle-matched comparisons still have theta RMSEs of 5.43-8.66° and x RMSEs of 2.90-10.33 cm.

The combined figure `results/full_run_distribution_comparison/real_vs_synthetic_means_and_wasserstein.png` shows why the W1 curve alone can be misleading: it places the real and synthetic means and spreads directly beside their time-resolved distance.

## Assessment of the 100 generated trajectories

All files are structurally valid and finite, but numerical validity is not physical validity.

- Every trajectory crosses `|theta| = 20°` between 4.04 and 4.22 s, with a median of 4.11 s.
- The observed S63 support ends between 0.33 and 1.22 s, so those crossing times are extrapolated rather than validated by the human recordings.
- By 5 s, maximum absolute theta is approximately 27.6-34.9° across the ensemble.
- Across 30 s, theta spans -340.4° to +292.9° and x spans -26.7 m to +48.2 m.

These magnitudes are incompatible with interpreting `x` as a person's CoM displacement and show that the 30-second region is unstable extrapolation. The files may be retained as outputs of the unchanged pole experiment, but they should not be labeled as 100 plausible synthetic human falls.

## Overall takeaway

The strongest result is the Stage 1 reconstruction, demonstrating that the conditional network can represent S63's short front-fall trajectories. The main negative result is the Stage 3 tradeoff: physics refinement improves the pole residual but damages agreement with the human measurements. The distribution analysis reaches the same conclusion from another direction—reasonable early theta overlap, but poor forward-x coverage and insufficient synthetic diversity.

## Recommended next experiments

1. Treat this run as the unchanged-pipeline baseline and preserve it unchanged.
2. Evaluate a shorter generation horizon tied to measured support; do not use 30-second curves as human-fall evidence.
3. Sample synthetic initial `x`, theta velocity, and x velocity from the measured trial distribution instead of fixing them to zero.
4. Repeat training across multiple seeds and report gain variability before interpreting controller parameters.
5. Use leave-one-trial-out evaluation if enough temporal support can be retained.
6. In a separate experiment—not by rewriting this baseline—rebalance Stage 3 losses or use human-scaled mechanics and compare reconstruction, residual, and distribution metrics together.

## Advisor-ready conclusion

> The S63 rerun completed successfully and identified effective controller parameters, but the result is a qualified baseline rather than a validated human-fall generator. Stage 1 reconstructed the five short measured trials accurately. Enforcing the unchanged pole physics in Stage 3 increased pooled reconstruction loss by 179.65 times, showing a conflict between the pole equations and S63 human CoM motion. The 100 generated trajectories are finite, but their forward-CoM diversity is too narrow and their 30-second extrapolations become non-human-scale. The early theta distribution is the most encouraging component; future experiments should improve initial-condition sampling and use a horizon supported by the measured data.
