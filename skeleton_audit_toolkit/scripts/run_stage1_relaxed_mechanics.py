"""Run Stage-1.5 variable-length and moving-support diagnostic ablations."""

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
from scipy.interpolate import CubicSpline

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import write_csv
from filter_motion import filter_motion
from phase_annotations import read_json, validate_phase_notes
from relaxed_pendulum_pinn import (
    GRAVITY_M_S2,
    RelaxedLossWeights,
    evaluate_model,
    train_model,
)
from run_stage1_inverted_pendulum import (
    DEFAULT_ACTIVITY_AXES,
    HORIZONTAL_AXES,
    constant_velocity_prediction,
    estimate_initial_velocity,
    margin_of_stability,
    numerical_velocity,
    parse_list,
    trajectory_metrics,
    uncontrolled_pendulum_prediction,
    wrap_angle_difference,
)
from skeleton_model import com_proxy, segment_model
from subject_frame import standing_body_frame, to_subject_frame


MECHANICS = {
    "variable_length": {
        "moving_support": False,
        "label": "fixed pivot + predicted l(t)",
    },
    "moving_support_variable_length": {
        "moving_support": True,
        "label": "measured moving-support diagnostic + predicted l(t)",
    },
}


def standardize_conditions(training, held_out):
    matrix = np.stack([item["condition_raw"] for item in training])
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale = np.where(scale < 1e-6, 1.0, scale)
    for item in training + [held_out]:
        item["condition_scaled"] = (item["condition_raw"] - mean) / scale
    return mean, scale


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
        raise ValueError(f"filtering unavailable for {trial}: {filter_status}")

    com = com_proxy(filtered, segments)[0]
    frame = standing_body_frame(
        filtered,
        window["initial_standing_frame0"],
        radius=settings["standing_radius"],
    )
    com_body = to_subject_frame(com, frame)
    left_foot_body = to_subject_frame(filtered[:, 21], frame)
    right_foot_body = to_subject_frame(filtered[:, 25], frame)
    foot_midpoint_body = (left_foot_body + right_foot_body) / 2.0
    axis = HORIZONTAL_AXES[settings["horizontal_axis"]]
    horizontal_index = axis["index"]
    support_body = to_subject_frame(
        filtered[:, axis["support_joint_indices"]], frame
    )

    onset = window["fall_onset_frame0"]
    contact = window["apparent_contact_frame0"]
    fps = float(config["fps"])
    time_s = np.arange(contact - onset + 1) / fps
    full_time_s = (np.arange(len(filtered)) - onset) / fps

    onset_pivot = foot_midpoint_body[onset]
    fixed_position_full = (
        com_body[:, [horizontal_index, 1]]
        - onset_pivot[[horizontal_index, 1]]
    )
    pivot_displacement_full = np.zeros_like(fixed_position_full)
    pivot_displacement_full[:, 0] = (
        foot_midpoint_body[:, horizontal_index]
        - onset_pivot[horizontal_index]
    )
    pivot_spline = CubicSpline(
        full_time_s,
        pivot_displacement_full[:, 0],
        bc_type="natural",
    )

    moving_support = MECHANICS[settings["mechanics"]]["moving_support"]
    model_position_full = (
        fixed_position_full - pivot_displacement_full
        if moving_support
        else fixed_position_full
    )
    fixed_position = fixed_position_full[onset : contact + 1]
    model_position = model_position_full[onset : contact + 1]
    pivot_displacement = pivot_displacement_full[onset : contact + 1]
    if not moving_support:
        pivot_displacement = np.zeros_like(pivot_displacement)

    initial_position = model_position[0].copy()
    initial_velocity = estimate_initial_velocity(
        model_position_full,
        onset,
        fps,
        settings["velocity_window_frames"],
    )
    onset_length = float(np.linalg.norm(initial_position))
    if onset_length <= 0.2:
        raise ValueError(f"implausible onset CoM-to-pivot length for {trial}")

    model_theta = np.unwrap(
        np.arctan2(model_position[:, 0], model_position[:, 1])
    )
    fixed_theta = np.unwrap(
        np.arctan2(fixed_position[:, 0], fixed_position[:, 1])
    )
    theta0 = float(model_theta[0])
    theta_velocity0 = float(
        (
            initial_position[1] * initial_velocity[0]
            - initial_position[0] * initial_velocity[1]
        )
        / np.dot(initial_position, initial_position)
    )
    support_coordinates = (
        support_body[onset, :, horizontal_index]
        - onset_pivot[horizontal_index]
    )
    bos_left = float(np.min(support_coordinates))
    bos_right = float(np.max(support_coordinates))
    support_span = bos_right - bos_left
    condition = np.array(
        [
            initial_position[0],
            initial_position[1],
            initial_velocity[0],
            initial_velocity[1],
            theta0,
            theta_velocity0,
            onset_length,
            support_span,
        ]
    )
    return {
        "trial": trial,
        "time_s": time_s,
        "fixed_position": fixed_position,
        "model_position": model_position,
        "fixed_theta": fixed_theta,
        "model_theta": model_theta,
        "pivot_displacement": pivot_displacement,
        "pivot_velocity": np.column_stack(
            [pivot_spline(time_s, 1), np.zeros(len(time_s))]
        )
        if moving_support
        else np.zeros_like(pivot_displacement),
        "pivot_acceleration": pivot_spline(time_s, 2)
        if moving_support
        else np.zeros(len(time_s)),
        "pivot_spline": pivot_spline,
        "initial_position": initial_position,
        "initial_velocity": initial_velocity,
        "initial_theta": theta0,
        "initial_theta_velocity": theta_velocity0,
        "condition_raw": condition,
        "onset_length_m": onset_length,
        "bos_left_m": bos_left,
        "bos_right_m": bos_right,
        "duration_s": float(time_s[-1]),
        "filter_status": filter_status,
        "actual_radius_range_m": float(
            np.ptp(np.linalg.norm(model_position, axis=1))
        ),
        "support_displacement_range_m": float(
            np.ptp(pivot_displacement[:, 0])
        ),
    }


