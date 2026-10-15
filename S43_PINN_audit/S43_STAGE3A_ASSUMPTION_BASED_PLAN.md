# S43 Stage 3A plan: assumption-based virtual perturbation sensitivity

## Decision and scope

S43 has skeleton trajectories but no measured perturbation torque, ground-reaction force, center of pressure or verified contact timing. The fixed-delay Stage-2 diagnostic also shows that response delay is not identifiable: all 16 loss profiles decrease through the 0.300-s upper boundary.

Stage 3 can therefore proceed only as a computational sensitivity experiment. Its question is:

> Under the retained fixed-link model and explicitly assumed torque pulses, how do simulated balance outcomes change across the full Stage-2 controller uncertainty ensemble?

It must not claim to estimate the force that caused a recorded fall, the person's true corrective controller, a physiological recovery limit or clinical fall risk.

## Frozen model ensemble

For each activity, retain:

- four leave-one-trial-out folds;
- two Stage-1 seeds;
- 11 fixed delays: 0.050, 0.075, ..., 0.300 s;
- the corresponding gradient-optimized Kp, Kd and Ki at each delay.

This produces 88 controllers per activity. Do not average parameters and do not select the 0.300-s boundary as a recovered delay. Each controller remains linked to its activity, fold, seed and fixed delay.

## Forward equation

Use the same primary plant as revised Stage 2:

\[
I\ddot\theta(t)=mgl\sin\theta(t)-b\dot\theta(t)
-K_p\theta(t-\Delta)-K_d\dot\theta(t-\Delta)
-K_i\int_0^t\theta(s)\,ds+\tau_p(t),
\]

with \(I=ml^2\), \(b=0\), fixed pivot, fixed trial-specific onset length and no fitted torque saturation. The prescribed perturbation is

\[
\tau_p(t)=s\,\gamma mgl
\]

during the pulse and zero otherwise, where \(s\in\{-1,+1\}\) is direction and \(\gamma\) is dimensionless amplitude. This expresses perturbation strength as an assumption rather than an unmeasured Newton-metre value.

## Predeclared 100-scenario grid

Create 50 scenarios for A11 and 50 for A13:

- amplitude \(\gamma\): 0.025, 0.050, 0.075, 0.100, 0.150;
- pulse duration: 0.05, 0.10, 0.15, 0.20, 0.30 s;
- direction: -1 and +1;
- pulse onset: 0.20 s;
- total simulation horizon: 3.0 s.

The 50 combinations per activity cycle deterministically through the four observed activity-specific onset states \((\theta_0,\dot\theta_0,l)\). Running every scenario through all 88 corresponding controllers produces 8,800 simulations.

The pulse is rectangular. It is a known virtual input, not nuisance-torque smoothing or an inferred force.

## Numerical controls

For every observed onset state, also run:

1. zero perturbation with the controller active;
2. the same perturbation with Kp=Kd=Ki=0;
3. a time-step convergence subset at 150, 300 and 600 Hz.

These checks distinguish controller effects from plant instability and integration artifacts.

## Outcomes

For each simulation, retain:

- maximum absolute angle;
- maximum horizontal CoM excursion \(|l\sin\theta|\);
- maximum angular velocity;
- integrated squared control effort \(\int\tau_c^2dt\);
- time to enter and remain in a predefined mathematical stable region;
- first crossing time for predefined angle thresholds;
- finite/diverged status.

Use at least two stable-region/angle-threshold definitions as a sensitivity check. These are mathematical labels, not measured balance recovery or ground contact.

Stop integration after a large-angle threshold because the single fixed-pivot plant does not represent stepping, changing support, impact or post-contact dynamics.

## Reporting

For each perturbation scenario, summarize outcomes across its 88 controllers with the median, 5th percentile and 95th percentile. Plot:

- amplitude-duration recovery maps for each direction and activity;
- uncertainty width across the controller ensemble;
- representative trajectories near threshold transitions;
- outcome sensitivity to delay;
- controlled versus uncontrolled comparisons.

Use the title **model recovery envelope under assumed perturbations**. Any apparent boundary that changes substantially across controller delays or mathematical thresholds must be reported as uncertain.

## Interpretation gate

Stage 3A is successful if the implementation is numerically verified and clearly maps assumed inputs to model outcomes across uncertainty. It does not need to reproduce an unmeasured force.

The analysis must stop short of physiological claims if:

- outcomes are dominated by the chosen delay;
- boundaries change materially with the mathematical threshold;
- time-step convergence fails;
- many trajectories require behavior beyond the fixed-pivot model's valid region.

## Recommended implementation order

1. Implement and verify the delayed-PID simulator with an explicit rectangular pulse.
2. Run zero-input, uncontrolled and time-step convergence fixtures.
3. Freeze the 176 total activity-specific controller profiles.
4. Generate the 100 scenario manifest before running simulations.
5. Run the 8,800 ensemble simulations.
6. Export raw trajectories, scenario outcomes, uncertainty summaries and plots.
7. Review the interpretation gate before describing any recovery envelope.
