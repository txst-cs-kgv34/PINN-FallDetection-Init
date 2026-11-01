# Findings: S55 Stage-3 fixed-gain sweep

## Executive conclusion

Chunk 5 is the best setting by the primary combined ranking. It has the lowest pooled normalized MSE (`0.430774`) and the lowest x MSE (`175.175 cm^2`). Relative to chunk 1, it improves those metrics by 5.52% and 9.24%, respectively, while increasing theta MSE by 2.30%.

The result is a tradeoff, not a universal optimum. Chunk 11 has the best theta MSE and lowest Stage-3 objective, but its x MSE is worst and its combined normalized MSE ranks last. Chunk 10 is only 0.62% behind chunk 5 on normalized MSE and has an essentially identical pooled x Wasserstein distance. Because one-seed Stage-3 variability is larger than this gap, chunks 5 and 10 should be treated as the leading region rather than as a definitive first and second place.

## Best setting by metric

| Question | Best chunk | Result |
|:---|---:|---:|
| Best combined paired reconstruction | 5 | normalized MSE = **0.430774** |
| Best paired angle reconstruction | 11 | theta MSE = **87.120 deg^2** |
| Best paired forward-CoM reconstruction | 5 | x MSE = **175.175 cm^2** |
| Best pooled angle distribution match | 3 | theta W1 = **0.7910 deg** |
| Best pooled forward-CoM distribution match | 10 | x W1 = **0.9597 cm** |
| Best time-resolved angle distribution match | 3 | mean W1 = **1.3056 deg** |
| Best time-resolved forward-CoM distribution match | 5 | mean W1 = **1.8221 cm** |
| Lowest Stage-3 training objective | 11 | objective = **1206.80** |

No chunk wins both theta and x reconstruction.

## Complete combined ranking

All rows pool the same 624 samples from S55 T01-T05. Lower is better. `Pi = 3.625025 deg` and `tau = 0.23 s` are fixed for every row. The rank is determined only by normalized MSE; the objective is included for completeness and is not a reconstruction metric.

| Combined rank | Chunk | Gain source | Kp_theta | Kd_theta | Kp_x | Kd_x | Best Stage-3 objective | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta W1 (deg) | x W1 (cm) |
|---:|---:|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 44.4% interpolation | 187.30 | 21.70 | 8.59 | 21.70 | 2246.77 | **0.430774** | 94.059 | **175.175** | 0.8376 | 0.9599 |
| 2 | 10 | Subject-B endpoint | 240.00 | 30.00 | 13.00 | 30.00 | 3447.65 | 0.433449 | 94.779 | 176.127 | 0.8397 | **0.9597** |
| 3 | 8 | 77.8% interpolation | 218.92 | 26.68 | 11.24 | 26.68 | 3261.81 | 0.438054 | 92.794 | 180.990 | 0.7995 | 1.0931 |
| 4 | 9 | 88.9% interpolation | 229.46 | 28.34 | 12.12 | 28.34 | 3645.87 | 0.441614 | 94.553 | 181.456 | 0.8376 | 1.0157 |
| 5 | 7 | 66.7% interpolation | 208.38 | 25.02 | 10.35 | 25.02 | 2934.15 | 0.451218 | 92.615 | 189.396 | 0.7960 | 1.1249 |
| 6 | 4 | 33.3% interpolation | 176.76 | 20.04 | 7.71 | 20.04 | 2017.87 | 0.452036 | 93.037 | 189.485 | 0.8377 | 1.0335 |
| 7 | 1 | S55 identified | 145.15 | 15.05 | 5.06 | 15.05 | 1366.44 | 0.455919 | 91.941 | 193.008 | 0.8277 | 1.0674 |
| 8 | 6 | 55.6% interpolation | 197.84 | 23.36 | 9.47 | 23.36 | 1988.84 | 0.459489 | 90.978 | 196.202 | 0.7931 | 1.1556 |
| 9 | 3 | 22.2% interpolation | 166.22 | 18.37 | 6.82 | 18.37 | 1674.46 | 0.468489 | 89.869 | 202.936 | **0.7910** | 1.1581 |
| 10 | 2 | 11.1% interpolation | 155.69 | 16.71 | 5.94 | 16.71 | 2085.29 | 0.480435 | 91.717 | 208.555 | 0.8302 | 1.1633 |
| 11 | 11 | Comparison gains | 120.00 | 28.00 | 14.00 | 19.00 | **1206.80** | 0.499217 | **87.120** | 224.890 | 0.8197 | 1.1414 |

## Direct comparisons

Relative to chunk 1, chunk 5 has:

- 5.52% lower normalized MSE;
- 9.24% lower x MSE;
- 10.07% lower pooled x W1;
- 2.30% higher theta MSE;
- 1.20% higher pooled theta W1; and
- 64.43% higher Stage-3 objective.

