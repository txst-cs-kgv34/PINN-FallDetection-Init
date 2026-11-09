# Findings: five-seed Physics versus No-Physics ablation

## Bottom line

Across five paired seeds, Unified Physics has a lower overall normalized MSE
than No Physics (`0.2143` versus `0.2762`), a nominal 22.4% reduction.
However, this mean advantage is dominated by S45. Physics and No Physics are
essentially tied for angle RMSE (`5.103°` versus `5.105°`) and differ by only
0.255 cm for CoM displacement RMSE (`7.772` versus `8.027 cm`).

Physics does not win for most subjects: each primary metric favors physics for
7 subjects and no physics for 8. None of the paired subject-level tests is
statistically significant, and all confidence intervals include zero.

The defensible interpretation is:

> At physics weight 0.01, the cart-pole residual acts as a useful protective
> constraint for the difficult S45/Fold 3 case, but the five-seed experiment
> does not show a consistent generalization advantage across the 15 subjects.

## Comparison validity

The analysis verified:

- identical five base seeds and effective fold-seed rules;
- identical 15 subjects, demographics, folds, and validation assignments;
- identical context encoder, DeepONet architecture, optimizer, and stopping
  rules;
- identical 66 eligible trials;
- 330 matched prediction evaluations per condition; and
- zero numerical difference in stored target time, theta, and forward-CoM
  arrays across conditions and seeds.

The only loss change is removal of the biomechanics residual.

## Primary paired results

Each subject was first averaged over the same five seeds. The 15 resulting
paired subject values are the primary analysis unit.

Physics improvement is defined as:

```text
no-physics error − physics error
```

Positive values favor Unified Physics.

| Metric | Physics mean | No-physics mean | Mean improvement | 95% subject-bootstrap CI | Subject wins P/N | Wilcoxon raw p | Holm p |
|:---|---:|---:|---:|---:|---:|---:|---:|
| Normalized MSE | **0.2143** | 0.2762 | +0.0619 | [-0.0466, 0.2301] | 7 / 8 | 0.847 | 1.000 |
| Angle RMSE | **5.103°** | 5.105° | +0.002° | [-0.971, 1.228] | 7 / 8 | 0.561 | 1.000 |
| CoM displacement RMSE | **7.772 cm** | 8.027 cm | +0.255 cm | [-1.169, 1.949] | 7 / 8 | 0.847 | 1.000 |

No metric supports a population-wide superiority claim in either direction.

The rank-based effect is also weak. Paired rank-biserial correlations are
`-0.067`, `-0.183`, and `-0.067` for normalized MSE, angle RMSE, and
displacement RMSE. The negative direction occurs because slightly more subject
ranks favor No Physics even though a few large-magnitude cases favor physics.

## Why normalized MSE favors physics in all five seeds

At the seed-aggregate level, normalized MSE favors physics in all five runs:

| Seed | Physics | No Physics | Improvement |
|---:|---:|---:|---:|
| 1 | 0.2082 | 0.2369 | +0.0287 |
| 2 | 0.2311 | 0.2758 | +0.0447 |
| 3 | 0.2662 | 0.2837 | +0.0175 |
| 4 | 0.2041 | 0.2649 | +0.0609 |
| 5 | 0.1619 | 0.3195 | +0.1576 |

This does not conflict with physics winning only 7 of 15 subjects. Equal-weight
seed means are sensitive to large subject errors. S45 has very high error under
both conditions, and physics reduces that error substantially in every seed.
That one large reduction outweighs smaller no-physics advantages across more
subjects.

## S45 sensitivity analysis

S45 is the largest absolute paired effect for every primary metric:

| Metric | Physics S45 mean | No-physics S45 mean | Physics improvement |
|:---|---:|---:|---:|
| Normalized MSE | 1.1258 | 2.2405 | +1.1147 |
| Angle RMSE | 11.139° | 18.070° | +6.932° |
| CoM displacement RMSE | 18.655 cm | 27.862 cm | +9.207 cm |

After excluding S45, the mean paired differences become:

