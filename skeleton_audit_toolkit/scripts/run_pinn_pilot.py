"""Train and evaluate the first physical-time A13 PINN pilot."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import write_csv
from phase_annotations import read_json, validate_phase_notes
from pinn_autograd import GRAVITY_M_S2, evaluate_pinn, train_pinn
from skeleton_model import com_proxy, segment_model
from subject_frame import standing_body_frame, to_subject_frame


AXES = ("lateral_right", "vertical_headward", "forward_nose_proxy")
AXIS_LABELS = ("Lateral rightward", "Vertical headward", "Forward nose proxy")


def estimate_initial_velocity(position, onset, fps, window_frames=5):
    start = max(0, onset - window_frames + 1)
    frames = np.arange(start, onset + 1)
    time = (frames - onset) / fps
    return np.array(
        [np.polyfit(time, position[start : onset + 1, axis], 1)[0] for axis in range(3)]
    )


def prepare_trial(run_dir, config, window, segments, standing_radius, velocity_window):
    trial = window["trial"]
    scale = {"mm": 0.001, "m": 1.0}[config["coordinate_units"]]
    pose = np.loadtxt(Path(run_dir) / "raw" / f"{trial}.csv", delimiter=",", ndmin=2)
    pose = pose.reshape(len(pose), 32, 3) * scale
    com = com_proxy(pose, segments)[0]
    frame = standing_body_frame(
        pose, window["initial_standing_frame0"], radius=standing_radius
    )
    com_body = to_subject_frame(com, frame)
    foot_midpoint = (pose[:, 21] + pose[:, 25]) / 2
    foot_midpoint_body = to_subject_frame(foot_midpoint, frame)
    onset = window["fall_onset_frame0"]
    contact = window["apparent_contact_frame0"]
    fps = float(config["fps"])
    time_s = np.arange(contact - onset + 1) / fps
    position = com_body[onset : contact + 1] - com_body[onset]
    initial_velocity = estimate_initial_velocity(
        com_body, onset, fps, window_frames=velocity_window
    )
    relative_com = com_body[onset] - foot_midpoint_body[onset]
    foot_separation = float(np.linalg.norm(pose[onset, 21] - pose[onset, 25]))
    condition = np.concatenate([initial_velocity, relative_com, [foot_separation]])
    return {
        "trial": trial,
        "time_s": time_s,
        "position": position,
        "duration_s": float(time_s[-1]),
        "initial_velocity": initial_velocity,
        "condition_raw": condition,
        "standing_span_m": frame["standing_head_to_foot_midpoint_m"],
    }


def standardize_conditions(training, held_out):
    matrix = np.stack([item["condition_raw"] for item in training])
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale = np.where(scale < 1e-6, 1.0, scale)
    for item in training + [held_out]:
        item["condition_scaled"] = (item["condition_raw"] - mean) / scale
    return mean, scale


def make_training_records(training, height_m, collocation_points):
    records = []
    for item in training:
        condition_data = np.tile(item["condition_scaled"], (len(item["time_s"]), 1))
        collocation_time = np.linspace(0.0, item["duration_s"], collocation_points)
        condition_collocation = np.tile(
            item["condition_scaled"], (collocation_points, 1)
        )
        records.append(
            {
                "time_data": item["time_s"],
                "position_data": item["position"],
                "condition_data": condition_data,
                "initial_velocity_data": np.tile(
                    item["initial_velocity"], (len(item["time_s"]), 1)
                ),
                "time_collocation": collocation_time,
                "condition_collocation": condition_collocation,
                "initial_velocity_collocation": np.tile(
                    item["initial_velocity"], (collocation_points, 1)
                ),
                "height_m": height_m,
            }
        )
    return records


def training_mean_prediction(training, query_time, query_duration):
    phase = query_time / query_duration
    trajectories = []
    for item in training:
        training_phase = item["time_s"] / item["duration_s"]
        trajectories.append(
            np.column_stack(
                [
                    np.interp(phase, training_phase, item["position"][:, axis])
                    for axis in range(3)
                ]
            )
        )
    return np.mean(trajectories, axis=0)


def error_metrics(actual, predicted):
    error = actual - predicted
    axis_rmse = np.sqrt(np.mean(error**2, axis=0))
    return {
        "lateral_right_rmse_m": axis_rmse[0],
        "vertical_headward_rmse_m": axis_rmse[1],
        "forward_nose_proxy_rmse_m": axis_rmse[2],
        "rmse_3d_m": np.sqrt(np.mean(np.sum(error**2, axis=1))),
        "endpoint_error_m": np.linalg.norm(error[-1]),
    }


def plot_fold(trial, time_s, actual, pinn, baseline, output_path):
    figure, axes = plt.subplots(3, 1, figsize=(7.4, 7.4), sharex=True)
    for axis_index, axis in enumerate(axes):
        axis.plot(
            time_s,
            actual[:, axis_index],
            color="#202733",
            linewidth=2.5,
            label="held-out",
        )
        axis.plot(
            time_s,
            baseline[:, axis_index],
            color="#d07326",
            linestyle="--",
            linewidth=1.7,
            label="training mean",
        )
        axis.plot(
            time_s,
            pinn[:, axis_index],
            color="#176d8a",
            linestyle="--",
            linewidth=1.9,
            label="PINN",
        )
        axis.axhline(0, color="#888888", linewidth=0.7)
        axis.grid(alpha=0.2)
        axis.set_ylabel(f"{AXIS_LABELS[axis_index]}\nΔCoM (m)")
    axes[0].legend(frameon=False, fontsize=8, ncol=3)
    axes[-1].set_xlabel("Physical time from marked fall onset (s)")
    figure.suptitle(f"A13 physical-time PINN — held out {trial}", fontsize=12)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def build_summary(output_dir, metrics, config):
    pinn_errors = [float(row["pinn_rmse_3d_m"]) for row in metrics]
    baseline_errors = [float(row["baseline_rmse_3d_m"]) for row in metrics]
    residuals = [float(row["held_out_physics_residual_rms_m_s2"]) for row in metrics]
    forces = [float(row["held_out_effective_force_rms_n"]) for row in metrics]
    condition_z = [float(row["held_out_max_abs_condition_z"]) for row in metrics]
    final_training_loss = [float(row["final_training_total_loss"]) for row in metrics]
    improved = sum(
        float(row["pinn_rmse_3d_m"]) < float(row["baseline_rmse_3d_m"])
        for row in metrics
    )
    lines = [
        "# S43 A13 first PINN pilot",
        "",
        "## Outcome",
        "",
        "The model was trained in four whole-trial folds using physical time and initial-state conditioning. It predicts body-frame CoM displacement while automatic differentiation supplies velocity and acceleration.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Mean PINN 3D RMSE | {np.mean(pinn_errors):.4f} m |",
        f"| Mean training-mean 3D RMSE | {np.mean(baseline_errors):.4f} m |",
        f"| Folds where PINN improves | {improved} / {len(metrics)} |",
        f"| Mean held-out physics residual RMS | {np.mean(residuals):.4f} m/s² |",
        f"| Mean effective-force RMS | {np.mean(forces):.1f} N |",
        f"| Largest held-out condition distance | {np.max(condition_z):.1f} training SD |",
        f"| Mean final training loss | {np.mean(final_training_loss):.6f} |",
        "",
        "## Observed inputs",
        "",
        "- Physical time from the manual fall-onset frame.",
        "- Raw skeleton-derived CoM in the fixed standing-body frame.",
        "- Pre-onset CoM velocity, onset CoM relative to the foot midpoint, and onset foot separation.",
        f"- Subject mass {config['mass_lb']} lb and reported height {config['height_in']} in from the subject configuration.",
        "",
        "## Physics-informed assumptions",
        "",
        "The model enforces `r¨ = g_proxy + a_effective`. The gravity proxy is 9.80665 m/s² opposite the standing headward axis. The effective acceleration is a learned low-complexity residual regularized for magnitude and temporal roughness. Multiplying it by subject mass produces the reported effective force.",
        "",
        "This effective force combines unmeasured support, voluntary control, contact effects, modeling error and any true perturbation. It is not a recovered perturbation or ground-reaction force.",
        "",
        "## Interpretation gate",
        "",
        "This is a software/research prototype. It is useful only if held-out position error and physics residual are reported together. A low residual alone is not validation because the effective term is learned. Synthetic falls should not yet be presented as physically validated.",
        "",
        "The training objective converged, but the PINN did not beat the training-mean baseline in any fold. Held-out initial-state conditions are outside the tiny three-trial training ranges; the largest standardized distance occurs for T02. This is a generalization/data-coverage failure, not evidence that the effective force is physically meaningful.",
        "",
        "## Next experiment",
        "",
        "Compare data-only and physics-informed networks under the same folds, then run loss-weight sensitivity. Only after the result is stable should the effective input be perturbed to generate candidate synthetic trajectories.",
        "",
    ]
    (output_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def run_pilot(
    run_dir, config_path, selection_path, notes_path, output_dir, activity, settings
):
    run_dir = Path(run_dir)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    config = read_json(config_path)
    selection = read_json(selection_path)
    _, windows = validate_phase_notes(notes_path, run_dir, config, selection)
    windows = [window for window in windows if window["activity"] == activity]
    if len(windows) != 4:
        raise ValueError(f"this pilot expects four eligible {activity} trials")
    segments = segment_model(config["sex"])
    trials = [
        prepare_trial(
            run_dir,
            config,
            window,
            segments,
            settings["standing_radius"],
            settings["velocity_window_frames"],
        )
        for window in windows
    ]
    output_dir.mkdir(parents=True)
    (output_dir / "plots").mkdir()
    height_m = float(config["height_in"]) * 0.0254
    mass_kg = float(config["mass_lb"]) * 0.45359237
    metrics = []
    prediction_rows = []
    histories = []
    models = []

    for fold_index, held_out in enumerate(trials):
        training = [
            item.copy() for item in trials if item["trial"] != held_out["trial"]
        ]
        held_out = held_out.copy()
        condition_mean, condition_scale = standardize_conditions(training, held_out)
        held_out_condition_z = held_out["condition_scaled"]
        time_scale_s = max(item["duration_s"] for item in training)
        records = make_training_records(
            training, height_m, settings["collocation_points"]
        )
        model = train_pinn(
            records,
            condition_size=len(condition_mean),
            time_scale_s=time_scale_s,
            hidden_size=settings["hidden_size"],
            epochs=settings["epochs"],
            learning_rate=settings["learning_rate"],
            weights=settings["loss_weights"],
            seed=settings["seed"] + fold_index,
        )
        condition = np.tile(held_out["condition_scaled"], (len(held_out["time_s"]), 1))
        velocity = np.tile(held_out["initial_velocity"], (len(held_out["time_s"]), 1))
        evaluation = evaluate_pinn(
            model, held_out["time_s"], condition, velocity, time_scale_s
        )
        baseline = training_mean_prediction(
            training, held_out["time_s"], held_out["duration_s"]
        )
        pinn_metrics = error_metrics(held_out["position"], evaluation["position"])
        baseline_metrics = error_metrics(held_out["position"], baseline)
        physics_rms = float(
            np.sqrt(np.mean(np.sum(evaluation["physics_residual"] ** 2, axis=1)))
        )
        effective_force_rms = float(
            mass_kg
            * np.sqrt(
                np.mean(np.sum(evaluation["effective_acceleration"] ** 2, axis=1))
            )
        )
        metrics.append(
            {
                "held_out_trial": held_out["trial"],
                "training_trials": ";".join(item["trial"] for item in training),
                **{f"pinn_{key}": value for key, value in pinn_metrics.items()},
                **{f"baseline_{key}": value for key, value in baseline_metrics.items()},
                "held_out_physics_residual_rms_m_s2": physics_rms,
                "held_out_effective_force_rms_n": effective_force_rms,
                "held_out_duration_s": held_out["duration_s"],
                "training_time_scale_s": time_scale_s,
                "held_out_max_abs_condition_z": float(
                    np.max(np.abs(held_out_condition_z))
                ),
                "final_training_total_loss": model["history"][-1]["total_loss"],
                "final_training_data_loss": model["history"][-1]["data"],
                "final_training_physics_loss": model["history"][-1]["physics"],
            }
        )
        for index, time_s in enumerate(held_out["time_s"]):
            row = {"held_out_trial": held_out["trial"], "time_s": time_s}
            for axis_index, axis in enumerate(AXES):
                row[f"actual_{axis}_m"] = held_out["position"][index, axis_index]
                row[f"pinn_{axis}_m"] = evaluation["position"][index, axis_index]
                row[f"baseline_{axis}_m"] = baseline[index, axis_index]
                row[f"effective_acceleration_{axis}_m_s2"] = evaluation[
                    "effective_acceleration"
                ][index, axis_index]
                row[f"physics_residual_{axis}_m_s2"] = evaluation["physics_residual"][
                    index, axis_index
                ]
            prediction_rows.append(row)
        histories.extend(
            {"held_out_trial": held_out["trial"], **row} for row in model["history"]
        )
        models.append(
            {
                "held_out_trial": held_out["trial"],
                "condition_mean": condition_mean.tolist(),
                "condition_scale": condition_scale.tolist(),
                "time_scale_s": time_scale_s,
                "parameter_shapes": [
                    list(shape) for shape in model["parameter_shapes"]
                ],
                "parameter_sizes": model["parameter_sizes"],
                "flat_parameters": model["flat_parameters"].tolist(),
            }
        )
        plot_fold(
            held_out["trial"],
            held_out["time_s"],
            held_out["position"],
            evaluation["position"],
            baseline,
            output_dir / "plots" / f"{held_out['trial']}_pinn.png",
        )

    write_csv(output_dir / "fold_metrics.csv", metrics)
    write_csv(output_dir / "fold_predictions.csv", prediction_rows)
    write_csv(output_dir / "training_history.csv", histories)
    (output_dir / "model_parameters.json").write_text(
        json.dumps(models, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "experiment_config.json").write_text(
        json.dumps(
            {
                "activity": activity,
                "settings": settings,
                "condition_order": [
                    "initial_velocity_lateral",
                    "initial_velocity_vertical",
                    "initial_velocity_forward",
                    "onset_relative_com_lateral",
                    "onset_relative_com_vertical",
                    "onset_relative_com_forward",
                    "onset_foot_separation_m",
                ],
                "gravity_proxy_m_s2": [0.0, -GRAVITY_M_S2, 0.0],
                "mass_kg": mass_kg,
                "height_m": height_m,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    build_summary(output_dir, metrics, config)
    return {"activity": activity, "folds": len(metrics), "metrics": metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--phase-notes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--activity", default="A13")
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--hidden-size", type=int, default=12)
    parser.add_argument("--collocation-points", type=int, default=24)
    parser.add_argument("--learning-rate", type=float, default=0.003)
    parser.add_argument("--seed", type=int, default=43013)
    args = parser.parse_args()
    settings = {
        "epochs": args.epochs,
        "hidden_size": args.hidden_size,
        "collocation_points": args.collocation_points,
        "learning_rate": args.learning_rate,
        "seed": args.seed,
        "standing_radius": 2,
        "velocity_window_frames": 5,
        "loss_weights": {
            "data": 1.0,
            "physics": 0.1,
            "effective_acceleration_l2": 0.0001,
            "effective_acceleration_jerk": 0.001,
        },
    }
    result = run_pilot(
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
