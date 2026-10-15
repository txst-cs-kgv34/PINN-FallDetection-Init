"""Run Stage 1 of the framework with a 2-D inverted-pendulum CoM PINN."""

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
from scipy.integrate import solve_ivp

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import write_csv
from filter_motion import filter_motion
from inverted_pendulum_pinn import (
    GRAVITY_M_S2,
    LossWeights,
    evaluate_model,
    train_model,
)
from phase_annotations import read_json, validate_phase_notes
from skeleton_model import com_proxy, segment_model
from subject_frame import standing_body_frame, to_subject_frame


HORIZONTAL_AXES = {
    "lateral": {
        "index": 0,
        "state_name": "horizontal_lateral",
        "description": "medial-lateral",
        "plot_label": "Medial-lateral CoM (m)",
        "support_joint_indices": (21, 25),
        "support_definition": "left and right FOOT joint projections",
    },
    "forward": {
        "index": 2,
        "state_name": "horizontal_forward",
        "description": "anterior-posterior (subject-forward)",
        "plot_label": "Anterior-posterior CoM (m)",
        "support_joint_indices": (20, 21, 24, 25),
        "support_definition": "left/right ANKLE and FOOT joint projections",
    },
}
DEFAULT_ACTIVITY_AXES = {"A11": "forward", "A13": "lateral"}


def parse_list(value, cast):
    parsed = [cast(item.strip()) for item in value.split(",") if item.strip()]
    if not parsed:
        raise argparse.ArgumentTypeError("provide at least one comma-separated value")
    return parsed


def estimate_initial_velocity(position, onset, fps, window_frames):
    start = max(0, onset - window_frames + 1)
    frames = np.arange(start, onset + 1)
    time = (frames - onset) / fps
    return np.array(
        [np.polyfit(time, position[start : onset + 1, axis], 1)[0] for axis in range(2)]
    )


def prepare_trial(run_dir, config, window, segments, settings):
    trial = window["trial"]
    scale = {"mm": 0.001, "m": 1.0}[config["coordinate_units"]]
    pose = np.loadtxt(
        Path(run_dir) / "raw" / f"{trial}.csv", delimiter=",", ndmin=2
    ).reshape(-1, 32, 3) * scale
    filtered, filter_status = filter_motion(
        pose,
        float(config["fps"]),
        settings["filter_cutoff_hz"],
        settings["filter_order"],
    )
    if filtered is None:
        raise ValueError(f"notebook-aligned filtering unavailable for {trial}: {filter_status}")

    com = com_proxy(filtered, segments)[0]
    frame = standing_body_frame(
        filtered,
        window["initial_standing_frame0"],
        radius=settings["standing_radius"],
    )
    com_body = to_subject_frame(com, frame)
    left_foot_body = to_subject_frame(filtered[:, 21], frame)
    right_foot_body = to_subject_frame(filtered[:, 25], frame)
    foot_midpoint_body = (left_foot_body + right_foot_body) / 2
    axis = HORIZONTAL_AXES[settings["horizontal_axis"]]
    horizontal_index = axis["index"]
    support_body = to_subject_frame(
        filtered[:, axis["support_joint_indices"]], frame
    )

    onset = window["fall_onset_frame0"]
    contact = window["apparent_contact_frame0"]
    fps = float(config["fps"])
    time_s = np.arange(contact - onset + 1) / fps

    # Fixed onset foot midpoint is the explicit single-link pivot assumption.
    pivot = foot_midpoint_body[onset]
    horizontal_vertical = (
        com_body[:, [horizontal_index, 1]] - pivot[[horizontal_index, 1]]
    )
    position = horizontal_vertical[onset : contact + 1]
    initial_position = position[0].copy()
    initial_velocity = estimate_initial_velocity(
        horizontal_vertical,
        onset,
        fps,
        settings["velocity_window_frames"],
    )
    pendulum_length = float(np.linalg.norm(initial_position))
    if pendulum_length <= 0.2:
        raise ValueError(f"implausible onset CoM-to-pivot length for {trial}")

    theta = np.unwrap(np.arctan2(position[:, 0], position[:, 1]))
    theta0 = float(theta[0])
    theta_velocity0 = float(
        (
            initial_position[1] * initial_velocity[0]
            - initial_position[0] * initial_velocity[1]
        )
        / np.dot(initial_position, initial_position)
    )
    support_coordinates = (
        support_body[onset, :, horizontal_index] - pivot[horizontal_index]
    )
    bos_left = float(np.min(support_coordinates))
    bos_right = float(np.max(support_coordinates))
    support_span = bos_right - bos_left
    duration_s = float(time_s[-1])
    condition = np.array(
        [
            initial_position[0],
            initial_position[1],
            initial_velocity[0],
            initial_velocity[1],
            theta0,
            theta_velocity0,
            pendulum_length,
            support_span,
        ]
    )
    return {
        "trial": trial,
        "time_s": time_s,
        "position": position,
        "theta": theta,
        "initial_position": initial_position,
        "initial_velocity": initial_velocity,
        "initial_theta": theta0,
        "initial_theta_velocity": theta_velocity0,
        "condition_raw": condition,
        "pendulum_length_m": pendulum_length,
        "bos_left_m": bos_left,
        "bos_right_m": bos_right,
        "duration_s": duration_s,
        "filter_status": filter_status,
        "actual_radius_range_m": float(
            np.ptp(np.linalg.vector_norm(position, axis=1))
        ),
        "pivot_definition": "fixed foot midpoint at marked fall onset",
        "horizontal_axis": settings["horizontal_axis"],
        "support_proxy_definition": axis["support_definition"],
    }


