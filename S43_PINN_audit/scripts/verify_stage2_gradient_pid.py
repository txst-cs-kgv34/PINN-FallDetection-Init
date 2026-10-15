"""Independent checks for the revised gradient-based Stage 2."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analyses" / "S43_stage2_gradient_pid"


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def finite(rows, columns):
    return all(np.isfinite(float(row[column])) for row in rows for column in columns)


def main():
    config = json.loads((OUTPUT / "experiment_config.json").read_text())
    metrics = read_csv(OUTPUT / "fold_metrics.csv")
    profiles = read_csv(OUTPUT / "optimization_profiles.csv")
    predictions = read_csv(OUTPUT / "held_out_com_predictions.csv")
    controls = read_csv(OUTPUT / "control_metrics.csv")
    histories = json.loads((OUTPUT / "optimization_histories.json").read_text())
    synthetic = json.loads((OUTPUT / "synthetic_recovery.json").read_text())
    checkpoint_path = ROOT / config["stage1"]["checkpoint_file"]
    checkpoints = json.loads(checkpoint_path.read_text())

    assert config["method"] == "automatic gradients through a frozen Stage-1 PINN"
    assert config["perturbation_policy"] == "zero"
    assert config["use_effective_torque_matching"] is False
    assert config["use_nuisance_torque"] is False
    assert config["use_torque_saturation"] is False
    assert config["stage2"]["trainable_parameters"] == ["Kp", "Kd", "Ki", "delay"]

    assert len(metrics) == 16
    assert len(profiles) == 48
    assert len(histories) == 48
    assert len(predictions) == 488
    assert len(controls) == 16
    assert len(checkpoints) == 16
    assert len(list((OUTPUT / "plots").glob("*.png"))) == 8
    assert all(row["simulation_finite"] == "True" for row in metrics)
    assert finite(
        metrics,
        [
            "alpha_kp", "beta_kd", "kappa_ki", "delay_s",
            "training_physics_loss", "xy_rmse_m", "theta_rmse_deg",
        ],
    )
    assert finite(profiles, ["training_physics_loss", "final_gradient_norm"])

    lower, upper = config["stage2"]["bounds"]["delay_s"]
    assert all(lower <= float(row["delay_s"]) <= upper for row in metrics)
    delay_upper_contacts = sum(abs(float(row["delay_s"]) - upper) < 1e-6 for row in metrics)

    for row in metrics:
        assert row["held_out_trial"] not in row["training_trials"].split(";")

    checkpoint_keys = {
        (row["activity"], row["held_out_trial"], int(row["seed"]))
        for row in checkpoints
    }
    metric_keys = {
        (row["activity"], row["held_out_trial"], int(row["seed"]))
        for row in metrics
    }
    assert checkpoint_keys == metric_keys
    assert all(
        checkpoint["held_out_trial"] not in checkpoint["training_trials"]
        for checkpoint in checkpoints
    )
    assert all(checkpoint["state_dict"] for checkpoint in checkpoints)

    errors = synthetic["errors"]
    assert errors["alpha_kp_relative_error"] < 0.05
    assert errors["beta_kd_relative_error"] < 0.10
    assert errors["kappa_ki_relative_error"] < 0.05
    assert errors["delay_absolute_error_s"] < 1.0 / 30.0

    control_columns = [
        "stage1_horizontal_rmse_m", "stage1_vertical_rmse_m",
        "stage1_xy_rmse_m", "stage1_theta_rmse_deg", "stage1_endpoint_error_m",
        "constant_velocity_horizontal_rmse_m", "constant_velocity_vertical_rmse_m",
        "constant_velocity_xy_rmse_m", "constant_velocity_theta_rmse_deg",
        "constant_velocity_endpoint_error_m",
    ]
    assert finite(controls, control_columns)

    activity_results = {}
    for activity in ("A11", "A13"):
        fitted = [row for row in metrics if row["activity"] == activity]
        baseline = [row for row in controls if row["activity"] == activity]
        activity_results[activity] = {
            "gradient_pid_xy_rmse_m": float(np.mean([float(row["xy_rmse_m"]) for row in fitted])),
            "frozen_stage1_xy_rmse_m": float(np.mean([float(row["stage1_xy_rmse_m"]) for row in baseline])),
            "constant_velocity_xy_rmse_m": float(np.mean([float(row["constant_velocity_xy_rmse_m"]) for row in baseline])),
        }

    controller_gate_pass = all(
        values["gradient_pid_xy_rmse_m"] < values["frozen_stage1_xy_rmse_m"]
        and values["gradient_pid_xy_rmse_m"] < values["constant_velocity_xy_rmse_m"]
        for values in activity_results.values()
    ) and delay_upper_contacts == 0

    report = {
        "software_verification": "pass",
        "synthetic_recovery_gate": "pass",
        "real_data_controller_identification_gate": "pass" if controller_gate_pass else "fail",
        "counts": {
            "fold_seed_fits": len(metrics),
            "optimizer_profiles": len(profiles),
            "prediction_rows": len(predictions),
            "plots": len(list((OUTPUT / "plots").glob("*.png"))),
            "delay_upper_bound_contacts": delay_upper_contacts,
            "frozen_stage1_checkpoints": len(checkpoints),
        },
        "activity_results": activity_results,
        "decision": (
            "Do not interpret the fitted real-data gains or delay as a validated controller phenotype. "
            "Stage 3 may proceed only as an explicitly assumption-based sensitivity simulation."
        ),
    }
    (OUTPUT / "VERIFICATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
