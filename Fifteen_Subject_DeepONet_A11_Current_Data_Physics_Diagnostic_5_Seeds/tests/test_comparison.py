from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compare_results import holm_adjust, paired_table


class ComparisonTests(unittest.TestCase):
    def test_holm_adjustment_is_monotone_and_capped(self):
        adjusted = holm_adjust({"a": .01, "b": .03, "c": .20})
        self.assertAlmostEqual(adjusted["a"], .03)
        self.assertAlmostEqual(adjusted["b"], .06)
        self.assertAlmostEqual(adjusted["c"], .20)

    def test_positive_improvement_favors_physics(self):
        physics = [{"seed_index": "1", "test_subject": "S30", "normalized_mse": "2.0"}]
        baseline = [{"seed_index": "1", "test_subject": "S30", "normalized_mse": "3.0"}]
        rows = paired_table(
            physics,
            baseline,
            ("seed_index", "test_subject"),
            ("normalized_mse",),
        )
        self.assertEqual(rows[0]["physics_improvement_normalized_mse"], 1.0)
        self.assertGreater(rows[0]["physics_relative_improvement_pct_normalized_mse"], 0.0)

    def test_pairing_mismatch_fails(self):
        physics = [{"seed_index": "1", "test_subject": "S30", "normalized_mse": "2.0"}]
        baseline = [{"seed_index": "1", "test_subject": "S32", "normalized_mse": "3.0"}]
        with self.assertRaises(ValueError):
            paired_table(
                physics,
                baseline,
                ("seed_index", "test_subject"),
                ("normalized_mse",),
            )


if __name__ == "__main__":
    unittest.main()
