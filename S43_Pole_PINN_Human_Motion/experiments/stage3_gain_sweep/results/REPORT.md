# Stage-3 fixed-gain sweep results

Completed 10 of 10 requested chunks.

Each chunk started from the same Stage-1 weights and used the original Stage-3 training function. Only the four Kp/Kd gains changed. Pi and tau remained fixed.

The current minimum pooled normalized MSE is chunk 1 at 1.23802.

## Ranked pooled reconstruction metrics

| Rank | Chunk | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta pooled W1 (deg) | x pooled W1 (cm) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 1.238019 | 212.641998 | 561.119629 | 3.599742 | 6.246578 |
| 2 | 5 | 1.246065 | 217.827454 | 560.963196 | 3.454927 | 5.930527 |
| 3 | 6 | 1.260837 | 215.266159 | 572.756653 | 3.593385 | 5.984454 |
| 4 | 2 | 1.261927 | 211.114410 | 577.589905 | 3.615781 | 6.692936 |
| 5 | 3 | 1.269347 | 213.766464 | 579.575623 | 3.528518 | 6.453306 |
| 6 | 4 | 1.275084 | 221.240189 | 575.687561 | 3.422683 | 5.991821 |
| 7 | 8 | 1.275158 | 216.410950 | 580.562683 | 3.551129 | 5.914120 |
| 8 | 10 | 1.278162 | 214.627365 | 584.223938 | 3.530962 | 5.932947 |
| 9 | 9 | 1.295477 | 215.387161 | 594.285645 | 3.602893 | 6.039833 |
| 10 | 7 | 1.304078 | 209.263550 | 605.785461 | 3.610101 | 6.667836 |

The Wasserstein figures show both real and synthetic means, their ranges, the time-resolved W1 distribution distance, and the absolute difference between the means. W1 and mean difference answer different questions and are labeled separately.
