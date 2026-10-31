# Findings: S57 Stage 3 fixed-gain sweep

## Executive conclusion

All 11 fixed-gain experiments completed successfully. The lowest pooled normalized reconstruction MSE is produced by **chunk 10**, the exact Subject-B endpoint:

```text
Kp_theta = 240.00
Kd_theta = 30.00
Kp_x     = 13.00
Kd_x     = 30.00
Pi       = 3.6295 deg (fixed)
tau      = 0.23 s (fixed)
```

Chunk 10 reduces normalized MSE by **12.71%** relative to the S57-identified endpoint in chunk 1. The improvement is driven entirely by forward-CoM reconstruction: x MSE falls by 33.64%, while theta MSE increases by 13.95%. Chunk 1 remains best for theta MSE, theta Wasserstein distance, and the Stage-3 objective.

Chunk 9 is only **0.75%** behind chunk 10 in normalized MSE and has lower theta error and a much lower Stage-3 objective. The sweep therefore identifies a high-gain region around chunks 9-10, not a uniquely established physiological controller. Multiple-seed or held-out validation is required before selecting one as a teacher.

## Run integrity

| Check | Result |
|---|---|
| Requested/completed chunks | 11 / 11 |
| Stage 3 epochs per chunk | 5,000 |
| Batch size | 4,096 |
| Random seed reset | 1,234 before every chunk |
| Real trials | S57 A11 T03-T05 |
| Pooled measured samples | 609 |
| Matched trajectory CSVs | 33 = 11 chunks × 3 trials |
| Common Wasserstein window | 0.00-1.87 s |
| Fixed Pi | 3.629528 deg |
| Fixed tau | 0.23 s |
| Non-finite result or loss values | None |
| Checkpoint provenance | Final and best Stage-3 weights are byte-identical in every chunk |

Every chunk restored the same clean S57 Stage-1 checkpoint, fixed one four-gain tuple, and ran the unchanged Stage-3 training function. The first contaminated S57/S63 run was not used.

## Combined ranking with all control parameters

The primary ranking metric is pooled normalized MSE over the same 609 measured samples. Lower is better. Pi and tau are displayed even though they were fixed across the sweep.

| Rank | Chunk | Kp_theta | Kd_theta | Kp_x | Kd_x | Pi (deg) | tau (s) | Normalized MSE | Theta MSE (deg²) | x MSE (cm²) | Theta W1 (deg) | x W1 (cm) | Best Stage-3 objective | Takeaway |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 10 | 240.00 | 30.00 | 13.00 | 30.00 | 3.6295 | 0.23 | **1.098801** | 394.278 | **292.473** | 10.768 | **4.153** | 8,116.70 | Best combined, x MSE, and x W1; highest objective. |
| 2 | 9 | 229.45 | 28.34 | 12.12 | 28.34 | 3.6295 | 0.23 | 1.106994 | 386.261 | 305.610 | 10.716 | 4.298 | 4,843.93 | Only 0.75% behind chunk 10; better theta/objective tradeoff. |
| 3 | 7 | 208.35 | 25.02 | 10.35 | 25.02 | 3.6295 | 0.23 | 1.133747 | 376.798 | 331.794 | 10.585 | 4.847 | 4,099.18 | Strong middle-high-gain compromise. |
| 4 | 8 | 218.90 | 26.68 | 11.24 | 26.68 | 3.6295 | 0.23 | 1.139441 | 376.639 | 335.512 | 10.602 | 4.778 | 4,809.95 | Local reversal: slightly worse combined MSE than chunk 7. |
| 5 | 6 | 197.81 | 23.36 | 9.47 | 23.36 | 3.6295 | 0.23 | 1.159551 | 378.665 | 346.054 | 10.587 | 5.100 | 3,162.02 | Balanced interpolation result. |
| 6 | 5 | 187.26 | 21.70 | 8.59 | 21.70 | 3.6295 | 0.23 | 1.164884 | 375.143 | 352.910 | 10.548 | 5.253 | 2,901.12 | Similar to chunk 6 with a lower objective. |
| 7 | 4 | 176.71 | 20.04 | 7.71 | 20.04 | 3.6295 | 0.23 | 1.177343 | 377.357 | 358.483 | 10.570 | 5.318 | 2,618.55 | Intermediate result; no metric minimum. |
| 8 | 3 | 166.16 | 18.38 | 6.83 | 18.38 | 3.6295 | 0.23 | 1.222913 | 370.989 | 393.331 | 10.423 | 6.042 | 1,737.71 | First clear combined improvement over chunks 1-2. |
| 9 | 1 | 145.06 | 15.06 | 5.06 | 15.06 | 3.6295 | 0.23 | 1.258779 | **346.025** | 440.712 | **10.124** | 6.775 | **1,676.61** | S57 endpoint; best theta MSE, theta W1, and objective. |
| 10 | 2 | 155.61 | 16.72 | 5.95 | 16.72 | 3.6295 | 0.23 | 1.262991 | 347.859 | 441.511 | 10.140 | 6.784 | 1,750.35 | Slightly worse than chunk 1 on the combined metric. |
| 11 | 11 | 120.00 | 28.00 | 14.00 | 19.00 | 3.6295 | 0.23 | 1.286592 | 381.284 | 422.836 | 10.514 | 6.564 | 2,256.49 | Subject-A gains; worst combined ranking for S57. |