def standardize_conditions(training, held_out):
    matrix = np.stack([item["condition_raw"] for item in training])
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale = np.where(scale < 1e-6, 1.0, scale)
    for item in training + [held_out]:
        item["condition_scaled"] = (item["condition_raw"] - mean) / scale
    return mean, scale


def make_training_records(
    training,
    height_m,
    mass_kg,
    damping_nms,
    collocation_points,
):
    records = []
    for item in training:
        data_count = len(item["time_s"])
        collocation_time = np.linspace(
            0.0, item["duration_s"], collocation_points
        )
        torque_scale = mass_kg * GRAVITY_M_S2 * item["pendulum_length_m"]
        records.append(
            {
                "time_data": item["time_s"],
                "position_data": item["position"],
                "condition_data": np.tile(item["condition_scaled"], (data_count, 1)),
                "initial_position_data": np.tile(item["initial_position"], (data_count, 1)),
                "initial_velocity_data": np.tile(item["initial_velocity"], (data_count, 1)),
                "torque_scale_data": np.full((data_count, 1), torque_scale),
                "time_collocation": collocation_time,
                "condition_collocation": np.tile(
                    item["condition_scaled"], (collocation_points, 1)
                ),
                "initial_position_collocation": np.tile(
                    item["initial_position"], (collocation_points, 1)
                ),
                "initial_velocity_collocation": np.tile(
                    item["initial_velocity"], (collocation_points, 1)
                ),
                "torque_scale_collocation": np.full(
                    (collocation_points, 1), torque_scale
                ),
                "mass_collocation": np.full(collocation_points, mass_kg),
                "length_collocation": np.full(
                    collocation_points, item["pendulum_length_m"]
                ),
                "damping_collocation": np.full(collocation_points, damping_nms),
                "height_m": height_m,
            }
        )
    return records


def constant_velocity_prediction(time_s, initial_position, initial_velocity):
    return initial_position + time_s[:, None] * initial_velocity


def uncontrolled_pendulum_prediction(
    time_s,
    initial_theta,
    initial_theta_velocity,
    pendulum_length_m,
    damping_nms,
    mass_kg,
):
    inertia = mass_kg * pendulum_length_m**2

    def dynamics(_, state):
        theta, theta_velocity = state
        theta_acceleration = (
            GRAVITY_M_S2 / pendulum_length_m * np.sin(theta)
            - damping_nms / inertia * theta_velocity
        )
        return [theta_velocity, theta_acceleration]

    result = solve_ivp(
        dynamics,
        (float(time_s[0]), float(time_s[-1])),
        [initial_theta, initial_theta_velocity],
        t_eval=time_s,
        rtol=1e-9,
        atol=1e-11,
        max_step=1 / 120,
    )
    if not result.success or result.y.shape[1] != len(time_s):
        raise RuntimeError("uncontrolled pendulum integration failed")
    theta = result.y[0]
    position = np.column_stack(
        [pendulum_length_m * np.sin(theta), pendulum_length_m * np.cos(theta)]
    )
    return position, theta


