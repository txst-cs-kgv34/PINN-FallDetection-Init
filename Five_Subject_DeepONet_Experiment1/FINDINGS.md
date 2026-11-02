# Experiment 1 findings: five-subject leave-two-out DeepONet

## Bottom line

The experiment ran as designed, with strict subject separation and real-subject
validation, but the four-window context-conditioned model did **not** show a
consistent advantage over the training mean-gain baseline.

- It clearly helped on S43 and S63.
- It was effectively tied with the baseline on S55 and S62.
- It generalized poorly to S57 and was worse than the baseline on every pooled
  metric for that subject.
- Across the five equally weighted test subjects, it improved x MAE by 3.34% and
  x RMSE by only 0.52%, while the baseline was better on normalized MSE, all
  theta metrics, and x Wasserstein-1 distance.

This is a useful pilot result: the operator can transfer to some unseen subjects,
but four-window gain inference is not yet reliably better than a constant gain
prior. With five subjects and one seed per fold, this should be reported as mixed
evidence rather than a generalization success.

## Protocol check

The returned artifacts support the intended separation:

| Item | Verified result |
|:---|:---|
| Folds completed | 5 of 5 |
| Training per fold | 3 subject-PINN teachers × 100 synthetic trajectories = 300 |
| Model selection | Real validation-subject forecast normalized MSE only |
| Test use in selection | None |
| Test evaluation | Real trajectories from one unseen subject per fold |
| Context | Four 0.10-second windows covering the first 0.40 seconds |
| Included real trials | S43: 4, S63: 4, S55: 5, S57: 3, S62: 4 |
| Exclusions for short context | S63A11T05 and S62A11T02 |
| Device | Apple MPS |

The selected epochs were 65, 124, 2, 70, and 1 for folds 1–5. The very early
selection in folds 3 and 5 shows that their real validation losses stopped
favoring additional synthetic-teacher training almost immediately. This is not
test leakage, but it is a sign of synthetic-to-real mismatch and high
fold-to-fold instability.

## What the mean-gain baseline is

For a fold with training teachers \(j=1,2,3\), each teacher supplies

\[
g_j = [K_{p\theta}, K_{d\theta}, K_{px}, K_{dx}]_j.
\]

The baseline gain is the component-wise arithmetic mean

\[
\bar g_{train}=\frac{1}{3}\sum_{j=1}^{3}g_j.
\]

| Fold | Test | Training subjects | \(\bar g_{train}\): `[Kp_theta, Kd_theta, Kp_x, Kd_x]` |
|---:|:---:|:---|:---|
| 1 | S43 | S55, S57, S62 | `[187.267, 21.687, 11.890, 21.687]` |
| 2 | S63 | S43, S57, S62 | `[173.212, 19.466, 10.708, 19.470]` |
| 3 | S55 | S43, S63, S62 | `[162.670, 17.805, 11.288, 17.809]` |
| 4 | S57 | S43, S63, S55 | `[176.756, 20.029, 9.164, 20.032]` |
| 5 | S62 | S63, S55, S57 | `[204.860, 24.463, 11.522, 24.464]` |

The tuple does **not** come from the DeepONet context encoder. It is calculated
directly from the three selected subject-PINN teacher gain tuples and uses no
validation- or test-subject gain.

The baseline trajectory still comes from the same trained DeepONet forward
operator. For each real test trial, the two test paths are:

1. **Four-window DeepONet:** early real motion → context encoder → predicted
   gains → trained forward operator → predicted theta and x.
2. **Mean-gain baseline:** constant \(\bar g_{train}\) → the same trained forward
   operator → baseline theta and x.

Both paths use the same trial initial state, demographics, training-fold
auxiliary values, query times, valid mask, and 0.40-second forecast boundary.
The comparison isolates whether context-specific gain prediction is better than
always using an average training gain. It is not a comparison with a separate
physics simulator or a separately trained baseline model.

## Cross-fold results

All values below are pooled over every valid forecast sample for the named test
subject. Lower is better. The percentage is

\[
100\times\frac{E_{baseline}-E_{DeepONet}}{E_{baseline}},
\]

so positive means that context conditioning improved the result.

| Test subject | Trials | Forecast samples | Normalized MSE: model / baseline | Improvement | Theta RMSE deg: model / baseline | Improvement | x RMSE cm: model / baseline | Improvement |
|:---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S43 | 4 | 1,013 | 0.376 / 0.447 | +15.94% | 8.903 / 8.430 | -5.61% | 12.480 / 14.439 | +13.57% |
| S63 | 4 | 218 | 0.287 / 0.367 | +21.71% | 8.532 / 8.580 | +0.56% | 10.325 / 12.471 | +17.21% |
| S55 | 5 | 424 | 0.627 / 0.627 | -0.03% | 10.842 / 10.843 | +0.01% | 16.569 / 16.564 | -0.03% |
| S57 | 3 | 489 | 2.190 / 1.791 | -22.29% | 17.070 / 16.272 | -4.90% | 32.822 / 29.231 | -12.29% |
| S62 | 4 | 694 | 0.411 / 0.413 | +0.60% | 12.753 / 12.877 | +0.96% | 9.701 / 9.616 | -0.88% |

### Mean across held-out subjects

Every subject contributes one value to this table, regardless of its number of
trials or samples. The ± term is the sample standard deviation across subjects.

