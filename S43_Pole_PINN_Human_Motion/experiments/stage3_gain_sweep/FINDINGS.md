# Findings: Stage 3 fixed-gain sweep

## Executive conclusion

The ten-run experiment supports using the S43-specific controller rather than substituting the Subject A paper controller for this subject. Chunk 1, the S43-identified endpoint, has the lowest pooled normalized MSE (`1.2380`). Chunk 10, the Subject A endpoint, is eighth (`1.2782`), 3.24% higher than chunk 1.

There is no single gain set that wins every metric:

| Question | Best chunk | Result |
|:---|---:|---:|
| Best combined paired reconstruction | 1 | normalized MSE = **1.2380** |
| Best paired angle reconstruction | 7 | theta MSE = **209.26 deg^2** |
| Best paired forward-CoM reconstruction | 5 | x MSE = **560.96 cm^2** |
| Best pooled angle distribution match | 4 | theta W1 = **3.423 deg** |
| Best pooled forward-CoM distribution match | 8 | x W1 = **5.914 cm** |
| Best time-resolved angle distribution match | 4 | mean time-resolved W1 = **3.759 deg** |
| Best time-resolved forward-CoM distribution match | 5 | mean time-resolved W1 = **6.457 cm** |

This is a genuine angle-versus-translation and paired-error-versus-distribution tradeoff. Therefore, the report should not call any W1 winner the "best reconstruction" without naming the metric.

## All ten chunks

All values below are pooled over the same 1,522 samples from T02-T05. Lower is better.

| Combined rank | Chunk | Kp_theta | Kd_theta | Kp_x | Kd_x | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta W1 (deg) | x W1 (cm) | Interpretation |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| 1 | 1 | 145.14 | 15.03 | 5.04 | 15.05 | **1.2380** | 212.64 | 561.12 | 3.600 | 6.247 | Best combined result; S43 endpoint. |
| 2 | 5 | 187.30 | 21.69 | 8.58 | 21.69 | **1.2461** | 217.83 | **560.96** | 3.455 | 5.931 | Best x MSE and a close overall second. |
| 3 | 6 | 197.84 | 23.35 | 9.46 | 23.35 | 1.2608 | 215.27 | 572.76 | 3.593 | 5.984 | Balanced third-place result. |
| 4 | 2 | 155.68 | 16.70 | 5.93 | 16.71 | 1.2619 | 211.11 | 577.59 | 3.616 | 6.693 | Good angle MSE; weakest pooled W1. |
| 5 | 3 | 166.22 | 18.36 | 6.81 | 18.37 | 1.2693 | 213.77 | 579.58 | 3.529 | 6.453 | Mid-ranked across the main metrics. |
| 6 | 4 | 176.76 | 20.02 | 7.70 | 20.03 | 1.2751 | 221.24 | 575.69 | **3.423** | 5.992 | Best theta W1 but worst theta MSE. |
| 7 | 8 | 218.92 | 26.67 | 11.23 | 26.68 | 1.2752 | 216.41 | 580.56 | 3.551 | **5.914** | Best pooled x W1; middling paired MSE. |
| 8 | 10 | 240.00 | 30.00 | 13.00 | 30.00 | 1.2782 | 214.63 | 584.22 | 3.531 | 5.933 | Paper endpoint; does not beat the S43 endpoint. |
| 9 | 9 | 229.46 | 28.34 | 12.12 | 28.34 | 1.2955 | 215.39 | 594.29 | 3.603 | 6.040 | High x error lowers the combined rank. |
| 10 | 7 | 208.38 | 25.01 | 10.35 | 25.02 | 1.3041 | **209.26** | 605.79 | 3.610 | 6.668 | Best theta MSE but worst x and combined MSE. |

## What changed as gains increased

The sweep does not show a smooth optimum along the line between the two endpoints. Normalized MSE rises overall with interpolation fraction (`r = 0.66`), but local reversals are large: chunks 5 and 6 improve over chunks 3 and 4, and chunk 10 improves over chunks 7 and 9.

The total best-to-worst spread is modest:

- normalized MSE: 1.2380 to 1.3041, a 5.34% spread relative to the minimum;
- theta MSE: 209.26 to 221.24 deg^2, a 5.72% spread;
- x MSE: 560.96 to 605.79 cm^2, a 7.99% spread.

