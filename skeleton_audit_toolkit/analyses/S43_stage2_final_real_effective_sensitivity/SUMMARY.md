# Final Stage 2: identifiability conclusion and exploratory S43 CoM prediction

## Decision

Stage 2 is complete as a feasibility and non-identifiability study. The real-data fits below are exploratory effective models, not recovered physiological controllers.

The displayed model for each fold is chosen using training-trial AIC only between zero perturbation and one shared activity-level pulse proxy. No held-out CoM sample is used to fit the controller, pulse or model choice.

## Held-out real-trial results

| Activity | Held-out folds | Selected effective-model XY RMSE | Zero-perturbation XY RMSE | Constant-velocity XY RMSE | Uncontrolled-pendulum XY RMSE |
|---|---:|---:|---:|---:|---:|
| A11 | 4 | 0.1216 m | 0.1325 m | 0.2848 m | 0.2813 m |
| A13 | 4 | 0.4332 m | 0.4446 m | 0.2681 m | 0.3452 m |

## Trial-level displayed models

| Held-out trial | Selected forcing | Shared pulse ratio | Delay | XY RMSE | Angle RMSE | Endpoint error |
|---|---|---:|---:|---:|---:|---:|
| S43A11T02 | shared_pulse | 0.585 | 6 frames | 0.0967 m | 3.83° | 0.3570 m |
| S43A11T03 | shared_pulse | 0.563 | 6 frames | 0.1427 m | 9.45° | 0.2840 m |
| S43A11T04 | shared_pulse | 0.528 | 6 frames | 0.1123 m | 7.85° | 0.4270 m |
| S43A11T05 | shared_pulse | 0.340 | 6 frames | 0.1347 m | 12.16° | 0.3846 m |
| S43A13T01 | zero | 0.000 | 6 frames | 0.2836 m | 24.55° | 0.6956 m |
| S43A13T02 | shared_pulse | 0.600 | 3 frames | 0.9439 m | 105.07° | 1.6613 m |
| S43A13T03 | zero | 0.000 | 6 frames | 0.2134 m | 18.30° | 0.4651 m |
| S43A13T05 | zero | 0.000 | 6 frames | 0.2917 m | 25.21° | 0.7177 m |

## Assumption sensitivity

The table below reports parameter ranges across ±5% onset-length scaling, zero or 0.10 normalized damping, and zero versus learned shared-pulse forcing. These ranges are sensitivity results, not confidence intervals.

| Activity | Alpha Kp range | Beta Kd range | Delay range | Gamma torque-limit range | Pulse-ratio range |
|---|---:|---:|---:|---:|---:|
| A11 | 0.409–2.000 | 0.000–0.606 | 4–6 frames | 0.349–0.500 | 0.000–0.600 |
| A13 | 0.020–1.400 | 0.300–1.200 | 2–6 frames | 0.065–0.500 | 0.000–0.600 |

## Interpretation

A closer CoM line does not validate the parameter values. The shared pulse is inferred from training falls rather than measured, and it can exchange explanatory torque with Kp, Kd, delay, damping and the assumed length.

The correct conclusion is that the reduced model can produce an assumption-dependent effective prediction of some held-out CoM paths, while the controller decomposition remains non-identifiable. The dataset contains fall skeletons but no measured external forces, recovery forces, ground-reaction forces or center of pressure, so Option 3 cannot be performed retrospectively.

## Files

- `assumption_grid_metrics.csv`: all 96 fold/assumption fits.
- `selected_fold_metrics.csv`: training-only selected central model and baselines.
- `held_out_com_predictions.csv`: real and predicted CoM samples.
- `optimization_profiles.csv`: all delay/start fits.
- `parameter_sensitivity_ranges.csv`: activity-level assumption ranges.
- `plots/`: one held-out CoM comparison per real trial.
