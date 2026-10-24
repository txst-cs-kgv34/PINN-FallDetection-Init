# Findings: S63 Stage 3 fixed-gain sweep

## Executive conclusion

All 11 fixed-gain experiments completed successfully. The lowest pooled normalized reconstruction MSE is produced by **chunk 6**:

```text
Kp_theta = 197.826
Kd_theta = 23.355
Kp_x     = 13.859
Kd_x     = 23.355
```

Chunk 6 reduces normalized MSE by **18.86%** relative to the S63-identified endpoint in chunk 1. The improvement is driven by forward-CoM reconstruction, especially T02. It is not a universal win: chunk 1 retains the lowest theta MSE and early x Wasserstein distance.

The strongest practical conclusion is therefore not that one exact gain tuple has been uniquely identified. Rather, the sweep shows a broad competitive region around chunks 6-7, with the Subject A paper gains in chunk 11 also performing very well. Their normalized MSE values differ by only 0.54%, which is too small to treat as a stable ranking without multiple-seed repetitions.

## Run integrity

| Check | Result |
|---|---|
| Requested/completed chunks | 11 / 11 |
| Stage 3 epochs per chunk | 5,000 |
| Batch size | 4,096 |
| Random seed reset | 1,234 before every chunk |
| Real trials | S63 A11 T01-T05 |
| Pooled measured samples | 412 |
| Matched trajectory CSVs | 55 = 11 chunks x 5 trials |
| Common Wasserstein window | 0.00-0.33 s |
| Fixed Pi | 3.628571 deg |
| Fixed tau | 0.23 s |
| Minimum-trial gate | 0.25 s |
| Non-finite loss or trajectory values | None |
| Checkpoint provenance | Final and best Stage 3 weights are byte-identical in every chunk |

The original pole source was not modified. Every chunk restored the same S63 Stage 1 checkpoint, assigned one fixed four-gain tuple, and called the original Stage 3 training function. The result JSON files agree exactly with the aggregate CSV.

## Combined ranking with all control parameters

The primary ranking metric is pooled normalized MSE over the same 412 real samples. Lower is better.

| Combined rank | Chunk | Kp_theta | Kd_theta | Kp_x | Kd_x | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta W1 (deg) | x W1 (cm) | Takeaway |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 6 | 197.83 | 23.35 | 13.86 | 23.35 | **0.103263** | 36.790 | **27.749** | 0.492 | 0.663 | Best combined and x MSE. |
| 2 | 7 | 208.37 | 25.02 | 13.64 | 25.02 | 0.103304 | 34.603 | 29.962 | **0.490** | 0.632 | Only 0.04% behind chunk 6; best theta W1. |
| 3 | 11 | 120.00 | 28.00 | 14.00 | 19.00 | 0.103816 | 37.051 | 27.835 | 0.498 | 0.513 | Subject A gains; only 0.54% behind chunk 6. |
| 4 | 10 | 240.00 | 30.00 | 13.00 | 30.00 | 0.105267 | 36.003 | 29.788 | 0.498 | 0.462 | Subject B endpoint; competitive but not best. |
| 5 | 5 | 187.28 | 21.69 | 14.07 | 21.69 | 0.105910 | 35.566 | 30.627 | 0.494 | 0.664 | Balanced middle-high-gain result. |
| 6 | 8 | 218.91 | 26.68 | 13.43 | 26.68 | 0.106734 | 34.525 | 32.184 | 0.501 | 0.446 | Low theta MSE and x W1, but weaker paired x error. |
| 7 | 9 | 229.46 | 28.34 | 13.21 | 28.34 | 0.107154 | 36.428 | 30.543 | 0.505 | 0.497 | No metric minimum. |
| 8 | 3 | 166.20 | 18.37 | 14.50 | 18.37 | 0.108744 | 35.356 | 32.609 | 0.498 | 0.672 | Better combined result than chunks 1-2 and 4. |
| 9 | 2 | 155.65 | 16.71 | 14.72 | 16.71 | 0.109965 | 36.367 | 32.362 | 0.496 | 0.680 | Early interpolation improves x MSE over chunk 1. |
| 10 | 4 | 176.74 | 20.03 | 14.29 | 20.03 | 0.114410 | 36.364 | 35.143 | 0.502 | 0.627 | Local reversal; sweep is not monotonic. |
| 11 | 1 | 145.11 | 15.05 | 14.93 | 15.05 | 0.127258 | **30.677** | 48.859 | 0.507 | **0.371** | S63 endpoint; best theta MSE and early x W1, but worst combined/x MSE. |

