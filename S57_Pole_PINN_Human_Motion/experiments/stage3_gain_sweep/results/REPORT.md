# Stage-3 fixed-gain sweep results

Completed 11 of 11 requested chunks.

Each chunk started from the same Stage-1 weights and used the original Stage-3 training function. Only the four Kp/Kd gains changed. Pi and tau remained fixed.

The current minimum pooled normalized MSE is chunk 10 at 1.0988.

## Ranked pooled reconstruction metrics

| Rank | Chunk | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta pooled W1 (deg) | x pooled W1 (cm) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 1.098801 | 394.278351 | 292.472534 | 10.768260 | 4.152714 |
| 2 | 9 | 1.106994 | 386.261047 | 305.609924 | 10.716105 | 4.297771 |
| 3 | 7 | 1.133747 | 376.798431 | 331.793579 | 10.585139 | 4.847275 |
| 4 | 8 | 1.139441 | 376.638733 | 335.511688 | 10.602080 | 4.777563 |
| 5 | 6 | 1.159551 | 378.665009 | 346.054291 | 10.587289 | 5.100341 |
| 6 | 5 | 1.164884 | 375.142792 | 352.909607 | 10.547939 | 5.252652 |
| 7 | 4 | 1.177343 | 377.356720 | 358.482849 | 10.570144 | 5.317664 |
| 8 | 3 | 1.222913 | 370.989197 | 393.331421 | 10.423153 | 6.041682 |
| 9 | 1 | 1.258779 | 346.024902 | 440.712128 | 10.123972 | 6.775072 |
| 10 | 2 | 1.262991 | 347.858978 | 441.510681 | 10.140207 | 6.784008 |
| 11 | 11 | 1.286592 | 381.283813 | 422.836060 | 10.514194 | 6.563809 |

The Wasserstein figures show both real and synthetic means, their ranges, the time-resolved W1 distribution distance, and the absolute difference between the means. W1 and mean difference answer different questions and are labeled separately.
