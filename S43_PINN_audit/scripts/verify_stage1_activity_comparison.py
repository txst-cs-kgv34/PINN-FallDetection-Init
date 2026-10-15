"""Regression checks for the retained A11/A13 Stage-1 comparison."""

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "comparison"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "compare_stage1_activities.py"),
                "--a11",
                str(ROOT / "analyses" / "S43_A11_stage1_inverted_pendulum"),
                "--a13",
                str(ROOT / "analyses" / "S43_A13_stage1_inverted_pendulum"),
                "--output",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        with (output / "activity_comparison.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = {row["activity"]: row for row in csv.DictReader(handle)}
        assert set(rows) == {"A11", "A13"}
        assert rows["A11"]["horizontal_axis"] == "forward"
        assert rows["A13"]["horizontal_axis"] == "lateral"
        assert np.isclose(float(rows["A11"]["data_only_xy_rmse_m"]), 0.24297435009691198)
        assert np.isclose(float(rows["A11"]["best_pinn_xy_rmse_m"]), 0.2519858034909324)
        assert float(rows["A11"]["trajectory_change_percent"]) > 0
        assert float(rows["A13"]["trajectory_change_percent"]) > 0
        assert float(rows["A11"]["residual_reduction_percent"]) > 0
        assert float(rows["A13"]["residual_reduction_percent"]) > 0
        assert (output / "activity_rmse_comparison.png").stat().st_size > 0
        summary = (output / "SUMMARY.md").read_text(encoding="utf-8")
        assert "lower residual alone is not evidence" in summary
        assert "do not increase its weight" in summary
    print("PASS retained A11/A13 Stage-1 comparison and interpretation guards")


if __name__ == "__main__":
    main()
