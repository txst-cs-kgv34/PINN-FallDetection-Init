# Stage-3 fixed-gain sweep results

Completed 11 of 11 requested chunks.

Each chunk started from the same Stage-1 weights and used the original Stage-3 training function. Only the four Kp/Kd gains changed. Pi and tau remained fixed.

The current minimum pooled normalized MSE is chunk 11 at 0.212552.

## Ranked pooled reconstruction metrics

| Rank | Chunk | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta pooled W1 (deg) | x pooled W1 (cm) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 11 | 0.212552 | 59.265709 | 73.579361 | 0.911109 | 1.050921 |
| 2 | 1 | 0.236283 | 66.456268 | 81.220856 | 0.910776 | 1.039249 |
| 3 | 2 | 0.247260 | 66.168190 | 88.369179 | 0.912349 | 1.047366 |
| 4 | 6 | 0.252705 | 60.641453 | 97.299286 | 0.910300 | 1.088753 |
| 5 | 3 | 0.254827 | 65.580177 | 93.686630 | 0.909235 | 1.061143 |
| 6 | 5 | 0.259771 | 65.953201 | 96.403831 | 0.911739 | 1.079035 |
| 7 | 4 | 0.261895 | 67.050415 | 96.634224 | 0.910574 | 1.063838 |
| 8 | 8 | 0.272950 | 58.713783 | 111.879875 | 0.909476 | 1.084618 |
| 9 | 7 | 0.273114 | 59.046078 | 111.650345 | 0.910436 | 1.085742 |
| 10 | 9 | 0.284035 | 63.451591 | 114.070442 | 0.911081 | 1.080312 |
| 11 | 10 | 0.377634 | 53.714981 | 182.306335 | 0.909530 | 1.080116 |

The Wasserstein figures show both real and synthetic means, their ranges, the time-resolved W1 distribution distance, and the absolute difference between the means. W1 and mean difference answer different questions and are labeled separately.