| Metric | Mean physics improvement without S45 |
|:---|---:|
| Normalized MSE | -0.0133 |
| Angle RMSE | -0.493° |
| CoM displacement RMSE | -0.384 cm |

Negative values favor No Physics. The median subject differences are also
slightly negative: `-0.0075` normalized MSE, `-0.283°`, and `-0.070 cm`.

This does not make S45 invalid. It shows that the physics benefit is a
hard-case effect rather than a broad improvement. S45 should remain in the
reported result, accompanied by the sensitivity analysis.

## Subject heterogeneity

The strongest consistent physics improvements include:

- **S45:** physics wins all five seeds on all primary metrics.
- **S44:** physics wins all five seeds on all primary metrics.
- **S62:** physics wins all five seeds for normalized MSE and displacement RMSE.
- **S57 and S43:** mean errors favor physics, though not in every seed.

The strongest no-physics result is S63:

| Metric | Physics | No Physics |
|:---|---:|---:|
| Normalized MSE | 0.1815 | **0.0454** |
| Angle RMSE | 5.848° | **2.707°** |
| CoM displacement RMSE | 8.646 cm | **4.172 cm** |

No Physics wins all five S63 seeds on every primary metric. S30, S32, and S48
also have notable no-physics advantages in their five-seed means.

## Fold effects

Mean physics improvement across seeds:

| Fold | Test subjects | Normalized MSE | Angle RMSE | CoM RMSE |
|---:|:---|---:|---:|---:|
| 1 | S57, S46, S30 | +0.0206 | +0.147° | +0.603 cm |
| 2 | S55, S48, S43 | +0.0334 | +0.556° | +0.656 cm |
| 3 | S45, S59, S56 | **+0.4953** | **+4.480°** | **+5.871 cm** |
| 4 | S34, S32, S49 | -0.0624 | -0.957° | -1.721 cm |
| 5 | S44, S62, S63 | +0.0752 | +0.574° | +2.825 cm |

Fold 3 is the main source of the overall physics advantage, primarily because
of S45. Fold 4 favors No Physics. Fold 5 mixes strong physics advantages for
S44/S62 with a strong no-physics advantage for S63.

## Seed effects

Angle and displacement results change direction by seed:

- Seeds 1–3 favor No Physics on mean angle and displacement RMSE.
- Seeds 4–5 favor Unified Physics.
- Normalized MSE favors physics in all five seeds.

Physics has greater across-seed variation than No Physics for angle and
displacement RMSE:

| Metric | Physics seed SD | No-physics seed SD |
|:---|---:|---:|
| Normalized MSE | 0.0383 | 0.0300 |
| Angle RMSE | 0.420° | 0.207° |
| CoM displacement RMSE | 0.574 cm | 0.315 cm |

Thus the physics term did not uniformly stabilize optimization under this
configuration.

## Checkpoint selection

Across the 25 models:

- Physics selected epochs range from 12 to 396, with median 83.
- No Physics selected epochs range from 35 to 325, with median 125.

Removing the residual changes the gradient path and validation curve, so
different checkpoint epochs are expected. This is part of the ablation effect,
not a protocol mismatch.

## Controller outputs

The no-physics model still produces four positive controller-head values to
preserve the exact Model B architecture. With no physics residual and no gain
supervision, those values are unsupervised latent conditioning variables. They
cannot be treated as biomechanical parameters.

The physics outputs influence the residual but are not measured ground-truth
human gains. Forecast accuracy, not gain magnitude, is the valid ablation
endpoint.

## Research conclusion

The experiment supports two narrower statements:

1. The physics residual can reduce large prediction failures for some difficult
   subjects, especially S45.
2. It does not consistently improve error for the typical held-out subject at
   the tested weight of 0.01.

The result should be reported as heterogeneous and inconclusive for general
superiority—not as proof that physics is useless or universally beneficial.

A sensible next experiment is a validation-only physics-weight study, for
example `0, 1e-4, 1e-3, 1e-2, 1e-1`, using the same folds and seeds. The test
subjects must remain untouched during weight selection. Reporting median,
trimmed/robust summaries, and worst-subject error alongside the mean would
clarify whether the goal is average accuracy or protection against severe
failures.

