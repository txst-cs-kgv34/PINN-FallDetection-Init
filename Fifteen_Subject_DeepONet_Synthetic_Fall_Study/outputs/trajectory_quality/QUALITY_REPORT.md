# Synthetic trajectory quality report

## Protocol

- Generator checkpoints were selected only by fold-specific validation-subject loss.
- Synthetic contexts and real-real references use only each fold's 11 training subjects.
- Real-real comparisons pair different trials from the same subject.
- Shape comparisons use phase-normalized forecast trajectories.
- Velocity and acceleration use identical Savitzky–Golay smoothing for real and synthetic signals.
- Per-fold acceptance thresholds are the 95th percentiles of training real-real distances.
- Shape gate: normalized RMSE and DTW must both remain within their reference thresholds.
- Kinematic gate: at least 75% of displacement, velocity, and acceleration distances must remain within their thresholds.

## Important duration limitation

The model predicts theta and x but does not predict contact time. Each synthetic trajectory therefore inherits the apparent-contact endpoint and valid duration of its source context trial. Duration differences are reported for transparency but are excluded from automatic quality decisions.

## Counts

- Real-real reference pairs: 489
- Synthetic-real comparisons: 516
- Synthetic trajectories passing the complete gate: 257/516 (49.8%)

## Generator summary

| Fold | Rank | Seed | Trajectories | Pass rate | Mean normalized RMSE | Mean DTW | Theta RMSE | x RMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 3 | 52 | 38.5% | 1.1692 | 0.2658 | 17.653° | 23.007 cm |
| 1 | 2 | 1 | 52 | 38.5% | 1.1521 | 0.2390 | 16.976° | 22.984 cm |
| 2 | 1 | 5 | 51 | 60.8% | 0.6952 | 0.1780 | 10.559° | 13.556 cm |
| 2 | 2 | 2 | 51 | 60.8% | 0.5887 | 0.1359 | 9.000° | 11.411 cm |
| 3 | 1 | 4 | 52 | 63.5% | 0.8898 | 0.1662 | 13.691° | 17.325 cm |
| 3 | 2 | 5 | 52 | 65.4% | 0.8690 | 0.1629 | 13.211° | 16.972 cm |
| 4 | 1 | 3 | 52 | 67.3% | 1.0527 | 0.1751 | 15.072° | 21.269 cm |
| 4 | 2 | 5 | 52 | 61.5% | 1.1605 | 0.2118 | 16.548° | 23.555 cm |
| 5 | 1 | 3 | 51 | 17.6% | 1.3082 | 0.3087 | 19.206° | 26.225 cm |
| 5 | 2 | 4 | 51 | 23.5% | 1.2592 | 0.2905 | 18.860° | 24.967 cm |

Passing this gate indicates that a conditional trajectory lies within the predefined training-subject real-real variability envelope. It does not by itself prove downstream fall-detection utility; that must be tested on unseen real subjects.
