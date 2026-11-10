# Findings — matched full-fall Physics versus no physics, five seeds

## Executive finding

The matched full-fall ablation favors Model B with Physics on all three primary
held-out trajectory metrics. Averaged at the independent-subject level,
Physics reduced normalized forecast RMSE by 8.15%, theta RMSE by 5.45%, and CoM
x RMSE by 8.04%. Physics had the lower error for 12 of the 15 subjects on each
metric.

This is descriptive evidence that the biomechanics residual improved
generalization under the tested configuration. It is not yet family-wise
statistical confirmation: after Holm correction across the three primary
metrics, the smallest adjusted p-value was 0.0646.

## Data and pairing audit

- 25 trained models per condition: five folds by five optimization seeds.
- 15 independent held-out subjects.
- 75 exactly matched subject-seed pairs.
- 70 accepted held-out trials.
- 350 exactly matched trial-seed pairs.
- Subject, seed, trial, fold, architecture, full-fall preparation, and data
  provenance hashes align across the conditions.
- The intended training difference is present: Physics uses
  `use_physics=true` and `physics_weight=0.01`; no physics uses
  `use_physics=false` and `physics_weight=0.0`.

The primary statistical unit is a human subject. Each subject's metric is
averaged over the five optimization seeds before the paired analysis, so seeds
do not inflate the sample size from 15 to 75.

## No-physics result alone

| Held-out metric | Mean over seeds | Across-seed SD | 95% t CI over five seeds |
|:---|---:|---:|:---|
| Normalized forecast MSE | 3.7831 | 0.5413 | 3.1109 to 4.4552 |
| Theta RMSE | 22.7223° | 0.8252° | 21.6976° to 23.7470° |
| CoM x RMSE | 30.9527 cm | 1.2103 cm | 29.4500 to 32.4555 cm |

Seed-level normalized MSE values were 3.7652, 3.0292, 4.5578, 3.8222, and
3.7411. The best no-physics seed was seed 2, while seed 3 was the worst. This
spread confirms that a single optimization seed would give an unstable summary.

The no-physics validation-selected epoch ranged from 16 to 341, with median 62
and mean 99.96 across the 25 models.

## Primary paired comparison

Normalized RMSE is calculated as the square root of each held-out
subject-seed normalized MSE before seed averaging. A positive paired difference
below means `no physics − Physics`, so positive values favor Physics.

| Metric | Physics mean | No-physics mean | Mean paired difference | Physics reduction | Subjects favoring Physics | Wilcoxon p | Holm p |
|:---|---:|---:|---:|---:|---:|---:|---:|
| Normalized forecast RMSE | 1.5883 | 1.7292 | 0.1409 | 8.15% | 12/15 | 0.0256 | 0.0646 |
| Theta RMSE | 21.4843° | 22.7223° | 1.2380° | 5.45% | 12/15 | 0.1354 | 0.1354 |
| CoM x RMSE | 28.4642 cm | 30.9527 cm | 2.4885 cm | 8.04% | 12/15 | 0.0215 | 0.0646 |

Subject-bootstrap 95% intervals for the mean paired improvement were 0.0286 to
0.2572 for normalized RMSE, −0.2225° to 2.5900° for theta RMSE, and 0.4865 cm
to 4.4381 cm for CoM x RMSE. The corresponding paired effect sizes, Cohen's
dz, were 0.606, 0.425, and 0.615.

The unadjusted normalized-RMSE and x-RMSE comparisons cross the conventional
0.05 threshold, while theta does not. Because three primary outcomes were
tested, the Holm-adjusted results should be used for the confirmatory statement;
none is below 0.05 after correction.

## Subject and seed heterogeneity

The largest normalized-MSE improvements from Physics occurred for S43, S44,
S49, S30, and S48. No physics performed better for S45, S46, and S55; S45 was
the clearest exception and favored no physics on all three primary metrics.
This heterogeneity is visible in the subject-difference plot and should not be
hidden by the overall mean.

Physics had lower subject-balanced errors for four of the five optimization
seeds. Seed 2 was the exception and favored no physics on all three primary
metrics. This is why the reported experiment uses all five matched seeds.

At the exploratory trial level, Physics had lower mean error for 41 of 70
trials on normalized RMSE, 43 of 70 on theta RMSE, and 41 of 70 on CoM x RMSE.
These counts are descriptive only because trials from the same participant are
not statistically independent.

## Important residual limitation

Physics residuals are intentionally excluded from the primary ablation claim.
The no-physics network retains the same four-coordinate head to preserve the
architecture, but those coordinates receive no physics supervision and are not
identified controller gains. Plugging them into the residual equations can
produce very large post-hoc residuals, especially horizontally, without being
a fair measure of trajectory prediction quality. Use normalized RMSE, theta
RMSE, and CoM x RMSE for the matched trajectory comparison.

## Recommended conclusion

> Across 15 held-out subjects and five matched optimization seeds, Model B with
> the cart-pole biomechanics residual achieved lower mean full-fall trajectory
> errors than the matched no-physics ablation (8.15% lower normalized RMSE,
> 5.45% lower angular RMSE, and 8.04% lower horizontal CoM RMSE). Physics was
> better for 12 of 15 subjects on each outcome. However, none of the three
> subject-level paired comparisons remained below 0.05 after Holm correction,
> so the result should be presented as consistent descriptive evidence rather
> than definitive statistical proof.

The full reproducible comparison, including matched tables and figures, is in
`comparison/`.
