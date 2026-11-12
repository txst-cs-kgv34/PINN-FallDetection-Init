# Findings: continuity-corrected synthetic falls

## Decision summary

The corrected workflow generated 516 conditional synthetic falls and approved 226 (43.8%) for downstream use. The approved-only dataset is defined by `outputs/trajectory_quality/final_approved_synthetic_manifest.json`. Rejected candidates remain in the archive for audit but should not enter detector training.

The quality decision is leakage-controlled: generator seeds were selected from validation-subject loss, while all quality thresholds were derived separately by fold from training subjects. Test subjects were not used for selection or threshold construction.

| Gate | Passed | Failed | Pass rate |
|---|---:|---:|---:|
| Boundary continuity | 474 | 42 | 91.9% |
| Shape | 465 | 51 | 90.1% |
| Kinematic | 282 | 234 | 54.7% |
| Complete gate | 226 | 290 | 43.8% |

Failures overlap, so the failed counts above should not be added. A trajectory passes the complete gate only when all three component gates pass.

## Main findings

1. **The boundary correction is working for most trajectories.** The median sampled transition step is 0.068° for theta and 0.113 cm for CoM x. Their 95th percentiles are 0.482° and 0.782 cm. The complete four-metric continuity gate passes for 474/516 trajectories.
2. **Overall trajectory shape is usually plausible.** The shape gate passes for 465/516 trajectories. Individually, normalized RMSE passes for 488/516 (94.6%) and normalized DTW passes for 479/516 (92.8%).
3. **Kinematic agreement is the current bottleneck.** Only 282/516 trajectories meet the kinematic rule. The weakest individual comparison is peak theta-acceleration difference, which passes for 212/516 (41.1%). Peak theta velocity passes for 355/516 (68.8%), and peak CoM x velocity passes for 380/516 (73.6%).
4. **Fold 5 remains substantially weaker.** Aggregate complete-gate pass rates are 32.7% for fold 1, 52.9% for fold 2, 57.7% for fold 3, 56.7% for fold 4, and 18.6% for fold 5. Fold 5 should be monitored in the detector study and reported separately rather than hidden inside the overall average.
5. **Approved files are correlated conditional variants.** The 226 approved files come from 46 unique real source trials, often with more than one selected generator applied to the same context. They are useful augmentation samples, but they are not equivalent to 226 independent recorded falls.

## What is measured for real-real and synthetic-real comparisons

### Kinematic features

The following scalar features are extracted from each forecast trajectory after identical Savitzky–Golay smoothing:

- duration;
- theta displacement;
- CoM x displacement;
- peak absolute theta velocity;
- peak absolute CoM x velocity;
- peak absolute theta acceleration;
- peak absolute CoM x acceleration.

For a real-real pair, the saved value is the absolute difference between the feature from two different trials of the same training subject:

```text
distance_feature = |feature(real trial A) - feature(real trial B)|
```

For a synthetic-real pair, it is the absolute difference between the synthetic trajectory and its own source real trajectory:

```text
distance_feature = |feature(synthetic forecast) - feature(source real forecast)|
```

Duration difference is calculated and reported, but it is not gated. The six gated kinematic distances are the two displacements, two peak velocities, and two peak accelerations.

### Boundary metrics

Boundary metrics are handled differently from the paired kinematic distances. Each real training trajectory is measured individually at 0.40 s to create a natural boundary-behavior distribution. The same four quantities are then measured on each joined synthetic trajectory:

- absolute theta step from the 0.40 s sample to the next sample;
- absolute CoM x step from the 0.40 s sample to the next sample;
- absolute change between the one-step theta velocity before and after 0.40 s;
- absolute change between the one-step CoM x velocity before and after 0.40 s.

Thus, these are not `|synthetic boundary metric - real boundary metric|` pair distances. The synthetic boundary values themselves are compared with the fold-specific distribution of real boundary values.

## Gate definition

“Within real-real variability” means at or below a fold-specific training-only 95th-percentile threshold. It does not mean inside the global real-real minimum-to-maximum range.

For candidate `j` in fold `f`, a metric passes when

```text
d(j) <= Q95(real training reference for fold f)
```

