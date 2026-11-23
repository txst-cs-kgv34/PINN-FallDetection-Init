from __future__ import annotations

import unittest

import numpy as np

from quality_metrics import (
    Trajectory,
    boundary_continuity_metrics,
    direction_consistent,
    kinematic_distance_metric_names,
    pair_distances,
    percentile_threshold,
)


class QualityMetricTests(unittest.TestCase):
    def test_identical_planar_and_rotation_distances_are_zero(self):
        time_s = np.linspace(0.4, 1.4, 101)
        planar = Trajectory(time_s, 0.2 * time_s, 0.1 * time_s)
        metrics = pair_distances(planar, planar, 101, 0.4, 0.25, None, 11, 3)
        self.assertAlmostEqual(metrics["normalized_rmse"], 0.0)
        self.assertTrue(all(metrics[name] == 0.0 for name in kinematic_distance_metric_names("planar")))
        rotation = Trajectory(time_s, 0.2 * time_s, 0.1 * time_s, -0.3 * time_s)
        metrics = pair_distances(rotation, rotation, 101, 0.4, 0.25, 1.57, 11, 3)
        self.assertAlmostEqual(metrics["yaw_rmse_deg"], 0.0)
        self.assertTrue(all(metrics[name] == 0.0 for name in kinematic_distance_metric_names("rotation")))

    def test_boundary_and_direction(self):
        time_s = np.linspace(0.0, 1.0, 101)
        valid = np.ones_like(time_s)
        metrics = boundary_continuity_metrics(
            time_s,
            time_s,
            2.0 * time_s,
            valid,
            0.40,
            -0.5 * time_s,
        )
        self.assertAlmostEqual(metrics["boundary_theta_velocity_change_deg_s"], 0.0, places=8)
        self.assertAlmostEqual(metrics["boundary_yaw_velocity_change_deg_s"], 0.0, places=8)
        source = Trajectory(time_s, time_s, time_s)
        same = Trajectory(time_s, time_s, 0.5 * time_s)
        opposite = Trajectory(time_s, time_s, -time_s)
        self.assertTrue(direction_consistent(same, source, 1.0))
        self.assertFalse(direction_consistent(opposite, source, 1.0))

    def test_higher_percentile(self):
        self.assertEqual(percentile_threshold([1.0, 2.0, 3.0, 4.0], 75.0), 4.0)


if __name__ == "__main__":
    unittest.main()

