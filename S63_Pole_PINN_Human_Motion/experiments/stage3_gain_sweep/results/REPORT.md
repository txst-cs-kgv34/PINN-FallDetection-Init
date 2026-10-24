# Stage-3 fixed-gain sweep results

Completed 11 of 11 requested chunks.

Each chunk started from the same Stage-1 weights and used the original Stage-3 training function. Only the four Kp/Kd gains changed. Pi and tau remained fixed.

The current minimum pooled normalized MSE is chunk 6 at 0.103263.

## Ranked pooled reconstruction metrics

| Rank | Chunk | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta pooled W1 (deg) | x pooled W1 (cm) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6 | 0.103263 | 36.789860 | 27.749422 | 0.492094 | 0.663246 |
| 2 | 7 | 0.103304 | 34.603489 | 29.961653 | 0.489712 | 0.632277 |
| 3 | 11 | 0.103816 | 37.050510 | 27.834713 | 0.498107 | 0.513477 |
| 4 | 10 | 0.105267 | 36.003460 | 29.788380 | 0.498344 | 0.461642 |
| 5 | 5 | 0.105910 | 35.566185 | 30.627422 | 0.493898 | 0.664350 |
| 6 | 8 | 0.106734 | 34.524895 | 32.183651 | 0.500697 | 0.446004 |
| 7 | 9 | 0.107154 | 36.428268 | 30.543192 | 0.505005 | 0.497499 |
| 8 | 3 | 0.108744 | 35.355808 | 32.609234 | 0.497805 | 0.671868 |
| 9 | 2 | 0.109965 | 36.366695 | 32.361698 | 0.496112 | 0.679595 |
| 10 | 4 | 0.114410 | 36.363548 | 35.142574 | 0.501670 | 0.627420 |
| 11 | 1 | 0.127258 | 30.677313 | 48.859226 | 0.506583 | 0.370996 |

The Wasserstein figures show both real and synthetic means, their ranges, the time-resolved W1 distribution distance, and the absolute difference between the means. W1 and mean difference answer different questions and are labeled separately.
