from __future__ import annotations

import unittest

import numpy as np

from prepare_audit_inputs import encode_as_two_markers, interpolate_to_rate


class AuditAdapterTests(unittest.TestCase):
    def test_marker_encoding_round_trip(self):
        theta = np.radians(np.asarray([-30.0, -5.0, 0.0, 12.0, 45.0]))
        x_m = np.asarray([-0.20, -0.03, 0.0, 0.07, 0.25])
        encoded = encode_as_two_markers(theta, x_m, 570.0)
        difference = encoded[:, :3] - encoded[:, 3:]
        length = np.linalg.norm(difference, axis=1)
        decoded_theta = np.arcsin(difference[:, 0] / length)
        decoded_x = encoded[:, 3] * 0.001
        np.testing.assert_allclose(decoded_theta, theta, atol=1e-12)
        np.testing.assert_allclose(decoded_x, x_m, atol=1e-12)

    def test_interpolation_keeps_endpoints(self):
        source = np.asarray([0.0, 1.0, 2.0, 3.0])
        target = interpolate_to_rate(source, 30.0, 250.0)
        self.assertAlmostEqual(float(target[0]), 0.0)
        self.assertAlmostEqual(float(target[-1]), 3.0)


if __name__ == "__main__":
    unittest.main()
