"""Regression checks for the Stage-1 inverted-pendulum PINN experiment."""

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

from inverted_pendulum_pinn import InvertedPendulumStage1, evaluate_model
from run_stage1_inverted_pendulum import (
    constant_velocity_prediction,
    uncontrolled_pendulum_prediction,
)


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check_hard_initial_state_and_angle():
    torch.manual_seed(7)
    model = InvertedPendulumStage1(
        condition_size=8,
        trajectory_hidden_size=4,
        trajectory_hidden_layers=2,
        torque_hidden_size=3,
        torque_hidden_layers=1,
    ).to(torch.float64)
    time = np.array([0.0, 0.05])
    condition = np.zeros((2, 8))
    initial_position = np.tile([0.1, 0.8], (2, 1))
    initial_velocity = np.tile([0.2, -0.1], (2, 1))
    result = evaluate_model(
        model,
        time,
        condition,
        initial_position,
        initial_velocity,
        time_scale_s=1.0,
        mass_kg=60.0,
        pendulum_length_m=np.linalg.norm(initial_position[0]),
        damping_nms=0.0,
        use_effective_torque=True,
    )
    assert np.allclose(result["position"][0], initial_position[0], atol=1e-12)
    assert np.allclose(result["velocity"][0], initial_velocity[0], atol=1e-12)
    assert np.isclose(
        result["theta"][0], np.arctan2(initial_position[0, 0], initial_position[0, 1])
    )
    assert all(np.isfinite(value).all() for value in result.values())


def check_controls():
    time = np.array([0.0, 0.1, 0.2])
    initial_position = np.array([0.1, 0.8])
    initial_velocity = np.array([0.2, -0.1])
    linear = constant_velocity_prediction(time, initial_position, initial_velocity)
    assert np.allclose(linear[0], initial_position)
    assert np.allclose(linear[-1], initial_position + 0.2 * initial_velocity)
    length = np.linalg.norm(initial_position)
    theta = np.arctan2(initial_position[0], initial_position[1])
    theta_velocity = (
        initial_position[1] * initial_velocity[0]
        - initial_position[0] * initial_velocity[1]
    ) / np.dot(initial_position, initial_position)
    position, angles = uncontrolled_pendulum_prediction(
        time, theta, theta_velocity, length, 0.0, 60.0
    )
    assert np.allclose(position[0], initial_position)
    assert np.isclose(angles[0], theta)
    assert np.allclose(np.linalg.norm(position, axis=1), length)


def check_workflow(activity, notes_name, expected_trials, expected_axis):
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / f"stage1_{activity.lower()}"
        command = [
            sys.executable,
            str(ROOT / "scripts" / "run_stage1_inverted_pendulum.py"),
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
        assert {row["held_out_trial"] for row in metrics} == set(expected_trials)
        for row in metrics:
            for key, value in row.items():
                if key not in {"held_out_trial", "training_trials"}:
                    assert np.isfinite(float(value)), (key, value)
        first_by_run = {}
        for row in predictions:
            key = (row["held_out_trial"], row["physics_weight"], row["seed"])
            first_by_run.setdefault(key, row)
        assert len(first_by_run) == 8
        for row in first_by_run.values():
            assert float(row["time_s"]) == 0.0
            assert np.isclose(
                float(row["actual_horizontal_m"]), float(row["model_horizontal_m"])
            )
            assert np.isclose(
                float(row["actual_vertical_m"]), float(row["model_vertical_m"])
            )
        assert len(list((output / "plots").glob("*.png"))) == 6
        config = (output / "experiment_config.json").read_text(encoding="utf-8")
        assert "no averaged-trial trajectory" in config
        assert "onset-to-contact duration is deliberately not supplied" in config
        assert f'"horizontal_axis": "{expected_axis}"' in config
        summary = (output / "SUMMARY.md").read_text(encoding="utf-8")
        assert "No trial-averaging trajectory" in summary
        assert "not an identified perturbation" in summary


def main():
    check_hard_initial_state_and_angle()
    check_controls()
    check_workflow(
        "A13",
        "S43_phase_notes_with_A13_eligibility.json",
        ("S43A13T01", "S43A13T02", "S43A13T03", "S43A13T05"),
        "lateral",
    )
    check_workflow(
        "A11",
        "S43_A11_phase_notes.json",
        ("S43A11T02", "S43A11T03", "S43A11T04", "S43A11T05"),
        "forward",
    )
    print(
        "PASS Stage-1 inverted-pendulum PINN, activity-specific axes, "
        "controls and four whole-trial folds"
    )


if __name__ == "__main__":
    main()
