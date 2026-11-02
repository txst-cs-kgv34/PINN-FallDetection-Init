# Findings: S62 Stage 3 fixed-gain sweep

## Executive conclusion

All 11 fixed-gain experiments completed successfully. The lowest pooled normalized reconstruction MSE is produced by **chunk 11**, the exact Subject-A comparison controller:

```text
Kp_theta = 120.00
Kd_theta = 28.00
Kp_x     = 14.00
Kd_x     = 19.00
Pi       = 3.6922 deg (fixed)
tau      = 0.23 s (fixed)
```

Relative to the S62-identified endpoint in chunk 1, chunk 11 reduces normalized MSE by **10.04%**, theta MSE by **10.82%**, x MSE by **9.41%**, and the Stage-3 objective by **13.11%**. Unlike S57, the combined winner improves both paired output errors and the training objective.

Chunk 10 has the lowest theta MSE but ranks last overall because its x MSE more than doubles relative to chunk 1. Chunk 11 is therefore the best balanced tested setting, although this remains an in-sample result and the Wasserstein comparison covers only 0.23 s because of T02.

## Run integrity

| Check | Result |
|---|---|
| Requested/completed chunks | 11 / 11 |
| Stage 3 epochs per chunk | 5,000 |
| Batch size | 4,096 |
| Random seed reset | 1,234 before every chunk |
| Real trials | S62 A11 T01-T05 |
| Pooled measured samples | 878 |
| Matched trajectory CSVs | 55 = 11 chunks × 5 trials |
| Common Wasserstein window | 0.00-0.23 s |
| Fixed Pi | 3.692218 deg |
| Fixed tau | 0.23 s |
| Non-finite result or loss values | None |
| Checkpoint provenance | Final and best Stage-3 weights are byte-identical in every chunk |

Every chunk restored the same clean S62 Stage-1 checkpoint, fixed one four-gain tuple, and ran the unchanged Stage-3 training function. The first contaminated S62/S63 run was not used. The camera-facing recording orientation was already normalized into the skeleton-derived subject-forward frame before training.

## Combined ranking with all control parameters

The primary ranking metric is pooled normalized MSE over the same 878 measured samples. Lower is better. Pi and tau are displayed even though they were fixed across the sweep.

| Rank | Chunk | Kp_theta | Kd_theta | Kp_x | Kd_x | Pi (deg) | tau (s) | Normalized MSE | Theta MSE (deg²) | x MSE (cm²) | Theta W1 (deg) | x W1 (cm) | Best Stage-3 objective | Takeaway |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 11 | 120.00 | 28.00 | 14.00 | 19.00 | 3.6922 | 0.23 | **0.212552** | 59.266 | **73.579** | 0.911 | 1.051 | **1,195.13** | Subject-A gains; best combined, x MSE, and objective. |
| 2 | 1 | 145.05 | 15.03 | 14.96 | 15.03 | 3.6922 | 0.23 | 0.236283 | 66.456 | 81.221 | 0.911 | **1.039** | 1,375.49 | S62 endpoint; runner-up and best x W1. |
| 3 | 2 | 155.60 | 16.69 | 14.74 | 16.69 | 3.6922 | 0.23 | 0.247260 | 66.168 | 88.369 | 0.912 | 1.047 | 1,648.45 | Early interpolation worsens x and combined error. |
| 4 | 6 | 197.80 | 23.34 | 13.87 | 23.34 | 3.6922 | 0.23 | 0.252705 | 60.641 | 97.299 | 0.910 | 1.089 | 2,118.95 | Better theta, but x penalty limits combined rank. |
| 5 | 3 | 166.15 | 18.35 | 14.53 | 18.35 | 3.6922 | 0.23 | 0.254827 | 65.580 | 93.687 | **0.909** | 1.061 | 1,390.58 | Best theta W1; only fifth on paired MSE. |
| 6 | 5 | 187.25 | 21.68 | 14.09 | 21.68 | 3.6922 | 0.23 | 0.259771 | 65.953 | 96.404 | 0.912 | 1.079 | 1,921.31 | Intermediate result; no metric minimum. |
| 7 | 4 | 176.70 | 20.02 | 14.31 | 20.02 | 3.6922 | 0.23 | 0.261895 | 67.050 | 96.634 | 0.911 | 1.064 | 1,718.88 | Local combined-error reversal. |
| 8 | 8 | 218.90 | 26.67 | 13.44 | 26.67 | 3.6922 | 0.23 | 0.272950 | 58.714 | 111.880 | 0.909 | 1.085 | 1,959.96 | Low theta MSE, but high x MSE. |
| 9 | 7 | 208.35 | 25.01 | 13.65 | 25.01 | 3.6922 | 0.23 | 0.273114 | 59.046 | 111.650 | 0.910 | 1.086 | 1,853.18 | Nearly tied with chunk 8; same theta/x tradeoff. |
| 10 | 9 | 229.45 | 28.34 | 13.22 | 28.34 | 3.6922 | 0.23 | 0.284035 | 63.452 | 114.070 | 0.911 | 1.080 | 1,748.49 | No metric minimum. |
| 11 | 10 | 240.00 | 30.00 | 13.00 | 30.00 | 3.6922 | 0.23 | 0.377634 | **53.715** | 182.306 | 0.910 | 1.080 | 4,054.20 | Subject-B endpoint; best theta MSE but worst combined/x result. |

