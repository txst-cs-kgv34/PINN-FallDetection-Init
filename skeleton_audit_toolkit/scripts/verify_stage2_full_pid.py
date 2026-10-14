"""Verify the complete frozen-Stage-1 delayed-PID Stage-2 experiment."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from stage2_full_pid import GRAVITY_M_S2, delayed, identify_pid, simulate_pid


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def verify_known_pid_recovery():
    """Recover all five terms from a deliberately saturated synthetic fixture."""

    mass_kg = 58.9670081
    length_m = 0.88
    damping_nms = 0.0
    observation_hz = 30
    torque_scale = mass_kg * GRAVITY_M_S2 * length_m
    derivative_scale = np.sqrt(mass_kg * length_m**2 * torque_scale)
    truth = {
        "kp_nm_per_rad": 1.0 * torque_scale,
        "kd_nms_per_rad": 0.4 * derivative_scale,
        "ki_nm_per_rad_s": 0.25 * torque_scale,
        "torque_limit_nm": 0.2 * torque_scale,
        "delay_s": 3 / observation_hz,
        "nuisance_0": 0.0,
        "nuisance_1": 0.0,
        "nuisance_2": 0.0,
    }
    records = []
    saturation_fractions = []
    for index, (initial_theta, initial_omega, duration_s) in enumerate(
        [(0.30, 0.55, 1.4), (-0.24, -0.40, 1.2), (0.20, -0.50, 1.5)]
    ):
        time_s = np.arange(round(duration_s * observation_hz) + 1) / observation_hz
        theta, omega, integral = simulate_pid(
            time_s,
            initial_theta,
            initial_omega,
            mass_kg,
            length_m,
            damping_nms,
            truth,
            "zero",
            300,
        )
        delayed_theta = delayed(theta, time_s, truth["delay_s"], theta[0])
        delayed_omega = delayed(omega, time_s, truth["delay_s"], omega[0])
        raw_control = (
            -truth["kp_nm_per_rad"] * delayed_theta
            - truth["kd_nms_per_rad"] * delayed_omega
            - truth["ki_nm_per_rad_s"] * integral
        )
        control = np.clip(
            raw_control, -truth["torque_limit_nm"], truth["torque_limit_nm"]
        )
        saturation_fractions.append(
            float(np.mean(np.abs(raw_control) > truth["torque_limit_nm"]))
        )
        inertia = mass_kg * length_m**2
        acceleration = (
            torque_scale * np.sin(theta) + control - damping_nms * omega
        ) / inertia
        records.append(
            {
                "trial": f"synthetic_{index}",
                "time_s": time_s,
                "duration_s": time_s[-1],
                "theta": theta,
                "theta_velocity": omega,
                "theta_acceleration": acceleration,
                "effective_torque": control,
                "torque_scale": torque_scale,
                "inertia": inertia,
                "damping_nms": damping_nms,
            }
        )

    assert max(saturation_fractions) > 0.4
    bounds = {
        "start_order": [
            "alpha_kp",
            "beta_kd",
            "kappa_ki",
            "gamma_torque_limit",
            "nuisance_0",
            "nuisance_1",
            "nuisance_2",
        ],
        "alpha_kp": [0.0, 2.0],
        "beta_kd": [0.0, 1.0],
        "kappa_ki": [0.0, 1.0],
        "gamma_torque_limit": [0.05, 1.0],
        "nuisance_0": [-0.5, 0.5],
        "nuisance_1": [-0.5, 0.5],
        "nuisance_2": [-0.5, 0.5],
    }
    starts = [
        [0.8, 0.2, 0.1, 0.3, 0.0, 0.0, 0.0],
        [1.2, 0.5, 0.3, 0.2, 0.0, 0.0, 0.0],
        [0.5, 0.7, 0.5, 0.6, 0.0, 0.0, 0.0],
    ]
    recovered, _ = identify_pid(
        records,
        mass_kg,
        length_m,
        "pid",
        "zero",
        range(2, 7),
        observation_hz,
        bounds,
        starts,
        0.5,
        500,
    )
    assert recovered["delay_frames"] == 3
    assert abs(recovered["alpha_kp"] - 1.0) < 1e-4
    assert abs(recovered["beta_kd"] - 0.4) < 1e-4
    assert abs(recovered["kappa_ki"] - 0.25) < 1e-4
    assert abs(recovered["gamma_torque_limit"] - 0.2) < 1e-6


def verify_retained_results(results: Path):
    required = [
        "SUMMARY.md",
        "experiment_config.json",
        "fold_metrics.csv",
        "control_metrics.csv",
        "optimization_profiles.csv",
        "held_out_com_predictions.csv",
        "stage1_frozen_checkpoints.json",
    ]
    for relative in required:
        path = results / relative
        assert path.is_file() and path.stat().st_size > 0, path
    assert len(list((results / "plots").glob("*_stage2_full_pid.png"))) == 8

    metrics = read_rows(results / "fold_metrics.csv")
    controls = read_rows(results / "control_metrics.csv")
    profiles = read_rows(results / "optimization_profiles.csv")
    predictions = read_rows(results / "held_out_com_predictions.csv")
    checkpoints = json.loads((results / "stage1_frozen_checkpoints.json").read_text())
    config = json.loads((results / "experiment_config.json").read_text())

    assert len(metrics) == 64
    assert len(controls) == 16
    assert len(profiles) == 960
    assert len(predictions) == 1952
    assert len(checkpoints) == 16
    assert config["primary_perturbation_policy"] == "zero"
    assert config["stage1"]["damping_nms"] == 0.0
    assert {row["controller_type"] for row in metrics} == {"pd", "pid"}
    assert {row["perturbation_policy"] for row in metrics} == {"zero", "nuisance"}
    assert all(np.isfinite(float(row["xy_rmse_m"])) for row in metrics)
    assert all(
        float(row["kappa_ki"]) == 0.0
        for row in metrics
        if row["controller_type"] == "pd"
    )

    # Whole-trial leakage guard for the Stage-2 controller fit and Stage-1 PINN.
    for row in metrics:
        assert row["held_out_trial"] not in row["training_trials"].split(";")
    for checkpoint in checkpoints:
        assert checkpoint["held_out_trial"] not in checkpoint["training_trials"]
        assert checkpoint["history"][-1]["epoch"] == 300

    # Reproducing the retained lambda=0.01 Stage-1 predictions is the freeze gate.
    control_lookup = {
        (row["activity"], row["held_out_trial"], int(row["seed"])): row
        for row in controls
    }
    for activity in ("A11", "A13"):
        original_path = (
            results.parent
            / f"S43_{activity}_stage1_inverted_pendulum"
            / "fold_metrics.csv"
        )
        original_rows = [
            row
            for row in read_rows(original_path)
            if np.isclose(float(row["physics_weight"]), 0.01)
        ]
        assert len(original_rows) == 8
        for row in original_rows:
            reproduced = control_lookup[
                (activity, row["held_out_trial"], int(row["seed"]))
            ]
            assert abs(
                float(row["model_xy_rmse_m"])
                - float(reproduced["stage1_xy_rmse_m"])
            ) < 1e-8
            assert abs(
                float(row["constant_velocity_xy_rmse_m"])
                - float(reproduced["constant_velocity_xy_rmse_m"])
            ) < 1e-12


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("analyses/S43_stage2_full_pid"),
    )
    args = parser.parse_args()
    verify_known_pid_recovery()
    verify_retained_results(args.results)
    print("Complete Stage-2 frozen-PINN delayed-PID verification passed.")


if __name__ == "__main__":
    main()
