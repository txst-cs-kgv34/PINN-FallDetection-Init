"""Regression checks for the controlled PyTorch physics-weight experiment."""

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

from pinn_torch import CoMDynamicsModel, evaluate_model
from run_physics_weight_experiment import gravity_only_prediction


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check_hard_initial_state():
    torch.manual_seed(7)
    model = CoMDynamicsModel(
        condition_size=8,
        trajectory_hidden_size=4,
        trajectory_hidden_layers=2,
        residual_hidden_size=3,
        residual_hidden_layers=1,
    ).to(torch.float64)
    time = np.array([0.0, 0.05])
    condition = np.zeros((2, 8))
    velocity = np.tile([0.2, -0.1, 0.05], (2, 1))
    result = evaluate_model(model, time, condition, velocity, 1.0)
    assert np.allclose(result["position"][0], 0.0, atol=1e-12)
    assert np.allclose(result["velocity"][0], velocity[0], atol=1e-12)
    assert all(np.isfinite(value).all() for value in result.values())


def check_gravity_baseline():
    time = np.array([0.0, 1.0])
    velocity = np.array([1.0, 0.0, -1.0])
    predicted = gravity_only_prediction(time, velocity)
    assert np.allclose(predicted[0], 0.0)
    assert np.allclose(predicted[1], [1.0, -4.903325, -1.0])


def check_workflow():
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "comparison"
        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_physics_weight_experiment.py"),
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
            "--collocation-points",
            "5",
            "--physics-weights",
            "0,0.1",
            "--seeds",
            "7",
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        metrics = read_csv(output / "fold_metrics.csv")
        predictions = read_csv(output / "fold_predictions.csv")
        history = read_csv(output / "training_history.csv")
        assert len(metrics) == 8
        assert len(history) == 16
        assert {float(row["physics_weight"]) for row in metrics} == {0.0, 0.1}
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
        first_by_run = {}
        for row in predictions:
            key = (row["held_out_trial"], row["physics_weight"], row["seed"])
            first_by_run.setdefault(key, row)
        assert len(first_by_run) == 8
        for row in first_by_run.values():
            assert float(row["time_s"]) == 0.0
            for axis in (
                "lateral_right",
                "vertical_headward",
                "forward_nose_proxy",
            ):
                assert abs(float(row[f"actual_{axis}_m"])) < 1e-12
                assert abs(float(row[f"model_{axis}_m"])) < 1e-12
        assert len(list((output / "plots").glob("*.png"))) == 6
        summary = (output / "SUMMARY.md").read_text(encoding="utf-8")
        assert "not a recovered external force" in summary


def main():
    check_hard_initial_state()
    check_gravity_baseline()
    check_workflow()
    print("PASS controlled PyTorch data-only/PINN comparison and gravity sanity check")


if __name__ == "__main__":
    main()
