from __future__ import annotations

import unittest

import numpy as np

from quality_metrics import (
    Trajectory,
    kinematic_features,
    normalized_dtw,
    pair_distances,
    percentile_threshold,
)


class QualityMetricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.time = np.linspace(0.4, 1.4, 101)
        self.linear = Trajectory(
            self.time,
            theta_rad=0.2 * (self.time - 0.4),
            x_m=0.1 * (self.time - 0.4),
        )

    def test_identical_trajectory_distances_are_zero(self) -> None:
        metrics = pair_distances(
            self.linear,
            self.linear,
            phase_points=101,
            theta_scale_rad=np.deg2rad(25.0),
            x_scale_m=0.25,
            smoothing_window=11,
            polynomial_order=3,
        )
        for value in metrics.values():
            self.assertAlmostEqual(value, 0.0, places=10)

    def test_linear_velocity_and_acceleration(self) -> None:
        features = kinematic_features(self.linear, 11, 3)
        self.assertAlmostEqual(features["duration_s"], 1.0, places=12)
        self.assertAlmostEqual(
            features["peak_abs_theta_velocity_deg_s"], np.degrees(0.2), places=6
        )
        self.assertAlmostEqual(features["peak_abs_x_velocity_cm_s"], 10.0, places=6)
        self.assertLess(features["peak_abs_theta_acceleration_deg_s2"], 1e-8)
        self.assertLess(features["peak_abs_x_acceleration_cm_s2"], 1e-8)

    def test_dtw_and_higher_percentile(self) -> None:
        values = np.column_stack([np.arange(5.0), np.arange(5.0)])
        self.assertEqual(normalized_dtw(values, values), 0.0)
        self.assertEqual(percentile_threshold([1.0, 2.0, 3.0, 4.0], 75.0), 4.0)


if __name__ == "__main__":
    unittest.main()
