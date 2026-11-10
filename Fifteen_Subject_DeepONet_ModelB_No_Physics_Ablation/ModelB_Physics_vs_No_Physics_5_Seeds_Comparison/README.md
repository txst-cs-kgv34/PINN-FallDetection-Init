# Model B: Unified Physics versus No Physics — five-seed comparison

This directory contains the paired comparison of the 15-subject Model B
DeepONet experiment with and without the cart-pole biomechanics residual.

The comparison uses:

- 15 independent held-out human subjects;
- five matched optimization seeds;
- five identical subject folds per seed;
- 25 trained models per condition;
- 75 paired subject-seed evaluations;
- 66 unique eligible held-out trials; and
- 330 paired trial-seed evaluations.

Every comparison is matched by seed index, fold, subject, and trial. Stored
target time, theta, and forward-CoM arrays were verified to be exactly identical
across both conditions and all five seeds.

## Controlled difference

The conditions differ only in the physics term:

```text
Unified Physics:
L = L_real_forecast + 0.01 × L_cart_pole_biomechanics

No Physics:
L = L_real_forecast
```

The context encoder, DeepONet branch and trunk, four-output head, hard initial
constraints, data, folds, optimizer, early stopping, and evaluation metrics are
unchanged.

## Primary result

The primary analysis averages each held-out subject over the same five seeds,
leaving 15 paired subject values. Positive improvement means:

```text
no-physics error − physics error
```

| Metric | Unified Physics | No Physics | Mean physics improvement | Relative improvement | Physics seed wins |
|:---|---:|---:|---:|---:|---:|
| Normalized MSE | **0.2143** | 0.2762 | +0.0619 | 22.4% | 5/5 |
| Angle RMSE | **5.103°** | 5.105° | +0.002° | 0.03% | 2/5 |
| CoM displacement RMSE | **7.772 cm** | 8.027 cm | +0.255 cm | 3.18% | 2/5 |

These overall means do not establish a general subject-level benefit:

- Physics wins only 7 of 15 subjects on each primary metric.
- All subject-bootstrap intervals include zero.
- Paired Wilcoxon tests are nonsignificant after Holm correction.
- S45 is the largest effect for all three metrics and drives the aggregate mean
  advantage.
- Excluding S45, the mean difference favors No Physics on all three metrics.

The correct conclusion is therefore heterogeneous and conditional: physics
substantially reduces the largest failure on S45/Fold 3, but it does not
consistently improve the typical held-out subject.

See [FINDINGS.md](FINDINGS.md) for the complete interpretation and sensitivity
analysis.

## Files

- `comparison_summary.json`: complete counts, validity checks, statistical
  summaries, sensitivity analysis, and fold results.
- `paired_seed_metrics.csv`: one paired aggregate row per seed.
- `paired_subject_metrics.csv`: one row per subject after averaging five seeds.
- `paired_subject_seed_metrics.csv`: all 75 subject-seed pairs.
- `paired_trial_metrics.csv`: one row per trial after averaging five seeds.
- `paired_trial_seed_metrics.csv`: all 330 trial-seed pairs.
- `paired_fold_seed_metrics.csv`: all 25 fold-seed comparisons.
- `training_selection_comparison.csv`: physics and no-physics checkpoint
  selections for all 25 seed/fold models.
- `figures/paired_seed_means.png`: direct pairing at each seed.
- `figures/paired_subject_means.png`: per-subject five-seed means and seed SD.
- `figures/paired_subject_difference_boxplots.png`: five paired seed
  differences per subject.
- `figures/paired_fold_difference_heatmaps.png`: seed-by-fold effects.
- `figures/paired_subject_scatter.png`: subject means against the equality line.
- `compare_five_seed_results.py`: reproducible comparison script.

## Reproduce

```bash
python compare_five_seed_results.py \
  --physics-results /path/to/physics_results \
  --no-physics-results /path/to/no_physics_results \
  --output .
```

The two result roots must contain the extracted five-seed result archives.

## Interpretation rules

- Five seeds characterize optimization variability; they do not increase the
  number of independent subjects from 15 to 75.
- The subject-level analysis is primary. Trial-level wins are descriptive
  because trials from one person are correlated.
- A lower error is better.
- The four outputs of the no-physics controller head are unsupervised latent
  variables and must not be interpreted as biomechanical gains.
- The result applies to the tested physics equation and weight
  `physics_weight=0.01`; it is not evidence about every possible physics loss.

