"""Regression checks for phase-note validation and the S43 baseline outputs."""

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "baseline"
        command = [
            sys.executable,
            str(ROOT / "scripts" / "build_phase_baseline.py"),
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
        validation = json.loads((output / "phase_validation.json").read_text())
        windows = read_csv(output / "phase_windows.csv")
        aligned = read_csv(output / "phase_aligned_com.csv")
        baseline = read_csv(output / "leave_one_out_baseline.csv")
        priority = read_csv(output / "trial_priority.csv")
        assert validation["annotated_trials"] == 17
        assert validation["annotations"] == 84
        assert len(windows) == 17
        assert len(aligned) == 17 * 101
        assert len(baseline) == 17
        assert len(priority) == 17
        assert "S43A10T01" not in {row["trial"] for row in windows}
        assert "S43A13T04" not in {row["trial"] for row in windows}
        assert "S43A13T05" in {row["trial"] for row in windows}
        t05 = next(row for row in windows if row["trial"] == "S43A13T05")
        assert t05["post_fall_frame0"] == ""
        for row in aligned[::101]:
            for axis in ("camera_x", "camera_y", "camera_z"):
                assert abs(float(row[f"com_delta_{axis}_m"])) < 1e-12
        assert len(list((output / "plots").glob("A*_phase_aligned_com.png"))) == 5
    print("PASS phase annotations, windows, normalized trajectories and LOO baseline")


if __name__ == "__main__":
    main()