## Which chunk is best depends on the question

| Question | Best chunk | Result |
|---|---:|---:|
| Best paired overall reconstruction | 11 | Normalized MSE = 0.212552 |
| Best paired theta reconstruction | 10 | Theta MSE = 53.715 deg² |
| Best paired forward-x reconstruction | 11 | x MSE = 73.579 cm² |
| Best early theta distribution match | 3 | Pooled W1 = 0.909 deg |
| Best early forward-x distribution match | 1 | Pooled W1 = 1.039 cm |
| Lowest Stage-3 training objective | 11 | Objective = 1,195.13 |

Chunk 11 is the only subject in this comparison where the same candidate wins combined MSE, x MSE, and Stage-3 objective while also improving theta MSE relative to the subject-specific endpoint.

## Endpoint comparisons

### Chunk 11 versus the S62-identified endpoint

Compared with chunk 1, chunk 11:

- reduces normalized MSE from 0.236283 to 0.212552: **10.04% improvement**;
- reduces theta MSE from 66.456 to 59.266 deg²: **10.82% improvement**;
- reduces x MSE from 81.221 to 73.579 cm²: **9.41% improvement**;
- reduces the best Stage-3 objective from 1,375.49 to 1,195.13: **13.11% improvement**;
- changes theta W1 by only +0.04% and x W1 by +1.12% over the short common interval.

This is a more consistent improvement than the S57 result, although it still requires held-out validation.

### Subject-B endpoint

Chunk 10 lowers theta MSE by 19.17% relative to chunk 1 but increases x MSE by 124.46%, normalized MSE by 59.82%, and the Stage-3 objective by 194.74%. It demonstrates that optimizing angle reconstruction alone would select a poor combined controller for S62.

### Subject-A versus Subject-B paper gains

Chunk 11 reduces normalized MSE by 43.71% and x MSE by 59.64% relative to chunk 10. Chunk 10 retains a 10.33% theta-MSE advantage. For S62, the Subject-A tuple provides the substantially better overall balance.

## Shape of the ten-chunk interpolation

Across chunks 1-10, moving from the S62-identified gains toward the Subject-B endpoint correlates with:

- higher normalized MSE (`r = +0.76`);
- lower theta MSE (`r = -0.81`);
- higher x MSE (`r = +0.79`);
- higher x W1 (`r = +0.84`);
- a higher Stage-3 objective (`r = +0.68`).

The interpolation steadily trades x fidelity for theta fidelity. Chunk 11 lies outside that interpolation and finds a better balance by combining lower `Kp_theta` with comparatively high `Kd_theta` and moderate x gains.

## Trial-level behavior