## Which chunk is best depends on the question

| Question | Best chunk | Result |
|---|---:|---:|
| Best paired overall reconstruction | 6 | Normalized MSE = 0.103263 |
| Best paired theta reconstruction | 1 | Theta MSE = 30.677 deg^2 |
| Best paired forward-x reconstruction | 6 | x MSE = 27.749 cm^2 |
| Best early theta distribution match | 7 | Pooled W1 = 0.490 deg |
| Best early forward-x distribution match | 1 | Pooled W1 = 0.371 cm |
| Lowest Stage 3 training objective | 1 | 2,470.09 |

These winners differ because paired MSE, marginal W1, and the Stage 3 training objective are not interchangeable.

## Endpoint comparisons

### Chunk 6 versus the S63-identified endpoint

Compared with chunk 1, chunk 6:

- reduces normalized MSE from 0.127258 to 0.103263, an **18.86% improvement**;
- reduces x MSE from 48.859 to 27.749 cm^2, a **43.21% improvement**;
- increases theta MSE from 30.677 to 36.790 deg^2, a **19.93% deterioration**.

Thus, the combined improvement comes from a large x benefit that outweighs a smaller angle penalty. Chunk 1 should not be called globally poor: it preserves angle reconstruction best and gives the smallest early x W1. It is poor only under the selected combined paired-reconstruction objective.

### Subject A and Subject B paper gains

The exact Subject A gains in chunk 11 rank third. They are:

- only **0.54% above** chunk 6 in normalized MSE;
- only **0.31% above** chunk 6 in x MSE;
- **1.38% better** than the Subject B endpoint in normalized MSE.

The Subject B endpoint in chunk 10 ranks fourth and is 1.90% worse than chunk 6. Both paper controllers are competitive for S63, but neither demonstrates a uniquely optimal or physiological human controller.

### Shape of the ten-chunk interpolation

The interpolation result is not monotonic. Across chunks 1-10, increasing the interpolation fraction correlates moderately with lower normalized MSE (`r = -0.68`) and lower x MSE (`r = -0.63`), but chunks 3-5 and 7-10 contain clear local reversals. The experiment therefore identifies a useful region rather than a smooth one-dimensional optimum.

## Trial-level behavior

The pooled optimum is not the best choice for every trial.

| Trial | Samples | Best normalized MSE | Best theta MSE | Best x MSE |
|---|---:|---|---|---|
| T01 | 74 | Chunk 1: 0.084602 | Chunk 1: 25.086 deg^2 | Chunk 1: 27.791 cm^2 |
| T02 | 123 | Chunk 6: 0.198795 | Chunk 1: 74.131 deg^2 | Chunk 6: 38.068 cm^2 |
| T03 | 70 | Chunk 1: 0.023948 | Chunk 1: 12.754 deg^2 | Chunk 1: 2.214 cm^2 |
| T04 | 111 | Chunk 1: 0.026216 | Chunk 1: 6.334 deg^2 | Chunk 1: 10.051 cm^2 |
| T05 | 34 | Chunk 1: 0.004819 | Chunk 7: 1.932 deg^2 | Chunk 1: 0.990 cm^2 |

T02 contains 29.9% of the samples but contributes 69.5-74.8% of pooled theta squared error and 41.0-83.3% of pooled x squared error across the sweep. Chunk 6 wins primarily because it lowers T02 x MSE from 136.335 cm^2 in chunk 1 to 38.068 cm^2. At the same time, chunk 1 is the best combined setting for T01, T03, T04, and T05.

This makes the result trial-sensitive. The pooled ranking should always be presented with the T02 dominance note.

## What the trajectory plots show

Even the best chunk does not reconstruct every complete trajectory closely:

