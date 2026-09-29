"""Regression checks for the standing-body reconstruction pilot."""

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from subject_frame import standing_body_frame, to_subject_frame

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check_known_frame():
    pose = np.zeros((5, 32, 3), dtype=float)
    pose[:, 21] = [-0.1, 0.0, 0.0]
    pose[:, 25] = [0.1, 0.0, 0.0]
    pose[:, 26] = [0.0, 1.6, 0.0]
    pose[:, 27] = [0.0, 1.6, 0.1]
    pose[:, 18] = [-0.15, 0.9, 0.0]
    pose[:, 22] = [0.15, 0.9, 0.0]
    frame = standing_body_frame(pose, 2)
    transformed = to_subject_frame(np.array([[0.2, 1.0, 0.3]]), frame)[0]
    assert np.allclose(transformed, [0.2, 1.0, 0.3], atol=1e-12)
    assert np.allclose(
        frame["basis_camera_columns"].T @ frame["basis_camera_columns"],
        np.eye(3),
        atol=1e-12,
    )


def main():
    check_known_frame()
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "pilot"
        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_reconstruction_pilot.py"),
            "--run",
            str(ROOT / "findings" / "S43_audit"),
            "--config",
            str(ROOT / "configs" / "S43.json"),
            "--selection",
            str(ROOT / "configs" / "S43_modeling_selection.json"),
            "--phase-notes",
            str(ROOT / "analysis_inputs" / "S43_phase_notes_with_A13_eligibility.json"),
            "--output",
            str(output),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        metrics = read_csv(output / "fold_metrics.csv")
        predictions = read_csv(output / "fold_predictions.csv")
        frames = json.loads((output / "subject_frames.json").read_text())
        assert len(metrics) == 8
        assert len(predictions) == 4 * 101
        assert len(frames) == 4
        assert {row["held_out_trial"] for row in metrics} == {
            "S43A13T01",
            "S43A13T02",
            "S43A13T03",
            "S43A13T05",
        }
        assert {row["method"] for row in metrics} == {
            "training_mean",
            "polynomial_ridge",
        }
        for row in predictions[::101]:
            for axis in AXIS_KEYS:
                assert abs(float(row[f"actual_{axis}_m"])) < 1e-12
                assert abs(float(row[f"polynomial_ridge_{axis}_m"])) < 1e-12
        assert len(list((output / "plots").glob("*.png"))) == 4
    print("PASS standing-body frame and four-fold reconstruction pilot")


AXIS_KEYS = ("lateral_right", "vertical_headward", "forward_nose_proxy")


if __name__ == "__main__":
    main()