## Which chunk is best depends on the question

| Question | Best chunk | Result |
|---|---:|---:|
| Best paired overall reconstruction | 10 | Normalized MSE = 1.098801 |
| Best paired theta reconstruction | 1 | Theta MSE = 346.025 deg² |
| Best paired forward-x reconstruction | 10 | x MSE = 292.473 cm² |
| Best theta distribution match | 1 | Pooled W1 = 10.124 deg |
| Best forward-x distribution match | 10 | Pooled W1 = 4.153 cm |
| Lowest Stage-3 training objective | 1 | Objective = 1,676.61 |

These winners differ because paired MSE, marginal Wasserstein distance, and the physics-dominated Stage-3 objective measure different properties.

## Endpoint comparisons

### Chunk 10 versus the S57-identified endpoint

Compared with chunk 1, chunk 10:

- reduces normalized MSE from 1.258779 to 1.098801: **12.71% improvement**;
- reduces x MSE from 440.712 to 292.473 cm²: **33.64% improvement**;
- reduces x W1 from 6.775 to 4.153 cm: **38.71% improvement**;
- increases theta MSE from 346.025 to 394.278 deg²: **13.95% deterioration**;
- increases theta W1 from 10.124 to 10.768 deg: **6.36% deterioration**;
- increases the best Stage-3 objective from 1,676.61 to 8,116.70: **384.11% increase**.

The combined ranking selects chunk 10 because the x improvement outweighs the theta penalty after normalization. It should not be described as globally better than chunk 1.

### Chunk 9 versus chunk 10

Chunk 9 is only 0.75% worse in normalized MSE. It improves theta MSE by 2.03% and reduces the Stage-3 objective by 40.32%, while its x MSE is 4.49% higher. This makes chunk 9 an important alternative candidate for repeated-seed testing.

### Subject-A comparison gains

Chunk 11 is 17.09% worse than chunk 10 and 2.21% worse than chunk 1 in normalized MSE. The exact Subject-A controller is therefore not competitive for S57 under the pooled combined metric.

## Shape of the ten-chunk interpolation

Across chunks 1-10, increasing the interpolation fraction strongly correlates with:

- lower normalized MSE (`r = -0.97`);
- lower x MSE (`r = -0.96`) and x W1 (`r = -0.97`);
- higher theta MSE (`r = +0.89`) and theta W1 (`r = +0.91`);
- a higher Stage-3 objective (`r = +0.92`).

The direction is clear: larger gains improve x reconstruction but degrade angle reconstruction and the training objective. The small reversals around chunks 7-8 show that the response is not perfectly monotonic.

