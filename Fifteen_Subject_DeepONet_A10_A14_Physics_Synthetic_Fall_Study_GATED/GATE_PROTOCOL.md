# GATE protocol for A10-A14 conditional synthetic falls

## Reference populations

All thresholds are constructed from real training subjects in the same model
group, fold, and activity as the candidate. Validation and test subjects are
excluded from threshold construction.

Real-real shape and kinematic references pair different trials from the same
subject and activity. The threshold for distance metric `d` is:

```text
threshold(group, fold, activity, d)
  = Q95(within-subject same-activity real-real distances)
```

Lower distances are better. Boundary thresholds use individual real training
trajectories rather than real-real differences.

## Shape distances

Forecast segments beginning at 0.40 seconds are phase-resampled to 101 points.
For A10-A13:

```text
z(t) = [theta(t) / theta_scale, x(t) / x_scale]
```

For A14:

```text
z(t) = [theta(t) / theta_scale, x(t) / x_scale, yaw(t) / yaw_scale]
```

Normalized RMSE is the square root of the mean sum of squared normalized
channel errors. Normalized DTW uses Euclidean distance in this normalized
space and divides accumulated path cost by the combined sequence length.

Both normalized RMSE and normalized DTW must pass.

## Kinematic distances

Savitzky-Golay smoothing is applied identically to real and synthetic signals
before derivatives. The default window is 11 samples with polynomial order 3.

Planar candidates have six gated absolute differences:

- theta and CoM-x displacement;
- peak absolute theta and CoM-x velocity;
- peak absolute theta and CoM-x acceleration.

A14 adds yaw displacement, peak yaw velocity, and peak yaw acceleration, for
nine metrics total. At least 75% must pass their activity/fold p95 thresholds.
This requires five of six planar metrics or seven of nine rotation metrics.

Duration is reported but is not gated because the apparent-contact endpoint is
inherited from the source trial.

## Boundary continuity

For every channel, GATE measures:

- absolute position step from the final observed context sample to the first
  forecast sample; and
- absolute change between the sampled velocity immediately before and after
  the join.

All theta/x continuity metrics must pass. A14 must also pass both yaw metrics.

## Direction

When the source forecast displacement magnitude is at least 1 cm, synthetic
CoM-x displacement must have the same sign as the source. This respects the
activity-aligned A10-A13 coordinate and the source-conditioned A14 direction.

## Physics residuals

The generator's inferred gains are used for both its source real trajectory and
its synthetic trajectory. The planar residual metrics are:

```text
angular_scaled_RMSE   = RMSE(r_angular / (g/l))
horizontal_scaled_RMSE = RMSE(r_horizontal / g)
```

A14 also includes the yaw residual RMSE. Because inferred gains differ by
generator, physics thresholds are constructed separately by generator rank,
fold, and activity from real training trajectories. All applicable physics
metrics must pass.

## Duplicate protection

Each valid synthetic trajectory is rounded to seven decimal places and hashed.
Any exact repeated hash in the candidate set fails the duplicate gate. The
synthetic-synthetic diversity table remains available for reviewing close but
non-identical top-two outputs.

## Complete rule

```text
overall_quality_pass
  = finite metrics
  AND all continuity metrics pass
  AND normalized RMSE passes
  AND normalized DTW passes
  AND required kinematic fraction passes
  AND direction passes
  AND all physics residual metrics pass
  AND exact-duplicate gate passes
```

Passing GATE means the conditional trajectory is inside the predefined
training-data quality envelope. It does not establish that the trajectory is
an independent real fall or that it improves downstream fall detection.