This means the controller gains affect reconstruction, but the choice among these ten gain sets is not the main source of the remaining error. The synthetic mean trajectories still diverge from the real means late in the common 2.69 s window, particularly in forward CoM.

## Trial-level result

The gain preference is trial-dependent:

| Trial | Best normalized MSE | Best theta MSE | Best x MSE |
|:---|:---|:---|:---|
| T02 | chunk 1: **0.06089** | chunk 2: **15.84 deg^2** | chunk 1: **21.51 cm^2** |
| T03 | chunk 5: **4.09304** | chunk 7: **682.85 deg^2** | chunk 5: **1845.69 cm^2** |
| T04 | chunk 7: **0.02433** | chunk 7: **10.83 deg^2** | chunk 2: **4.01 cm^2** |
| T05 | chunk 4: **0.14188** | chunk 4: **19.53 deg^2** | chunk 4: **69.14 cm^2** |

T03 is the dominant source of pooled error. It contains 28.9% of the samples but contributes 94.29-94.55% of theta squared error and 94.65-96.01% of x squared error, depending on the chunk. Consequently, the pooled normalized-MSE ranking is mostly a ranking of how each controller handles T03. This should be stated whenever the pooled result is presented.

## How to interpret MSE and Wasserstein-1 together

The metrics answer different questions:

- **Paired MSE** compares each synthetic trajectory with its matching real trial at the same time points. It measures whether the simulation follows the correct trajectory.
- **Pooled W1** compares all real samples with all synthetic samples after pooling. It measures distributional displacement in the original unit but discards trial and time pairing.
- **Time-resolved W1** compares the four real trial values with the four matched synthetic values at each time, then the reported line is the mean of those distances over the shared 2.69 s interval.
- **Absolute mean difference** compares only the real and synthetic means. It can be smaller than W1 because W1 also responds to spread and shape differences.

The observed disagreement is expected. Chunk 4 has the lowest theta W1 but the highest theta MSE, and chunk 8 has the lowest pooled x W1 while chunk 5 has the lowest x MSE. A distribution can be in the right overall region while individual simulated trajectories are paired incorrectly or diverge at the wrong times.

The per-chunk means-and-distances plots add the missing context from the earlier W1-only plots: they show the real and synthetic means, their ranges, the instantaneous W1 curve, and the absolute mean difference on the same time base. For chunk 1, both angle and forward-CoM distances increase strongly late in the window, matching the visible separation of the mean curves.

## Stage 3 objective versus reconstruction error

The Stage 3 training objective is not the same quantity as the reported reconstruction MSE. It combines weighted physics residual, real-data, and history/initial-condition terms, with different units and scaling. The best Stage 3 objective therefore should not be interpreted as a physical trajectory MSE.

Across these ten runs, the best Stage 3 objective and normalized reconstruction MSE have only a moderate association (`r = 0.63`). Model selection for the advisor's question should use the post-training matched reconstruction metrics, not the raw Stage 3 objective magnitude.

## Reliability checks

- 10 of 10 requested chunks completed.
- Every chunk used 5,000 Stage 3 epochs and batch size 4,096.
- `Pi = 3.6066 deg` and `tau = 0.23 s` stayed fixed.
- Every chunk has exactly four matched synthetic trajectory CSVs.
- Every chunk has 5,000 finite loss-history entries and 270 time-resolved comparison rows.
- Each saved best checkpoint's objective agrees with the minimum in its loss history.
- Aggregate CSV values agree with the corresponding per-chunk JSON records.

## Limitations and next experiment

This sweep changes all four gains together along one interpolation line. It cannot determine which individual gain caused a change. It also uses one deterministic seed per setting, so the small 0.65% difference between chunks 1 and 5 may not be robust to optimization randomness.

The highest-value follow-up is:

1. Diagnose T03 separately for alignment, onset marking, initial state, and range because it dominates the pooled result.
2. Repeat chunks 1 and 5 over multiple seeds to quantify optimization variability.
3. If the result is stable, run a small local grid around chunks 1 and 5, varying the theta and x gain pairs separately rather than moving all four gains together.

Until that follow-up, chunk 1 is the defensible overall choice, chunk 5 is the forward-CoM alternative, and chunk 7 should only be selected if angle MSE is explicitly prioritized over forward-CoM accuracy.
