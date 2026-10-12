"""Complete Stage 2 with real-data effective-parameter sensitivity and CoM paths."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from filter_motion import filter_motion
from phase_annotations import read_json, validate_phase_notes
from skeleton_model import com_proxy, segment_model
from stage2_real_effective import (
    RealTrial,
    position_from_theta,
    recover_real_effective_controller,
    simulate_record,
    trajectory_metrics,
)
from stage2a_delayed_pd import Controller
from subject_frame import standing_body_frame, to_subject_frame


HORIZONTAL_INDEX = {"lateral": 0, "forward": 2}


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"no rows supplied for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def estimate_initial_velocity(position, onset, fps, window_frames):
    start = max(0, onset - window_frames + 1)
    frame = np.arange(start, onset + 1)
    time = (frame - onset) / fps
    return np.array(
        [np.polyfit(time, position[start : onset + 1, axis], 1)[0] for axis in range(2)]
    )


def prepare_real_trial(run_dir, subject_config, window, segments, settings, horizontal_axis):
    scale = {"mm": 0.001, "m": 1.0}[subject_config["coordinate_units"]]
    pose = np.loadtxt(
        run_dir / "raw" / f"{window['trial']}.csv", delimiter=",", ndmin=2
    ).reshape(-1, 32, 3) * scale
    filtered, status = filter_motion(
        pose,
        float(subject_config["fps"]),
        settings["filter_cutoff_hz"],
        settings["filter_order"],
    )
    if filtered is None:
        raise ValueError(f"filter unavailable for {window['trial']}: {status}")
    center = com_proxy(filtered, segments)[0]
    body_frame = standing_body_frame(
        filtered, window["initial_standing_frame0"], radius=settings["standing_radius"]
    )
    center_body = to_subject_frame(center, body_frame)
    left_foot = to_subject_frame(filtered[:, 21], body_frame)
    right_foot = to_subject_frame(filtered[:, 25], body_frame)
    onset = window["fall_onset_frame0"]
    contact = window["apparent_contact_frame0"]
    pivot = ((left_foot + right_foot) / 2)[onset]
    horizontal = HORIZONTAL_INDEX[horizontal_axis]
    full_position = center_body[:, [horizontal, 1]] - pivot[[horizontal, 1]]
    position = full_position[onset : contact + 1]
    fps = float(subject_config["fps"])
    initial_velocity = estimate_initial_velocity(
        full_position, onset, fps, settings["velocity_window_frames"]
    )
    theta = np.unwrap(np.arctan2(position[:, 0], position[:, 1]))
    length = float(np.linalg.norm(position[0]))
    omega = float(
        (position[0, 1] * initial_velocity[0] - position[0, 0] * initial_velocity[1])
        / np.dot(position[0], position[0])
    )
    return RealTrial(
        trial=window["trial"],
        activity=window["activity"],
        horizontal_axis=horizontal_axis,
        time_s=np.arange(len(position), dtype=float) / fps,
        position_m=position,
        theta_rad=theta,
        initial_theta_rad=float(theta[0]),
        initial_omega_rad_s=omega,
        initial_position_m=position[0].copy(),
        initial_velocity_m_s=initial_velocity,
        onset_length_m=length,
    )


def constant_velocity(record):
    return record.initial_position_m + record.time_s[:, None] * record.initial_velocity_m_s


def evaluate_baselines(record, mass_kg, simulation):
    constant = constant_velocity(record)
    constant_theta = np.unwrap(np.arctan2(constant[:, 0], constant[:, 1]))
    uncontrolled_controller = Controller(0.0, 0.0, 2 / simulation["observation_hz"], 0.5)
    _, uncontrolled_theta = simulate_record(
        record,
        mass_kg,
        1.0,
        0.0,
        uncontrolled_controller,
        0.0,
        simulation["pulse_onset_s"],
        simulation["pulse_duration_s"],
        simulation["internal_hz"],
        simulation["observation_hz"],
    )
    uncontrolled = position_from_theta(uncontrolled_theta, record.onset_length_m)
    return {
        "constant_position": constant,
        "constant_theta": constant_theta,
        "constant_metrics": trajectory_metrics(
            record.position_m, record.theta_rad, constant, constant_theta
        ),
        "uncontrolled_position": uncontrolled,
        "uncontrolled_theta": uncontrolled_theta,
        "uncontrolled_metrics": trajectory_metrics(
            record.position_m, record.theta_rad, uncontrolled, uncontrolled_theta
        ),
    }


def plot_trial(output, record, predictions, axis_name):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    time = record.time_s
    axes[0].plot(time, record.position_m[:, 0], color="#1a202c", linewidth=2.2, label="Real filtered CoM")
    axes[0].plot(time, predictions["selected_position"][:, 0], "--", color="#2b6cb0", linewidth=2, label="Selected effective model")
    axes[0].plot(time, predictions["zero_position"][:, 0], ":", color="#c05621", linewidth=2, label="Zero-perturbation model")
    axes[0].set(xlabel="Time (s)", ylabel="Horizontal CoM (m)", title=f"{axis_name} component")
    axes[1].plot(time, record.position_m[:, 1], color="#1a202c", linewidth=2.2, label="Real filtered CoM")
    axes[1].plot(time, predictions["selected_position"][:, 1], "--", color="#2b6cb0", linewidth=2, label="Selected effective model")
    axes[1].plot(time, predictions["zero_position"][:, 1], ":", color="#c05621", linewidth=2, label="Zero-perturbation model")
    axes[1].set(xlabel="Time (s)", ylabel="Vertical CoM (m)", title="Vertical component")
    axes[2].plot(record.position_m[:, 0], record.position_m[:, 1], color="#1a202c", linewidth=2.2, label="Real filtered CoM")
    axes[2].plot(predictions["selected_position"][:, 0], predictions["selected_position"][:, 1], "--", color="#2b6cb0", linewidth=2, label="Selected effective model")
    axes[2].plot(predictions["zero_position"][:, 0], predictions["zero_position"][:, 1], ":", color="#c05621", linewidth=2, label="Zero-perturbation model")
    axes[2].scatter(record.position_m[0, 0], record.position_m[0, 1], color="#2f855a", s=35, zorder=4, label="Onset")
    axes[2].set(xlabel="Horizontal CoM (m)", ylabel="Vertical CoM (m)", title="2-D CoM path")
    for axis in axes:
        axis.grid(alpha=0.25)
    handles, labels = axes[2].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(
        f"{record.trial}: leave-one-trial-out real CoM versus predicted CoM\n"
        f"selected forcing assumption: {predictions['selected_model']}"
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def aggregate_metrics(rows, key):
    return float(np.mean([row[key] for row in rows]))


def fit_job(job):
    (
        activity,
        trials,
        held_out,
        length_scale,
        damping_ratio,
        perturbation_model,
        mass_kg,
        config,
    ) = job
    training = [trial for trial in trials if trial.trial != held_out.trial]
    scenario = f"l{length_scale:.2f}_d{damping_ratio:.2f}_{perturbation_model}"
    controller, pulse, fit_profiles = recover_real_effective_controller(
        training,
        mass_kg,
        length_scale,
        damping_ratio,
        perturbation_model,
        config["recovery"]["delay_frames"],
        config["simulation"]["observation_hz"],
        config["simulation"]["internal_hz"],
        config["simulation"]["pulse_onset_s"],
        config["simulation"]["pulse_duration_s"],
        config["recovery"]["bounds"],
        config["recovery"]["starts"],
        config["recovery"]["max_nfev"],
    )
    plant, predicted_theta = simulate_record(
        held_out,
        mass_kg,
        length_scale,
        damping_ratio,
        controller,
        pulse,
        config["simulation"]["pulse_onset_s"],
        config["simulation"]["pulse_duration_s"],
        config["simulation"]["internal_hz"],
        config["simulation"]["observation_hz"],
    )
    predicted_position = position_from_theta(predicted_theta, plant.length_m)
    score = trajectory_metrics(
        held_out.position_m, held_out.theta_rad, predicted_position, predicted_theta
    )
    physical = controller.physical(plant)
    residual_count = sum(len(item.time_s) for item in training)
    parameter_count = 4 if perturbation_model == "shared_pulse" else 3
    residual_sum_squares = 2.0 * fit_profiles[0]["cost"]
    training_aic = residual_count * np.log(
        max(residual_sum_squares / residual_count, np.finfo(float).tiny)
    ) + 2.0 * parameter_count
    row = {
        "activity": activity,
        "held_out_trial": held_out.trial,
        "training_trials": ";".join(item.trial for item in training),
        "scenario": scenario,
        "length_scale": length_scale,
        "damping_ratio": damping_ratio,
        "perturbation_model": perturbation_model,
        "alpha_kp": controller.alpha_kp,
        "beta_kd": controller.beta_kd,
        "delay_frames": controller.delay_s * config["simulation"]["observation_hz"],
        "delay_s": controller.delay_s,
        "gamma_torque_limit": controller.gamma_torque_limit,
        "pulse_amplitude_ratio": pulse,
        "held_out_fit_length_m": plant.length_m,
        "held_out_damping_nms": plant.damping_nms,
        "held_out_kp_nm_per_rad": physical["kp_nm_per_rad"],
        "held_out_kd_nms_per_rad": physical["kd_nms_per_rad"],
        "held_out_torque_limit_nm": physical["torque_limit_nm"],
        "training_objective_rmse": fit_profiles[0]["training_objective_rmse"],
        "training_aic": float(training_aic),
        **score,
    }
    profile_rows = [
        {
            "activity": activity,
            "held_out_trial": held_out.trial,
            "scenario": scenario,
            **profile,
        }
        for profile in fit_profiles
    ]
    return row, profile_rows, predicted_theta, predicted_position


def render_summary(output, metrics, selected_rows, parameter_ranges):
    activities = sorted({row["activity"] for row in selected_rows})
    lines = [
        "# Final Stage 2: identifiability conclusion and exploratory S43 CoM prediction",
        "",
        "## Decision",
        "",
        "Stage 2 is complete as a feasibility and non-identifiability study. The real-data fits below are exploratory effective models, not recovered physiological controllers.",
        "",
        "The displayed model for each fold is chosen using training-trial AIC only between zero perturbation and one shared activity-level pulse proxy. No held-out CoM sample is used to fit the controller, pulse or model choice.",
        "",
        "## Held-out real-trial results",
        "",
        "| Activity | Held-out folds | Selected effective-model XY RMSE | Zero-perturbation XY RMSE | Constant-velocity XY RMSE | Uncontrolled-pendulum XY RMSE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for activity in activities:
        group = [row for row in selected_rows if row["activity"] == activity]
        lines.append(
            f"| {activity} | {len(group)} | {aggregate_metrics(group, 'selected_xy_rmse_m'):.4f} m | "
            f"{aggregate_metrics(group, 'zero_xy_rmse_m'):.4f} m | "
            f"{aggregate_metrics(group, 'constant_velocity_xy_rmse_m'):.4f} m | "
            f"{aggregate_metrics(group, 'uncontrolled_xy_rmse_m'):.4f} m |"
        )
    lines.extend(
        [
            "",
            "## Trial-level displayed models",
            "",
            "| Held-out trial | Selected forcing | Shared pulse ratio | Delay | XY RMSE | Angle RMSE | Endpoint error |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in selected_rows:
        lines.append(
            f"| {row['held_out_trial']} | {row['selected_model']} | {row['selected_pulse_amplitude_ratio']:.3f} | "
            f"{row['selected_delay_frames']:.0f} frames | {row['selected_xy_rmse_m']:.4f} m | "
            f"{row['selected_theta_rmse_deg']:.2f}° | {row['selected_endpoint_error_m']:.4f} m |"
        )
    lines.extend(
        [
            "",
            "## Assumption sensitivity",
            "",
            "The table below reports parameter ranges across ±5% onset-length scaling, zero or 0.10 normalized damping, and zero versus learned shared-pulse forcing. These ranges are sensitivity results, not confidence intervals.",
            "",
            "| Activity | Alpha Kp range | Beta Kd range | Delay range | Gamma torque-limit range | Pulse-ratio range |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in parameter_ranges:
        lines.append(
            f"| {row['activity']} | {row['alpha_min']:.3f}–{row['alpha_max']:.3f} | "
            f"{row['beta_min']:.3f}–{row['beta_max']:.3f} | {row['delay_min_frames']:.0f}–{row['delay_max_frames']:.0f} frames | "
            f"{row['gamma_min']:.3f}–{row['gamma_max']:.3f} | {row['pulse_min']:.3f}–{row['pulse_max']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "A closer CoM line does not validate the parameter values. The shared pulse is inferred from training falls rather than measured, and it can exchange explanatory torque with Kp, Kd, delay, damping and the assumed length.",
            "",
            "The correct conclusion is that the reduced model can produce an assumption-dependent effective prediction of some held-out CoM paths, while the controller decomposition remains non-identifiable. The dataset contains fall skeletons but no measured external forces, recovery forces, ground-reaction forces or center of pressure, so Option 3 cannot be performed retrospectively.",
            "",
            "## Files",
            "",
            "- `assumption_grid_metrics.csv`: all 96 fold/assumption fits.",
            "- `selected_fold_metrics.csv`: training-only selected central model and baselines.",
            "- `held_out_com_predictions.csv`: real and predicted CoM samples.",
            "- `optimization_profiles.csv`: all delay/start fits.",
            "- `parameter_sensitivity_ranges.csv`: activity-level assumption ranges.",
            "- `plots/`: one held-out CoM comparison per real trial.",
        ]
    )
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(config_path, run_dir, subject_config_path, selection_path, output, workers):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    subject_config = read_json(subject_config_path)
    selection = read_json(selection_path)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    output.mkdir(parents=True)
    (output / "plots").mkdir()
    segments = segment_model(subject_config["sex"])
    mass_kg = float(subject_config["mass_lb"]) * 0.45359237
    all_activity_trials = {}
    for activity_spec in config["activities"]:
        _, windows = validate_phase_notes(
            activity_spec["phase_notes"], run_dir, subject_config, selection
        )
        windows = [
            window for window in windows if window["activity"] == activity_spec["activity"]
        ]
        all_activity_trials[activity_spec["activity"]] = [
            prepare_real_trial(
                run_dir,
                subject_config,
                window,
                segments,
                config["preprocessing"],
                activity_spec["horizontal_axis"],
            )
            for window in windows
        ]

    metrics = []
    profiles = []
    central = {}
    jobs = []
    for activity, trials in all_activity_trials.items():
        for held_out in trials:
            for length_scale in config["assumption_grid"]["length_scales"]:
                for damping_ratio in config["assumption_grid"]["damping_ratios"]:
                    for perturbation_model in config["assumption_grid"]["perturbation_models"]:
                        jobs.append((activity, trials, held_out, length_scale, damping_ratio, perturbation_model, mass_kg, config))

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        results = executor.map(fit_job, jobs)
        for index, (job, result) in enumerate(zip(jobs, results), start=1):
            activity, _, held_out, length_scale, damping_ratio, perturbation_model, _, _ = job
            scenario = f"l{length_scale:.2f}_d{damping_ratio:.2f}_{perturbation_model}"
            row, fit_profiles, predicted_theta, predicted_position = result
            print(f"[{index}/{len(jobs)}] complete {activity}/{held_out.trial} {scenario}", flush=True)
            metrics.append(row)
            profiles.extend(fit_profiles)
            if length_scale == 1.0 and damping_ratio == 0.0:
                central.setdefault((activity, held_out.trial), {})[perturbation_model] = {
                    "row": row,
                    "theta": predicted_theta,
                    "position": predicted_position,
                }

    prediction_rows = []
    selected_rows = []
    for activity, trials in all_activity_trials.items():
        for record in trials:
            candidates = central[(activity, record.trial)]
            selected_model = min(
                candidates,
                key=lambda name: candidates[name]["row"]["training_aic"],
            )
            selected = candidates[selected_model]
            zero = candidates["zero"]
            shared = candidates["shared_pulse"]
            baselines = evaluate_baselines(record, mass_kg, config["simulation"])
            selected_row = {
                "activity": activity,
                "held_out_trial": record.trial,
                "selected_model": selected_model,
                "selected_training_objective_rmse": selected["row"]["training_objective_rmse"],
                "selected_training_aic": selected["row"]["training_aic"],
                "selected_alpha_kp": selected["row"]["alpha_kp"],
                "selected_beta_kd": selected["row"]["beta_kd"],
                "selected_delay_frames": selected["row"]["delay_frames"],
                "selected_gamma_torque_limit": selected["row"]["gamma_torque_limit"],
                "selected_pulse_amplitude_ratio": selected["row"]["pulse_amplitude_ratio"],
                **{f"selected_{key}": value for key, value in trajectory_metrics(record.position_m, record.theta_rad, selected["position"], selected["theta"]).items()},
                **{f"zero_{key}": value for key, value in trajectory_metrics(record.position_m, record.theta_rad, zero["position"], zero["theta"]).items()},
                **{f"shared_{key}": value for key, value in trajectory_metrics(record.position_m, record.theta_rad, shared["position"], shared["theta"]).items()},
                **{f"constant_velocity_{key}": value for key, value in baselines["constant_metrics"].items()},
                **{f"uncontrolled_{key}": value for key, value in baselines["uncontrolled_metrics"].items()},
            }
            selected_rows.append(selected_row)
            for frame, time_s in enumerate(record.time_s):
                prediction_rows.append(
                    {
                        "activity": activity,
                        "held_out_trial": record.trial,
                        "frame": frame,
                        "time_s": float(time_s),
                        "selected_model": selected_model,
                        "actual_horizontal_m": float(record.position_m[frame, 0]),
                        "actual_vertical_m": float(record.position_m[frame, 1]),
                        "selected_horizontal_m": float(selected["position"][frame, 0]),
                        "selected_vertical_m": float(selected["position"][frame, 1]),
                        "zero_horizontal_m": float(zero["position"][frame, 0]),
                        "zero_vertical_m": float(zero["position"][frame, 1]),
                        "shared_horizontal_m": float(shared["position"][frame, 0]),
                        "shared_vertical_m": float(shared["position"][frame, 1]),
                        "constant_velocity_horizontal_m": float(baselines["constant_position"][frame, 0]),
                        "constant_velocity_vertical_m": float(baselines["constant_position"][frame, 1]),
                        "uncontrolled_horizontal_m": float(baselines["uncontrolled_position"][frame, 0]),
                        "uncontrolled_vertical_m": float(baselines["uncontrolled_position"][frame, 1]),
                        "actual_theta_deg": float(np.rad2deg(record.theta_rad[frame])),
                        "selected_theta_deg": float(np.rad2deg(selected["theta"][frame])),
                    }
                )
            axis_label = "Anterior-posterior" if record.horizontal_axis == "forward" else "Medial-lateral"
            plot_trial(
                output / "plots" / f"{activity}_{record.trial}_held_out_com_path.png",
                record,
                {
                    "selected_model": selected_model,
                    "selected_position": selected["position"],
                    "zero_position": zero["position"],
                },
                axis_label,
            )

    parameter_ranges = []
    for activity in sorted(all_activity_trials):
        group = [row for row in metrics if row["activity"] == activity]
        parameter_ranges.append(
            {
                "activity": activity,
                "alpha_min": min(row["alpha_kp"] for row in group),
                "alpha_max": max(row["alpha_kp"] for row in group),
                "beta_min": min(row["beta_kd"] for row in group),
                "beta_max": max(row["beta_kd"] for row in group),
                "delay_min_frames": min(row["delay_frames"] for row in group),
                "delay_max_frames": max(row["delay_frames"] for row in group),
                "gamma_min": min(row["gamma_torque_limit"] for row in group),
                "gamma_max": max(row["gamma_torque_limit"] for row in group),
                "pulse_min": min(row["pulse_amplitude_ratio"] for row in group),
                "pulse_max": max(row["pulse_amplitude_ratio"] for row in group),
            }
        )

    write_csv(output / "assumption_grid_metrics.csv", metrics)
    write_csv(output / "selected_fold_metrics.csv", selected_rows)
    write_csv(output / "held_out_com_predictions.csv", prediction_rows)
    write_csv(output / "optimization_profiles.csv", profiles)
    write_csv(output / "parameter_sensitivity_ranges.csv", parameter_ranges)
    frozen = {
        "stage2_real_config": config,
        "subject_config": subject_config,
        "source_run": str(run_dir),
        "selection": str(selection_path),
    }
    (output / "experiment_config.json").write_text(
        json.dumps(frozen, indent=2) + "\n", encoding="utf-8"
    )
    render_summary(output, metrics, selected_rows, parameter_ranges)
    print("Final Stage-2 real-data sensitivity run complete.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/S43_stage2_real_effective_sensitivity.json"))
    parser.add_argument("--run", type=Path, default=Path("findings/S43_audit"))
    parser.add_argument("--subject-config", type=Path, default=Path("configs/S43.json"))
    parser.add_argument("--selection", type=Path, default=Path("configs/S43_modeling_selection.json"))
    parser.add_argument("--output", type=Path, default=Path("analyses/S43_stage2_final_real_effective_sensitivity"))
    parser.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 1) - 1)))
    args = parser.parse_args()
    run(args.config, args.run, args.subject_config, args.selection, args.output, args.workers)


if __name__ == "__main__":
    main()
