# Findings: Stage 3 fixed-gain sweep

## Executive conclusion

The exact Subject A Kp/Kd values in chunk 11 produce the lowest pooled normalized MSE (`1.09499`) and the lowest forward-CoM MSE (`442.04 cm^2`) of all eleven settings. Relative to chunk 1, the previous overall winner, those metrics improve by 11.55% and 21.22%, respectively.

The improvement is specific to translation. Chunk 11 raises angle MSE by 13.96% relative to chunk 1 and is worst among all chunks for angle MSE, pooled angle W1, mean time-resolved angle W1, and time-mean angle mean difference. It is therefore accurate to call the Subject A result promising for forward-CoM reconstruction, but not to call it the best controller overall without stating the angle tradeoff.

## Best setting by metric

| Question | Best chunk | Result |
|:---|---:|---:|
| Best combined paired reconstruction | 11 | normalized MSE = **1.09499** |
| Best paired angle reconstruction | 7 | theta MSE = **209.26 deg^2** |
| Best paired forward-CoM reconstruction | 11 | x MSE = **442.04 cm^2** |
| Best pooled angle distribution match | 4 | theta W1 = **3.423 deg** |
| Best pooled forward-CoM distribution match | 11 | x W1 = **5.198 cm** |
| Best time-resolved angle distribution match | 4 | mean W1 = **3.759 deg** |
| Best time-resolved forward-CoM distribution match | 11 | mean W1 = **5.524 cm** |
| Closest angle means over time | 4 | mean absolute difference = **2.572 deg** |
| Closest forward-CoM means over time | 11 | mean absolute difference = **3.517 cm** |

No chunk wins both the angle and forward-CoM metrics.

## Ranked combined reconstruction

All values below pool the same 1,522 samples from T02-T05. Lower is better.

| Combined rank | Chunk | Gain source | Kp_theta | Kd_theta | Kp_x | Kd_x | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta W1 (deg) | x W1 (cm) |
|---:|---:|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 11 | Subject A | 120.00 | 28.00 | 14.00 | 19.00 | **1.094987** | 242.3315 | **442.0355** | 3.8633 | **5.1980** |
| 2 | 1 | S43 endpoint | 145.14 | 15.03 | 5.04 | 15.05 | 1.238019 | 212.6420 | 561.1196 | 3.5997 | 6.2466 |
| 3 | 5 | Interpolation | 187.30 | 21.69 | 8.58 | 21.69 | 1.246065 | 217.8275 | 560.9632 | 3.4549 | 5.9305 |
| 4 | 6 | Interpolation | 197.84 | 23.35 | 9.46 | 23.35 | 1.260837 | 215.2662 | 572.7567 | 3.5934 | 5.9845 |
| 5 | 2 | Interpolation | 155.68 | 16.70 | 5.93 | 16.71 | 1.261927 | 211.1144 | 577.5899 | 3.6158 | 6.6929 |
| 6 | 3 | Interpolation | 166.22 | 18.36 | 6.81 | 18.37 | 1.269347 | 213.7665 | 579.5756 | 3.5285 | 6.4533 |
| 7 | 4 | Interpolation | 176.76 | 20.02 | 7.70 | 20.03 | 1.275084 | 221.2402 | 575.6876 | **3.4227** | 5.9918 |
| 8 | 8 | Interpolation | 218.92 | 26.67 | 11.23 | 26.68 | 1.275158 | 216.4110 | 580.5627 | 3.5511 | 5.9141 |
| 9 | 10 | Subject B | 240.00 | 30.00 | 13.00 | 30.00 | 1.278162 | 214.6274 | 584.2239 | 3.5310 | 5.9329 |
| 10 | 9 | Interpolation | 229.46 | 28.34 | 12.12 | 28.34 | 1.295477 | 215.3872 | 594.2856 | 3.6029 | 6.0398 |
| 11 | 7 | Interpolation | 208.38 | 25.01 | 10.35 | 25.02 | 1.304078 | **209.2636** | 605.7855 | 3.6101 | 6.6678 |

## Direct comparisons

Relative to the S43-identified gains in chunk 1, chunk 11 has:

- 11.55% lower normalized MSE;
- 21.22% lower x MSE;
- 16.79% lower pooled x W1 and 43.99% lower time-mean x mean difference;
- 13.96% higher theta MSE;
- 7.32% higher pooled theta W1 and 13.11% higher time-mean theta mean difference.

Relative to the Subject B gains in chunk 10, chunk 11 has 14.33% lower normalized MSE and 24.34% lower x MSE, but 12.91% higher theta MSE. Thus, Subject A gains are clearly preferable to Subject B gains when forward-CoM or combined MSE is the priority on these S43 trials, while Subject B remains better for angle reconstruction.

