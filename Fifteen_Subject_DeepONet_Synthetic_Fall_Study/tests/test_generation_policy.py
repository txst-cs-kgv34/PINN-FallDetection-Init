from __future__ import annotations

import unittest

import numpy as np

from generate_synthetic import combine_context_and_forecast, transition_jump


class GenerationPolicyTests(unittest.TestCase):
    def test_observed_context_and_model_forecast_are_separated_at_point_four(self) -> None:
        time = np.arange(0.0, 1.01, 0.1, dtype=np.float32)
        real_theta = time.copy()
        real_x = 2.0 * time
        prediction = np.column_stack([10.0 + time, 20.0 + time]).astype(np.float32)
        valid = np.ones_like(time)
        theta, x_m, context, forecast = combine_context_and_forecast(
            real_theta,
            real_x,
            prediction,
            time,
            valid,
            context_region_s=0.4,
        )
        np.testing.assert_allclose(theta[context], real_theta[context])
        np.testing.assert_allclose(x_m[context], real_x[context])
        np.testing.assert_allclose(theta[forecast], prediction[forecast, 0])
        np.testing.assert_allclose(x_m[forecast], prediction[forecast, 1])
        self.assertTrue(forecast[np.flatnonzero(np.isclose(time, 0.4))[0]])
        jump_theta, jump_x = transition_jump(theta, x_m, context, forecast)
        self.assertGreater(jump_theta, 0.0)
        self.assertGreater(jump_x, 0.0)


if __name__ == "__main__":
    unittest.main()
