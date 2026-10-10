"""Run Stage 2A: recover known delayed-PD parameters in simulation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stage2a_delayed_pd import (
    Controller,
    PerturbationTrial,
    Plant,
    control_torque_from_state,
    filtered_prediction,
    make_observations,
    recover_controller,
    simulate_trials,
    zero_phase_filter,
)


def trial_bank():
    """Known, diverse perturbations; held-out trials are never used in fitting."""

    return [
        PerturbationTrial("train_01", "train", 0.030, 0.00, 0.20, 0.18, 0.12),
        PerturbationTrial("train_02", "train", -0.035, 0.00, 0.28, 0.22, -0.14),
        PerturbationTrial("train_03", "train", 0.000, 0.05, 0.18, 0.16, 0.22),
        PerturbationTrial("train_04", "train", 0.045, -0.04, 0.35, 0.25, -0.20),
        PerturbationTrial("train_05", "train", -0.055, 0.03, 0.22, 0.28, 0.27),
        PerturbationTrial("train_06", "train", 0.020, 0.08, 0.42, 0.14, -0.30),
        PerturbationTrial("train_07", "train", -0.015, -0.08, 0.16, 0.32, 0.18),
        PerturbationTrial(
            "train_08", "train", 0.060, 0.00, 0.25, 0.18, 0.25,
            0.78, 0.20, -0.18,
        ),
        PerturbationTrial("test_01", "test", 0.025, -0.02, 0.31, 0.20, 0.17),
        PerturbationTrial("test_02", "test", -0.045, 0.06, 0.19, 0.26, -0.24),
        PerturbationTrial(
            "test_03", "test", 0.010, 0.00, 0.24, 0.15, 0.28,
            0.68, 0.24, -0.16,
        ),
        PerturbationTrial(
            "test_04", "test", -0.020, -0.05, 0.38, 0.30, -0.19,
            0.92, 0.16, 0.23,
        ),
    ]


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"no rows supplied for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def relative_error(estimate, truth):
    return abs(estimate - truth) / abs(truth)


def saturation_fraction(plant, controller, simulation):
    fractions = []
    for theta, omega in zip(
        simulation["theta_internal_rad"], simulation["omega_internal_rad_s"]
    ):
        _, unsaturated = control_torque_from_state(
            plant,
            controller,
            theta,
            omega,
            simulation["internal_time_s"],
        )
        limit = controller.physical(plant)["torque_limit_nm"]
        fractions.append(float(np.mean(np.abs(unsaturated) >= limit)))
    return float(np.mean(fractions)), float(np.max(fractions))


def trajectory_rows(case_id, trials, time, observed, truth, predicted):
    rows = []
    for trial_index, trial in enumerate(trials):
        for frame, t in enumerate(time):
            rows.append(
                {
                    "case_id": case_id,
                    "trial": trial.trial,
                    "split": trial.split,
                    "frame": frame,
                    "time_s": float(t),
                    "observed_theta_deg": float(np.rad2deg(observed[trial_index, frame])),
                    "true_filtered_theta_deg": float(np.rad2deg(truth[trial_index, frame])),
                    "estimated_filtered_theta_deg": float(np.rad2deg(predicted[trial_index, frame])),
                }
            )
    return rows


def make_plots(output, metrics, trajectories):
    plot_dir = output / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    labels = [row["case_id"] for row in metrics]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    panels = [
        ("kp_relative_error", "Kp relative error", 0.15),
        ("kd_relative_error", "Kd relative error", 0.15),
        ("delay_error_frames", "Delay error (frames)", 1.0),
        ("torque_limit_relative_error", "Torque-limit relative error", 0.15),
    ]
    colors = ["#2b6cb0" if row["all_parameter_gates_pass"] else "#c53030" for row in metrics]
    for axis, (key, label, gate) in zip(axes, panels):
        axis.bar(x, [float(row[key]) for row in metrics], color=colors)
        axis.axhline(gate, color="#1a202c", linestyle="--", linewidth=1)
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=0.25)
    axes[-1].set_xticks(x, labels, rotation=55, ha="right", fontsize=8)
    fig.suptitle("Stage 2A delayed-PD parameter recovery")
    fig.tight_layout()
    fig.savefig(plot_dir / "parameter_recovery_errors.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    pairs = [
        ("true_kp_nm_per_rad", "estimated_kp_nm_per_rad", "Kp (N·m/rad)"),
        ("true_kd_nms_per_rad", "estimated_kd_nms_per_rad", "Kd (N·m·s/rad)"),
        ("true_torque_limit_nm", "estimated_torque_limit_nm", "Torque limit (N·m)"),
    ]
    for axis, (truth_key, estimate_key, label) in zip(axes, pairs):
        truth = np.array([float(row[truth_key]) for row in metrics])
        estimate = np.array([float(row[estimate_key]) for row in metrics])
        low = min(truth.min(), estimate.min()) * 0.95
        high = max(truth.max(), estimate.max()) * 1.05
        axis.plot([low, high], [low, high], "--", color="#4a5568")
        axis.scatter(truth, estimate, c=colors, s=38)
        axis.set(xlabel=f"True {label}", ylabel=f"Recovered {label}")
        axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(plot_dir / "parameter_identity_plots.png", dpi=180)
    plt.close(fig)

    example_case = metrics[len(metrics) // 2]["case_id"]
    example = [row for row in trajectories if row["case_id"] == example_case and row["trial"] == "test_03"]
    fig, axis = plt.subplots(figsize=(9, 4.5))
    time = [float(row["time_s"]) for row in example]
    axis.plot(time, [float(row["observed_theta_deg"]) for row in example], color="#a0aec0", label="Noisy filtered observation")
    axis.plot(time, [float(row["true_filtered_theta_deg"]) for row in example], color="#1a202c", linewidth=2, label="Known truth")
    axis.plot(time, [float(row["estimated_filtered_theta_deg"]) for row in example], color="#2b6cb0", linestyle="--", linewidth=2, label="Recovered-controller prediction")
    axis.set(xlabel="Time (s)", ylabel="Angle (deg)", title=f"Held-out double-pulse trial: {example_case}")
    axis.legend()
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(plot_dir / "held_out_trajectory_example.png", dpi=180)
    plt.close(fig)


def render_summary(output, config, metrics):
    gates = config["acceptance_gates"]
    pass_count = sum(bool(row["case_pass"]) for row in metrics)
    parameter_pass_count = sum(bool(row["all_parameter_gates_pass"]) for row in metrics)
    fraction = pass_count / len(metrics)
    aggregate_pass = fraction >= gates["required_case_pass_fraction"]

    def median(key):
        return float(np.median([float(row[key]) for row in metrics]))

    lines = [
        "# S43 Stage 2A delayed-PD parameter-recovery benchmark",
        "",
        "## Decision",
        "",
        (
            f"**{'PASS' if aggregate_pass else 'DO NOT PASS'} Stage 2A:** "
            f"{pass_count}/{len(metrics)} cases ({100*fraction:.1f}%) passed all parameter "
            "and held-out-trajectory gates."
        ),
        "",
        "This benchmark establishes recoverability only for the correctly specified simulated Stage-1 plant. "
        "It does not identify a physiological controller in S43 or validate synthetic human falls.",
        "",
        "## Aggregate results",
        "",
        f"- Median Kp relative error: {100*median('kp_relative_error'):.2f}%.",
        f"- Median Kd relative error: {100*median('kd_relative_error'):.2f}%.",
        f"- Median delay error: {median('delay_error_frames'):.2f} observation frames.",
        f"- Median torque-limit relative error: {100*median('torque_limit_relative_error'):.2f}%.",
        f"- Median held-out angle RMSE: {median('held_out_theta_rmse_deg'):.3f} degrees.",
        f"- Parameter-only gates passed in {parameter_pass_count}/{len(metrics)} cases.",
        "",
        "## Design",
        "",
        "- Original Stage-1 fixed-pivot, constant-length point-mass plant; no Stage-1.5 mechanics.",
        "- Subject mass 58.967 kg; separate A11 and A13 median onset lengths.",
        "- Passive damping fixed to zero, so Kd is not confounded with an unknown damping term.",
        "- Known raised-cosine torque perturbations; eight training and four unseen test trials.",
        "- Three known controller profiles, two plant lengths, and two independent angle-noise seeds.",
        "- 30 Hz observations with 0.12-degree Gaussian angle noise and the retained Stage-1 1.5 Hz, order-6 zero-phase filter.",
        "- Delay searched only in whole 30 Hz frames; sub-frame recovery is not claimed.",
        "",
        "### Development note",
        "",
        "A preliminary 3.0 s dry run was rejected before the retained benchmark because the tested delayed controllers produced multiple full rotations (up to about 297 degrees), outside the marked S43 fall-window regime and the intended local recovery question. The 1.2 s retained horizon was then fixed to the scale of the observed onset-to-contact windows. The parameter-error gates were not relaxed.",
        "",
        "## Prespecified gates",
        "",
        f"- Kp relative error <= {100*gates['kp_relative_error_max']:.0f}%.",
        f"- Kd relative error <= {100*gates['kd_relative_error_max']:.0f}%.",
        f"- Delay error <= {gates['delay_error_frames_max']} frame.",
        f"- Torque-limit relative error <= {100*gates['torque_limit_relative_error_max']:.0f}%.",
        f"- Held-out angle RMSE <= {gates['held_out_theta_rmse_deg_max']:.1f} degree.",
        f"- At least {100*gates['required_case_pass_fraction']:.0f}% of cases must pass all gates.",
        "",
        "## Interpretation and next step",
        "",
        "If this benchmark passes, the inverse implementation is capable of recovering known gains, delay, and saturation under its own assumptions. "
        "The next step is a mismatch/sensitivity stage (noise, incorrect length, unknown perturbation, and nonzero passive damping) before any exploratory S43 fit. "
        "Human-data estimates must be called effective delayed-feedback parameters because the available skeleton trials contain no measured perturbation torque, center of pressure, or ground-reaction force.",
        "",
        "## Files",
        "",
        "- `recovery_metrics.csv`: one row per plant/profile/noise case.",
        "- `optimization_profiles.csv`: all delay/start fits, not only winners.",
        "- `held_out_trajectories.csv`: unseen-trial observations, truth, and predictions.",
        "- `experiment_config.json`: complete frozen settings and trial bank.",
        "- `plots/`: parameter and held-out trajectory figures.",
    ]
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return aggregate_pass


def run(config_path, output):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    output.mkdir(parents=True)
    all_trials = trial_bank()
    training_trials = [trial for trial in all_trials if trial.split == "train"]
    test_trials = [trial for trial in all_trials if trial.split == "test"]
    settings = config["simulation"]
    recovery = config["recovery"]
    gates = config["acceptance_gates"]
    metrics = []
    profiles = []
    trajectories = []

    frozen_config = dict(config)
    frozen_config["trial_bank"] = [trial.__dict__ for trial in all_trials]
    frozen_config["source_config"] = str(config_path)
    frozen_config["source_config_sha256"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
    (output / "experiment_config.json").write_text(
        json.dumps(frozen_config, indent=2) + "\n", encoding="utf-8"
    )

    total_cases = (
        len(config["plants"])
        * len(config["controller_profiles"])
        * len(settings["noise_seeds"])
    )
    case_number = 0
    for plant_spec in config["plants"]:
        plant = Plant(
            mass_kg=config["mass_kg"],
            length_m=plant_spec["length_m"],
            damping_nms=plant_spec["damping_nms"],
        )
        for profile in config["controller_profiles"]:
            truth_controller = Controller(
                alpha_kp=profile["alpha_kp"],
                beta_kd=profile["beta_kd"],
                delay_s=profile["delay_frames"] / settings["observation_hz"],
                gamma_torque_limit=profile["gamma_torque_limit"],
            )
            truth_train = simulate_trials(
                plant,
                truth_controller,
                training_trials,
                settings["duration_s"],
                settings["internal_hz"],
                settings["observation_hz"],
            )
            truth_test = simulate_trials(
                plant,
                truth_controller,
                test_trials,
                settings["duration_s"],
                settings["internal_hz"],
                settings["observation_hz"],
            )
            filtered_truth_test = zero_phase_filter(
                truth_test["theta_rad"],
                settings["observation_hz"],
                settings["filter_cutoff_hz"],
                settings["filter_order"],
            )
            mean_sat, max_sat = saturation_fraction(plant, truth_controller, truth_train)

            for noise_seed in settings["noise_seeds"]:
                case_number += 1
                case_id = f"{plant_spec['source_activity']}_{profile['profile']}_n{noise_seed}"
                print(f"[{case_number}/{total_cases}] {case_id}", flush=True)
                rng = np.random.default_rng(noise_seed)
                observed_train = make_observations(
                    truth_train,
                    rng,
                    np.deg2rad(settings["noise_sd_deg"]),
                    settings["observation_hz"],
                    settings["filter_cutoff_hz"],
                    settings["filter_order"],
                )
                observed_test = make_observations(
                    truth_test,
                    rng,
                    np.deg2rad(settings["noise_sd_deg"]),
                    settings["observation_hz"],
                    settings["filter_cutoff_hz"],
                    settings["filter_order"],
                )
                estimated, fit_records = recover_controller(
                    plant,
                    training_trials,
                    observed_train,
                    settings["duration_s"],
                    recovery["delay_frames"],
                    settings["observation_hz"],
                    settings["internal_hz"],
                    settings["filter_cutoff_hz"],
                    settings["filter_order"],
                    recovery["bounds"],
                    recovery["starts"],
                    recovery["max_nfev"],
                )
                for record in fit_records:
                    profiles.append({"case_id": case_id, **record})

                predicted_test = filtered_prediction(
                    plant,
                    estimated,
                    test_trials,
                    settings["duration_s"],
                    settings["internal_hz"],
                    settings["observation_hz"],
                    settings["filter_cutoff_hz"],
                    settings["filter_order"],
                )
                held_out_rmse_rad = float(
                    np.sqrt(np.mean((predicted_test - filtered_truth_test) ** 2))
                )
                held_out_rmse_deg = float(np.rad2deg(held_out_rmse_rad))
                true_xy = np.stack(
                    [
                        plant.length_m * np.sin(filtered_truth_test),
                        plant.length_m * np.cos(filtered_truth_test),
                    ],
                    axis=-1,
                )
                pred_xy = np.stack(
                    [
                        plant.length_m * np.sin(predicted_test),
                        plant.length_m * np.cos(predicted_test),
                    ],
                    axis=-1,
                )
                held_out_xy_rmse_m = float(np.sqrt(np.mean((pred_xy - true_xy) ** 2)))
                true_physical = truth_controller.physical(plant)
                estimated_physical = estimated.physical(plant)
                kp_error = relative_error(estimated.alpha_kp, truth_controller.alpha_kp)
                kd_error = relative_error(estimated.beta_kd, truth_controller.beta_kd)
                delay_error_frames = abs(
                    estimated.delay_s * settings["observation_hz"]
                    - profile["delay_frames"]
                )
                torque_error = relative_error(
                    estimated.gamma_torque_limit,
                    truth_controller.gamma_torque_limit,
                )
                parameter_pass = (
                    kp_error <= gates["kp_relative_error_max"]
                    and kd_error <= gates["kd_relative_error_max"]
                    and delay_error_frames <= gates["delay_error_frames_max"]
                    and torque_error <= gates["torque_limit_relative_error_max"]
                )
                case_pass = parameter_pass and held_out_rmse_deg <= gates["held_out_theta_rmse_deg_max"]
                metrics.append(
                    {
                        "case_id": case_id,
                        "plant_id": plant_spec["plant_id"],
                        "source_activity": plant_spec["source_activity"],
                        "profile": profile["profile"],
                        "noise_seed": noise_seed,
                        "mass_kg": plant.mass_kg,
                        "length_m": plant.length_m,
                        "damping_nms": plant.damping_nms,
                        "true_alpha_kp": truth_controller.alpha_kp,
                        "estimated_alpha_kp": estimated.alpha_kp,
                        "true_beta_kd": truth_controller.beta_kd,
                        "estimated_beta_kd": estimated.beta_kd,
                        "true_delay_frames": profile["delay_frames"],
                        "estimated_delay_frames": estimated.delay_s * settings["observation_hz"],
                        "true_delay_s": truth_controller.delay_s,
                        "estimated_delay_s": estimated.delay_s,
                        "true_gamma_torque_limit": truth_controller.gamma_torque_limit,
                        "estimated_gamma_torque_limit": estimated.gamma_torque_limit,
                        "true_kp_nm_per_rad": true_physical["kp_nm_per_rad"],
                        "estimated_kp_nm_per_rad": estimated_physical["kp_nm_per_rad"],
                        "true_kd_nms_per_rad": true_physical["kd_nms_per_rad"],
                        "estimated_kd_nms_per_rad": estimated_physical["kd_nms_per_rad"],
                        "true_torque_limit_nm": true_physical["torque_limit_nm"],
                        "estimated_torque_limit_nm": estimated_physical["torque_limit_nm"],
                        "kp_relative_error": kp_error,
                        "kd_relative_error": kd_error,
                        "delay_error_frames": delay_error_frames,
                        "torque_limit_relative_error": torque_error,
                        "held_out_theta_rmse_deg": held_out_rmse_deg,
                        "held_out_xy_rmse_m": held_out_xy_rmse_m,
                        "training_theta_rmse_deg": float(np.rad2deg(fit_records[0]["training_theta_rmse_rad"])),
                        "mean_training_saturation_fraction": mean_sat,
                        "max_trial_saturation_fraction": max_sat,
                        "all_parameter_gates_pass": parameter_pass,
                        "held_out_gate_pass": held_out_rmse_deg <= gates["held_out_theta_rmse_deg_max"],
                        "case_pass": case_pass,
                    }
                )
                trajectories.extend(
                    trajectory_rows(
                        case_id,
                        test_trials,
                        truth_test["time_s"],
                        observed_test,
                        filtered_truth_test,
                        predicted_test,
                    )
                )

    write_csv(output / "recovery_metrics.csv", metrics)
    write_csv(output / "optimization_profiles.csv", profiles)
    write_csv(output / "held_out_trajectories.csv", trajectories)
    make_plots(output, metrics, trajectories)
    aggregate_pass = render_summary(output, config, metrics)
    print(f"Stage 2A aggregate decision: {'PASS' if aggregate_pass else 'DO NOT PASS'}")
    return aggregate_pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/S43_stage2a_simulation.json"))
    parser.add_argument("--output", type=Path, default=Path("analyses/S43_stage2a_delayed_pd_parameter_recovery"))
    args = parser.parse_args()
    run(args.config, args.output)


if __name__ == "__main__":
    main()