where lower distance is better. The complete rule is:

```text
overall pass
  = all 4 boundary metrics pass
  AND normalized RMSE passes
  AND normalized DTW passes
  AND at least 75% of the 6 kinematic metrics pass
```

Because there are six kinematic metrics, the 75% setting effectively requires at least five passes: four of six is 66.7%, while five of six is 83.3%.

Theta RMSE and CoM x RMSE are descriptive outputs. They are not additional automatic gate conditions because normalized RMSE already combines both channels. Duration is also descriptive only.

## Pairwise trajectory-error calculations

Before the four shape errors are calculated, both forecast segments (`t >= 0.40 s`) are phase-resampled to 101 equally spaced points. This lets trials of different durations be compared at matching relative fall progress.

Let `theta1[i]`, `x1[i]` and `theta2[i]`, `x2[i]` be the two phase-aligned trajectories, with `N = 101`. For synthetic-real, trajectory 1 can be synthetic and trajectory 2 its source real trajectory. For real-real, both are different real trials from the same subject.

### Theta RMSE

```text
theta_RMSE_deg
  = (180 / pi) * sqrt(mean((theta1[i] - theta2[i])^2))
```

This is the ordinary pointwise theta error, reported in degrees.

### CoM x RMSE

```text
x_RMSE_cm
  = 100 * sqrt(mean((x1[i] - x2[i])^2))
```

This is the ordinary pointwise horizontal CoM error, reported in centimeters.

### Normalized RMSE

Theta and x have different units and magnitudes, so each error is divided by the model scale used during training:

```text
theta_scale = 0.436332 rad = 25 degrees
x_scale     = 0.25 m = 25 cm

normalized_RMSE
  = sqrt(mean(
      ((theta1[i] - theta2[i]) / theta_scale)^2
      + ((x1[i] - x2[i]) / x_scale)^2
    ))
```

The result is dimensionless. A smaller value means the two-channel trajectories are closer after accounting for their different units.

### Normalized DTW

Each phase point is first represented as a normalized two-dimensional vector:

```text
z[i] = [theta[i] / theta_scale, x[i] / x_scale]
```

Dynamic Time Warping finds a monotonic alignment path through the two sequences. Its local cost is the Euclidean distance between normalized vectors:

```text
cost(i, j) = ||z1[i] - z2[j]||2
D(i, j) = cost(i, j) + min(D(i-1, j), D(i, j-1), D(i-1, j-1))
normalized_DTW = D(N, N) / (N + N)
```

Here `N = 101`, so the accumulated cost is divided by 202. DTW can align similar motion patterns that occur at slightly different relative phases, whereas RMSE compares the same phase index directly.

## Fold and generator results

| Fold | Rank | Seed | Candidates | Approved | Pass rate |
|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 3 | 52 | 17 | 32.7% |
| 1 | 2 | 1 | 52 | 17 | 32.7% |
| 2 | 1 | 5 | 51 | 27 | 52.9% |
| 2 | 2 | 2 | 51 | 27 | 52.9% |
| 3 | 1 | 4 | 52 | 29 | 55.8% |
| 3 | 2 | 5 | 52 | 31 | 59.6% |
| 4 | 1 | 3 | 52 | 31 | 59.6% |
| 4 | 2 | 5 | 52 | 28 | 53.8% |
| 5 | 1 | 3 | 51 | 8 | 15.7% |
| 5 | 2 | 4 | 51 | 11 | 21.6% |

## Recommended next stage

Proceed to the downstream fall-detection experiment using only the 226 files listed in the approved manifest. Compare:

1. real falls + real ADL;
2. approved synthetic Physics falls + real ADL;
3. real falls + approved synthetic Physics falls + real ADL.

All detector splitting must occur by real source subject before augmentation. Synthetic variants derived from a subject must stay in the same training partition as that source and must never cross into validation or test partitions. Report aggregate results together with fold-specific results, especially fold 5.

Do not generate additional synthetic trajectories yet. First establish whether the approved set improves unseen-real-subject fall detection. Generate more data only if the detector study shows a clear coverage or class-balance need that the current approved set cannot satisfy.
