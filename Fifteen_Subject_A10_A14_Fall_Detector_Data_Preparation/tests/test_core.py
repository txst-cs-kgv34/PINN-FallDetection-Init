import unittest

import numpy as np

from detector_data_core import parse_trial, ratio_policies, resample_valid


class CoreTests(unittest.TestCase):
    def test_trial_parser(self):
        self.assertEqual(parse_trial("S43A14T05"), ("S43", 14, 5))

    def test_ratio_policies(self):
        policies = ratio_policies(10)
        self.assertEqual(policies["real60_synthetic40"]["real_per_fall_batch"], 6)
        self.assertEqual(policies["real60_synthetic40"]["synthetic_per_fall_batch"], 4)
        self.assertEqual(policies["real40_synthetic60"]["real_per_fall_batch"], 4)
        self.assertEqual(policies["real40_synthetic60"]["synthetic_per_fall_batch"], 6)

    def test_ratio_size_guard(self):
        with self.assertRaises(ValueError):
            ratio_policies(8)

    def test_resample(self):
        time = np.arange(101) / 100.0
        signal = 2.0 * time
        target, values = resample_valid(time, signal, target_hz=30.0)
        self.assertEqual(len(target), 31)
        np.testing.assert_allclose(values, 2.0 * target, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
