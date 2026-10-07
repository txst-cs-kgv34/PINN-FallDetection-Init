# S43 A11 Stage-1 inverted-pendulum PINN

## Outcome

This experiment implements Stage 1 of the framework as a reduced-order angular inverted-pendulum PINN. It uses notebook-aligned filtered, female segment-weighted CoM in the standing subject frame. The horizontal state is the anterior-posterior (subject-forward) CoM direction. Horizontal and vertical CoM are measured relative to the fixed foot midpoint at marked fall onset, and the CoM angle is `atan2(horizontal, vertical)`.

No tested nonzero physics weight improved aggregate held-out accuracy relative to the identical data-only network.

| Metric | Value |
|---|---:|
| Data-only network mean held-out XY RMSE | 0.2430 m |
| Best tested nonzero physics weight | 0.01 |
| Best PINN mean held-out XY RMSE | 0.2520 m |
| Change relative to data-only | 3.7% worse |
| Matched fold/seed PINN wins | 4 / 8 |
| Best PINN mean angle RMSE | 11.73° |
| Constant-velocity control RMSE | 0.4028 m |
| Uncontrolled-pendulum control RMSE | 0.3978 m |
| Best PINN runs beating constant velocity | 8 / 8 |
| Best PINN angular-equation residual RMS | 171.60 N·m |
| Best PINN normalized residual RMS | 0.3333 |
| Residual reduction relative to data-only | 33.9% |

## Governing equation

The implemented residual follows the framework:

`I θ¨ = m g l sin(θ) + τ_effective - b θ˙`, with `I = m l²`.

The current feasibility run fixes `b = 0`. The learned `τ_effective` combines unmeasured human control, external perturbation, support/contact effects and model error. It is not an identified perturbation or corrective human torque.

## Data and validation

- Trials: S43A11T02, S43A11T03, S43A11T04, S43A11T05.
- Horizontal direction: anterior-posterior (subject-forward) (forward).
- Support-span proxy: left/right ANKLE and FOOT joint projections at onset.
- Window: every filtered CoM frame from marked onset through apparent contact.
- Four whole-trial leave-one-out folds and training-only condition normalization.
- Physics weights: 0, 0.01, 0.1, 1, 10.
- Seeds per fold/weight: 2.
- Notebook filter: order-6 zero-phase Butterworth at 1.5 Hz on each complete raw trial before window extraction.
- No trial-averaging trajectory is used as a quantitative baseline.
- Controls: identical data-only network, constant-velocity extrapolation and zero-torque inverted pendulum.
- Marked contact duration is not included in the condition vector.

## Physical diagnostics

The within-trial onset-to-contact CoM radius variation ranges from 0.167 to 0.304 m, demonstrating departure from a perfectly rigid single link.
The fixed onset foot midpoint is a deliberate reduced-order pivot, not a measured center of pressure. XCoM and Margin of Stability are notebook-derived validation diagnostics, not additional ground truth.

The hardest selected-weight run is S43A11T03 (seed 43013) at 0.3789 m XY RMSE.
The strongest aggregate method in this four-trial experiment is the data-only network at 0.2430 m RMSE.

## Decision gate

This run can establish whether the framework-aligned angular physics improves an identical data-only model on held-out S43 A11 trials. It cannot identify separate controller or perturbation torques, and it does not validate synthetic falls. Stage 2 remains gated on stronger identifiability evidence or additional measurements.
