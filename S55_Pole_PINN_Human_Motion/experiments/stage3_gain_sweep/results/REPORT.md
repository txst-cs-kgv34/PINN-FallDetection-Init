# Stage-3 fixed-gain sweep results

Completed 11 of 11 requested chunks.

Each chunk started from the same Stage-1 weights and used the original Stage-3 training function. Only the four Kp/Kd gains changed. Pi and tau remained fixed.

The current minimum pooled normalized MSE is chunk 5 at 0.430774.

## Ranked pooled reconstruction metrics

| Rank | Chunk | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta pooled W1 (deg) | x pooled W1 (cm) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 0.430774 | 94.058746 | 175.175323 | 0.837649 | 0.959870 |
| 2 | 10 | 0.433449 | 94.778809 | 176.126984 | 0.839739 | 0.959732 |
| 3 | 8 | 0.438054 | 92.794006 | 180.989639 | 0.799454 | 1.093087 |
| 4 | 9 | 0.441614 | 94.553154 | 181.455658 | 0.837637 | 1.015734 |
| 5 | 7 | 0.451218 | 92.615097 | 189.396439 | 0.796049 | 1.124886 |
| 6 | 4 | 0.452036 | 93.036873 | 189.485352 | 0.837666 | 1.033461 |
| 7 | 1 | 0.455919 | 91.941444 | 193.008133 | 0.827737 | 1.067401 |
| 8 | 6 | 0.459489 | 90.978455 | 196.202316 | 0.793140 | 1.155598 |
| 9 | 3 | 0.468489 | 89.869072 | 202.936401 | 0.791017 | 1.158150 |
| 10 | 2 | 0.480435 | 91.717438 | 208.554581 | 0.830198 | 1.163311 |
| 11 | 11 | 0.499217 | 87.120102 | 224.890381 | 0.819713 | 1.141402 |

The Wasserstein figures show both real and synthetic means, their ranges, the time-resolved W1 distribution distance, and the absolute difference between the means. W1 and mean difference answer different questions and are labeled separately.
