"""Regression checks for automatic differentiation and the A13 PINN workflow."""

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from pinn_autograd import evaluate_pinn, initialize_parameters


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check_hard_initial_conditions():
    flat, shapes, sizes = initialize_parameters(8, 4, seed=7)
    model = {
        "flat_parameters": flat,
        "parameter_shapes": shapes,
        "parameter_sizes": sizes,
    }
    time = np.array([0.0, 0.05])
    condition = np.zeros((2, 7))
    initial_velocity = np.tile([0.2, -0.1, 0.05], (2, 1))
    result = evaluate_pinn(model, time, condition, initial_velocity, 1.0)
    assert np.allclose(result["position"][0], 0.0, atol=1e-12)
    assert np.allclose(result["velocity"][0], initial_velocity[0], atol=1e-12)
    for value in result.values():
        assert np.isfinite(value).all()


def main():
    check_hard_initial_conditions()
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "pinn"
        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_pinn_pilot.py"),
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
            "--epochs",
            "2",
            "--hidden-size",
            "4",
            "--collocation-points",
            "5",
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        metrics = read_csv(output / "fold_metrics.csv")
        predictions = read_csv(output / "fold_predictions.csv")
        history = read_csv(output / "training_history.csv")
        assert len(metrics) == 4
        assert len(history) == 8
        assert {row["held_out_trial"] for row in metrics} == {
            "S43A13T01",
            "S43A13T02",
            "S43A13T03",
            "S43A13T05",
        }
        for row in metrics:
            for key, value in row.items():
                if key not in {"held_out_trial", "training_trials"}:
                    assert np.isfinite(float(value))
        first_by_trial = {}
        for row in predictions:
            first_by_trial.setdefault(row["held_out_trial"], row)
        for row in first_by_trial.values():
            assert float(row["time_s"]) == 0.0
            for axis in (
                "lateral_right",
                "vertical_headward",
                "forward_nose_proxy",
            ):
                assert abs(float(row[f"actual_{axis}_m"])) < 1e-12
                assert abs(float(row[f"pinn_{axis}_m"])) < 1e-12
        assert len(list((output / "plots").glob("*.png"))) == 4
    print("PASS PINN automatic derivatives, hard initial state and four-fold workflow")


if __name__ == "__main__":
    main()
