# S43 Stage 2A robustness study

## Decision

**DO NOT PASS the moderate robustness gate.** 5/10 required moderate conditions passed.

The unchanged correctly specified Stage-2A reference remains a software/recovery control. This study measures how parameter interpretation degrades when the observation or plant assumptions are wrong.

## Condition outcomes

| Condition | Overall | Parameters | Trajectory | Median Kp error | Median Kd error | Median delay error | Median torque-limit error | Held-out RMSE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reference | 4/4 | 4/4 | 4/4 | 0.1% | 0.5% | 0.0 frames | 0.6% | 0.018° |
| noise_0p5deg | 4/4 | 4/4 | 4/4 | 0.5% | 2.9% | 0.0 frames | 3.4% | 0.089° |
| noise_1p0deg | 4/4 | 4/4 | 4/4 | 0.9% | 6.3% | 0.0 frames | 7.3% | 0.187° |
| noise_2p0deg | 1/4 | 1/4 | 4/4 | 0.9% | 11.7% | 0.5 frames | 18.7% | 0.309° |
| length_minus10pct | 0/4 | 0/4 | 4/4 | 11.5% | 57.4% | 2.0 frames | 8.7% | 0.189° |
| length_minus5pct | 0/4 | 0/4 | 4/4 | 5.7% | 30.8% | 1.0 frames | 4.5% | 0.095° |
| length_plus5pct | 0/4 | 0/4 | 4/4 | 5.5% | 31.1% | 1.0 frames | 8.2% | 0.113° |
| length_plus10pct | 0/4 | 0/4 | 4/4 | 12.3% | 28.1% | 1.0 frames | 4.4% | 0.295° |
| damping_0p05 | 4/4 | 4/4 | 4/4 | 0.8% | 13.8% | 0.0 frames | 7.4% | 0.091° |
| damping_0p10 | 4/4 | 4/4 | 4/4 | 0.3% | 12.5% | 1.0 frames | 10.4% | 0.153° |
| damping_0p20 | 0/4 | 0/4 | 4/4 | 0.7% | 15.2% | 1.0 frames | 20.0% | 0.152° |
| perturb_unmeasured | 0/4 | 0/4 | 0/4 | 25.3% | 15.4% | 2.0 frames | 49.9% | 7.828° |
| perturb_minus25pct | 0/4 | 0/4 | 4/4 | 1.8% | 27.8% | 2.0 frames | 19.7% | 0.881° |
| perturb_minus10pct | 1/4 | 1/4 | 4/4 | 1.0% | 15.2% | 1.0 frames | 0.9% | 0.293° |
| perturb_plus10pct | 0/4 | 0/4 | 4/4 | 1.6% | 53.5% | 2.0 frames | 2.9% | 0.170° |
| perturb_plus25pct | 0/4 | 0/4 | 4/4 | 1.9% | 23.4% | 2.0 frames | 1.4% | 0.768° |
| filter_1p0hz | 4/4 | 4/4 | 4/4 | 0.1% | 1.0% | 0.0 frames | 1.0% | 0.022° |
| filter_2p0hz | 4/4 | 4/4 | 4/4 | 0.1% | 0.5% | 0.0 frames | 0.5% | 0.014° |
| filter_3p0hz | 4/4 | 4/4 | 4/4 | 0.1% | 0.5% | 0.0 frames | 0.5% | 0.014° |
| combined_moderate | 0/12 | 0/12 | 12/12 | 4.0% | 39.9% | 1.0 frames | 11.0% | 0.325° |

## Boundary summary

- Conditions passing the 80% case rule: reference, noise_0p5deg, noise_1p0deg, damping_0p05, damping_0p10, filter_1p0hz, filter_2p0hz, filter_3p0hz.
- Conditions failing the rule: noise_2p0deg, length_minus10pct, length_minus5pct, length_plus5pct, length_plus10pct, damping_0p20, perturb_unmeasured, perturb_minus25pct, perturb_minus10pct, perturb_plus10pct, perturb_plus25pct, combined_moderate.
- Combined moderate mismatch: 0/12 overall, 0/12 parameter, and 12/12 trajectory cases passed; median held-out RMSE 0.325°.
- Failed cases were rerun with the original three-start optimizer. A retained failure therefore persisted after the initialization check.

## Interpretation

Passing held-out trajectories does not by itself mean controller parameters are unbiased. Parameter gates and trajectory gates are reported separately in `robustness_metrics.csv`.

The unmeasured-perturbation condition is the closest tested analogue to the available S43 skeleton trials. If that condition fails, real-data controller parameters remain non-identifiable without stronger perturbation/contact information, even if a trajectory fit looks visually good.

## Outputs

- `robustness_metrics.csv`: every plant/profile/noise replicate.
- `condition_summary.csv`: pass fractions and median errors by condition.
- `optimization_profiles.csv`: every retained delay/start fit.
- `combined_example_trajectories.csv`: one combined-mismatch held-out example.
- `plots/`: condition, parameter-bias, and trajectory figures.
