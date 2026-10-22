# Stage 3 fixed-gain sweep results

Completed 11 of 11 requested chunks. Each chunk started from the same Stage 1 weights and used the original Stage 3 training function. Only the four Kp/Kd gains changed; Pi and tau remained fixed.

Chunk 11, the exact Subject A gain set, has the lowest pooled normalized MSE (`1.09499`) and x MSE (`442.04 cm^2`). It also has the highest theta MSE (`242.33 deg^2`) and theta W1 (`3.863 deg`). The result is therefore a forward-CoM improvement with an angle tradeoff, not a uniform reconstruction improvement.

## Ranked pooled reconstruction metrics

| Rank | Chunk | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta pooled W1 (deg) | x pooled W1 (cm) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 11 | 1.094987 | 242.331512 | 442.035492 | 3.863256 | 5.197951 |
| 2 | 1 | 1.238019 | 212.641998 | 561.119629 | 3.599742 | 6.246578 |
| 3 | 5 | 1.246065 | 217.827454 | 560.963196 | 3.454927 | 5.930527 |
| 4 | 6 | 1.260837 | 215.266159 | 572.756653 | 3.593385 | 5.984454 |
| 5 | 2 | 1.261927 | 211.114410 | 577.589905 | 3.615781 | 6.692936 |
| 6 | 3 | 1.269347 | 213.766464 | 579.575623 | 3.528518 | 6.453306 |
| 7 | 4 | 1.275084 | 221.240189 | 575.687561 | 3.422683 | 5.991821 |
| 8 | 8 | 1.275158 | 216.410950 | 580.562683 | 3.551129 | 5.914120 |
| 9 | 10 | 1.278162 | 214.627365 | 584.223938 | 3.530962 | 5.932947 |
| 10 | 9 | 1.295477 | 215.387161 | 594.285645 | 3.602893 | 6.039833 |
| 11 | 7 | 1.304078 | 209.263550 | 605.785461 | 3.610101 | 6.667836 |

Compared with chunk 1, chunk 11 reduces normalized MSE by 11.55% and x MSE by 21.22%, while increasing theta MSE by 13.96%. T03 contributes 90.69% of chunk 11's pooled x squared error and is the main reason the pooled x result improves. T02 and T04 are worse under chunk 11, so the gain preference is trial-dependent.

The Wasserstein figures show real and synthetic means, their ranges, time-resolved W1 distribution distance, and absolute difference between the means. W1 measures distribution displacement and does not replace paired trajectory MSE. See the parent `FINDINGS.md` for the full analysis and limitations.
