from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from quality_check import (
    apply_quality_gate,
    build_real_real_rows,
    build_synthetic_real_rows,
    thresholds_by_fold,
)


def record(subject: str, trial: str, offset: float):
    time = np.linspace(0.0, 1.4, 141, dtype=np.float32)
    theta = (0.1 * time + offset * time**2).astype(np.float32)
    x_m = (0.05 * time + 0.5 * offset * time**2).astype(np.float32)
    return SimpleNamespace(
        subject=subject,
        trial=trial,
        time_s=time,
        theta_rad=theta,
        x_m=x_m,
        valid_mask=np.ones_like(time),
    )


class QualityPipelineTests(unittest.TestCase):
    def test_training_only_reference_and_gate(self) -> None:
        experiment = {
            "model": {
                "context_region_s": 0.4,
                "theta_scale_rad": float(np.deg2rad(25.0)),
                "x_scale_m": 0.25,
            },
            "folds": [
                {
                    "id": 1,
                    "train": ["S01", "S02"],
                    "validation": "S03",
                    "test": ["S04", "S05", "S06"],
                }
            ],
        }
        settings = {
            "phase_normalized_points": 51,
            "real_real_percentile": 95.0,
            "savgol_window_samples": 11,
            "savgol_polynomial_order": 3,
        }
        records = [
            record(subject, f"{subject}A11T{trial:02d}", 0.01 * trial)
            for subject in ("S01", "S02")
            for trial in range(1, 4)
        ]
        real_real = build_real_real_rows(records, experiment, [1], settings)
        self.assertEqual(len(real_real), 6)
        self.assertEqual({row["subject"] for row in real_real}, {"S01", "S02"})

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = records[0]
            data_file = root / "fold_01" / "synthetic.npz"
            data_file.parent.mkdir(parents=True)
            np.savez_compressed(
                data_file,
                time_s=source.time_s,
                synthetic_theta_rad=source.theta_rad + 0.001,
                synthetic_x_m=source.x_m + 0.001,
                valid_mask=source.valid_mask,
            )
            manifest = {
                "samples": [
                    {
                        "synthetic_id": "fixture",
                        "fold": 1,
                        "generator_rank": 1,
                        "seed_index": 2,
                        "base_optimization_seed": 20261102,
                        "validation_subject": "S03",
                        "source_subject": "S01",
                        "source_trial": source.trial,
                        "transition_jump_theta_deg": 0.0,
                        "transition_jump_x_cm": 0.0,
                        "data_file": str(data_file.relative_to(root)),
                    }
                ]
            }
            synthetic_real, _ = build_synthetic_real_rows(
                root, manifest, records, experiment, settings
            )
            threshold_rows, lookup = thresholds_by_fold(
                real_real, [1], 95.0, minimum_pairs=2
            )
            self.assertTrue(threshold_rows)
            decisions = apply_quality_gate(
                synthetic_real,
                lookup,
                ["normalized_rmse", "dtw_normalized"],
                [
                    "theta_displacement_abs_difference_deg",
                    "x_displacement_abs_difference_cm",
                ],
                0.5,
            )
            self.assertEqual(len(decisions), 1)
            self.assertTrue(decisions[0]["overall_quality_pass"])


if __name__ == "__main__":
    unittest.main()
