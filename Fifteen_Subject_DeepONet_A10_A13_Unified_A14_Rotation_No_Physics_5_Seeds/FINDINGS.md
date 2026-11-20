# Baseline design

- This condition is intentionally identical to the physics experiment except for disabling both physics losses.
- The unified planar baseline uses the same 257 A10–A13 trials, including 64 A11 frontfalls.
- The rotation baseline uses the same 49 A14 trials and predicts yaw, but receives no CartPole or yaw-residual penalty.
- The comparison script refuses to run if the two experiment configurations differ beyond the intended physics switches.
- Negative `physics_minus_baseline` error values indicate that physics improved the metric.
