from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from generate_synthetic import combine_context_and_forecast, selected_generator_rows


class GenerationPolicyTests(unittest.TestCase):
    def test_c1_bridge_supports_rotation_channels(self):
        time_s = np.linspace(0.0, 1.0, 101)
        real = np.column_stack((time_s, 2.0 * time_s, -0.5 * time_s))
        raw = real + np.asarray([0.2, -0.3, 0.4])
        valid = np.ones_like(time_s)
        synthetic, context, forecast, corrected, metadata = combine_context_and_forecast(
            real, raw, time_s, valid, 0.40, 0.15, 11
        )
        boundary = int(np.flatnonzero(context)[-1])
        self.assertTrue(np.allclose(synthetic[context], real[context]))
        self.assertTrue(np.allclose(corrected[boundary], real[boundary], atol=1e-7))
        self.assertEqual(synthetic.shape[1], 3)
        self.assertGreater(int(forecast.sum()), 0)
        self.assertIn("channel_2_velocity_offset", metadata)

    def test_lambda_zero_selection_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / "state.pt"
            checkpoint.write_bytes(b"state")
            selection = root / "selection.json"
            selection.write_text(
                json.dumps(
                    {
                        "groups": {
                            "planar": {
                                "selected": [
                                    {
                                        "model_group": "planar",
                                        "fold": 1,
                                        "rank_within_fold": 1,
                                        "physics_weight": 0.0,
                                        "checkpoint": str(checkpoint),
                                    }
                                ]
                            },
                            "rotation": {"selected": []},
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "lambda=0"):
                selected_generator_rows(selection)


if __name__ == "__main__":
    unittest.main()