Relative to the Subject-B endpoint in chunk 10, chunk 5 has 0.62% lower normalized MSE, 0.76% lower theta MSE, and 0.54% lower x MSE. Their pooled x W1 values differ by only `0.00014 cm`, with chunk 10 slightly lower. This is too small to support a strong practical distinction.

Chunk 11 illustrates the opposite tradeoff. Relative to chunk 5, it lowers theta MSE by 7.38% and the training objective by 46.29%, but raises normalized MSE by 15.89% and x MSE by 28.38%. It is therefore the angle-oriented setting, not the best combined controller.

## Trial-level winners

| Trial | Samples | Best normalized MSE | Best theta MSE | Best x MSE |
|:---|---:|:---|:---|:---|
| T01 | 147 | Chunk 5: 0.624181 | Chunk 11: 117.851 deg^2 | Chunk 5: 260.677 cm^2 |
| T02 | 54 | Chunk 10: 0.020574 | Chunk 3: 3.429 deg^2 | Chunk 10: 9.014 cm^2 |
| T03 | 136 | Chunk 5: 0.601416 | Chunk 11: 122.240 deg^2 | Chunk 5: 242.951 cm^2 |
| T04 | 134 | Chunk 5: 0.684797 | Chunk 11: 138.930 deg^2 | Chunk 5: 277.490 cm^2 |
| T05 | 153 | Chunk 5: 0.015541 | Chunk 5: 7.920 deg^2 | Chunk 8: 1.161 cm^2 |

For chunk 5, T01, T03, and T04 contribute 97.6% of theta squared error and 99.3% of x squared error. T02 and T05 are comparatively easy. The pooled ranking is therefore controlled almost entirely by the three difficult trials.

## Gain trend and optimization behavior

Across interpolation chunks 1-10, increasing the interpolation fraction is associated with lower normalized MSE (`r = -0.697`) and lower x MSE (`r = -0.708`), but higher theta MSE (`r = +0.650`). The Stage-3 objective rises strongly with interpolation (`r = +0.927`). This shows why the raw training objective cannot select the best time-aligned reconstruction.

The trend is not monotonic: chunk 5 beats several higher-gain chunks, and chunk 6 is worse than chunks 4 and 5. The sweep changes four gains together, so it cannot identify which gain pair causes the angle/translation tradeoff.

## Same-gain repeatability warning

The clean full run and sweep chunk 1 use the same identified gains and data, but Stage 3 entered from a different random-number history. Their results differ:

| Run with identical gains | Normalized MSE | Theta MSE | x MSE | Best objective |
|:---|---:|---:|---:|---:|
| Full-run Stage 3 | 0.483574 | 92.519 deg^2 | 209.715 cm^2 | 1726.20 |
| Sweep chunk 1 | 0.455919 | 91.941 deg^2 | 193.008 cm^2 | 1366.44 |

That is a 5.72% normalized-MSE and 7.97% x-MSE change without changing the gains. It is much larger than the 0.62% difference between chunks 5 and 10. Multiple-seed repeats are therefore required before declaring chunk 5 uniquely best.

## Trajectory and Wasserstein interpretation

Paired MSE compares time-aligned real and predicted values. Pooled W1 compares the distributions of values and ignores which trial and time generated each value. Time-resolved W1 compares the five-trial real and synthetic distributions at each time over the common 0.52 s window. These metrics can legitimately disagree.

The trajectory plots show that chunk 5 improves forward-CoM reconstruction for the difficult trials but still moves in the wrong late-window direction for T01, T03, and T04. T02 is short and roughly followed. T05 is tracked much more closely, although the late rise is underpredicted. The synthetic x curves remain much less diverse than the observed trials.

## Stage-3 objective

The objective combines weighted physics residual, measured-data, and initial/history terms. It has different scaling and meaning from normalized MSE. Chunk 11's lowest objective does not make it the best reconstruction, and chunk 5's relatively high objective does not prevent it from winning the paired metric. Controller selection for this experiment should therefore use the reconstruction metric tied to the scientific question, not the minimum raw objective alone.

## Reliability checks

- All 11 requested chunks completed with 5,000 finite loss rows each.
- Every chunk used batch size 4,096 and the same seed, fixed `Pi`, fixed `tau`, S55 Stage-1 checkpoint, and five S55 trials.
- Best epochs range from 4,137 to 4,969.
- Final-epoch loss is 1.54-3.68 times the minimum, but each packaged final checkpoint is byte-identical to its restored best checkpoint.
- Aggregate values agree with the per-chunk records.
- The sweep archive passed its integrity test.

## Recommendation

Carry chunks 5 and 10 into a multi-seed confirmation run, with chunk 1 as the S55 baseline and chunk 11 as the angle-oriented comparison. Report theta and x separately. If only one provisional setting must be chosen for generating an S55 teacher set, use chunk 5 because it minimizes the declared combined metric, but retain the warning that it remains 144.2 times worse than Stage 1's normalized reconstruction loss and is not yet a validated long-horizon human-motion model.
