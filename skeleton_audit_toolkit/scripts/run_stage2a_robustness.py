"""Run Stage-2A delayed-PD robustness and mismatch experiments."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import replace
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from run_stage2a_parameter_recovery import trial_bank
from stage2a_delayed_pd import (
    Controller,
    Plant,
    filtered_prediction,
    make_observations,
    recover_controller,
    simulate_trials,
    zero_phase_filter,
)


DEFAULTS = {
    "angle_noise_sd_deg": 0.12,
    "estimated_length_scale": 1.0,
    "unmodelled_damping_ratio": 0.0,
    "reported_perturbation_scale": 1.0,
    "filter_cutoff_hz": 1.5,
}


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"no rows supplied for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def scaled_trials(trials, scale):
    return [
        replace(
            trial,
            pulse_amplitude_ratio=trial.pulse_amplitude_ratio * scale,
            pulse2_amplitude_ratio=trial.pulse2_amplitude_ratio * scale,
        )
        for trial in trials
    ]


def profile_controller(profile, observation_hz):
    return Controller(
        alpha_kp=profile["alpha_kp"],
        beta_kd=profile["beta_kd"],
        delay_s=profile["delay_frames"] / observation_hz,
        gamma_torque_limit=profile["gamma_torque_limit"],
    )


def relative_error(estimate, truth):
    return abs(estimate - truth) / abs(truth)


def condition_values(condition):
    values = dict(DEFAULTS)
    if condition["factor"] != "reference" and condition["factor"] != "combined_mismatch":
        values[condition["factor"]] = condition["level"]
    for key in DEFAULTS:
        if key in condition:
            values[key] = condition[key]
    return values


def calculate_metrics(
    estimated,
    truth_controller,
    truth_plant,
    fit_plant,
    profile,
    settings,
    predicted_test,
    filtered_truth_test,
    gates,
):
    truth_physical = truth_controller.physical(truth_plant)
    estimated_physical = estimated.physical(fit_plant)
    kp_error = relative_error(
        estimated_physical["kp_nm_per_rad"], truth_physical["kp_nm_per_rad"]
    )
    kd_error = relative_error(
        estimated_physical["kd_nms_per_rad"], truth_physical["kd_nms_per_rad"]
    )
    delay_error = abs(
        estimated.delay_s * settings["observation_hz"] - profile["delay_frames"]
    )
    torque_error = relative_error(
        estimated_physical["torque_limit_nm"], truth_physical["torque_limit_nm"]
    )
    angle_rmse = float(np.rad2deg(np.sqrt(np.mean((predicted_test - filtered_truth_test) ** 2))))
    true_xy = np.stack(
        [
            truth_plant.length_m * np.sin(filtered_truth_test),
            truth_plant.length_m * np.cos(filtered_truth_test),
        ],
        axis=-1,
    )
    # Compare trajectories in the true plant geometry; this isolates controller
    # trajectory error from the deliberately wrong estimator length.
    predicted_xy = np.stack(
        [
            truth_plant.length_m * np.sin(predicted_test),
            truth_plant.length_m * np.cos(predicted_test),
        ],
        axis=-1,
    )
    xy_rmse = float(np.sqrt(np.mean((predicted_xy - true_xy) ** 2)))
    parameter_pass = (
        kp_error <= gates["kp_relative_error_max"]
        and kd_error <= gates["kd_relative_error_max"]
        and delay_error <= gates["delay_error_frames_max"]
        and torque_error <= gates["torque_limit_relative_error_max"]
    )
    held_out_pass = angle_rmse <= gates["held_out_theta_rmse_deg_max"]
    return {
        "kp_relative_error": kp_error,
        "kd_relative_error": kd_error,
        "delay_error_frames": delay_error,
        "torque_limit_relative_error": torque_error,
        "held_out_theta_rmse_deg": angle_rmse,
        "held_out_xy_rmse_m": xy_rmse,
        "all_parameter_gates_pass": parameter_pass,
        "held_out_gate_pass": held_out_pass,
        "case_pass": parameter_pass and held_out_pass,
        "true_kp_nm_per_rad": truth_physical["kp_nm_per_rad"],
        "estimated_kp_nm_per_rad": estimated_physical["kp_nm_per_rad"],
        "true_kd_nms_per_rad": truth_physical["kd_nms_per_rad"],
        "estimated_kd_nms_per_rad": estimated_physical["kd_nms_per_rad"],
        "true_torque_limit_nm": truth_physical["torque_limit_nm"],
        "estimated_torque_limit_nm": estimated_physical["torque_limit_nm"],
    }


def fit_case(
    base,
    robust,
    plant_spec,
    profile,
    noise_seed,
    condition,
    training_trials,
    test_trials,
):
    settings = base["simulation"]
    gates = base["acceptance_gates"]
    values = condition_values(condition)
    nominal_plant = Plant(base["mass_kg"], plant_spec["length_m"], 0.0)
    damping_nms = (
        values["unmodelled_damping_ratio"]
        * nominal_plant.derivative_gain_scale_nms
    )
    truth_plant = Plant(base["mass_kg"], plant_spec["length_m"], damping_nms)
    fit_plant = Plant(
        base["mass_kg"],
        plant_spec["length_m"] * values["estimated_length_scale"],
        0.0,
    )
    truth_controller = profile_controller(profile, settings["observation_hz"])
    reported_training = scaled_trials(
        training_trials, values["reported_perturbation_scale"]
    )
    reported_test = scaled_trials(test_trials, values["reported_perturbation_scale"])

    truth_train = simulate_trials(
        truth_plant,
        truth_controller,
        training_trials,
        settings["duration_s"],
        settings["internal_hz"],
        settings["observation_hz"],
    )
    truth_test = simulate_trials(
        truth_plant,
        truth_controller,
        test_trials,
        settings["duration_s"],
        settings["internal_hz"],
        settings["observation_hz"],
    )
    rng = np.random.default_rng(noise_seed)
    observed_train = make_observations(
        truth_train,
        rng,
        np.deg2rad(values["angle_noise_sd_deg"]),
        settings["observation_hz"],
        values["filter_cutoff_hz"],
        settings["filter_order"],
    )
    observed_test = make_observations(
        truth_test,
        rng,
        np.deg2rad(values["angle_noise_sd_deg"]),
        settings["observation_hz"],
        values["filter_cutoff_hz"],
        settings["filter_order"],
    )
    filtered_truth_test = zero_phase_filter(
        truth_test["theta_rad"],
        settings["observation_hz"],
        values["filter_cutoff_hz"],
        settings["filter_order"],
    )

    def recover(starts):
        estimated, records = recover_controller(
            fit_plant,
            reported_training,
            observed_train,
            settings["duration_s"],
            base["recovery"]["delay_frames"],
            settings["observation_hz"],
            settings["internal_hz"],
            values["filter_cutoff_hz"],
            settings["filter_order"],
            base["recovery"]["bounds"],
            starts,
            robust["max_nfev"],
        )
        predicted = filtered_prediction(
            fit_plant,
            estimated,
            reported_test,
            settings["duration_s"],
            settings["internal_hz"],
            settings["observation_hz"],
            values["filter_cutoff_hz"],
            settings["filter_order"],
        )
        score = calculate_metrics(
            estimated,
            truth_controller,
            truth_plant,
            fit_plant,
            profile,
            settings,
            predicted,
            filtered_truth_test,
            gates,
        )
        return estimated, records, predicted, score

    estimated, records, predicted, score = recover([robust["neutral_start"]])
    adaptive = False
    if robust["adaptive_multistart"] and not score["case_pass"]:
        estimated, records, predicted, score = recover(base["recovery"]["starts"])
        adaptive = True

    return {
        "values": values,
        "truth_plant": truth_plant,
        "fit_plant": fit_plant,
        "truth_controller": truth_controller,
        "estimated": estimated,
        "records": records,
        "predicted_test": predicted,
        "observed_test": observed_test,
        "filtered_truth_test": filtered_truth_test,
        "test_time_s": truth_test["time_s"],
        "score": score,
        "adaptive_multistart_used": adaptive,
    }


def summarize_conditions(rows, gates):
    summaries = []
    condition_order = []
    for row in rows:
        if row["condition_id"] not in condition_order:
            condition_order.append(row["condition_id"])
    for condition_id in condition_order:
        group = [row for row in rows if row["condition_id"] == condition_id]
        pass_fraction = float(np.mean([bool(row["case_pass"]) for row in group]))
        parameter_pass_fraction = float(
            np.mean([bool(row["all_parameter_gates_pass"]) for row in group])
        )
        trajectory_pass_fraction = float(
            np.mean([bool(row["held_out_gate_pass"]) for row in group])
        )
        summaries.append(
            {
                "condition_id": condition_id,
                "factor": group[0]["factor"],
                "level": group[0]["level"],
                "case_count": len(group),
                "case_pass_count": sum(bool(row["case_pass"]) for row in group),
                "case_pass_fraction": pass_fraction,
                "parameter_pass_count": sum(
                    bool(row["all_parameter_gates_pass"]) for row in group
                ),
                "parameter_pass_fraction": parameter_pass_fraction,
                "trajectory_pass_count": sum(
                    bool(row["held_out_gate_pass"]) for row in group
                ),
                "trajectory_pass_fraction": trajectory_pass_fraction,
                "condition_gate_pass": pass_fraction >= gates["required_case_pass_fraction"],
                "median_kp_relative_error": float(np.median([row["kp_relative_error"] for row in group])),
                "median_kd_relative_error": float(np.median([row["kd_relative_error"] for row in group])),
                "median_delay_error_frames": float(np.median([row["delay_error_frames"] for row in group])),
                "median_torque_limit_relative_error": float(np.median([row["torque_limit_relative_error"] for row in group])),
                "median_held_out_theta_rmse_deg": float(np.median([row["held_out_theta_rmse_deg"] for row in group])),
                "max_held_out_theta_rmse_deg": float(np.max([row["held_out_theta_rmse_deg"] for row in group])),
                "adaptive_multistart_case_count": sum(bool(row["adaptive_multistart_used"]) for row in group),
            }
        )
    return summaries


def make_plots(output, summaries, rows, trajectory_rows):
    plot_dir = output / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    labels = [row["condition_id"] for row in summaries]
    colors = ["#2f855a" if row["condition_gate_pass"] else "#c53030" for row in summaries]

    fig, axis = plt.subplots(figsize=(13, 6))
    axis.bar(np.arange(len(labels)), [row["case_pass_fraction"] for row in summaries], color=colors)
    axis.axhline(0.8, color="#1a202c", linestyle="--", linewidth=1, label="Condition gate (80%)")
    axis.set(ylim=(0, 1.05), ylabel="Case pass fraction", title="Stage 2A robustness by condition")
    axis.set_xticks(np.arange(len(labels)), labels, rotation=55, ha="right", fontsize=8)
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "condition_pass_fraction.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(4, 1, figsize=(13, 11), sharex=True)
    panels = [
        ("median_kp_relative_error", "Median Kp relative error", 0.15),
        ("median_kd_relative_error", "Median Kd relative error", 0.15),
        ("median_torque_limit_relative_error", "Median torque-limit error", 0.15),
        ("median_held_out_theta_rmse_deg", "Median held-out RMSE (deg)", 1.0),
    ]
    for axis, (key, label, gate) in zip(axes, panels):
        axis.bar(np.arange(len(labels)), [row[key] for row in summaries], color=colors)
        axis.axhline(gate, color="#1a202c", linestyle="--", linewidth=1)
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=0.25)
    axes[-1].set_xticks(np.arange(len(labels)), labels, rotation=55, ha="right", fontsize=8)
    fig.tight_layout()
    fig.savefig(plot_dir / "condition_median_errors.png", dpi=180)
    plt.close(fig)

    combined = [row for row in rows if row["condition_id"] == "combined_moderate"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    pairs = [
        ("true_kp_nm_per_rad", "estimated_kp_nm_per_rad", "Kp (N·m/rad)"),
        ("true_kd_nms_per_rad", "estimated_kd_nms_per_rad", "Kd (N·m·s/rad)"),
        ("true_torque_limit_nm", "estimated_torque_limit_nm", "Torque limit (N·m)"),
    ]
    for axis, (truth_key, estimate_key, label) in zip(axes, pairs):
        truth = np.array([row[truth_key] for row in combined])
        estimated = np.array([row[estimate_key] for row in combined])
        low = min(truth.min(), estimated.min()) * 0.95
        high = max(truth.max(), estimated.max()) * 1.05
        axis.plot([low, high], [low, high], "--", color="#4a5568")
        axis.scatter(truth, estimated, c=["#2f855a" if row["case_pass"] else "#c53030" for row in combined])
        axis.set(xlabel=f"True {label}", ylabel=f"Recovered {label}")
        axis.grid(alpha=0.25)
    fig.suptitle("Combined moderate mismatch: parameter recovery")
    fig.tight_layout()
    fig.savefig(plot_dir / "combined_parameter_identity.png", dpi=180)
    plt.close(fig)

    example = [row for row in trajectory_rows if row["trial"] == "test_03"]
    fig, axis = plt.subplots(figsize=(9, 4.5))
    axis.plot([row["time_s"] for row in example], [row["true_theta_deg"] for row in example], color="#1a202c", linewidth=2, label="Known truth")
    axis.plot([row["time_s"] for row in example], [row["observed_theta_deg"] for row in example], color="#a0aec0", label="Noisy filtered observation")
    axis.plot([row["time_s"] for row in example], [row["estimated_theta_deg"] for row in example], color="#c05621", linestyle="--", linewidth=2, label="Mismatch-model prediction")
    axis.set(xlabel="Time (s)", ylabel="Angle (deg)", title="Combined moderate mismatch: held-out double pulse")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / "combined_held_out_trajectory.png", dpi=180)
    plt.close(fig)


def render_summary(output, summaries, rows, robust):
    by_id = {row["condition_id"]: row for row in summaries}
    moderate = [by_id[item] for item in robust["moderate_gate_conditions"]]
    robustness_pass = all(row["condition_gate_pass"] for row in moderate)
    passed = [row["condition_id"] for row in summaries if row["condition_gate_pass"]]
    failed = [row["condition_id"] for row in summaries if not row["condition_gate_pass"]]
    combined = by_id["combined_moderate"]
    lines = [
        "# S43 Stage 2A robustness study",
        "",
        "## Decision",
        "",
        f"**{'PASS' if robustness_pass else 'DO NOT PASS'} the moderate robustness gate.** "
        f"{sum(row['condition_gate_pass'] for row in moderate)}/{len(moderate)} required moderate conditions passed.",
        "",
        "The unchanged correctly specified Stage-2A reference remains a software/recovery control. This study measures how parameter interpretation degrades when the observation or plant assumptions are wrong.",
        "",
        "## Condition outcomes",
        "",
        "| Condition | Overall | Parameters | Trajectory | Median Kp error | Median Kd error | Median delay error | Median torque-limit error | Held-out RMSE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['condition_id']} | {row['case_pass_count']}/{row['case_count']} | "
            f"{row['parameter_pass_count']}/{row['case_count']} | {row['trajectory_pass_count']}/{row['case_count']} | "
            f"{100*row['median_kp_relative_error']:.1f}% | "
            f"{100*row['median_kd_relative_error']:.1f}% | {row['median_delay_error_frames']:.1f} frames | "
            f"{100*row['median_torque_limit_relative_error']:.1f}% | {row['median_held_out_theta_rmse_deg']:.3f}° |"
        )
    lines.extend(
        [
            "",
            "## Boundary summary",
            "",
            f"- Conditions passing the 80% case rule: {', '.join(passed) if passed else 'none'}.",
            f"- Conditions failing the rule: {', '.join(failed) if failed else 'none'}.",
            f"- Combined moderate mismatch: {combined['case_pass_count']}/{combined['case_count']} overall, {combined['parameter_pass_count']}/{combined['case_count']} parameter, and {combined['trajectory_pass_count']}/{combined['case_count']} trajectory cases passed; median held-out RMSE {combined['median_held_out_theta_rmse_deg']:.3f}°.",
            "- Failed cases were rerun with the original three-start optimizer. A retained failure therefore persisted after the initialization check.",
            "",
            "## Interpretation",
            "",
            "Passing held-out trajectories does not by itself mean controller parameters are unbiased. Parameter gates and trajectory gates are reported separately in `robustness_metrics.csv`.",
            "",
            "The unmeasured-perturbation condition is the closest tested analogue to the available S43 skeleton trials. If that condition fails, real-data controller parameters remain non-identifiable without stronger perturbation/contact information, even if a trajectory fit looks visually good.",
            "",
            "## Outputs",
            "",
            "- `robustness_metrics.csv`: every plant/profile/noise replicate.",
            "- `condition_summary.csv`: pass fractions and median errors by condition.",
            "- `optimization_profiles.csv`: every retained delay/start fit.",
            "- `combined_example_trajectories.csv`: one combined-mismatch held-out example.",
            "- `plots/`: condition, parameter-bias, and trajectory figures.",
        ]
    )
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return robustness_pass


def run(robustness_config_path, output):
    robust = json.loads(robustness_config_path.read_text(encoding="utf-8"))
    base_path = Path(robust["base_config"])
    base = json.loads(base_path.read_text(encoding="utf-8"))
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    output.mkdir(parents=True)
    all_trials = trial_bank()
    training_trials = [trial for trial in all_trials if trial.split == "train"]
    test_trials = [trial for trial in all_trials if trial.split == "test"]
    profile_map = {row["profile"]: row for row in base["controller_profiles"]}
    rows = []
    optimization_rows = []
    example_rows = []

    frozen = {"robustness": robust, "base_stage2a": base, "trial_bank": [trial.__dict__ for trial in all_trials]}
    (output / "experiment_config.json").write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")

    jobs = []
    for condition in robust["conditions"]:
        profiles = base["controller_profiles"] if condition.get("profiles") == "all" else [profile_map[robust["one_factor_profile"]]]
        for plant_spec in base["plants"]:
            for profile in profiles:
                for seed in base["simulation"]["noise_seeds"]:
                    jobs.append((condition, plant_spec, profile, seed))

    for index, (condition, plant_spec, profile, seed) in enumerate(jobs, start=1):
        case_id = f"{condition['condition_id']}__{plant_spec['source_activity']}__{profile['profile']}__n{seed}"
        print(f"[{index}/{len(jobs)}] {case_id}", flush=True)
        result = fit_case(
            base,
            robust,
            plant_spec,
            profile,
            seed,
            condition,
            training_trials,
            test_trials,
        )
        values = result["values"]
        estimated = result["estimated"]
        score = result["score"]
        row = {
            "case_id": case_id,
            "condition_id": condition["condition_id"],
            "factor": condition["factor"],
            "level": condition["level"],
            "plant_id": plant_spec["plant_id"],
            "source_activity": plant_spec["source_activity"],
            "profile": profile["profile"],
            "noise_seed": seed,
            **values,
            "true_length_m": result["truth_plant"].length_m,
            "estimated_plant_length_m": result["fit_plant"].length_m,
            "true_damping_nms": result["truth_plant"].damping_nms,
            "fit_damping_nms": result["fit_plant"].damping_nms,
            "true_delay_frames": profile["delay_frames"],
            "estimated_delay_frames": estimated.delay_s * base["simulation"]["observation_hz"],
            "adaptive_multistart_used": result["adaptive_multistart_used"],
            "training_theta_rmse_deg": float(np.rad2deg(result["records"][0]["training_theta_rmse_rad"])),
            **score,
        }
        rows.append(row)
        for record in result["records"]:
            optimization_rows.append({"case_id": case_id, **record})

        if case_id == "combined_moderate__A13__balanced__n43021":
            for trial_index, trial in enumerate(test_trials):
                for frame, time_s in enumerate(result["test_time_s"]):
                    example_rows.append(
                        {
                            "case_id": case_id,
                            "trial": trial.trial,
                            "frame": frame,
                            "time_s": float(time_s),
                            "observed_theta_deg": float(np.rad2deg(result["observed_test"][trial_index, frame])),
                            "true_theta_deg": float(np.rad2deg(result["filtered_truth_test"][trial_index, frame])),
                            "estimated_theta_deg": float(np.rad2deg(result["predicted_test"][trial_index, frame])),
                        }
                    )

    summaries = summarize_conditions(rows, base["acceptance_gates"])
    write_csv(output / "robustness_metrics.csv", rows)
    write_csv(output / "condition_summary.csv", summaries)
    write_csv(output / "optimization_profiles.csv", optimization_rows)
    write_csv(output / "combined_example_trajectories.csv", example_rows)
    make_plots(output, summaries, rows, example_rows)
    passed = render_summary(output, summaries, rows, robust)
    print(f"Stage 2A moderate robustness decision: {'PASS' if passed else 'DO NOT PASS'}")
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/S43_stage2a_robustness.json"))
    parser.add_argument("--output", type=Path, default=Path("analyses/S43_stage2a_robustness"))
    args = parser.parse_args()
    run(args.config, args.output)


if __name__ == "__main__":
    main()