- T01: both theta and x growth are underpredicted late in the trial.
- T02: theta diverges with the wrong late direction, while synthetic x rises and then plateaus as real x continues upward.
- T03: the early trend is captured, but later angle and x growth are underpredicted.
- T04: theta is underpredicted and synthetic x overshoots late.
- T05: agreement is closest, but this is also the shortest 0.33 s trial.

Accordingly, “best chunk” means best among the tested settings under the pooled metric. It does not mean the pole forward block accurately reproduces all five human falls.

## Wasserstein and mean-distance interpretation

Wasserstein-1 is computed only over the common 0.00-0.33 s support, because T05 is the shortest trial. Paired MSE uses every available sample in each full trial, up to 1.22 s.

This time-window difference explains the apparent contradiction in chunk 1:

- it has the lowest x W1, 0.371 cm, over the early common window;
- it has the highest full-trajectory x MSE, 48.859 cm^2.

W1 also ignores trial identity. It asks whether the real and synthetic values occupy similar distributions at a time point or when pooled; MSE asks whether each specific synthetic trajectory follows its paired real trial.

For chunk 6, all distances are zero at onset because each simulation receives the measured initial state. By 0.33 s:

- theta W1 and the absolute mean difference both reach 1.415 deg;
- x W1 and the absolute mean difference both reach 1.896 cm.

The corresponding time-mean W1 values are 0.661 deg and 0.788 cm. The combined mean/W1 figure is more informative than a W1 curve alone because it shows where the synthetic mean begins to separate from the real mean.

## Stage 3 objective is not reconstruction MSE

Chunk 1 has the lowest best Stage 3 objective (2,470.09) but the worst combined reconstruction MSE. Chunk 6 has a higher best objective (3,480.10) while producing the lowest paired MSE.

The Stage 3 objective combines physics, data, and history/initial-condition terms with different scaling. Changing the fixed controller gains changes the physics residual itself. Therefore:

- do not rank chunks by Stage 3 objective when the research question is trajectory reconstruction;
- do not report the objective value as an MSE;
- use normalized MSE for paired reconstruction and W1 for marginal distribution similarity.

All loss histories contain 5,000 finite values. Their minima occur late, between epochs 4,287 and 4,988, and the raw final-epoch losses are often above the minima. The saved final model nevertheless matches the best checkpoint byte-for-byte for every chunk, confirming that the original training routine restored the best weights.

## Cross-subject implication

The earlier S43 sweep favored its subject-specific endpoint, whereas S63 favors an intermediate higher-gain setting and gives strong results for the Subject A paper gains. This difference is evidence against selecting one universal controller solely from a paper or another subject. It also shows why a subject-specific result must be checked across trials rather than inferred from the fitted gain values alone.

## Recommended next analysis

1. Treat chunk 6 as the current combined-MSE choice, while reporting chunks 7 and 11 as near-ties.
2. Repeat chunks 6, 7, and 11 with at least three seeds. The 0.04-0.54% gaps are small enough to be optimization variability.
3. Inspect T02 alignment, onset state, and input quality because it controls most of the pooled ranking.
4. Run a small local grid that varies the theta and x gain pairs separately. The current interpolation changes all four gains together and cannot identify which gain causes the improvement.
5. Preserve paired MSE and mean/W1 plots together. Neither metric alone gives the complete result.
6. If possible, evaluate on a held-out S63 trial or a longer common interval. The current results are in-sample and the W1 window is only 0.33 s.

## Advisor-ready conclusion

> The S63 fixed-gain sweep completed all 11 Stage 3 runs using the same data, Stage 1 checkpoint, architecture, Pi, tau, seed, epochs, and batch size. Chunk 6 produced the lowest pooled normalized MSE and forward-CoM MSE, improving the combined error by 18.86% over the S63-identified endpoint. However, chunks 6, 7, and the Subject A paper controller were separated by only 0.54%, so the exact ranking should be confirmed across multiple seeds. The S63 endpoint remained best for angle MSE and early x Wasserstein distance, demonstrating that paired trajectory accuracy and short-window distribution similarity select different gain settings. T02 dominated the pooled error, and visible late-trajectory mismatches remain even for the best chunk.
