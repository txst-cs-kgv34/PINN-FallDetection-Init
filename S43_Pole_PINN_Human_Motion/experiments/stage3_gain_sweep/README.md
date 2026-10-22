# Stage 3 fixed-gain sweep: completed results

This package contains the completed eleven-setting sensitivity experiment for the unchanged pole-PINN Stage 3 forward block on the same S43 A11 data (trials T02-T05).

## Controlled design

- Every chunk starts from the same saved Stage 1 weights and uses the same Stage 3 architecture, equations, losses, seed, 5,000 epochs, and batch size of 4,096.
- `Pi = 3.6066 deg` and `tau = 0.23 s` remain fixed.
- Only `Kp_theta`, `Kd_theta`, `Kp_x`, and `Kd_x` change.
- Chunks 1-10 interpolate from the S43-identified gains to the Subject B paper gains.
- Chunk 11 uses the exact Subject A paper gains: `Kp_theta=120`, `Kd_theta=28`, `Kp_x=14`, `Kd_x=19`.
- The experiment uses Subject A's gains with the S43 trial data; it is not a simulation of Subject A's recorded motion.

The paper also reports `Pi=1.75` for Subject A, but it is deliberately not used here because the requested experiment changes Kp/Kd only. This preserves a controlled comparison with the earlier ten chunks.

## Main result

Chunk 11 is first by pooled normalized MSE (`1.09499`) and has the lowest forward-CoM MSE (`442.04 cm^2`). Compared with chunk 1, the previous overall winner, its normalized MSE is 11.55% lower and its forward-CoM MSE is 21.22% lower.

This is not an across-the-board improvement. Chunk 11 has the highest angle MSE (`242.33 deg^2`) and the largest angle Wasserstein distances. The Subject A gains therefore improve translation while sacrificing angle reconstruction and angle-distribution agreement.

## All eleven chunks

All values are pooled over the same 1,522 measured samples. Lower is better.

| Chunk | Gain source | Kp_theta | Kd_theta | Kp_x | Kd_x | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta W1 (deg) | x W1 (cm) | Takeaway |
|---:|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| 1 | S43 endpoint | 145.14 | 15.03 | 5.04 | 15.05 | 1.2380 | 212.64 | 561.12 | 3.600 | 6.247 | Second overall after adding Subject A. |
| 2 | Interpolation | 155.68 | 16.70 | 5.93 | 16.71 | 1.2619 | 211.11 | 577.59 | 3.616 | 6.693 | Strong angle MSE, weakest x W1. |
| 3 | Interpolation | 166.22 | 18.36 | 6.81 | 18.37 | 1.2693 | 213.77 | 579.58 | Mid-ranked; no metric minimum. |
| 4 | Interpolation | 176.76 | 20.02 | 7.70 | 20.03 | 1.2751 | 221.24 | 575.69 | **3.423** | 5.992 | Best theta W1, despite relatively high theta MSE. |
| 5 | Interpolation | 187.30 | 21.69 | 8.58 | 21.69 | 1.2461 | 217.83 | 560.96 | 3.455 | 5.931 | Third overall; previous best x MSE. |
| 6 | Interpolation | 197.84 | 23.35 | 9.46 | 23.35 | 1.2608 | 215.27 | 572.76 | 3.593 | 5.984 | Balanced fourth-place result. |
| 7 | Interpolation | 208.38 | 25.01 | 10.35 | 25.02 | 1.3041 | **209.26** | 605.79 | 3.610 | 6.668 | Best theta MSE, but worst combined and x MSE. |
| 8 | Interpolation | 218.92 | 26.67 | 11.23 | 26.68 | 1.2752 | 216.41 | 580.56 | 3.551 | 5.914 | Second-best pooled x W1. |
| 9 | Interpolation | 229.46 | 28.34 | 12.12 | 28.34 | 1.2955 | 215.39 | 594.29 | 3.603 | 6.040 | High x error lowers the combined rank. |
| 10 | Subject B | 240.00 | 30.00 | 13.00 | 30.00 | 1.2782 | 214.63 | 584.22 | 3.531 | 5.933 | Subject B endpoint; ninth overall. |
| 11 | Subject A | 120.00 | 28.00 | 14.00 | 19.00 | **1.0950** | 242.33 | **442.04** | 3.863 | **5.198** | Best combined and x result; worst theta result. |

## Trial dependence

The pooled result is dominated by T03: in chunk 11 it contributes 92.99% of theta squared error and 90.69% of x squared error, although it contains 28.9% of the samples. Chunk 11 improves T03 and T05 combined reconstruction but is the worst chunk for T02 and T04 normalized MSE. Therefore, the aggregate win should be described as a T03-driven improvement rather than a uniform improvement across all trials.

## How to read the metrics and figures

- Paired MSE asks whether each simulated trial follows its matching real trajectory at the same times.
- Pooled Wasserstein-1 (W1) asks how far the overall real and synthetic value distributions are displaced, in degrees or centimeters. It discards trial and time pairing.
- Time-resolved W1 compares the four real values and four synthetic values at every common time point; its reported mean is the average of that distance curve.
- Absolute mean difference compares only the real and synthetic means. W1 can remain high when the means are close because it also responds to differences in spread and distribution shape.

For chunk 11, the angle mean increasingly separates from the real mean late in the window, so angle W1 and mean difference rise. The forward-CoM mean is closer, but late-time x W1 still rises because the real and synthetic trial distributions have different spread.

See [`FINDINGS.md`](FINDINGS.md) for ranked comparisons, the per-trial analysis, limitations, and the advisor-ready conclusion. The `results/` directory contains the aggregate tables and plots; each `chunk_N/` directory contains its per-trial metrics, trajectories, time-resolved distances, figures, loss history, and checkpoints.

## Scope

These synthetic curves are matched forward simulations used for controller-sensitivity evaluation. They are different from the earlier set of 100 trajectories generated from random initial angles.