## Trial-level behavior

| Trial | Samples | Best normalized MSE | Best theta MSE | Best x MSE |
|---|---:|---|---|---|
| T03 | 188 | Chunk 10: 0.637732 | Chunk 1: 254.614 deg² | Chunk 10: 84.732 cm² |
| T04 | 208 | Chunk 10: 1.922483 | Chunk 1: 714.097 deg² | Chunk 10: 389.882 cm² |
| T05 | 213 | Chunk 1: 0.481685 | Chunk 11: 45.410 deg² | Chunk 1: 233.779 cm² |

T04 contributes about 70-71% of pooled theta squared error and 46-62% of pooled x squared error across the sweep, despite containing only 34% of the samples. Chunk 10 wins mainly by lowering x error for T03 and T04; chunk 1 remains better for T05 and for theta reconstruction.

This makes the pooled result trial-sensitive. T04 should always be mentioned when presenting the S57 ranking.

## What the best-chunk plots show

Chunk 10 still does not reproduce the three human trajectories closely:

- T03 and T04: synthetic theta moves strongly negative while measured theta eventually turns positive; late forward-x growth is underpredicted.
- T04: it is the largest mismatch and dominates pooled error.
- T05: synthetic theta and x overshoot the measured trajectory, even though T05 has lower pooled error than T04.

“Best chunk” therefore means best among the tested gain sets under the selected pooled metric, not accurate reproduction of all S57 falls.

## Wasserstein interpretation

Wasserstein-1 is calculated over the common 0.00-1.87 s support. Paired MSE uses all available samples, through 2.07 s for T04 and 2.12 s for T05. W1 also ignores trial identity, whereas paired MSE tests each synthetic trajectory against its corresponding real trial.

This explains why chunk 1 can have the best theta W1 while chunk 10 has the best combined MSE. The higher gains move the synthetic x distribution closer to the measured x distribution, but move the theta distribution farther away.

## Stage-3 objective is not reconstruction MSE

Chunk 1 has the lowest Stage-3 objective but ranks ninth on combined reconstruction. Chunk 10 has the highest objective but the lowest paired normalized MSE. The objective combines physics, data, and history terms with different scaling, and fixed gains directly change the physics residual.

All loss histories contain 5,000 finite values. Their minima occur between epochs 4,249 and 4,993. Final-epoch losses are 1.62-5.12 times their minima, but `final_stage3.weights.h5` and `stage3_best.weights.h5` are byte-identical for every chunk, confirming that the best checkpoint was restored before saving.

## Recommended next analysis

1. Treat chunk 10 as the current combined-MSE candidate and chunk 9 as the main tradeoff candidate.
2. Repeat chunks 9 and 10 with at least three seeds; their 0.75% gap may reflect optimization variability.
3. Report chunk 1 alongside them because it remains best for theta reconstruction and the Stage-3 objective.
4. Inspect T04 alignment and input quality because it dominates the pooled result.
5. Run a local grid that varies theta and x gain pairs separately; the current interpolation changes all four gains together.
6. Use held-out trials or subjects before selecting an S57 teacher.
7. If chunk 9 or 10 is selected, generate a new set of 100 trajectories from that chunk checkpoint; the existing full-run 100 trajectories were generated from a different Stage-3 model.

## Advisor-ready conclusion

> The clean S57 fixed-gain sweep completed all 11 Stage-3 runs using the same three trials, Stage-1 checkpoint, architecture, Pi, tau, seed, epochs, and batch size. Chunk 10, the Subject-B endpoint, produced the lowest pooled normalized MSE, improving the combined error by 12.71% over the S57-identified endpoint. The improvement came from a 33.64% reduction in forward-CoM x MSE, while theta MSE increased by 13.95% and the Stage-3 objective increased substantially. Chunk 9 was only 0.75% behind and provided a better theta/objective tradeoff. T04 dominated the pooled error, and visible direction and late-trajectory mismatches remain, so the exact gain choice requires repeated-seed and held-out validation.