def make_training_records(
    training, height_m, mass_kg, damping_nms, collocation_points, moving_support
):
    records = []
    for item in training:
        data_count = len(item["time_s"])
        collocation_time = np.linspace(
            0.0, item["duration_s"], collocation_points
        )
        torque_scale = mass_kg * GRAVITY_M_S2 * item["onset_length_m"]
        pivot_acceleration = (
            item["pivot_spline"](collocation_time, 2)
            if moving_support
            else np.zeros(collocation_points)
        )
        records.append(
            {
                "time_data": item["time_s"],
                "position_data": item["model_position"],
                "condition_data": np.tile(
                    item["condition_scaled"], (data_count, 1)
                ),
                "initial_position_data": np.tile(
                    item["initial_position"], (data_count, 1)
                ),
                "initial_velocity_data": np.tile(
                    item["initial_velocity"], (data_count, 1)
                ),
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
                "damping_collocation": np.full(
                    collocation_points, damping_nms
                ),
                "pivot_acceleration_collocation": pivot_acceleration,
                "height_m": height_m,
            }
        )
    return records


def aggregate(metrics, weight):
    rows = [r for r in metrics if float(r["physics_weight"]) == weight]
    return {
        "xy_rmse": float(np.mean([float(r["model_xy_rmse_m"]) for r in rows])),
        "physics_theta_rmse": float(
            np.mean([float(r["model_physics_theta_rmse_deg"]) for r in rows])
        ),
        "residual": float(
            np.mean([float(r["physics_residual_rms_nm"]) for r in rows])
        ),
        "radius_rmse": float(
            np.mean([float(r["model_radius_rmse_m"]) for r in rows])
        ),
    }