| Metric | 4-window DeepONet | Mean-gain baseline | Improvement |
|:---|---:|---:|---:|
| Normalized MSE | 0.778 ± 0.799 | 0.729 ± 0.602 | -6.75% |
| Theta MAE (deg) | 8.992 ± 3.191 | 8.886 ± 3.033 | -1.19% |
| Theta RMSE (deg) | 11.620 ± 3.482 | 11.401 ± 3.279 | -1.92% |
| Theta W1 (deg) | 7.812 ± 2.759 | 7.648 ± 2.753 | -2.13% |
| x MAE (cm) | 12.987 ± 7.035 | 13.436 ± 6.301 | +3.34% |
| x RMSE (cm) | 16.379 ± 9.577 | 16.464 ± 7.582 | +0.52% |
| x W1 (cm) | 10.508 ± 6.448 | 9.720 ± 3.473 | -8.11% |

The large standard deviations, especially for x, confirm that the five subjects
do not behave like repeated measurements from one stable error regime. S57 is
the dominant hard case.

## How to read `cross_fold_comparison.png`

The figure has three panels: normalized MSE, theta RMSE in degrees, and x RMSE
in centimeters. The horizontal axis names the completely held-out real test
subject.

- Blue is the prediction using gains inferred from that trial's first four
  motion windows.
- Orange is the prediction from the same trained forward operator using the
  constant training mean gain.
- A shorter bar is better.

It is not showing training loss, and “training mean gains” is not a gain learned
or emitted by DeepONet. The name means only that the gain tuple was averaged over
the three PINN teachers assigned to the training side of that fold.

The visual pattern is straightforward: S43 and S63 show meaningful x-error and
normalized-MSE reductions; S55 and S62 bars nearly overlap; and S57 is both the
largest-error test subject and the clearest regression from context conditioning.

## What `x_mae_cm` means

For valid forecast indices \(i=1,\ldots,N\), beginning at 0.40 seconds,

\[
x\_mae\_cm = 100\,\frac{1}{N}\sum_{i=1}^{N}
\left|\hat{x}_i-x_i\right|.
\]

Here \(x_i\) and \(\hat{x}_i\) are the measured and predicted forward-x values
in meters. Multiplication by 100 reports the mean absolute error in centimeters.
The x signal is the pole-compatible forward CoM coordinate after the experiment's
initial-position centering, not the full-body skeleton.

MAE weights every absolute miss linearly. RMSE squares the misses first and is
therefore more sensitive to large errors. Wasserstein-1 compares the two value
distributions and does not preserve point-by-point time alignment.

At the fold level, the reported pooled x MAE combines every valid forecast sample
from all accepted trials of that test subject. At the experiment level, the five
pooled subject x MAEs are averaged equally. Thus, a long S43 trajectory does not
give S43 more weight than S57 in the final cross-subject mean.

## Gain behavior and failure case

The context encoder did produce trial-dependent gains, but a changed gain is not
automatically a better gain. The average predicted test-trial gains were:

| Test | Training mean gain | Mean context-predicted gain over test trials |
|:---:|:---|:---|
| S43 | `[187.267, 21.687, 11.890, 21.687]` | `[185.135, 23.534, 12.198, 22.639]` |
| S63 | `[173.212, 19.466, 10.708, 19.470]` | `[221.535, 26.549, 13.691, 24.280]` |
| S55 | `[162.670, 17.805, 11.288, 17.809]` | `[167.634, 20.259, 13.449, 19.239]` |
| S57 | `[176.756, 20.029, 9.164, 20.032]` | `[248.717, 31.313, 17.934, 30.948]` |
| S62 | `[204.860, 24.463, 11.522, 24.464]` | `[138.076, 17.654, 2.971, 14.405]` |

For S57, the encoder moved all four gains substantially above the fold mean and
the resulting trajectory was worse on every pooled metric. This association
makes gain extrapolation a strong diagnostic target, but it does not by itself
prove that gain magnitude caused the failure. For S62, large gain changes yielded
nearly unchanged trajectory errors, which suggests that gain identifiability or
forward-operator sensitivity should also be tested.

## Recommended next steps

1. **Treat Experiment 1 as mixed/negative against its control.** Report the
   subject-specific successes, but do not claim consistent unseen-subject
   superiority.
2. **Repeat each fold with at least three optimization seeds.** Five held-out
   subjects measure subject variability, not training-seed variability.
3. **Diagnose S57 first.** Plot its three trial predictions and context gains,
   compare early-window feature ranges with the three training subjects, and
   test clipping predicted gains to the training-teacher min/max range.
4. **Add a stronger baseline.** In addition to the mean gain, compare nearest
   training teacher, demographic-weighted gain, and a direct trajectory model
   without the gain bottleneck.
5. **Test gain identifiability.** Sweep one gain at a time through the trained
   forward operator while holding the trial inputs fixed. If very different
   gains generate nearly identical trajectories, gain RMSE should not be treated
   as evidence of physiological identification.
6. **Proceed to Experiment 2.** The current result makes the direct-real versus
   subject-PINN-distilled ablation especially important. Use identical folds,
   contexts, validation rules, and metrics so the training source is the primary
   changed variable.
7. **Add more subjects when phase-marked data are available.** Five subjects are
   sufficient for a pilot protocol check, but not for a population-level claim.

## Files supporting these findings

- `results/full/aggregate_summary.json`: subject-equal means, standard
  deviations, and percent improvements.
- `results/full/cross_fold_metrics.csv`: one pooled row per held-out test subject.
- `results/full/cross_fold_comparison.png`: the three primary bar comparisons.
- `results/full/fold_*/summary.json`: fold roles, sample counts, and pooled
  metrics.
- `results/full/fold_*/test_metrics_by_trial.csv`: trial-level metrics and
  predicted gains.
- `results/full/fold_*/fold_manifest.json`: teacher IDs and training mean gains.
- `results/full/fold_*/training_selection.json`: validation-selected epoch and
  proof that the test subject was not used for selection.
