from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from detector_data_core import load_skeleton_csv, resample_signal, segment_model
from prepare_detector_data import fall_sample_files, initialize_output, resolved_path


class DetectorDataCoreTests(unittest.TestCase):
    def test_segment_mass_models_sum_to_one(self) -> None:
        for sex in ("male", "female"):
            self.assertAlmostEqual(
                sum(segment["mass_fraction"] for segment in segment_model(sex)),
                1.0,
                places=9,
            )

    def test_wholly_blank_skeleton_row_is_interpolated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "trial.csv"
            first = np.arange(96, dtype=float)
            third = first + 2.0
            path.write_text(
                ",".join(map(str, first))
                + "\n"
                + "," * 95
                + "\n"
                + ",".join(map(str, third))
                + "\n",
                encoding="utf-8",
            )
            data, repaired = load_skeleton_csv(path)
            self.assertEqual(repaired, [1])
            np.testing.assert_allclose(data[1], first + 1.0)

    def test_resample_to_thirty_hz(self) -> None:
        time = np.arange(101, dtype=float) / 100.0
        target_time, theta, x_m = resample_signal(time, 2.0 * time, time, 30.0)
        self.assertEqual(len(target_time), 31)
        self.assertAlmostEqual(float(target_time[-1]), 1.0, places=6)
        np.testing.assert_allclose(theta, 2.0 * target_time, atol=1e-6)
        np.testing.assert_allclose(x_m, target_time, atol=1e-6)

    def test_repository_default_path_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project_root = Path(temporary).resolve()
            self.assertEqual(
                resolved_path(None, project_root, "FallSamples"),
                project_root / "FallSamples",
            )

    def test_fall_sample_discovery_covers_a10_to_a14(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fall_root = Path(temporary) / "FallSamples"
            subject_root = fall_root / "S30_FallSamples"
            subject_root.mkdir(parents=True)
            for activity in range(10, 15):
                (subject_root / f"S30A{activity:02d}T01.csv").touch()
            files = fall_sample_files(fall_root, "S30")
            self.assertEqual(set(files), {f"S30A{activity:02d}T01" for activity in range(10, 15)})

    def test_output_overwrite_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project_root = Path(temporary).resolve()
            output_root = project_root / "detector" / "outputs"
            output_root.mkdir(parents=True)
            (output_root / "stale.txt").write_text("old", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                initialize_output(output_root, False, project_root)
            initialize_output(output_root, True, project_root)
            self.assertEqual(list(output_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
