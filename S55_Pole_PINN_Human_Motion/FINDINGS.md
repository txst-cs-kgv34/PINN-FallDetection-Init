# Findings: S55 pole-PINN full run

## Executive conclusion

The rerun is technically valid and subject-clean: it used exactly the five S55 A11 trials, completed all four stages, and generated 100 finite synthetic trajectories. The identified controller is reproducible, but the final Stage-3 model does not reconstruct the observed S55 falls nearly as well as Stage 1. Stage 3's pooled normalized MSE is 161.9 times Stage 1's, and its error is concentrated in T01, T03, and T04.

The synthetic set is useful as output from the current model, but not yet as a validated representation of long S55 falls. The measured support ends at 0.53-1.52 s, whereas every synthetic trajectory first crosses 20 degrees at about 4.84-5.15 s and then extrapolates to 30 s.

## Data and integrity checks

- Subject: S55, male, 145 lb, 5 ft 5 in.
- Activity: A11 front fall.
- Included trials: T01-T05 only; 624 total samples.
- A11 repaired rows: zero in all five source manifests.
- Core source SHA-256: `604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9`.
- Full archive integrity test: passed.
- Final and Stage-3 checkpoint bytes: identical, confirming the restored best Stage-3 state was packaged.

## Identified controller

| Parameter | Value |
|:---|---:|
| `Kp_theta` | 145.145751953125 |
| `Kd_theta` | 15.052887916565 |
| `Kp_x` | 5.059634685516 |
| `Kd_x` | 15.053012847900 |
| `Pi` | 3.625025144902 deg |
| `tau` | 0.23 s |

Training minima were `2.812356e-03` for the Stage-1 objective, `7.618546` for the Stage-2 inverse objective, and `1726.196` for the Stage-3 objective. These training objectives are not interchangeable with the post-training trajectory metrics below.

## Checkpoint reconstruction

All values pool the same 624 measured samples.

| Checkpoint | Normalized MSE | Theta RMSE | Theta MAE | x RMSE | x MAE |
|:---|---:|---:|---:|---:|---:|
| Stage 1 | **0.0029866** | **0.7108 deg** | **0.5618 deg** | **1.1668 cm** | **0.9259 cm** |
| Stage 3/final | 0.4835740 | 9.6187 deg | 6.2965 deg | 14.4815 cm | 9.4606 cm |

Stage 3 is 161.9 times worse in normalized MSE. Its trial-level reconstruction is:

| Trial | Samples | Normalized MSE | Theta RMSE | x RMSE |
|:---|---:|---:|---:|---:|
| T01 | 147 | 0.69899 | 11.280 deg | 17.597 cm |
| T02 | 54 | **0.02445** | **1.955 deg** | 3.385 cm |
| T03 | 136 | 0.67858 | 11.429 deg | 17.132 cm |
| T04 | 134 | 0.76872 | 12.164 deg | 18.234 cm |
| T05 | 153 | **0.01557** | 2.837 deg | **1.297 cm** |

The trajectory plot agrees with the metrics. Stage 1 closely follows the observed windows. Stage 3 moves in the wrong late-window direction for T01, T03, and T04; it follows short T02 roughly and tracks T05 more closely, while underpredicting T05's late rise.

## Synthetic trajectory audit

All 100 requested `.npy` trajectories exist, contain 3,001 finite samples at 100 Hz, and cover 30 s. Across the complete synthetic set:

- theta ranges from -159.409 to 279.160 degrees;
- x ranges from -108.289 to 50.471 m;
- first 20-degree crossing ranges from 4.84 to 5.15 s, median 4.92 s.

Those extremes occur far outside the measured time span, so they test the network's extrapolation rather than agreement with recorded human motion. Long-horizon values should not be interpreted as observed whole-body fall kinematics.

## Short-horizon distribution comparison

The common measured window is controlled by T02 and ends at 0.53 s in the full-run distribution analysis.

| Variable | Pooled W1 | 95% bootstrap CI | Mean time-resolved W1 | Real-real median W1 | Synthetic-split median W1 | Real points inside synthetic 5-95% envelope |
|:---|---:|---:|---:|---:|---:|---:|
| Theta | 2.981 deg | [1.430, 5.195] | 3.103 deg | 4.536 deg | 0.344 deg | 37.4% |
| x | 2.175 cm | [1.259, 3.773] | 3.037 cm | 1.359 cm | 0.046 cm | 4.8% |

Theta's pooled W1 is below the median distance between real trials, but the synthetic ensemble is much less diverse than the human trials. For x, the real-synthetic distance exceeds typical real-real variation, while synthetic-split distance is almost zero. Only 4.8% of real x observations lie inside the synthetic 5-95% envelope. Thus a moderate W1 value must not be read as good coverage; the synthetic ensemble is too narrow.

Horizon sensitivity supports the same conclusion:

| Horizon | Theta W1 | x W1 |
|---:|---:|---:|
| 0.25 s | 3.242 deg | 0.974 cm |
| 0.50 s | 2.952 deg | 1.843 cm |
| 0.53 s | 2.981 deg | 2.175 cm |

Even after matching each observed trial to a synthetic trajectory with a similar initial angle, theta RMSE remains 6.54-8.32 degrees and x RMSE remains 9.00-13.40 cm. Initial-angle mismatch is therefore not the main cause of the reconstruction gap.

## Interpretation

The clean S55 run identifies a controller and completes the requested generation pipeline, but Stage 3 trades away most of Stage 1's empirical fit. The result indicates a mismatch among the Stage-3 physics/history objectives, the observed short human windows, and the extrapolated fall behavior. The 100 trajectories are highly repeatable relative to one another but do not reproduce S55's across-trial spread, particularly for forward CoM.

The gain sweep improves the final reconstruction somewhat, but it does not close this gap: its best chunk has normalized MSE `0.430774`, still 144.2 times the Stage-1 normalized MSE. Controller tuning alone is therefore insufficient.

## Recommended use and next steps

1. Use Stage 1 when the goal is reconstruction of the observed S55 windows.
2. Label the 100 Stage-3 outputs as model-generated pole/CoM trajectories, not validated full-body or 30-second human falls.
3. Treat comparisons after the measured window as extrapolation.
4. Repeat promising sweep settings across multiple random seeds before selecting a controller.
5. Examine Stage-3 loss weights, initial/history constraints, and synthetic initial-condition diversity before using S55 as a teacher model.
