from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compare_calibration import holm_adjust, pair_rows


class ComparisonTests(unittest.TestCase):
    def test_holm_adjustment_is_monotone_and_capped(self):
        adjusted = holm_adjust({"a": .01, "b": .03, "c": .20})
        self.assertAlmostEqual(adjusted["a"], .03)
        self.assertAlmostEqual(adjusted["b"], .06)
        self.assertAlmostEqual(adjusted["c"], .20)

    def test_positive_improvement_favors_selected_v2(self):
        selected = [{"seed_index": "1", "test_subject": "S30", **{metric: "2.0" for metric in (
            "normalized_mse", "theta_rmse_deg", "theta_mae_deg", "x_rmse_cm",
            "x_mae_cm", "theta_w1_deg", "x_w1_cm", "angular_residual_rmse",
            "horizontal_residual_rmse")}}]
        baseline = [{"seed_index": "1", "test_subject": "S30", "normalized_mse": "3.0"}]
        baseline[0].update({key: "3.0" for key in selected[0] if key not in {"seed_index", "test_subject"}})
        rows = pair_rows(selected, baseline, ("seed_index", "test_subject"))
        self.assertEqual(rows[0]["selected_v2_improvement_normalized_mse"], 1.0)
        self.assertGreater(rows[0]["selected_v2_relative_improvement_pct_normalized_mse"], 0.0)

    def test_pairing_mismatch_fails(self):
        selected = [{"seed_index": "1", "test_subject": "S30"}]
        baseline = [{"seed_index": "1", "test_subject": "S32"}]
        with self.assertRaises(ValueError):
            pair_rows(selected, baseline, ("seed_index", "test_subject"))


if __name__ == "__main__":
    unittest.main()