def wrap_angle_difference(a, b):
    return np.arctan2(np.sin(a - b), np.cos(a - b))


def trajectory_metrics(actual_position, predicted_position, actual_theta, predicted_theta):
    error = actual_position - predicted_position
    axis_rmse = np.sqrt(np.mean(error**2, axis=0))
    theta_error = wrap_angle_difference(actual_theta, predicted_theta)
    return {
        "horizontal_rmse_m": float(axis_rmse[0]),
        "vertical_rmse_m": float(axis_rmse[1]),
        "xy_rmse_m": float(np.sqrt(np.mean(np.sum(error**2, axis=1)))),
        "theta_rmse_deg": float(np.degrees(np.sqrt(np.mean(theta_error**2)))),
        "endpoint_error_m": float(np.linalg.norm(error[-1])),
    }


def numerical_velocity(position, time_s):
    return np.gradient(position, time_s, axis=0, edge_order=2)


def margin_of_stability(position, velocity, pendulum_length_m, bos_left, bos_right):
    omega0 = np.sqrt(GRAVITY_M_S2 / pendulum_length_m)
    xcom = position[:, 0] + velocity[:, 0] / omega0
    margin = np.minimum(bos_right - xcom, xcom - bos_left)
    return xcom, margin


def plot_rmse_sweep(metrics, output_path, subject, activity):
    weights = sorted({float(row["physics_weight"]) for row in metrics})
    groups = {
        weight: [
            float(row["model_xy_rmse_m"])
            for row in metrics
            if float(row["physics_weight"]) == weight
        ]
        for weight in weights
    }
    x = np.arange(len(weights))
    figure, axis = plt.subplots(figsize=(7.4, 4.7))
    axis.errorbar(
        x,
        [np.mean(groups[w]) for w in weights],
        yerr=[np.std(groups[w]) for w in weights],
        marker="o",
        capsize=4,
        color="#176d8a",
        linewidth=2,
        label="network mean ± SD",
    )
    axis.axhline(
        np.mean([float(row["constant_velocity_xy_rmse_m"]) for row in metrics]),
        color="#d07326",
        linestyle="--",
        label="constant velocity",
    )
    axis.axhline(
        np.mean([float(row["uncontrolled_pendulum_xy_rmse_m"]) for row in metrics]),
        color="#7a5c9e",
        linestyle=":",
        label="uncontrolled pendulum",
    )
    axis.set_xticks(x, [f"{w:g}" for w in weights])
    axis.set_xlabel("Inverted-pendulum physics weight λ (0 = data-only)")
    axis.set_ylabel("Held-out horizontal/vertical CoM RMSE (m)")
    axis.set_title(f"{subject} {activity} Stage-1 physics-weight sensitivity")
    axis.grid(alpha=0.22)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(output_path, dpi=170)
    plt.close(figure)


def aggregate(metrics, weight):
    rows = [row for row in metrics if float(row["physics_weight"]) == weight]
    return {
        "xy_rmse": float(np.mean([float(row["model_xy_rmse_m"]) for row in rows])),
        "theta_rmse": float(
            np.mean([float(row["model_theta_rmse_deg"]) for row in rows])
        ),
        "residual": float(
            np.mean([float(row["physics_residual_rms_nm"]) for row in rows])
        ),
        "normalized_residual": float(
            np.mean([float(row["physics_residual_rms_normalized"]) for row in rows])
        ),
    }


def plot_fold_comparison(metrics, best_weight, output_path, subject, activity):
    trials = sorted({row["held_out_trial"] for row in metrics})
    methods = {
        "constant velocity": [],
        "uncontrolled pendulum": [],
        "data-only network": [],
        f"PINN λ={best_weight:g}": [],
    }
    for trial in trials:
        rows = [row for row in metrics if row["held_out_trial"] == trial]
        methods["constant velocity"].append(float(rows[0]["constant_velocity_xy_rmse_m"]))
        methods["uncontrolled pendulum"].append(float(rows[0]["uncontrolled_pendulum_xy_rmse_m"]))
        methods["data-only network"].append(
            np.mean([float(r["model_xy_rmse_m"]) for r in rows if float(r["physics_weight"]) == 0])
        )
        methods[f"PINN λ={best_weight:g}"].append(
            np.mean([float(r["model_xy_rmse_m"]) for r in rows if float(r["physics_weight"]) == best_weight])
        )
    x = np.arange(len(trials))
    width = 0.19
    colors = ["#d07326", "#7a5c9e", "#6b7a8f", "#176d8a"]
    figure, axis = plt.subplots(figsize=(8.5, 4.8))
    for index, (label, values) in enumerate(methods.items()):
        axis.bar(x + (index - 1.5) * width, values, width, label=label, color=colors[index])
    axis.set_xticks(x, [trial.replace(f"{subject}{activity}", "") for trial in trials])
    axis.set_xlabel("Held-out trial")
    axis.set_ylabel("Horizontal/vertical CoM RMSE (m)")
    axis.set_title("Whole-trial leave-one-out controls")
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, fontsize=8, ncol=2)
    figure.tight_layout()
    figure.savefig(output_path, dpi=170)
    plt.close(figure)


