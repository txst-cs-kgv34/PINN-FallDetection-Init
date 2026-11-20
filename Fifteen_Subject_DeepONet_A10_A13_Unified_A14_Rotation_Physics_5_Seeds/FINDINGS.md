# Experiment design findings

- The exact earlier delayed CartPole residual is retained for theta/x. It is not replaced with a simplified pendulum equation.
- A10–A13 share one operator because direction alignment places each fall in a common planar coordinate system. Activity, subject characteristics, and fall direction remain explicit conditioning variables.
- A11 frontfall contributes 64 strict-primary trials.
- A14 is trained separately. Its model retains the CartPole residual for the falling component and adds a delayed yaw residual.
- The physics and no-physics folders use identical trial filters, preprocessing, folds, optimization seeds, model widths, and early-stopping rules. Only the physics-loss switches and weights differ.
- Repaired frames and the final 0.03 s at apparent contact are excluded from physics losses. Incomplete falls and unavailable trials are not training samples.
- A14 has 49 strict-primary trials from 14 subjects; S34 has no eligible A14 trial. Aggregation therefore uses every eligible A14 subject rather than inventing an S34 sample.
