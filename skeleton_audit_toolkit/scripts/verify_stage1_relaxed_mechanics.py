"""Regression checks for the Stage-1.5 relaxed-mechanics ablations."""

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

from inverted_pendulum_pinn import pendulum_residual
from relaxed_pendulum_pinn import variable_length_residual


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check_equation_reduces_to_stage1():
    theta = torch.tensor([0.2, -0.1], dtype=torch.float64)
    theta_velocity = torch.tensor([0.3, 0.4], dtype=torch.float64)
    theta_acceleration = torch.tensor([0.5, -0.2], dtype=torch.float64)
    torque = torch.tensor([[1.2], [-0.7]], dtype=torch.float64)
    mass = torch.tensor([60.0, 60.0], dtype=torch.float64)
    length = torch.tensor([0.9, 0.9], dtype=torch.float64)
    damping = torch.tensor([0.0, 0.0], dtype=torch.float64)
    old = pendulum_residual(
        theta,
        theta_velocity,
        theta_acceleration,
        torque,
        mass,
        length,
        damping,
    )
    relaxed = variable_length_residual(
        theta,
        theta_velocity,
        theta_acceleration,
        length,
        torch.zeros_like(length),
        torque,
        mass,
        damping,
        torch.zeros_like(length),
    )
    assert torch.allclose(old, relaxed)


def run_smoke(mechanics, activity, notes_name):
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / mechanics
        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_stage1_relaxed_mechanics.py"),
            "--run",
            str(ROOT / "findings" / "S43_audit"),
            "--config",
            str(ROOT / "configs" / "S43.json"),
            "--selection",
            str(ROOT / "configs" / "S43_modeling_selection.json"),
            "--phase-notes",
            str(ROOT / "analysis_inputs" / notes_name),
            "--output",
            str(output),
            "--activity",
            activity,
            "--mechanics",
            mechanics,
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
        assert len(metrics) == 8
        assert {float(row["physics_weight"]) for row in metrics} == {0.0, 0.1}
        assert len({row["held_out_trial"] for row in metrics}) == 4
        assert all(
            np.isfinite(float(value))
            for row in metrics
            for key, value in row.items()
            if key not in {"held_out_trial", "training_trials", "mechanics"}
        )
        first = {}
        for row in predictions:
            key = (row["held_out_trial"], row["physics_weight"], row["seed"])
            first.setdefault(key, row)
        assert len(first) == 8
        for row in first.values():
            assert float(row["time_s"]) == 0.0
            assert np.isclose(
                float(row["actual_horizontal_m"]),
                float(row["model_horizontal_m"]),
            )
            assert np.isclose(
                float(row["actual_vertical_m"]),
                float(row["model_vertical_m"]),
            )
        summary = (output / "SUMMARY.md").read_text(encoding="utf-8")
        if mechanics.startswith("moving_support"):
            assert "diagnostic ceiling" in summary
            assert "not center of pressure" in summary
        else:
            assert "true held-out CoM radius is not supplied" in summary


def main():
    check_equation_reduces_to_stage1()
    run_smoke(
        "variable_length",
        "A13",
        "S43_phase_notes_with_A13_eligibility.json",
    )
    run_smoke(
        "moving_support_variable_length",
        "A11",
        "S43_A11_phase_notes.json",
    )
    print("PASS Stage-1.5 variable-length and moving-support diagnostics")


if __name__ == "__main__":
    main()