| Trial | Samples | Best normalized MSE | Best theta MSE | Best x MSE |
|---|---:|---|---|---|
| T01 | 297 | Chunk 11: 0.133413 | Chunk 4: 20.667 deg² | Chunk 11: 57.125 cm² |
| T02 | 24 | Chunk 6: 0.001362 | Chunk 6: 0.461 deg² | Chunk 6: 0.391 cm² |
| T03 | 263 | Chunk 11: 0.324300 | Chunk 10: 79.878 deg² | Chunk 1: 104.389 cm² |
| T04 | 65 | Chunk 7: 0.071223 | Chunk 6: 21.191 deg² | Chunk 7: 23.104 cm² |
| T05 | 229 | Chunk 10: 0.199169 | Chunk 10: 74.173 deg² | Chunk 6: 38.452 cm² |

No single chunk wins every trial. T03 contributes about 45-49% of pooled theta squared error, while T01 and T03 together contribute most pooled x error. T02 contributes less than 0.03% of pooled theta error and less than 0.02% of pooled x error because it has only 24 samples.

This creates an important split: T02 controls the length of the all-trial Wasserstein window, but it does not control the pooled MSE ranking.

## What the best-chunk plots show

Chunk 11 still has substantial late-trajectory mismatches:

- T01: synthetic theta and x oscillate while the measured fall rises sharply late.
- T02: agreement is close, but the trial is only 0.23 s long.
- T03 and T05: synthetic theta stays negative and x oscillates while measured theta and x rise late.
- T04: the direction is broadly captured, but the late amplitude is underpredicted.

Thus, chunk 11 is the best tested pooled setting, not a faithful forward simulation of every S62 fall.

## Wasserstein interpretation and T02 limitation

Wasserstein-1 uses only the common 0.00-0.23 s interval because T02 is the shortest trial. Paired MSE uses all 878 samples, including trials extending to 2.96 s.

The pooled theta W1 values span only 0.909-0.912 deg across all chunks, and x W1 spans only 1.039-1.089 cm. Those small differences cannot evaluate the later fall dynamics that determine most paired MSE. This explains why chunk 3 wins theta W1, chunk 1 wins x W1, and chunk 11 wins full-trajectory paired reconstruction.

For a more informative distribution comparison, report a second analysis excluding T02, while preserving the 0.23 s all-trial result for transparency.

## Stage-3 objective is not reconstruction MSE

Chunk 11 happens to minimize both the Stage-3 objective and pooled normalized MSE, but the metrics are still conceptually different. Chunk 10 illustrates this: it improves theta MSE but has the highest objective and worst combined MSE.

All loss histories contain 5,000 finite values. Their minima occur between epochs 3,582 and 4,743. Final-epoch losses are 1.48-4.91 times their minima, but `final_stage3.weights.h5` and `stage3_best.weights.h5` are byte-identical for every chunk, confirming that the best checkpoint was restored before saving.

## Recommended next analysis

1. Treat chunk 11 as the current S62 combined-MSE candidate.
2. Repeat chunk 11 and chunk 1 with at least three seeds to test ranking stability.
3. Recompute Wasserstein and mean-distance metrics without T02 to obtain a longer common interval.
4. Report chunk 10 only as the theta-MSE specialist; do not call it the best S62 controller.
5. Run a local grid around the Subject-A tuple, varying theta and x gain pairs separately.
6. Use held-out trials or subjects before selecting the final S62 teacher.
7. If chunk 11 is selected, generate a new set of 100 trajectories from its checkpoint; the existing full-run trajectories came from another Stage-3 model.

## Advisor-ready conclusion

> The clean S62 fixed-gain sweep completed all 11 Stage-3 runs using the same five trials, Stage-1 checkpoint, architecture, Pi, tau, seed, epochs, and batch size. Chunk 11, the Subject-A gain tuple, produced the lowest pooled normalized MSE and forward-CoM MSE and also minimized the Stage-3 objective. Relative to the S62-identified endpoint, it improved normalized MSE by 10.04%, theta MSE by 10.82%, x MSE by 9.41%, and the objective by 13.11%. However, no chunk won every trial, visible late-trajectory mismatches remain, and the all-trial Wasserstein window is only 0.23 s because of T02. The result supports chunk 11 as the current S62 candidate, subject to repeated-seed, longer-window, and held-out validation.