def plot_trial(trial, rows, best_weight, seed, output_path, horizontal_axis):
    selected = [r for r in rows if int(r["seed"]) == seed]
    data_rows = sorted(
        [r for r in selected if float(r["physics_weight"]) == 0],
        key=lambda r: float(r["time_s"]),
    )
    pinn_rows = sorted(
        [r for r in selected if float(r["physics_weight"]) == best_weight],
        key=lambda r: float(r["time_s"]),
    )
    time = np.array([float(r["time_s"]) for r in data_rows])
    figure, axes = plt.subplots(4, 1, figsize=(7.7, 9.1), sharex=True)
    series = [
        (
            "actual_horizontal_m",
            "model_horizontal_m",
            "model_horizontal_m",
            HORIZONTAL_AXES[horizontal_axis]["plot_label"],
        ),
        ("actual_vertical_m", "model_vertical_m", "model_vertical_m", "Vertical CoM (m)"),
        ("actual_theta_deg", "model_theta_deg", "model_theta_deg", "Angle θ (degrees)"),
        ("actual_mos_m", "model_mos_m", "model_mos_m", "MoS proxy (m)"),
    ]
    for axis, (actual_key, data_key, pinn_key, label) in zip(axes, series):
        axis.plot(time, [float(r[actual_key]) for r in data_rows], color="#202733", linewidth=2.3, label="held-out")
        axis.plot(time, [float(r[data_key]) for r in data_rows], color="#6b7a8f", linestyle=":", linewidth=1.8, label="data-only")
        axis.plot(time, [float(r[pinn_key]) for r in pinn_rows], color="#176d8a", linestyle="--", linewidth=1.9, label=f"PINN λ={best_weight:g}")
        axis.axhline(0, color="#888888", linewidth=0.7)
        axis.grid(alpha=0.2)
        axis.set_ylabel(label)
    axes[0].legend(frameon=False, fontsize=8, ncol=3)
    axes[-1].set_xlabel("Physical time from marked fall onset (s)")
    figure.suptitle(f"Stage-1 inverted pendulum — held out {trial}", fontsize=12)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(output_path, dpi=170)
    plt.close(figure)


