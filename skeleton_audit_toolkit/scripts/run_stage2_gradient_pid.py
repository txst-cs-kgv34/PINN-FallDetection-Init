"""Run the advisor-requested gradient-based revised Stage 2."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import write_csv
from filter_motion import filter_motion
from phase_annotations import read_json, validate_phase_notes
from skeleton_model import com_proxy, segment_model
from stage2_gradient_pid import (
    GRAVITY_M_S2,
    ParameterBounds,
    build_synthetic_records,
    identify_gradient_pid,
    load_frozen_stage1,
    prepare_frozen_records,
    simulate_unbounded_pid,
)
from stage2_full_pid import stage1_derivatives
from subject_frame import standing_body_frame, to_subject_frame


AXES = {"lateral": 0, "forward": 2}


def _estimate_initial_velocity(position, onset, fps, frames):
    start = max(0, onset - frames + 1)
    sample = np.arange(start, onset + 1)
    time = (sample - onset) / fps
    return np.array(
        [np.polyfit(time, position[start:onset + 1, axis], 1)[0] for axis in range(2)]
    )


def prepare_trial(run_dir, subject, window, segments, settings, horizontal_axis):
    scale = {"mm": 0.001, "m": 1.0}[subject["coordinate_units"]]
    pose = np.loadtxt(
        run_dir / "raw" / f"{window['trial']}.csv", delimiter=",", ndmin=2
    ).reshape(-1, 32, 3) * scale
    filtered, status = filter_motion(
        pose, float(subject["fps"]), settings["filter_cutoff_hz"], settings["filter_order"]
    )
    if filtered is None:
        raise ValueError(f"filter unavailable for {window['trial']}: {status}")
    com = com_proxy(filtered, segments)[0]
    frame = standing_body_frame(
        filtered, window["initial_standing_frame0"], radius=settings["standing_radius"]
    )
    com_body = to_subject_frame(com, frame)
    left_foot = to_subject_frame(filtered[:, 21], frame)
    right_foot = to_subject_frame(filtered[:, 25], frame)
    onset, contact = window["fall_onset_frame0"], window["apparent_contact_frame0"]
    pivot = ((left_foot + right_foot) / 2)[onset]
    horizontal = AXES[horizontal_axis]
    full_position = com_body[:, [horizontal, 1]] - pivot[[horizontal, 1]]
    position = full_position[onset:contact + 1]
    fps = float(subject["fps"])
    time_s = np.arange(len(position)) / fps
    initial_velocity = _estimate_initial_velocity(
        full_position, onset, fps, settings["velocity_window_frames"]
    )
    theta = np.unwrap(np.arctan2(position[:, 0], position[:, 1]))
    length = float(np.linalg.norm(position[0]))
    omega = float(
        (position[0, 1] * initial_velocity[0] - position[0, 0] * initial_velocity[1])
        / np.dot(position[0], position[0])
    )
    support_indices = (20, 21, 24, 25) if horizontal_axis == "forward" else (21, 25)
    support = to_subject_frame(filtered[:, support_indices], frame)[onset, :, horizontal] - pivot[horizontal]
    condition = np.array([
        position[0, 0], position[0, 1], initial_velocity[0], initial_velocity[1],
        theta[0], omega, length, np.ptp(support),
    ])
    return {
        "trial": window["trial"], "activity": window["activity"],
        "horizontal_axis": horizontal_axis, "time_s": time_s,
        "duration_s": float(time_s[-1]), "position": position, "theta": theta,
        "initial_position": position[0].copy(), "initial_velocity": initial_velocity,
        "initial_theta": float(theta[0]), "initial_omega": omega,
        "length_m": length, "condition_raw": condition,
    }


def _wrap_angle(value):
    return np.arctan2(np.sin(value), np.cos(value))


def metrics(actual_position, actual_theta, predicted_position, predicted_theta):
    error = predicted_position - actual_position
    return {
        "horizontal_rmse_m": float(np.sqrt(np.mean(error[:, 0] ** 2))),
        "vertical_rmse_m": float(np.sqrt(np.mean(error[:, 1] ** 2))),
        "xy_rmse_m": float(np.sqrt(np.mean(np.sum(error**2, axis=1)))),
        "theta_rmse_deg": float(
            np.degrees(np.sqrt(np.mean(_wrap_angle(predicted_theta - actual_theta) ** 2)))
        ),
        "endpoint_error_m": float(np.linalg.norm(error[-1])),
    }


def constant_velocity(trial):
    position = trial["initial_position"] + trial["time_s"][:, None] * trial["initial_velocity"]
    return position, np.unwrap(np.arctan2(position[:, 0], position[:, 1]))


def _bounds(settings):
    raw = settings["bounds"]
    return ParameterBounds(
        alpha_kp=tuple(raw["alpha_kp"]),
        beta_kd=tuple(raw["beta_kd"]),
        kappa_ki=tuple(raw["kappa_ki"]),
        delay_s=tuple(raw["delay_s"]),
    )


def _controller_kwargs(settings):
    return {
        "bounds": _bounds(settings),
        "starts": settings["starts"],
        "adam_epochs": settings["adam_epochs"],
        "adam_learning_rate": settings["adam_learning_rate"],
        "lbfgs_max_iter": settings["lbfgs_max_iter"],
        "gradient_clip_norm": settings["gradient_clip_norm"],
        "integral_time_reference_s": settings["integral_time_reference_s"],
    }


def _fit_checkpoint(job):
    checkpoint, trials, mass_kg, config = job
    stage1 = config["stage1"]
    stage2 = config["stage2"]
    model = load_frozen_stage1(checkpoint, stage1["architecture"])
    mean = np.asarray(checkpoint["condition_mean"])
    scale = np.asarray(checkpoint["condition_scale"])
    local_trials = []
    for original in trials:
        trial = dict(original)
        trial["condition_scaled"] = (trial["condition_raw"] - mean) / scale
        trial["torque_scale"] = mass_kg * GRAVITY_M_S2 * trial["length_m"]
        local_trials.append(trial)
    by_name = {trial["trial"]: trial for trial in local_trials}
    training = [by_name[name] for name in checkpoint["training_trials"]]
    held_out = by_name[checkpoint["held_out_trial"]]
    reference_length = float(np.median([trial["length_m"] for trial in training]))
    records = prepare_frozen_records(
        model,
        training,
        mass_kg,
        stage1["damping_nms"],
        checkpoint["time_scale_s"],
        stage2["controller_collocation_points"],
        stage2["bounds"]["delay_s"][1],
    )
    fit, profiles = identify_gradient_pid(
        records,
        mass_kg,
        reference_length,
        **_controller_kwargs(stage2),
    )
    prediction_theta, _, _, _, _ = simulate_unbounded_pid(
        held_out["time_s"],
        held_out["initial_theta"],
        held_out["initial_omega"],
        mass_kg,
        held_out["length_m"],
        stage1["damping_nms"],
        fit,
        stage2["internal_hz"],
    )
    if np.all(np.isfinite(prediction_theta)):
        prediction_position = np.column_stack(
            [
                held_out["length_m"] * np.sin(prediction_theta),
                held_out["length_m"] * np.cos(prediction_theta),
            ]
        )
        score = metrics(
            held_out["position"],
            held_out["theta"],
            prediction_position,
            prediction_theta,
        )
        simulation_finite = True
    else:
        prediction_position = np.full_like(held_out["position"], np.nan)
        score = {
            "horizontal_rmse_m": np.nan,
            "vertical_rmse_m": np.nan,
            "xy_rmse_m": np.nan,
            "theta_rmse_deg": np.nan,
            "endpoint_error_m": np.nan,
        }
        simulation_finite = False

    held_count = len(held_out["time_s"])
    stage1_held = stage1_derivatives(
        model,
        held_out["time_s"],
        {
            "condition": np.tile(held_out["condition_scaled"], (held_count, 1)),
            "initial_position": np.tile(held_out["initial_position"], (held_count, 1)),
            "initial_velocity": np.tile(held_out["initial_velocity"], (held_count, 1)),
            "torque_scale": np.full((held_count, 1), held_out["torque_scale"]),
        },
    )
    constant_position, constant_theta = constant_velocity(held_out)
    control = {
        "stage1": metrics(
            held_out["position"], held_out["theta"], stage1_held["position"], stage1_held["theta"]
        ),
        "constant": metrics(
            held_out["position"], held_out["theta"], constant_position, constant_theta
        ),
    }
    metric_row = {
        "activity": checkpoint["activity"],
        "held_out_trial": checkpoint["held_out_trial"],
        "training_trials": ";".join(checkpoint["training_trials"]),
        "seed": checkpoint["seed"],
        "simulation_finite": simulation_finite,
        **{key: value for key, value in fit.items() if key != "history"},
        **score,
    }
    profile_rows = []
    histories = []
    for profile in profiles:
        profile_rows.append(
            {
                "activity": checkpoint["activity"],
                "held_out_trial": checkpoint["held_out_trial"],
                "seed": checkpoint["seed"],
                **{key: value for key, value in profile.items() if key != "history"},
            }
        )
        histories.append(
            {
                "activity": checkpoint["activity"],
                "held_out_trial": checkpoint["held_out_trial"],
                "seed": checkpoint["seed"],
                "start_index": profile["start_index"],
                "history": profile["history"],
            }
        )
    prediction_rows = []
    for index, time_value in enumerate(held_out["time_s"]):
        prediction_rows.append(
            {
                "activity": checkpoint["activity"],
                "held_out_trial": checkpoint["held_out_trial"],
                "seed": checkpoint["seed"],
                "frame": index,
                "time_s": float(time_value),
                "actual_horizontal_m": float(held_out["position"][index, 0]),
                "actual_vertical_m": float(held_out["position"][index, 1]),
                "predicted_horizontal_m": float(prediction_position[index, 0]),
                "predicted_vertical_m": float(prediction_position[index, 1]),
                "stage1_horizontal_m": float(stage1_held["position"][index, 0]),
                "stage1_vertical_m": float(stage1_held["position"][index, 1]),
                "constant_horizontal_m": float(constant_position[index, 0]),
                "constant_vertical_m": float(constant_position[index, 1]),
                "actual_theta_deg": float(np.degrees(held_out["theta"][index])),
                "predicted_theta_deg": float(np.degrees(prediction_theta[index])),
            }
        )
    control_row = {
        "activity": checkpoint["activity"],
        "held_out_trial": checkpoint["held_out_trial"],
        "seed": checkpoint["seed"],
        **{f"stage1_{key}": value for key, value in control["stage1"].items()},
        **{f"constant_velocity_{key}": value for key, value in control["constant"].items()},
    }
    return metric_row, profile_rows, histories, prediction_rows, control_row


def _run_synthetic(config):
    settings = config["synthetic_validation"]
    stage2 = config["stage2"]
    mass = settings["mass_kg"]
    length = settings["length_m"]
    torque_reference = mass * GRAVITY_M_S2 * length
    inertia_reference = mass * length**2
    derivative_reference = np.sqrt(inertia_reference * torque_reference)
    true_fit = {
        "kp_nm_per_rad": settings["true_alpha_kp"] * torque_reference,
        "kd_nms_per_rad": settings["true_beta_kd"] * derivative_reference,
        "ki_nm_per_rad_s": settings["true_kappa_ki"] * torque_reference / stage2["integral_time_reference_s"],
        "delay_s": settings["true_delay_s"],
    }
    records = build_synthetic_records(
        mass,
        length,
        settings["damping_nms"],
        true_fit,
        settings["initial_states"],
        settings["duration_s"],
        settings["internal_hz"],
        stage2["bounds"]["delay_s"][1],
    )
    fit, profiles = identify_gradient_pid(
        records,
        mass,
        length,
        **_controller_kwargs(stage2),
    )
    truth = {
        "alpha_kp": settings["true_alpha_kp"],
        "beta_kd": settings["true_beta_kd"],
        "kappa_ki": settings["true_kappa_ki"],
        "delay_s": settings["true_delay_s"],
        **true_fit,
    }
    errors = {}
    for key in ("alpha_kp", "beta_kd", "kappa_ki", "kp_nm_per_rad", "kd_nms_per_rad", "ki_nm_per_rad_s"):
        errors[f"{key}_relative_error"] = abs(fit[key] - truth[key]) / abs(truth[key])
    errors["delay_absolute_error_s"] = abs(fit["delay_s"] - truth["delay_s"])
    return {
        "truth": truth,
        "estimated": {key: value for key, value in fit.items() if key != "history"},
        "errors": errors,
        "profiles": [{key: value for key, value in item.items() if key != "history"} for item in profiles],
    }


def _plot_fold(path, trial, seed, prediction_rows, axis_label):
    rows = sorted(
        [
            row
            for row in prediction_rows
            if row["held_out_trial"] == trial and int(row["seed"]) == seed
        ],
        key=lambda row: float(row["time_s"]),
    )
    time = np.array([float(row["time_s"]) for row in rows])
    actual = np.array([[row["actual_horizontal_m"], row["actual_vertical_m"]] for row in rows], dtype=float)
    gradient = np.array([[row["predicted_horizontal_m"], row["predicted_vertical_m"]] for row in rows], dtype=float)
    stage1 = np.array([[row["stage1_horizontal_m"], row["stage1_vertical_m"]] for row in rows], dtype=float)
    constant = np.array([[row["constant_horizontal_m"], row["constant_vertical_m"]] for row in rows], dtype=float)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    labels = [
        ("Measured CoM", actual, "#202733", "-"),
        ("Gradient PID", gradient, "#176d8a", "--"),
        ("Frozen Stage 1", stage1, "#805ad5", "-."),
        ("Constant velocity", constant, "#c05621", ":"),
    ]
    for label, value, color, style in labels:
        axes[0].plot(time, value[:, 0], style, color=color, label=label, linewidth=2)
        axes[1].plot(time, value[:, 1], style, color=color, label=label, linewidth=2)
        axes[2].plot(value[:, 0], value[:, 1], style, color=color, label=label, linewidth=2)
    axes[0].set(xlabel="Time (s)", ylabel="Horizontal CoM (m)", title=axis_label)
    axes[1].set(xlabel="Time (s)", ylabel="Vertical CoM (m)", title="Vertical")
    axes[2].set(xlabel="Horizontal CoM (m)", ylabel="Vertical CoM (m)", title="2-D CoM path")
    for axis in axes:
        axis.grid(alpha=0.22)
    handles, legend_labels = axes[2].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(f"{trial} revised Stage 2 held-out CoM")
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _summary(config, metrics_rows, control_rows, synthetic):
    lines = [
        "# Revised Stage 2: gradient-based PID identification",
        "",
        "## Method",
        "",
        "The exact retained Stage-1 fold/seed checkpoints are loaded and frozen. Only Kp, Kd, Ki and continuous response delay are optimized. The loss is the normalized Stage-1 governing-equation residual. The effective-torque branch is not a fitting target. Perturbation torque is fixed to zero, and no nuisance torque or torque saturation is used.",
        "",
        "## Synthetic recovery check",
        "",
        "| Parameter | True | Estimated | Error |",
        "|---|---:|---:|---:|",
    ]
    for key, label in (("alpha_kp", "alpha Kp"), ("beta_kd", "beta Kd"), ("kappa_ki", "kappa Ki")):
        lines.append(
            f"| {label} | {synthetic['truth'][key]:.6f} | {synthetic['estimated'][key]:.6f} | {100*synthetic['errors'][key + '_relative_error']:.3f}% |"
        )
    lines.append(
        f"| Delay | {synthetic['truth']['delay_s']:.6f} s | {synthetic['estimated']['delay_s']:.6f} s | {1000*synthetic['errors']['delay_absolute_error_s']:.3f} ms |"
    )
    lines += [
        "",
        "## Held-out CoM results",
        "",
        "Values are means over four held-out trials and two frozen Stage-1 seeds.",
        "",
        "| Activity | Gradient PID | Frozen Stage 1 | Constant velocity |",
        "|---|---:|---:|---:|",
    ]
    for activity in sorted(set(row["activity"] for row in metrics_rows)):
        fitted = [row for row in metrics_rows if row["activity"] == activity]
        controls = [row for row in control_rows if row["activity"] == activity]
        gradient_mean = np.nanmean([row["xy_rmse_m"] for row in fitted])
        stage1_mean = np.mean([row["stage1_xy_rmse_m"] for row in controls])
        constant_mean = np.mean([row["constant_velocity_xy_rmse_m"] for row in controls])
        lines.append(f"| {activity} | {gradient_mean:.4f} m | {stage1_mean:.4f} m | {constant_mean:.4f} m |")
    lines += ["", "## Effective parameter summary", ""]
    lines += [
        "| Activity | alpha Kp mean [range] | beta Kd mean [range] | kappa Ki mean [range] | Delay mean [range] |",
        "|---|---:|---:|---:|---:|",
    ]
    for activity in sorted(set(row["activity"] for row in metrics_rows)):
        rows = [row for row in metrics_rows if row["activity"] == activity]
        def describe(key):
            values = np.asarray([row[key] for row in rows], dtype=float)
            return f"{values.mean():.4f} [{values.min():.4f}, {values.max():.4f}]"
        lines.append(
            f"| {activity} | {describe('alpha_kp')} | {describe('beta_kd')} | {describe('kappa_ki')} | {describe('delay_s')} s |"
        )
    finite = sum(bool(row["simulation_finite"]) for row in metrics_rows)
    lines += [
        "",
        "## Interpretation",
        "",
        f"- {finite}/{len(metrics_rows)} held-out forward simulations remained finite.",
        "- These estimates are effective zero-perturbation model parameters, not physiological measurements.",
        "- Progress to Stage 3 should depend on synthetic recovery, cross-start convergence, held-out prediction, and parameter consistency—not training physics loss alone.",
        "- The previous least-squares/nuisance-torque analysis is retained as legacy evidence and is not the primary revised Stage-2 result.",
        "",
    ]
    return "\n".join(lines)


def run(config_path, run_dir, subject_path, selection_path, output, workers):
    config = json.loads(config_path.read_text())
    subject = read_json(subject_path)
    selection = read_json(selection_path)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    (output / "plots").mkdir()

    segments = segment_model(subject["sex"])
    mass_kg = float(subject["mass_lb"]) * 0.45359237
    activity_trials = {}
    for specification in config["activities"]:
        _, windows = validate_phase_notes(
            Path(specification["phase_notes"]), run_dir, subject, selection
        )
        windows = [item for item in windows if item["activity"] == specification["activity"]]
        activity_trials[specification["activity"]] = [
            prepare_trial(
                run_dir,
                subject,
                window,
                segments,
                config["preprocessing"],
                specification["horizontal_axis"],
            )
            for window in windows
        ]

    checkpoints = json.loads(Path(config["stage1"]["checkpoint_file"]).read_text())
    synthetic = _run_synthetic(config)
    (output / "synthetic_recovery.json").write_text(json.dumps(synthetic, indent=2) + "\n")

    jobs = [
        (checkpoint, activity_trials[checkpoint["activity"]], mass_kg, config)
        for checkpoint in checkpoints
    ]
    metrics_rows = []
    profile_rows = []
    histories = []
    prediction_rows = []
    control_rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        for index, result in enumerate(executor.map(_fit_checkpoint, jobs), 1):
            metric, profiles, local_histories, predictions, control = result
            metrics_rows.append(metric)
            profile_rows.extend(profiles)
            histories.extend(local_histories)
            prediction_rows.extend(predictions)
            control_rows.append(control)
            print(
                f"[{index}/{len(jobs)}] {metric['activity']} {metric['held_out_trial']} seed {metric['seed']}",
                flush=True,
            )

    metrics_rows.sort(key=lambda row: (row["activity"], row["held_out_trial"], row["seed"]))
    write_csv(output / "fold_metrics.csv", metrics_rows)
    write_csv(output / "optimization_profiles.csv", profile_rows)
    write_csv(output / "held_out_com_predictions.csv", prediction_rows)
    write_csv(output / "control_metrics.csv", control_rows)
    (output / "optimization_histories.json").write_text(json.dumps(histories, indent=2) + "\n")
    (output / "experiment_config.json").write_text(json.dumps(config, indent=2) + "\n")

    first_seed = config["stage1"]["seeds"][0]
    for specification in config["activities"]:
        axis_label = "Anterior-posterior" if specification["horizontal_axis"] == "forward" else "Medial-lateral"
        for trial in activity_trials[specification["activity"]]:
            _plot_fold(
                output / "plots" / f"{trial['trial']}_stage2_gradient_pid.png",
                trial["trial"],
                first_seed,
                prediction_rows,
                axis_label,
            )
    (output / "SUMMARY.md").write_text(
        _summary(config, metrics_rows, control_rows, synthetic) + "\n"
    )
    print("Revised gradient-based Stage 2 finished.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/S43_stage2_gradient_pid.json"))
    parser.add_argument("--run", type=Path, default=Path("findings/S43_audit"))
    parser.add_argument("--subject-config", type=Path, default=Path("configs/S43.json"))
    parser.add_argument("--selection", type=Path, default=Path("configs/S43_modeling_selection.json"))
    parser.add_argument("--output", type=Path, default=Path("analyses/S43_stage2_gradient_pid"))
    parser.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 1) - 1)))
    arguments = parser.parse_args()
    run(
        arguments.config,
        arguments.run,
        arguments.subject_config,
        arguments.selection,
        arguments.output,
        arguments.workers,
    )


if __name__ == "__main__":
    main()