def plot_weight_sweep(metrics, output_path, subject, activity, label):
    weights = sorted({float(r["physics_weight"]) for r in metrics})
    means = []
    errors = []
    for weight in weights:
        values = [
            float(r["model_xy_rmse_m"])
            for r in metrics
            if float(r["physics_weight"]) == weight
        ]
        means.append(np.mean(values))
        errors.append(np.std(values))
    x = np.arange(len(weights))
    fig, ax = plt.subplots(figsize=(7.5, 4.7))
    ax.errorbar(x, means, yerr=errors, marker="o", capsize=4, color="#176d8a")
    ax.set_xticks(x, [f"{w:g}" for w in weights])
    ax.set_xlabel("Physics weight lambda (0 = matched data-only)")
    ax.set_ylabel("Held-out CoM XY RMSE (m)")
    ax.set_title(f"{subject} {activity}: {label}")
    ax.grid(alpha=0.22)
    fig.tight_layout()
    fig.savefig(output_path, dpi=170)
    plt.close(fig)


def build_summary(output_dir, metrics, settings, best_weight, trials, subject, activity):
    data_only = aggregate(metrics, 0.0)
    best = aggregate(metrics, best_weight)
    change = 100.0 * (data_only["xy_rmse"] - best["xy_rmse"]) / data_only["xy_rmse"]
    residual_change = 100.0 * (data_only["residual"] - best["residual"]) / data_only["residual"]
    matched = {}
    for row in metrics:
        key = (row["held_out_trial"], int(row["seed"]))
        matched.setdefault(key, {})[float(row["physics_weight"])] = float(row["model_xy_rmse_m"])
    wins = sum(v[best_weight] < v[0.0] for v in matched.values())
    label = MECHANICS[settings["mechanics"]]["label"]
    if change >= 0:
        change_text = f"{change:.1f}% better"
    else:
        change_text = f"{-change:.1f}% worse"
    lines = [
        f"# {subject} {activity} Stage-1.5 relaxed-mechanics ablation",
        "",
        f"Mechanics: **{label}**.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Matched data-only XY RMSE | {data_only['xy_rmse']:.4f} m |",
        f"| Best nonzero physics weight | {best_weight:g} |",
        f"| Best relaxed PINN XY RMSE | {best['xy_rmse']:.4f} m |",
        f"| Change vs matched data-only | {change_text} |",
        f"| Matched fold/seed PINN wins | {wins} / {len(matched)} |",
        f"| Physics residual reduction | {residual_change:.1f}% |",
        f"| Best PINN physics-angle RMSE | {best['physics_theta_rmse']:.2f} degrees |",
        f"| Best PINN radius RMSE | {best['radius_rmse']:.4f} m |",
        "",
        "## Equation",
        "",
        "The angular residual uses `m*l(t)^2*theta_ddot + 2*m*l(t)*l_dot(t)*theta_dot = m*g*l(t)*sin(theta) + tau_effective - b*theta_dot - m*l(t)*pivot_ddot dot e_theta`.",
        "The predicted trajectory defines `l(t)`; the true held-out CoM radius is not supplied to the model.",
        "",
        "## Interpretation boundary",
        "",
    ]
    if MECHANICS[settings["mechanics"]]["moving_support"]:
        lines.extend(
            [
                "This is a diagnostic ceiling, not a standalone forecast. It uses the held-out trial's filtered left/right FOOT midpoint displacement and acceleration as an observed exogenous support proxy. It does not use held-out CoM after onset, but the support trajectory would be unavailable for prospective simulation and must eventually be predicted or replaced by measured CoP/contact data.",
                "The proxy is not center of pressure and no foot-contact labels are available.",
            ]
        )
    else:
        lines.append(
            "This model remains prospective with respect to post-onset CoM: only onset conditions and time are inputs. The variable length is generated by the trajectory network."
        )
    lines.extend(
        [
            "",
            "## Data and controls",
            "",
            f"- Trials: {', '.join(t['trial'] for t in trials)}.",
            f"- Horizontal direction: {HORIZONTAL_AXES[settings['horizontal_axis']]['description']}.",
            "- Four whole-trial leave-one-out folds, two seeds, and 300 epochs.",
            f"- Physics weights: {', '.join(f'{w:g}' for w in settings['physics_weights'])}.",
            "- Same trajectory and torque architectures as Stage 1.",
            "- Same constant-velocity and uncontrolled-pendulum reference controls are retained.",
            "",
        ]
    )
    (output_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def run_experiment(run_dir, config_path, selection_path, notes_path, output_dir, activity, settings):
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    config = read_json(config_path)
    selection = read_json(selection_path)
    _, windows = validate_phase_notes(notes_path, run_dir, config, selection)
    windows = [w for w in windows if w["activity"] == activity]
    if len(windows) != 4:
        raise ValueError(f"expected four eligible {activity} trials")

    subject = config["subject_id"]
    segments = segment_model(config["sex"])
    trials = [prepare_trial(run_dir, config, w, segments, settings) for w in windows]
    output_dir.mkdir(parents=True)
    (output_dir / "plots").mkdir()
    height_m = float(config["height_in"]) * 0.0254
    mass_kg = float(config["mass_lb"]) * 0.45359237
    damping_nms = float(settings["damping_nms"])
    moving_support = MECHANICS[settings["mechanics"]]["moving_support"]
    metrics, predictions, histories = [], [], []

    for fold_index, original_held_out in enumerate(trials):
        training = [t.copy() for t in trials if t["trial"] != original_held_out["trial"]]
        held_out = original_held_out.copy()
        condition_mean, _ = standardize_conditions(training, held_out)
        time_scale_s = max(t["duration_s"] for t in training)
        records = make_training_records(
            training,
            height_m,
            mass_kg,
            damping_nms,
            settings["collocation_points"],
            moving_support,
        )
        count = len(held_out["time_s"])
        condition = np.tile(held_out["condition_scaled"], (count, 1))
        initial_position = np.tile(held_out["initial_position"], (count, 1))
        initial_velocity = np.tile(held_out["initial_velocity"], (count, 1))

        # The fixed-frame controls retain the original Stage-1 onset state.
        fixed_initial_velocity = (
            held_out["initial_velocity"] + held_out["pivot_velocity"][0]
            if moving_support
            else held_out["initial_velocity"]
        )
        constant_velocity = constant_velocity_prediction(
            held_out["time_s"], held_out["fixed_position"][0], fixed_initial_velocity
        )
        constant_theta = np.unwrap(np.arctan2(constant_velocity[:, 0], constant_velocity[:, 1]))
        constant_metrics = trajectory_metrics(
            held_out["fixed_position"], constant_velocity, held_out["fixed_theta"], constant_theta
        )
        fixed_theta0 = float(held_out["fixed_theta"][0])
        fixed_theta_velocity0 = float(
            (
                held_out["fixed_position"][0, 1] * fixed_initial_velocity[0]
                - held_out["fixed_position"][0, 0] * fixed_initial_velocity[1]
            )
            / np.dot(held_out["fixed_position"][0], held_out["fixed_position"][0])
        )
        uncontrolled, uncontrolled_theta = uncontrolled_pendulum_prediction(
            held_out["time_s"],
            fixed_theta0,
            fixed_theta_velocity0,
            held_out["onset_length_m"],
            damping_nms,
            mass_kg,
        )
        uncontrolled_metrics = trajectory_metrics(
            held_out["fixed_position"], uncontrolled, held_out["fixed_theta"], uncontrolled_theta
        )

        for physics_weight in settings["physics_weights"]:
            for seed in settings["seeds"]:
                data_only = physics_weight == 0.0
                weights = RelaxedLossWeights(
                    physics=physics_weight,
                    effective_torque_l2=0.0 if data_only else settings["effective_torque_l2"],
                    effective_torque_rate=0.0 if data_only else settings["effective_torque_rate"],
                )
                model, history = train_model(
                    records,
                    condition_size=len(condition_mean),
                    time_scale_s=time_scale_s,
                    architecture=settings["architecture"],
                    epochs=settings["epochs"],
                    learning_rate=settings["learning_rate"],
                    loss_weights=weights,
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
                    held_out["onset_length_m"],
                    damping_nms,
                    held_out["pivot_acceleration"],
                    use_effective_torque=not data_only,
                )
                predicted_fixed = evaluation["position_relative"] + held_out["pivot_displacement"]
                predicted_fixed_velocity = evaluation["velocity_relative"] + held_out["pivot_velocity"]
                predicted_fixed_theta = np.unwrap(
                    np.arctan2(predicted_fixed[:, 0], predicted_fixed[:, 1])
                )
                model_metrics = trajectory_metrics(
                    held_out["fixed_position"],
                    predicted_fixed,
                    held_out["fixed_theta"],
                    predicted_fixed_theta,
                )
                physics_theta_error = wrap_angle_difference(
                    held_out["model_theta"], evaluation["theta"]
                )
                actual_radius = np.linalg.norm(held_out["model_position"], axis=1)
                actual_velocity = numerical_velocity(
                    held_out["fixed_position"], held_out["time_s"]
                )
                actual_xcom, actual_mos = margin_of_stability(
                    held_out["fixed_position"],
                    actual_velocity,
                    held_out["onset_length_m"],
                    held_out["bos_left_m"],
                    held_out["bos_right_m"],
                )
                model_xcom, model_mos = margin_of_stability(
                    predicted_fixed,
                    predicted_fixed_velocity,
                    held_out["onset_length_m"],
                    held_out["bos_left_m"],
                    held_out["bos_right_m"],
                )
                residual_rms = float(np.sqrt(np.mean(evaluation["physics_residual"] ** 2)))
                torque_scale = mass_kg * GRAVITY_M_S2 * held_out["onset_length_m"]
                row = {
                    "held_out_trial": held_out["trial"],
                    "training_trials": ";".join(t["trial"] for t in training),
                    "mechanics": settings["mechanics"],
                    "physics_weight": physics_weight,
                    "seed": seed,
                    **{f"model_{k}": v for k, v in model_metrics.items()},
                    "model_physics_theta_rmse_deg": float(
                        np.degrees(np.sqrt(np.mean(physics_theta_error**2)))
                    ),
                    "model_radius_rmse_m": float(
                        np.sqrt(np.mean((evaluation["radius"] - actual_radius) ** 2))
                    ),
                    "model_radius_range_error_m": float(
                        abs(np.ptp(evaluation["radius"]) - np.ptp(actual_radius))
                    ),
                    **{f"constant_velocity_{k}": v for k, v in constant_metrics.items()},
                    **{f"uncontrolled_pendulum_{k}": v for k, v in uncontrolled_metrics.items()},
                    "model_mos_rmse_m": float(np.sqrt(np.mean((model_mos - actual_mos) ** 2))),
                    "physics_residual_rms_nm": residual_rms,
                    "physics_residual_rms_normalized": residual_rms / torque_scale,
                    "effective_torque_rms_nm": float(np.sqrt(np.mean(evaluation["effective_torque"] ** 2))),
                    "actual_radius_range_m": held_out["actual_radius_range_m"],
                    "support_displacement_range_m": held_out["support_displacement_range_m"],
                    "held_out_duration_s": held_out["duration_s"],
                    "held_out_max_abs_condition_z": float(np.max(np.abs(held_out["condition_scaled"]))),
                    "final_training_total_loss": history[-1]["total_loss"],
                    "final_training_data_loss": history[-1]["data"],
                    "final_training_physics_loss": history[-1]["physics"],
                }
                metrics.append(row)
                histories.extend(
                    {
                        "held_out_trial": held_out["trial"],
                        "mechanics": settings["mechanics"],
                        "physics_weight": physics_weight,
                        "seed": seed,
                        **h,
                    }
                    for h in history
                )
                for index, time_value in enumerate(held_out["time_s"]):
                    predictions.append(
                        {
                            "held_out_trial": held_out["trial"],
                            "mechanics": settings["mechanics"],
                            "physics_weight": physics_weight,
                            "seed": seed,
                            "time_s": time_value,
                            "actual_horizontal_m": held_out["fixed_position"][index, 0],
                            "actual_vertical_m": held_out["fixed_position"][index, 1],
                            "model_horizontal_m": predicted_fixed[index, 0],
                            "model_vertical_m": predicted_fixed[index, 1],
                            "actual_physics_radius_m": actual_radius[index],
                            "model_physics_radius_m": evaluation["radius"][index],
                            "support_displacement_m": held_out["pivot_displacement"][index, 0],
                            "effective_torque_nm": evaluation["effective_torque"][index],
                            "physics_residual_nm": evaluation["physics_residual"][index],
                        }
                    )

    nonzero = [w for w in settings["physics_weights"] if w > 0]
    best_weight = min(nonzero, key=lambda w: aggregate(metrics, w)["xy_rmse"])
    write_csv(output_dir / "fold_metrics.csv", metrics)
    write_csv(output_dir / "fold_predictions.csv", predictions)
    write_csv(output_dir / "training_history.csv", histories)
    plot_weight_sweep(
        metrics,
        output_dir / "plots" / "rmse_vs_physics_weight.png",
        subject,
        activity,
        MECHANICS[settings["mechanics"]]["label"],
    )
    config_payload = {
        "subject": subject,
        "activity": activity,
        "framework_stage": "1.5 diagnostic ablation",
        "mechanics": settings["mechanics"],
        "mechanics_label": MECHANICS[settings["mechanics"]]["label"],
        "equation": "m*l(t)^2*theta_ddot + 2*m*l(t)*l_dot(t)*theta_dot = m*g*l(t)*sin(theta) + tau_effective - b*theta_dot - m*l(t)*pivot_ddot dot e_theta",
        "length_policy": "l(t) is the norm of the predicted relative CoM trajectory; held-out CoM radius is not an input",
        "support_policy": (
            "observed filtered FOOT midpoint horizontal trajectory from the held-out trial; diagnostic only"
            if moving_support
            else "fixed foot midpoint at marked onset"
        ),
        "settings": settings,
        "selected_best_nonzero_physics_weight": best_weight,
        "selection_note": "minimum mean XY RMSE on the same exploratory folds; not independent validation",
        "condition_order": [
            "initial_horizontal_com_m",
            "initial_vertical_com_m",
            "initial_horizontal_velocity_m_s",
            "initial_vertical_velocity_m_s",
            "initial_theta_rad",
            "initial_theta_velocity_rad_s",
            "onset_length_m",
            "onset_support_span_m",
        ],
    }
    (output_dir / "experiment_config.json").write_text(
        json.dumps(config_payload, indent=2) + "\n", encoding="utf-8"
    )
    build_summary(output_dir, metrics, settings, best_weight, trials, subject, activity)
    return {
        "activity": activity,
        "mechanics": settings["mechanics"],
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
    parser.add_argument("--activity", required=True)
    parser.add_argument("--mechanics", required=True, choices=sorted(MECHANICS))
    parser.add_argument("--horizontal-axis", choices=sorted(HORIZONTAL_AXES))
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--collocation-points", type=int, default=24)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--physics-weights", default="0,0.01,0.1,1,10")
    parser.add_argument("--seeds", default="43013,43014")
    args = parser.parse_args()
    physics_weights = parse_list(args.physics_weights, float)
    seeds = parse_list(args.seeds, int)
    if 0.0 not in physics_weights or not any(w > 0 for w in physics_weights):
        raise ValueError("physics weights require zero and at least one nonzero value")
    horizontal_axis = args.horizontal_axis or DEFAULT_ACTIVITY_AXES.get(args.activity)
    if horizontal_axis is None:
        raise ValueError("provide --horizontal-axis")
    settings = {
        "mechanics": args.mechanics,
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
