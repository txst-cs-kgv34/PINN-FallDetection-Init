# Findings: Model B physics versus B-no-physics

## Bottom line

The matched ablation does **not provide evidence that the cart-pole
biomechanics residual improves prediction of an unseen subject** under the
tested configuration (`physics_weight = 0.01`). B-no-physics has numerically
lower subject-mean error on all three primary metrics, but the paired effects
are inconsistent across the 15 subjects and all uncertainty intervals include
zero.

This is a negative or inconclusive ablation result, not proof that physics is
harmful. Only one optimization seed was run, and the difference changes
substantially by fold and subject.

## Validity of the comparison

The comparison script verified all of the following before calculating any
difference:

- same optimization seed and split seed;
- same 15 subjects and demographics;
- same five train/validation/test subject folds;
- same DeepONet architecture and context encoder;
- same data preparation, optimizer, learning rate, maximum epochs, and early
stopping rule;
- same 66 eligible held-out trials; and
- exactly identical stored test time and target theta/x arrays.

The only objective change is:

```text
Physics:     L = L_real_forecast + 0.01 * L_cart_pole_biomechanics
No physics: L = L_real_forecast
```

## Primary held-out-subject comparison

Every subject contributes one value: the mean over that subject's eligible
held-out trials. This avoids treating correlated trials from the same person
as independent observations.

Define physics improvement as:

```text
no-physics error - physics error
```

A positive value favors physics; a negative value favors no-physics.

| Metric | Physics mean | No-physics mean | Mean physics improvement (95% subject-bootstrap CI) | Relative change of physics mean | Physics wins | Wilcoxon p |
|:---|---:|---:|---:|---:|---:|---:|
| Normalized MSE | 0.2584 | **0.2363** | -0.0221 [-0.1371, 0.0909] | 9.4% higher error | 7/15 | 0.639 |
| Angle RMSE (degrees) | 5.698 | **4.810** | -0.888 [-2.135, 0.326] | 18.5% higher error | 6/15 | 0.229 |
| CoM displacement RMSE (cm) | 8.868 | **7.787** | -1.081 [-3.003, 0.631] | 13.9% higher error | 7/15 | 0.454 |

All three intervals cross zero and all two-sided paired Wilcoxon p-values are
greater than 0.05. No formal superiority claim is supported in either
direction.

The held-out-trial win counts are similarly balanced: physics wins 31/66,
30/66, and 32/66 trials for normalized MSE, angle RMSE, and displacement RMSE,
respectively. These are descriptive only because trials belonging to one
subject are not independent.

## Subject-level normalized MSE

| Subject | Fold | Physics | No physics | Lower-error condition |
|:---:|---:|---:|---:|:---|
| S30 | 1 | **0.0151** | 0.0348 | Physics |
| S32 | 4 | 0.7267 | **0.1397** | No physics |
| S34 | 4 | 0.2142 | **0.0306** | No physics |
| S43 | 2 | **0.1184** | 0.1739 | Physics |
| S44 | 5 | **0.0984** | 0.2458 | Physics |
| S45 | 3 | **1.1588** | 1.6964 | Physics |
| S46 | 1 | **0.0971** | 0.1399 | Physics |
| S48 | 2 | 0.4658 | **0.3417** | No physics |
| S49 | 4 | 0.2020 | **0.0724** | No physics |
| S55 | 2 | 0.1666 | **0.0971** | No physics |
| S56 | 3 | 0.0936 | **0.0750** | No physics |
| S57 | 1 | **0.1771** | 0.2582 | Physics |
| S59 | 3 | 0.0688 | **0.0466** | No physics |
| S62 | 5 | **0.1097** | 0.1499 | Physics |
| S63 | 5 | 0.1642 | **0.0431** | No physics |

S45 is difficult for both conditions but contributes a large improvement in
favor of physics. Conversely, S32 is a large improvement in favor of
no-physics. The overall mean is therefore sensitive to a small number of
subjects; medians, paired plots, and win counts should accompany every mean.

## Fold and axis observations

Physics has lower pooled normalized MSE in Folds 1, 3, and 5; no-physics is
lower in Folds 2 and 4. Fold 4 shows the largest no-physics advantage
(`0.3929` versus `0.0993`) and contains S34, S32, and S49. S32 and S34 were the
front-fall recordings oriented toward the camera/Z axis, but orientation alone
cannot explain the result: tilted-Z S30 favors physics, and slightly tilted-Z
S44 also favors physics. Fold-level checkpoint behavior, subject composition,
trajectory length, and axis construction remain confounded.

The validation-selected epochs also differ because removing the physics term
changes the optimization path:

| Fold | Validation subject | Physics epoch / val nMSE | No-physics epoch / val nMSE |
|---:|:---:|---:|---:|
| 1 | S63 | 64 / 0.0281 | 169 / 0.0415 |
| 2 | S62 | 86 / 0.1098 | 276 / 0.0447 |
| 3 | S57 | 405 / 0.1628 | 84 / 0.1633 |
| 4 | S55 | 26 / 0.1043 | 97 / 0.0863 |
| 5 | S43 | 37 / 0.0433 | 50 / 0.0876 |

Lower validation loss does not consistently predict the three-subject test
result. That is expected with only one validation subject per fold.

## Controller-output interpretation

Both models save four outputs from the positive controller head for every
trial. In the no-physics model those outputs are completely unsupervised
latent conditioning variables. In the physics model they influence the
residual but are still not supervised by measured human-control parameters.
Their numerical values are therefore not a valid target for the ablation and
must not be described as recovered physiological gains.

## Recommended next experiment

1. Repeat both conditions with at least 5, preferably 10, paired optimization

   seeds while preserving every fold and pairing seeds across conditions.
2. Report the distribution of paired subject-level differences across seeds,

   not just trial-pooled means.
3. If retaining physics, tune its weight using training/validation data only;

   include `0, 1e-4, 1e-3, 1e-2, 1e-1` as a practical starting grid.
4. Audit the residual scale relative to data loss and report both unweighted

   and weighted terms. A nominal weight of 0.01 does not by itself describe
    the effective gradient contribution.
5. Stratify or standardize the anatomical forward axis before attributing

   subject differences to biomechanics.

Until those repeats are available, the defensible statement is:

> In one matched five-fold, 15-subject run, adding the cart-pole residual at
> weight 0.01 did not improve average held-out-subject trajectory error over
> the otherwise identical no-physics DeepONet; paired differences were
> heterogeneous and inconclusive.
