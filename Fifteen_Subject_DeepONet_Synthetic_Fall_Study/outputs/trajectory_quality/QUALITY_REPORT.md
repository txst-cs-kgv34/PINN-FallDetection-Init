# Synthetic trajectory quality report

## Protocol

- Generator checkpoints were selected only by fold-specific validation-subject loss.
- Synthetic contexts and real-real references use only each fold's 11 training subjects.
- Real-real comparisons pair different trials from the same subject.
- Shape comparisons use phase-normalized forecast trajectories.
- Velocity and acceleration use identical Savitzky–Golay smoothing for real and synthetic signals.
- Per-fold acceptance thresholds are the 95th percentiles of training real-real distances.
- Boundary continuity is checked against the fold-specific 95th-percentile position step and velocity change of real training trajectories at 0.40 s.
- Continuity gate: all four theta/x position-step and velocity-change metrics must pass.
- Shape gate: normalized RMSE and DTW must both remain within their reference thresholds.
- Kinematic gate: at least 75% of displacement, velocity, and acceleration distances must remain within their thresholds.

## Important duration limitation

The model predicts theta and x but does not predict contact time. Each synthetic trajectory therefore inherits the apparent-contact endpoint and valid duration of its source context trial. Duration differences are reported for transparency but are excluded from automatic quality decisions.

## Counts

- Real-real reference pairs: 489
- Synthetic-real comparisons: 516
- Synthetic trajectories passing the complete gate: 226/516 (43.8%)
- Continuity-gate passes: 474/516

## Generator summary

| Fold | Rank | Seed | Trajectories | Pass rate | Mean normalized RMSE | Mean DTW | Theta RMSE | x RMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 3 | 52 | 32.7% | 1.1531 | 0.2575 | 17.363° | 22.734 cm |
| 1 | 2 | 1 | 52 | 32.7% | 1.1387 | 0.2298 | 16.727° | 22.765 cm |
| 2 | 1 | 5 | 51 | 52.9% | 0.6901 | 0.1732 | 10.494° | 13.436 cm |
| 2 | 2 | 2 | 51 | 52.9% | 0.5844 | 0.1313 | 8.952° | 11.309 cm |
| 3 | 1 | 4 | 52 | 55.8% | 0.8743 | 0.1554 | 13.384° | 17.067 cm |
| 3 | 2 | 5 | 52 | 59.6% | 0.8542 | 0.1531 | 12.914° | 16.734 cm |
| 4 | 1 | 3 | 52 | 59.6% | 1.0446 | 0.1669 | 14.963° | 21.113 cm |
| 4 | 2 | 5 | 52 | 53.8% | 1.1493 | 0.2041 | 16.374° | 23.345 cm |
| 5 | 1 | 3 | 51 | 15.7% | 1.2949 | 0.3016 | 19.006° | 25.957 cm |
| 5 | 2 | 4 | 51 | 21.6% | 1.2460 | 0.2842 | 18.662° | 24.702 cm |

Passing this gate indicates that a conditional trajectory lies within the predefined training-subject real-real variability envelope. It does not by itself prove downstream fall-detection utility; that must be tested on unseen real subjects.

The detector-ready list is `final_approved_synthetic_manifest.json`; rejected candidates remain available for audit but must not enter downstream training.
