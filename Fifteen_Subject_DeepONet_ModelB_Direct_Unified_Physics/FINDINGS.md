# Findings: five-seed Unified Physics experiment

## Main result

The repeated Unified Physics experiment completed all 25 planned models: five
optimization seeds for each of the five grouped subject folds. Across seeds,
the model obtains:

| Held-out-subject metric | Mean | SD across the five seed means | Descriptive 95% t interval | CV |
|:---|---:|---:|---:|---:|
| Normalized MSE | 0.2143 | 0.0383 | [0.1667, 0.2619] | 17.9% |
| Angle RMSE | 5.103° | 0.420° | [4.582°, 5.625°] | 8.2% |
| CoM displacement RMSE | 7.772 cm | 0.574 cm | [7.059, 8.484] cm | 7.4% |

The physical-unit RMSE metrics are moderately stable, while normalized MSE is
more sensitive to the optimization seed. Five seeds reduce reliance on one
lucky or unlucky initialization, but they do not add new human subjects.

## Completeness and data-equivalence checks

- 5 optimization seeds × 5 folds = 25 completed trained models.
- 15 unique held-out subjects are evaluated once per seed.
- 66 unique eligible held-out trials are evaluated per seed.
- 75 subject-seed evaluations and 330 trial-seed evaluations are present.
- The trial IDs are identical across seeds.
- For every corresponding trial, `time_s`, `target_theta_rad`, and `target_x_m`
  are exactly identical across all five seeds (maximum absolute difference 0).
- Every corresponding generated trajectory differs from Seed 1 for Seeds 2–5.
- Every corresponding inferred four-controller vector differs from Seed 1 for
  Seeds 2–5.

These checks confirm that seed variability comes from model fitting, not from
different held-out samples or targets.

## Seed-level comparison

Each value below is the equal-weight mean of the 15 held-out subject means for
that seed.

| Seed index | Base seed | Normalized MSE | Angle RMSE | CoM displacement RMSE |
|---:|---:|---:|---:|---:|
| 1 | 20261101 | 0.2082 | 5.500° | 8.274 cm |
| 2 | 20261102 | 0.2311 | 5.355° | 8.136 cm |
| 3 | 20261103 | 0.2662 | 5.356° | 8.150 cm |
| 4 | 20261104 | 0.2041 | 4.737° | 7.231 cm |
| 5 | 20261105 | **0.1619** | **4.568°** | **7.067 cm** |

Seed 5 is numerically best on all three metrics, but selecting it after seeing
the test results would be optimistic model selection. The reported result must
remain the five-seed mean and variability. Seed 3 is worst for normalized MSE;
Seed 1 is worst for angle and displacement RMSE.

The observed best-to-worst span equals 48.7% of the five-seed normalized-MSE
mean, 18.3% of the angle-RMSE mean, and 15.5% of the displacement-RMSE mean.
That spread demonstrates why the earlier one-seed conclusion was fragile.

## Subject-level findings

S45 is the dominant difficult case in every seed:

| Subject | Normalized MSE mean ± SD | Interpretation |
|:---:|---:|:---|
| S45 | 1.1258 ± 0.5648 | Highest error and large seed sensitivity |
| S48 | 0.3947 ± 0.2081 | Second-highest mean; seed sensitive |
| S32 | 0.2966 ± 0.1881 | Third-highest mean; seed sensitive |
| S57 | 0.2322 ± 0.0677 | Elevated but more stable |
| S34 | 0.0393 ± 0.0405 | Lowest mean, though relative variability is large |
| S49 | 0.0587 ± 0.0651 | Low mean but sensitive in relative terms |
| S44 | 0.0595 ± 0.0320 | Low mean and moderate spread |

The result is therefore heterogeneous: an overall seed mean hides subjects
whose trajectories are consistently difficult and others whose success
depends strongly on initialization.

## Fold-level findings

| Fold | Test subjects | Normalized MSE mean ± SD | Angle RMSE mean ± SD | Displacement RMSE mean ± SD |
|---:|:---|---:|---:|---:|
| 1 | S57, S46, S30 | 0.1971 ± 0.0501 | 5.670° ± 0.791° | 9.447 ± 1.267 cm |
| 2 | S55, S48, S43 | 0.1861 ± 0.0575 | 5.675° ± 0.796° | 9.037 ± 1.543 cm |
| 3 | S45, S59, S56 | 0.5450 ± 0.2536 | 9.449° ± 2.255° | 15.400 ± 3.555 cm |
| 4 | S34, S32, S49 | 0.1534 ± 0.0930 | 5.384° ± 1.615° | 7.695 ± 2.646 cm |
| 5 | S44, S62, S63 | 0.0831 ± 0.0125 | 4.161° ± 0.247° | 5.845 ± 0.741 cm |

Fold 3 is the hardest and most variable, mainly because S45 is difficult. Fold
5 is the lowest-error and most stable fold. Fold 4 is also seed sensitive,
consistent with the large variation observed for S32.

## What changes with each seed?

The seed is not a new subject split and does not alter the biomechanics. It
initializes the Python, NumPy, and PyTorch random-number generators. This
changes:

1. the initial weights and biases of the context encoder, four-controller
   head, DeepONet branch, and Fourier trunk;
2. the shuffled order of training trajectories at every epoch;
3. the sequence of gradient updates and the optimization path;
4. the validation-loss curve and the checkpoint selected by early stopping;
5. the resulting held-out trajectory predictions and inferred controller
   outputs.

The validation-selected epoch ranges from 12 to 396, with a median of 83,
which is direct evidence that the optimization path changes substantially.

The seed does **not** change:

- the 15 subjects or their demographics;
- repaired skeleton rows or manual phase marks;
- the five train/validation/test folds (split seed remains 220);
- the 0.40-second context input or held-out targets;
- the DeepONet architecture;
- the cart-pole residual equations or physics weight 0.01;
- learning rate, optimizer, batch size, maximum epochs, or patience; or
- the definitions of normalized MSE, angle RMSE, and displacement RMSE.

The implementation uses:

```text
effective_fold_seed = base_optimization_seed + fold_id
```

Consequently, adjacent seed repeats can reuse the same numeric effective seed
on a *different* fold. Because those folds contain different data and subject
roles, they remain different training problems. Nevertheless, the five
seed-level aggregates do not use five completely disjoint sets of RNG numbers.
For the upcoming no-physics experiment, preserve this exact matrix so every
physics model has a matched no-physics counterpart. A future independent
study could use widely spaced base seeds.

## Controller-output interpretation

The four controller-head outputs change with seed because they are learned
jointly with the forecast model. Their variation is not evidence that a
person's actual physiology changes. They remain effective internal parameters,
not supervised or experimentally measured biomechanical gains. Forecast-error
stability should be the primary endpoint.

## Recommended comparison with no physics

Run B-no-physics with exactly the same five base seeds, fold offsets, subject
splits, data, and checkpoint-selection rule. Compare physics and no-physics
within each matched `(seed, subject)` pair. The primary comparison should:

1. average trials within subject;
2. calculate `no-physics error - physics error` for every matched seed and
   subject;
3. summarize the paired differences across seeds without treating the 75 rows
   as 75 independent people; and
4. report subject heterogeneity, seed heterogeneity, and fold heatmaps.

## Defensible conclusion

> Across five optimization seeds, Unified Physics achieved mean held-out
> subject errors of 0.214 normalized MSE, 5.10° angle RMSE, and 7.77 cm CoM
> displacement RMSE. Performance varied meaningfully with initialization,
> especially for normalized MSE and the difficult S45/S48/S32 subjects, so the
> five-seed distribution is more defensible than any single-seed result.