Chunk 11 also expands the total sensitivity range. Across all eleven settings, the best-to-worst normalized-MSE difference is 16.03% relative to the worst value; this is substantially larger than the 5.34% spread observed among chunks 1-10.

## Chunk 11 by trial

| Trial | Samples | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Standing among 11 chunks |
|:---|---:|---:|---:|---:|:---|
| T02 | 502 | 0.18047 | 29.28 | 83.52 | Worst for all three metrics. |
| T03 | 440 | **3.46584** | 779.51 | **1,386.63** | Best combined and x MSE; worst theta MSE. |
| T04 | 310 | 0.10287 | 11.17 | 53.13 | Near-best theta MSE, but worst combined and x MSE. |
| T05 | 270 | **0.07080** | 28.46 | **15.79** | Best combined and x MSE; worst theta MSE. |
| Pooled | 1,522 | **1.09499** | 242.33 | **442.04** | Best combined and x; worst theta. |

T03 contributes 92.99% of chunk 11's theta squared error and 90.69% of its x squared error while containing only 28.9% of the samples. The pooled ranking is therefore driven mainly by the large reduction in T03 forward-CoM error. Chunk 11 is not uniformly better: it improves T03 and T05 translation but degrades T02 and T04.

## Interpretation of the trajectory and Wasserstein figures

Paired MSE and W1 answer different questions:

- Paired MSE measures time-aligned error between each real trial and its corresponding simulation.
- Pooled W1 measures the displacement between all real and synthetic values after pooling; it ignores which trial and time produced each value.
- Time-resolved W1 compares the real and synthetic four-trial distributions at every time. Its horizontal mean line summarizes the average height of that W1 curve over the shared 2.69 s window.
- Absolute mean difference measures only separation of the two mean curves. W1 can be larger because it also detects different spread and distribution shape.

In chunk 11's means-and-distances plot, the synthetic angle mean drifts negative late while the real mean turns positive. The angle W1 and mean-difference curves rise accordingly, explaining the worst angle-distribution scores. The synthetic forward-CoM mean is closer to the real mean, which explains the strong x metrics. However, x W1 still rises late because the four synthetic trajectories do not reproduce the real across-trial spread even where their means are relatively close.

The trial plot explains the aggregate result: T03 still diverges strongly but its x error is much smaller than under every other gain setting; T05 also improves in x. T02 shows larger oscillation/overshoot, and T04 develops substantial x error. This is why the combined score improves while two trials get worse.

## Stage 3 objective versus reconstruction

The Stage 3 best objective is a weighted sum of physics residual, real-data, and history/initial-condition terms. It is not the reported trajectory MSE and has different units and scaling.

Chunk 11's best objective is `437.58`, which is higher than chunk 1's `354.24`, even though chunk 11 has better post-training combined reconstruction. Conversely, chunk 10 has a much larger objective (`905.43`) while its angle MSE is better than chunk 11. Model selection for this question should therefore use the matched reconstruction metrics, not the raw Stage 3 loss magnitude.

## Reliability checks

- All 11 requested chunks completed.
- Every chunk used 5,000 Stage 3 epochs and batch size 4,096.
- `Pi = 3.6066 deg` and `tau = 0.23 s` stayed fixed.
- Every chunk contains four matched synthetic trajectory CSVs, one for each real trial.
- Every chunk contains five MSE rows (four trials plus pooled), 270 time-resolved rows, and 5,000 finite loss-history rows.
- Each saved best objective agrees with the minimum in its loss history.
- Aggregate CSV values agree with the corresponding per-chunk JSON records.
- Chunk 11's best checkpoint occurred at epoch 4,399 and was restored before evaluation; its final-epoch loss was higher, as expected in a noisy optimization.

## Limitations and next experiment

This experiment changes all four gains together, so it cannot identify whether the observed tradeoff comes from the theta gains, the x gains, or their interaction. It also uses one deterministic seed per setting. Finally, Subject A controller gains are applied to S43 data; this tests parameter transfer, not subject-matched motion reconstruction.

The most informative follow-up is to vary the angle-gain pair and position-gain pair separately, repeat the strongest settings across several seeds, and inspect T03 alignment and initial conditions because T03 dominates the pooled score.

## Advisor-ready takeaway

Using Subject A's Kp/Kd values in the same Stage 3 pipeline is promising for forward-CoM reconstruction: it gives the lowest combined MSE and improves x MSE by 21.22% over the previous best chunk. The gain set does not improve the whole reconstruction, because angle error and angle Wasserstein distance are the worst of all tested settings, and T02/T04 become worse. The defensible conclusion is that Subject A gains provide a strong translation-oriented setting whose benefit is mostly driven by T03, while a different or separately tuned theta-gain pair is needed to preserve angle accuracy.