def build_summary(
    output_dir,
    metrics,
    settings,
    best_weight,
    trials,
    subject,
    activity,
):
    data_only = aggregate(metrics, 0.0)
    best = aggregate(metrics, best_weight)
    constant_velocity = np.mean([float(r["constant_velocity_xy_rmse_m"]) for r in metrics])
    uncontrolled = np.mean([float(r["uncontrolled_pendulum_xy_rmse_m"]) for r in metrics])
    improvement = 100 * (data_only["xy_rmse"] - best["xy_rmse"]) / data_only["xy_rmse"]
    residual_reduction = 100 * (data_only["residual"] - best["residual"]) / data_only["residual"]
    matched = {}
    for row in metrics:
        key = (row["held_out_trial"], int(row["seed"]))
        matched.setdefault(key, {})[float(row["physics_weight"])] = float(row["model_xy_rmse_m"])
    paired_wins = sum(
        values[best_weight] < values[0.0]
        for values in matched.values()
        if best_weight in values and 0.0 in values
    )
    best_rows = [r for r in metrics if float(r["physics_weight"]) == best_weight]
    control_wins = sum(
        float(r["model_xy_rmse_m"]) < float(r["constant_velocity_xy_rmse_m"])
        for r in best_rows
    )
    hardest = max(best_rows, key=lambda r: float(r["model_xy_rmse_m"]))
    radius_ranges = [trial["actual_radius_range_m"] for trial in trials]
    axis = HORIZONTAL_AXES[settings["horizontal_axis"]]
    aggregate_methods = {
        "constant-velocity control": constant_velocity,
        "uncontrolled-pendulum control": uncontrolled,
        "data-only network": data_only["xy_rmse"],
        f"PINN (lambda={best_weight:g})": best["xy_rmse"],
    }
    strongest_method = min(aggregate_methods, key=aggregate_methods.get)
    if improvement >= 0:
        accuracy_change = f"{improvement:.1f}% improvement"
        outcome = "The best nonzero physics weight improved aggregate held-out accuracy relative to the identical data-only network."
    else:
        accuracy_change = f"{-improvement:.1f}% worse"
        outcome = "No tested nonzero physics weight improved aggregate held-out accuracy relative to the identical data-only network."
    lines = [
        f"# {subject} {activity} Stage-1 inverted-pendulum PINN",
        "",
        "## Outcome",
        "",
        f"This experiment implements Stage 1 of the framework as a reduced-order angular inverted-pendulum PINN. It uses notebook-aligned filtered, female segment-weighted CoM in the standing subject frame. The horizontal state is the {axis['description']} CoM direction. Horizontal and vertical CoM are measured relative to the fixed foot midpoint at marked fall onset, and the CoM angle is `atan2(horizontal, vertical)`.",
        "",
        outcome,
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Data-only network mean held-out XY RMSE | {data_only['xy_rmse']:.4f} m |",
        f"| Best tested nonzero physics weight | {best_weight:g} |",
        f"| Best PINN mean held-out XY RMSE | {best['xy_rmse']:.4f} m |",
        f"| Change relative to data-only | {accuracy_change} |",
        f"| Matched fold/seed PINN wins | {paired_wins} / {len(matched)} |",
        f"| Best PINN mean angle RMSE | {best['theta_rmse']:.2f}° |",
        f"| Constant-velocity control RMSE | {constant_velocity:.4f} m |",
        f"| Uncontrolled-pendulum control RMSE | {uncontrolled:.4f} m |",
        f"| Best PINN runs beating constant velocity | {control_wins} / {len(best_rows)} |",
        f"| Best PINN angular-equation residual RMS | {best['residual']:.2f} N·m |",
        f"| Best PINN normalized residual RMS | {best['normalized_residual']:.4f} |",
        f"| Residual reduction relative to data-only | {residual_reduction:.1f}% |",
        "",
        "## Governing equation",
        "",
        "The implemented residual follows the framework:",
        "",
        "`I θ¨ = m g l sin(θ) + τ_effective - b θ˙`, with `I = m l²`.",
        "",
        "The current feasibility run fixes `b = 0`. The learned `τ_effective` combines unmeasured human control, external perturbation, support/contact effects and model error. It is not an identified perturbation or corrective human torque.",
        "",
        "## Data and validation",
        "",
        f"- Trials: {', '.join(trial['trial'] for trial in trials)}.",
        f"- Horizontal direction: {axis['description']} ({settings['horizontal_axis']}).",
        f"- Support-span proxy: {axis['support_definition']} at onset.",
        "- Window: every filtered CoM frame from marked onset through apparent contact.",
        "- Four whole-trial leave-one-out folds and training-only condition normalization.",
        f"- Physics weights: {', '.join(f'{w:g}' for w in settings['physics_weights'])}.",
        f"- Seeds per fold/weight: {len(settings['seeds'])}.",
        f"- Notebook filter: order-{settings['filter_order']} zero-phase Butterworth at {settings['filter_cutoff_hz']:g} Hz on each complete raw trial before window extraction.",
        "- No trial-averaging trajectory is used as a quantitative baseline.",
        "- Controls: identical data-only network, constant-velocity extrapolation and zero-torque inverted pendulum.",
        "- Marked contact duration is not included in the condition vector.",
        "",
        "## Physical diagnostics",
        "",
        f"The within-trial onset-to-contact CoM radius variation ranges from {min(radius_ranges):.3f} to {max(radius_ranges):.3f} m, demonstrating departure from a perfectly rigid single link.",
        "The fixed onset foot midpoint is a deliberate reduced-order pivot, not a measured center of pressure. XCoM and Margin of Stability are notebook-derived validation diagnostics, not additional ground truth.",
        "",
        f"The hardest selected-weight run is {hardest['held_out_trial']} (seed {hardest['seed']}) at {float(hardest['model_xy_rmse_m']):.4f} m XY RMSE.",
        f"The strongest aggregate method in this four-trial experiment is the {strongest_method} at {aggregate_methods[strongest_method]:.4f} m RMSE.",
        "",
        "## Decision gate",
        "",
        f"This run can establish whether the framework-aligned angular physics improves an identical data-only model on held-out {subject} {activity} trials. It cannot identify separate controller or perturbation torques, and it does not validate synthetic falls. Stage 2 remains gated on stronger identifiability evidence or additional measurements.",
        "",
    ]
    (output_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def run_experiment(run_dir, config_path, selection_path, notes_path, output_dir, activity, settings):
    run_dir = Path(run_dir)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    config = read_json(config_path)
    selection = read_json(selection_path)
    _, windows = validate_phase_notes(notes_path, run_dir, config, selection)
    windows = [window for window in windows if window["activity"] == activity]
    if len(windows) != 4:
        raise ValueError(f"this experiment expects four eligible {activity} trials")

    segments = segment_model(config["sex"])
    subject = config["subject_id"]
    trials = [prepare_trial(run_dir, config, window, segments, settings) for window in windows]
    output_dir.mkdir(parents=True)
    (output_dir / "plots").mkdir()
    height_m = float(config["height_in"]) * 0.0254
    mass_kg = float(config["mass_lb"]) * 0.45359237
    damping_nms = float(settings["damping_nms"])
    metrics = []
    predictions = []
    histories = []

    for fold_index, original_held_out in enumerate(trials):
        training = [item.copy() for item in trials if item["trial"] != original_held_out["trial"]]
        held_out = original_held_out.copy()
        condition_mean, condition_scale = standardize_conditions(training, held_out)
        time_scale_s = max(item["duration_s"] for item in training)
        records = make_training_records(
            training,
            height_m,
            mass_kg,
            damping_nms,
            settings["collocation_points"],
        )
        count = len(held_out["time_s"])
        condition = np.tile(held_out["condition_scaled"], (count, 1))
        initial_position = np.tile(held_out["initial_position"], (count, 1))
        initial_velocity = np.tile(held_out["initial_velocity"], (count, 1))
        actual_velocity = numerical_velocity(held_out["position"], held_out["time_s"])
        actual_xcom, actual_mos = margin_of_stability(
            held_out["position"],
            actual_velocity,
            held_out["pendulum_length_m"],
            held_out["bos_left_m"],
            held_out["bos_right_m"],
        )

        constant_velocity = constant_velocity_prediction(
            held_out["time_s"], held_out["initial_position"], held_out["initial_velocity"]
        )
        constant_theta = np.unwrap(np.arctan2(constant_velocity[:, 0], constant_velocity[:, 1]))
        constant_metrics = trajectory_metrics(
            held_out["position"], constant_velocity, held_out["theta"], constant_theta
        )
        uncontrolled, uncontrolled_theta = uncontrolled_pendulum_prediction(
            held_out["time_s"],
            held_out["initial_theta"],
            held_out["initial_theta_velocity"],
            held_out["pendulum_length_m"],
            damping_nms,
            mass_kg,
        )
        uncontrolled_metrics = trajectory_metrics(
            held_out["position"], uncontrolled, held_out["theta"], uncontrolled_theta
        )

        for physics_weight in settings["physics_weights"]:
            for seed in settings["seeds"]:
                data_only = physics_weight == 0
                loss_weights = LossWeights(
                    physics=physics_weight,
                    rigid_length=(0.0 if data_only else physics_weight * settings["rigid_length_ratio"]),
                    effective_torque_l2=(0.0 if data_only else settings["effective_torque_l2"]),
                    effective_torque_rate=(0.0 if data_only else settings["effective_torque_rate"]),
                )
                model, history = train_model(
                    records,
                    condition_size=len(condition_mean),
                    time_scale_s=time_scale_s,
                    architecture=settings["architecture"],
                    epochs=settings["epochs"],
                    learning_rate=settings["learning_rate"],
                    loss_weights=loss_weights,
                    seed=seed + fold_index,
                    history_interval=settings["history_interval"],
                )
                evaluation = evaluate_model(
                    model,
                    held_out["time_s"],
                    condition,
                    initial_position,
                    initial_velocity,
                    time_scale_s,
                    mass_kg,
                    held_out["pendulum_length_m"],
                    damping_nms,
                    use_effective_torque=not data_only,
                )
                model_metrics = trajectory_metrics(
                    held_out["position"], evaluation["position"], held_out["theta"], evaluation["theta"]
                )
                model_xcom, model_mos = margin_of_stability(
                    evaluation["position"],
                    evaluation["velocity"],
                    held_out["pendulum_length_m"],
                    held_out["bos_left_m"],
                    held_out["bos_right_m"],
                )
                torque_scale = mass_kg * GRAVITY_M_S2 * held_out["pendulum_length_m"]
                residual_rms = float(np.sqrt(np.mean(evaluation["physics_residual"] ** 2)))
                metrics.append(
                    {
                        "held_out_trial": held_out["trial"],
                        "training_trials": ";".join(item["trial"] for item in training),
                        "physics_weight": physics_weight,
                        "seed": seed,
                        **{f"model_{k}": v for k, v in model_metrics.items()},
                        **{f"constant_velocity_{k}": v for k, v in constant_metrics.items()},
                        **{f"uncontrolled_pendulum_{k}": v for k, v in uncontrolled_metrics.items()},
                        "model_mos_rmse_m": float(np.sqrt(np.mean((model_mos - actual_mos) ** 2))),
                        "physics_residual_rms_nm": residual_rms,
                        "physics_residual_rms_normalized": residual_rms / torque_scale,
                        "effective_torque_rms_nm": float(np.sqrt(np.mean(evaluation["effective_torque"] ** 2))),
                        "rigid_length_rmse_m": float(np.sqrt(np.mean((evaluation["radius"] - held_out["pendulum_length_m"]) ** 2))),
                        "actual_radius_range_m": held_out["actual_radius_range_m"],
                        "pendulum_length_m": held_out["pendulum_length_m"],
                        "held_out_duration_s": held_out["duration_s"],
                        "held_out_max_abs_condition_z": float(np.max(np.abs(held_out["condition_scaled"]))),
                        "final_training_total_loss": history[-1]["total_loss"],
                        "final_training_data_loss": history[-1]["data"],
                        "final_training_physics_loss": history[-1]["physics"],
                        "final_training_rigid_length_loss": history[-1]["rigid_length"],
                    }
                )
                histories.extend(
                    {"held_out_trial": held_out["trial"], "physics_weight": physics_weight, "seed": seed, **row}
                    for row in history
                )
                for index, time_s in enumerate(held_out["time_s"]):
                    predictions.append(
                        {
                            "held_out_trial": held_out["trial"],
                            "physics_weight": physics_weight,
                            "seed": seed,
                            "time_s": time_s,
                            "actual_horizontal_m": held_out["position"][index, 0],
                            "actual_vertical_m": held_out["position"][index, 1],
                            "model_horizontal_m": evaluation["position"][index, 0],
                            "model_vertical_m": evaluation["position"][index, 1],
                            "constant_velocity_horizontal_m": constant_velocity[index, 0],
                            "constant_velocity_vertical_m": constant_velocity[index, 1],
                            "uncontrolled_horizontal_m": uncontrolled[index, 0],
                            "uncontrolled_vertical_m": uncontrolled[index, 1],
                            "actual_theta_deg": np.degrees(held_out["theta"][index]),
                            "model_theta_deg": np.degrees(evaluation["theta"][index]),
                            "actual_xcom_m": actual_xcom[index],
                            "model_xcom_m": model_xcom[index],
                            "actual_mos_m": actual_mos[index],
                            "model_mos_m": model_mos[index],
                            "effective_torque_nm": evaluation["effective_torque"][index],
                            "physics_residual_nm": evaluation["physics_residual"][index],
                        }
                    )

    nonzero = [weight for weight in settings["physics_weights"] if weight > 0]
    best_weight = min(nonzero, key=lambda weight: aggregate(metrics, weight)["xy_rmse"])
    write_csv(output_dir / "fold_metrics.csv", metrics)
    write_csv(output_dir / "fold_predictions.csv", predictions)
    write_csv(output_dir / "training_history.csv", histories)
    plot_rmse_sweep(
        metrics,
        output_dir / "plots" / "rmse_vs_physics_weight.png",
        subject,
        activity,
    )
    plot_fold_comparison(
        metrics,
        best_weight,
        output_dir / "plots" / "fold_rmse_comparison.png",
        subject,
        activity,
    )
    for trial in sorted({row["held_out_trial"] for row in predictions}):
        plot_trial(
            trial,
            [row for row in predictions if row["held_out_trial"] == trial],
            best_weight,
            settings["seeds"][0],
            output_dir / "plots" / f"{trial}_stage1.png",
            settings["horizontal_axis"],
        )

    experiment_config = {
        "activity": activity,
        "subject": subject,
        "framework_stage": 1,
        "equation": "I*theta_ddot = m*g*l*sin(theta) + tau_effective - b*theta_dot",
        "inertia_assumption": "point mass I=m*l^2",
        "horizontal_axis": settings["horizontal_axis"],
        "horizontal_axis_description": HORIZONTAL_AXES[settings["horizontal_axis"]]["description"],
        "theta_definition": f"atan2({HORIZONTAL_AXES[settings['horizontal_axis']]['state_name']}_com, vertical_headward_com) relative to fixed onset foot midpoint",
        "pivot_definition": "fixed foot midpoint at marked fall onset",
        "support_proxy_definition": HORIZONTAL_AXES[settings["horizontal_axis"]]["support_definition"],
        "torque_interpretation": "unidentified effective sum; not measured human control or perturbation",
        "settings": settings,
        "seed_policy": "training seed = listed base seed + zero-based fold index",
        "selected_best_nonzero_physics_weight": best_weight,
        "selection_note": "minimum mean XY RMSE on the same four exploratory folds; not independent validation",
        "condition_order": [
            "initial_horizontal_com_m",
            "initial_vertical_com_m",
            "initial_horizontal_velocity_m_s",
            "initial_vertical_velocity_m_s",
            "initial_theta_rad",
            "initial_theta_velocity_rad_s",
            "onset_pendulum_length_m",
            "onset_support_span_m",
        ],
        "excluded_condition": "marked onset-to-contact duration is deliberately not supplied",
        "mass_kg": mass_kg,
        "height_m": height_m,
        "baseline_policy": "no averaged-trial trajectory; use data-only, constant velocity and uncontrolled pendulum controls",
    }
    (output_dir / "experiment_config.json").write_text(
        json.dumps(experiment_config, indent=2) + "\n", encoding="utf-8"
    )
    build_summary(
        output_dir,
        metrics,
        settings,
        best_weight,
        trials,
        subject,
        activity,
    )
    return {
        "activity": activity,
        "folds": 4,
        "weights": settings["physics_weights"],
        "seeds": settings["seeds"],
        "best_nonzero_physics_weight": best_weight,
        "output": str(output_dir),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--phase-notes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--activity", default="A13")
    parser.add_argument("--horizontal-axis", choices=sorted(HORIZONTAL_AXES))
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--collocation-points", type=int, default=24)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--physics-weights", default="0,0.01,0.1,1,10")
    parser.add_argument("--seeds", default="43013,43014")
    args = parser.parse_args()
    physics_weights = parse_list(args.physics_weights, float)
    seeds = parse_list(args.seeds, int)
    if 0.0 not in physics_weights:
        raise ValueError("physics weights must include 0 for the data-only control")
    if not any(weight > 0 for weight in physics_weights):
        raise ValueError("include at least one nonzero physics weight")
    horizontal_axis = args.horizontal_axis or DEFAULT_ACTIVITY_AXES.get(args.activity)
    if horizontal_axis is None:
        raise ValueError(
            "provide --horizontal-axis for activities without a predefined direction"
        )
    settings = {
        "epochs": args.epochs,
        "collocation_points": args.collocation_points,
        "learning_rate": args.learning_rate,
        "physics_weights": physics_weights,
        "seeds": seeds,
        "history_interval": 50,
        "standing_radius": 2,
        "velocity_window_frames": 5,
        "filter_cutoff_hz": 1.5,
        "filter_order": 6,
        "horizontal_axis": horizontal_axis,
        "damping_nms": 0.0,
        "rigid_length_ratio": 0.1,
        "effective_torque_l2": 0.0001,
        "effective_torque_rate": 0.001,
        "architecture": {
            "trajectory_hidden_size": 32,
            "trajectory_hidden_layers": 3,
            "torque_hidden_size": 16,
            "torque_hidden_layers": 2,
        },
    }
    result = run_experiment(
        args.run,
        args.config,
        args.selection,
        args.phase_notes,
        args.output,
        args.activity,
        settings,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
