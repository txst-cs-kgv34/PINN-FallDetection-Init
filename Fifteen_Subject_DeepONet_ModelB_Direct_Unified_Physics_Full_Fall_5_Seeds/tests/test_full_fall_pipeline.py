from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from prepare_real_data import load_trial, pad_to_grid

try:
    import resampy  # noqa: F401
except ImportError:
    resampy = None


class FullFallPreparationTests(unittest.TestCase):
    @unittest.skipUnless(resampy is not None, "resampy is not installed")
    def test_loader_keeps_motion_beyond_twenty_degrees(self):
        warmup = 16
        motion_samples = 251
        theta = np.linspace(0.0, np.radians(110.0), motion_samples)
        marker_1 = np.column_stack(
            [np.sin(theta), np.cos(theta), np.zeros_like(theta)]
        )
        marker_2 = np.zeros_like(marker_1)
        motion = np.column_stack([marker_1, marker_2])
        raw = np.vstack([np.repeat(motion[:1], warmup, axis=0), motion])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "trial.tsv"
            np.savetxt(path, raw, delimiter="\t")
            loaded_theta, loaded_x = load_trial(
                path,
                {
                    "raw_warmup_rows": warmup,
                    "source_rate_hz": 250,
                    "target_rate_hz": 100,
                },
            )
        self.assertEqual(len(loaded_theta), len(loaded_x))
        self.assertGreater(float(np.max(np.abs(loaded_theta))), np.radians(100.0))

    def test_grid_refuses_to_silently_truncate_a_full_fall(self):
        with self.assertRaisesRegex(ValueError, "increase data.horizon_s"):
            pad_to_grid(np.arange(11, dtype=np.float32), 10)


if __name__ == "__main__":
    unittest.main()
