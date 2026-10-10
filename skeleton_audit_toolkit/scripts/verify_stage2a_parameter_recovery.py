"""Verify Stage-2A simulation, scaling, recovery, and retained outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from stage2a_delayed_pd import (
    Controller,
    PerturbationTrial,
    Plant,
    control_torque_from_state,
    recover_controller,
    simulate_trials,
    zero_phase_filter,
)


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def verify_dynamics_and_recovery():
    plant = Plant(58.9670081, 0.90, 0.0)
    controller = Controller(1.42, 0.48, 3 / 30, 0.14)
    trials = [
        PerturbationTrial("v1", "train", 0.03, 0.00, 0.18, 0.18, 0.20),
        PerturbationTrial("v2", "train", -0.04, 0.04, 0.27, 0.22, -0.24),
        PerturbationTrial("v3", "train", 0.01, -0.05, 0.20, 0.26, 0.28),
    ]
    simulation = simulate_trials(plant, controller, trials, 0.9, 300, 30)
    assert simulation["theta_rad"].shape == (3, 28)
    assert np.all(np.isfinite(simulation["theta_rad"]))
    assert np.allclose(simulation["time_s"], np.arange(28) / 30)

    # Dimensionless subject scaling: mass cancels when gains, limit and known
    # perturbations are all scaled by m*g*l.
    heavier = Plant(75.0, 0.90, 0.0)
    heavier_simulation = simulate_trials(heavier, controller, trials, 0.9, 300, 30)
    assert np.allclose(
        simulation["theta_rad"], heavier_simulation["theta_rad"], atol=1e-11
    )

    physical = controller.physical(plant)
    assert np.isclose(
        physical["kp_nm_per_rad"], controller.alpha_kp * plant.gravity_torque_scale_nm
    )
    assert np.isclose(
        physical["torque_limit_nm"],
        controller.gamma_torque_limit * plant.gravity_torque_scale_nm,
    )
    torque, unsaturated = control_torque_from_state(
        plant,
        controller,
        simulation["theta_internal_rad"][2],
        simulation["omega_internal_rad_s"][2],
        simulation["internal_time_s"],
    )
    assert np.max(np.abs(torque)) <= physical["torque_limit_nm"] + 1e-10
    assert np.any(np.abs(unsaturated) > physical["torque_limit_nm"])

    observed = zero_phase_filter(simulation["theta_rad"], 30, 1.5, 6)
    recovered, records = recover_controller(
        plant=plant,
        trials=trials,
        observed_theta_rad=observed,
        duration_s=0.9,
        delay_frames=[3],
        observation_hz=30,
        internal_hz=300,
        cutoff_hz=1.5,
        filter_order=6,
        bounds={
            "alpha_kp": [1.02, 1.9],
            "beta_kd": [0.15, 0.85],
            "gamma_torque_limit": [0.06, 0.3],
        },
        starts=[[1.35, 0.42, 0.12]],
        max_nfev=60,
    )
    assert records[0]["success"]
    assert abs(recovered.alpha_kp / controller.alpha_kp - 1.0) < 0.01
    assert abs(recovered.beta_kd / controller.beta_kd - 1.0) < 0.01
    assert abs(recovered.gamma_torque_limit / controller.gamma_torque_limit - 1.0) < 0.01
    assert recovered.delay_s == controller.delay_s


def verify_retained_results(results):
    required = [
        "SUMMARY.md",
        "experiment_config.json",
        "recovery_metrics.csv",
        "optimization_profiles.csv",
        "held_out_trajectories.csv",
        "plots/parameter_recovery_errors.png",
        "plots/parameter_identity_plots.png",
        "plots/held_out_trajectory_example.png",
    ]
    for relative in required:
        path = results / relative
        assert path.is_file() and path.stat().st_size > 0, path
    rows = read_rows(results / "recovery_metrics.csv")
    assert len(rows) == 12
    assert {row["source_activity"] for row in rows} == {"A11", "A13"}
    assert {row["profile"] for row in rows} == {"responsive", "balanced", "limited"}
    assert all(row["case_pass"] == "True" for row in rows)
    assert max(float(row["kp_relative_error"]) for row in rows) <= 0.15
    assert max(float(row["kd_relative_error"]) for row in rows) <= 0.15
    assert max(float(row["delay_error_frames"]) for row in rows) <= 1.0
    assert max(float(row["torque_limit_relative_error"]) for row in rows) <= 0.15
    assert max(float(row["held_out_theta_rmse_deg"]) for row in rows) <= 1.0
    assert len(read_rows(results / "optimization_profiles.csv")) == 12 * 5 * 3
    assert len(read_rows(results / "held_out_trajectories.csv")) == 12 * 4 * 37


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("analyses/S43_stage2a_delayed_pd_parameter_recovery"),
    )
    args = parser.parse_args()
    verify_dynamics_and_recovery()
    verify_retained_results(args.results)
    print("Stage-2A delayed-PD verification passed.")


if __name__ == "__main__":
    main()
