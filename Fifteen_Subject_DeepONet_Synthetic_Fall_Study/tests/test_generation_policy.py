from __future__ import annotations

import unittest

import numpy as np

from generate_synthetic import combine_context_and_forecast, transition_jump


class GenerationPolicyTests(unittest.TestCase):
    def test_observed_context_and_model_forecast_are_separated_at_point_four(self) -> None:
        time = np.arange(0.0, 1.001, 0.001, dtype=np.float32)
        real_theta = time.copy()
        real_x = 2.0 * time
        prediction = np.column_stack([10.0 + time, 20.0 + time]).astype(np.float32)
        valid = np.ones_like(time)
        theta, x_m, context, forecast, corrected, metadata = combine_context_and_forecast(
            real_theta,
            real_x,
            prediction,
            time,
            valid,
            context_region_s=0.4,
        )
        np.testing.assert_allclose(theta[context], real_theta[context])
        np.testing.assert_allclose(x_m[context], real_x[context])
        boundary = np.flatnonzero(np.isclose(time, 0.4))[0]
        self.assertTrue(context[boundary])
        self.assertFalse(forecast[boundary])
        self.assertAlmostEqual(corrected[boundary, 0], real_theta[boundary], places=5)
        self.assertAlmostEqual(corrected[boundary, 1], real_x[boundary], places=5)
        self.assertAlmostEqual(metadata["theta_observed_boundary_velocity"], 1.0, places=4)
        self.assertAlmostEqual(metadata["x_observed_boundary_velocity"], 2.0, places=4)
        corrected_theta_slope = (corrected[boundary + 1, 0] - corrected[boundary, 0]) / (
            time[boundary + 1] - time[boundary]
        )
        corrected_x_slope = (corrected[boundary + 1, 1] - corrected[boundary, 1]) / (
            time[boundary + 1] - time[boundary]
        )
        self.assertAlmostEqual(corrected_theta_slope, 1.0, delta=0.25)
        self.assertAlmostEqual(corrected_x_slope, 2.0, delta=0.5)
        self.assertFalse(np.allclose(theta[forecast], prediction[forecast, 0]))
        jump_theta, jump_x = transition_jump(theta, x_m, context, forecast)
        self.assertGreater(jump_theta, 0.0)
        self.assertGreater(jump_x, 0.0)
        self.assertLess(jump_theta, 0.1)
        self.assertLess(jump_x, 0.3)


if __name__ == "__main__":
    unittest.main()
