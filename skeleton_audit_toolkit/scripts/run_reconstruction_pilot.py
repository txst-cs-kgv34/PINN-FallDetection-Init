"""Run a fixed leave-one-trial-out kinematic reconstruction pilot."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import interpolate_trajectory, write_csv
from phase_annotations import read_json, validate_phase_notes
from skeleton_model import com_proxy, segment_model
from subject_frame import standing_body_frame, to_subject_frame

AXIS_KEYS = ("lateral_right", "vertical_headward", "forward_nose_proxy")
AXIS_LABELS = (
    "Body lateral, rightward",
    "Body vertical, headward",
    "Body forward, nose proxy",
)


def polynomial_design(phase, degree):
    """No intercept: onset displacement is constrained to zero."""
    return np.column_stack([phase**power for power in range(1, degree + 1)])


def fit_ridge_shape(training_trajectories, phase, degree, ridge):
    design = polynomial_design(phase, degree)
    x = np.tile(design, (len(training_trajectories), 1))
    y = np.concatenate(training_trajectories, axis=0)
    penalty = ridge * np.eye(degree)
    weights = np.linalg.solve(x.T @ x + penalty, x.T @ y)
    return design @ weights, weights


def reconstruction_metrics(actual, predicted):
    error = actual - predicted
    axis_rmse = np.sqrt(np.mean(error**2, axis=0))
    return {
        "lateral_right_rmse_m": axis_rmse[0],
        "vertical_headward_rmse_m": axis_rmse[1],
        "forward_nose_proxy_rmse_m": axis_rmse[2],
        "rmse_3d_m": np.sqrt(np.mean(np.sum(error**2, axis=1))),
        "endpoint_error_m": np.linalg.norm(error[-1]),
    }


def plot_fold(trial, phase, actual, predictions, output_path):
    figure, axes = plt.subplots(3, 1, figsize=(7.4, 7.4), sharex=True)
    colors = {"training_mean": "#d07326", "polynomial_ridge": "#176d8a"}
    labels = {
        "training_mean": "training-trial mean",
        "polynomial_ridge": "degree-5 ridge shape",
    }
    for axis_index, axis in enumerate(axes):
        axis.plot(
            phase,
            actual[:, axis_index],
            color="#202733",
            linewidth=2.5,
            label="held-out trial",
        )
        for method, prediction in predictions.items():
            axis.plot(
                phase,
                prediction[:, axis_index],
                color=colors[method],
                linewidth=1.8,
                linestyle="--",
                label=labels[method],
            )
        axis.axhline(0, color="#888888", linewidth=0.7)
        axis.grid(alpha=0.2)
        axis.set_ylabel(f"{AXIS_LABELS[axis_index]}\nΔCoM (m)")
    axes[0].legend(frameon=False, fontsize=8, ncol=3)
    axes[-1].set_xlabel("Normalized phase: onset = 0, apparent contact = 1")
    figure.suptitle(f"A13 reconstruction pilot — held out {trial}", fontsize=12)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def serializable_frame(trial, frame, reported_height_m):
    return {
        "trial": trial,
        "origin_camera_m": frame["origin_camera_m"].tolist(),
        "lateral_right_camera": frame["lateral_right_camera"].tolist(),
        "vertical_headward_camera": frame["vertical_headward_camera"].tolist(),
        "forward_nose_proxy_camera": frame["forward_nose_proxy_camera"].tolist(),
        "basis_determinant": frame["basis_determinant"],
        "nose_alignment": frame["nose_alignment"],
        "standing_window_start_frame0": frame["standing_window_start_frame0"],
        "standing_window_end_frame0": frame["standing_window_end_frame0"],
        "standing_head_to_foot_midpoint_m": frame["standing_head_to_foot_midpoint_m"],
        "reported_height_m": reported_height_m,
        "standing_span_to_reported_height_ratio": frame[
            "standing_head_to_foot_midpoint_m"
        ]
        / reported_height_m,
    }


def build_summary(output_dir, activity, trials, metrics, frames, degree, ridge):
    grouped = defaultdict(list)
    for row in metrics:
        grouped[row["method"]].append(float(row["rmse_3d_m"]))
    method_means = {
        method: float(np.mean(values)) for method, values in grouped.items()
    }
    polynomial_rows = [row for row in metrics if row["method"] == "polynomial_ridge"]
    largest_fold = max(polynomial_rows, key=lambda row: float(row["rmse_3d_m"]))
    duration_mae = float(
        np.mean([float(row["duration_absolute_error_s"]) for row in polynomial_rows])
    )
    span_ratios = [row["standing_span_to_reported_height_ratio"] for row in frames]
    lines = [
        f"# {activity} kinematic reconstruction pilot",
        "",
        "## Outcome",
        "",
        f"Ran {len(trials)} leave-one-trial-out folds. Each fold used the other "
        f"{len(trials) - 1} trials and kept the held-out trial completely unseen.",
        "",
        "| Method | Mean 3D RMSE (m) | Median 3D RMSE (m) |",
        "|---|---:|---:|",
    ]
    for method in ("training_mean", "polynomial_ridge"):
        values = grouped[method]
        lines.append(f"| {method} | {np.mean(values):.4f} | {np.median(values):.4f} |")
    lines.extend(
        [
            "",
            "## Key findings",
            "",
            f"The polynomial model improves mean 3D RMSE over the training mean by only "
            f"{method_means['training_mean'] - method_means['polynomial_ridge']:.4f} m. "
            "Treat the simple training mean as a competitive baseline rather than "
            "claiming a meaningful smoothing advantage.",
            "",
            f"{largest_fold['held_out_trial']} is the largest polynomial reconstruction "
            f"error ({float(largest_fold['rmse_3d_m']):.4f} m) and has a duration error "
            f"of {float(largest_fold['duration_absolute_error_s']):.3f} s. Mean duration "
            f"absolute error across the four folds is {duration_mae:.3f} s. The later "
            "PINN must operate in physical seconds and report timing separately from "
            "phase-normalized shape.",
            "",
            f"The standing head-to-foot-midpoint proxy spans "
            f"{min(span_ratios):.3f}–{max(span_ratios):.3f} of reported stature across "
            "the four trials. This is a frame-orientation check, not a stature estimate.",
            "",
            "## Fixed reconstruction rules",
            "",
            "- Input/output uses a fixed standing-body frame per trial: hip-left to hip-right, foot-midpoint to head, and an orthogonal forward axis oriented toward the nose proxy.",
            "- CoM is the documented female segment-mass proxy. Coordinates are raw input converted to metres; no temporal filter is applied.",
            "- Every onset-to-apparent-contact trajectory is resampled to 101 normalized phase points and expressed as displacement from its onset frame.",
            f"- The polynomial model uses phase powers 1–{degree}, no intercept, and ridge λ={ridge:g}. These settings are fixed for all folds.",
            "- Duration is predicted only as the median duration of the training trials; the model is therefore a trajectory-shape baseline, not a physical-time fall predictor.",
            "",
            "## Interpretation",
            "",
            "This pilot asks whether a simple training-trial template can reconstruct an unseen A13 CoM trajectory after body-frame and phase alignment. It is the benchmark for a later PINN. A PINN must be compared on the same held-out folds and must not use the held-out trajectory to select loss weights or preprocessing.",
            "",
            "The standing-body vertical is not a measured gravity vector, and the origin is not a calibrated floor contact. No forces, torques or perturbations are inferred here.",
            "",
            "## Next PINN step",
            "",
            "Use CoM position as the observed state and obtain velocity/acceleration through automatic differentiation of a smooth network. Begin with a point-mass residual in the standing-body frame. Because external forces and contacts were not measured, any learned forcing term must be labeled an effective residual—not a recovered physical perturbation.",
            "",
            "## Files",
            "",
            "- `fold_metrics.csv`: held-out errors for both fixed baselines.",
            "- `fold_predictions.csv`: actual and predicted trajectories for every fold.",
            "- `subject_frames.json`: per-trial fixed coordinate transforms and stature-span checks.",
            "- `model_parameters.json`: fixed polynomial/ridge settings and fitted fold coefficients.",
            "- `plots/`: held-out trajectory comparisons.",
            "",
        ]
    )
    (output_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def run_pilot(
    run_dir,
    config_path,
    selection_path,
    notes_path,
    output_dir,
    activity="A13",
    points=101,
    degree=5,
    ridge=1e-6,
    standing_radius=2,
):
    run_dir = Path(run_dir)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    config = read_json(config_path)
    selection = read_json(selection_path)
    _, windows = validate_phase_notes(notes_path, run_dir, config, selection)
    windows = [window for window in windows if window["activity"] == activity]
    if len(windows) < 3:
        raise ValueError(
            f"{activity} requires at least three eligible annotated trials"
        )
    output_dir.mkdir(parents=True)
    (output_dir / "plots").mkdir()

    scale = {"mm": 0.001, "m": 1.0}[config["coordinate_units"]]
    segments = segment_model(config["sex"])
    phase = np.linspace(0.0, 1.0, points)
    reported_height_m = float(config["height_in"]) * 0.0254
    trial_data = []
    frame_rows = []

    for window in windows:
        trial = window["trial"]
        pose = np.loadtxt(run_dir / "raw" / f"{trial}.csv", delimiter=",", ndmin=2)
        pose = pose.reshape(len(pose), 32, 3) * scale
        com = com_proxy(pose, segments)[0]
        frame = standing_body_frame(
            pose, window["initial_standing_frame0"], radius=standing_radius
        )
        com_body = to_subject_frame(com, frame)
        onset = window["fall_onset_frame0"]
        contact = window["apparent_contact_frame0"]
        displacement = com_body - com_body[onset]
        aligned = interpolate_trajectory(displacement, onset, contact, phase)
        trial_data.append(
            {
                "trial": trial,
                "trajectory": aligned,
                "duration_s": window["onset_to_apparent_contact_s"],
            }
        )
        frame_rows.append(serializable_frame(trial, frame, reported_height_m))

    metrics = []
    predictions_rows = []
    parameter_rows = []
    for held_out in trial_data:
        training = [item for item in trial_data if item["trial"] != held_out["trial"]]
        training_trajectories = [item["trajectory"] for item in training]
        predictions = {
            "training_mean": np.mean(training_trajectories, axis=0),
        }
        polynomial, weights = fit_ridge_shape(
            training_trajectories, phase, degree, ridge
        )
        predictions["polynomial_ridge"] = polynomial
        predicted_duration = float(np.median([item["duration_s"] for item in training]))
        for method, prediction in predictions.items():
            metrics.append(
                {
                    "held_out_trial": held_out["trial"],
                    "method": method,
                    "training_trials": ";".join(item["trial"] for item in training),
                    "actual_duration_s": held_out["duration_s"],
                    "predicted_duration_s": predicted_duration,
                    "duration_absolute_error_s": abs(
                        held_out["duration_s"] - predicted_duration
                    ),
                    **reconstruction_metrics(held_out["trajectory"], prediction),
                }
            )
        for index, normalized_phase in enumerate(phase):
            row = {
                "held_out_trial": held_out["trial"],
                "normalized_phase": normalized_phase,
            }
            for axis_index, axis in enumerate(AXIS_KEYS):
                row[f"actual_{axis}_m"] = held_out["trajectory"][index, axis_index]
                for method, prediction in predictions.items():
                    row[f"{method}_{axis}_m"] = prediction[index, axis_index]
            predictions_rows.append(row)
        parameter_rows.append(
            {
                "held_out_trial": held_out["trial"],
                "training_trials": [item["trial"] for item in training],
                "degree": degree,
                "ridge_lambda": ridge,
                "powers": list(range(1, degree + 1)),
                "axis_order": list(AXIS_KEYS),
                "weights": weights.tolist(),
            }
        )
        plot_fold(
            held_out["trial"],
            phase,
            held_out["trajectory"],
            predictions,
            output_dir / "plots" / f"{held_out['trial']}_reconstruction.png",
        )

    write_csv(output_dir / "fold_metrics.csv", metrics)
    write_csv(output_dir / "fold_predictions.csv", predictions_rows)
    (output_dir / "subject_frames.json").write_text(
        json.dumps(frame_rows, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "model_parameters.json").write_text(
        json.dumps(
            {
                "activity": activity,
                "coordinate_frame": "fixed standing-body proxy",
                "points": points,
                "degree": degree,
                "ridge_lambda": ridge,
                "standing_median_radius_frames": standing_radius,
                "folds": parameter_rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    build_summary(
        output_dir,
        activity,
        [item["trial"] for item in trial_data],
        metrics,
        frame_rows,
        degree,
        ridge,
    )
    return {
        "activity": activity,
        "trials": [item["trial"] for item in trial_data],
        "folds": len(trial_data),
        "metrics_rows": len(metrics),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--phase-notes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--activity", default="A13")
    parser.add_argument("--points", type=int, default=101)
    parser.add_argument("--degree", type=int, default=5)
    parser.add_argument("--ridge", type=float, default=1e-6)
    parser.add_argument("--standing-radius", type=int, default=2)
    args = parser.parse_args()
    if args.points < 2 or args.degree < 1 or args.ridge < 0 or args.standing_radius < 0:
        parser.error("invalid reconstruction setting")
    result = run_pilot(
        args.run,
        args.config,
        args.selection,
        args.phase_notes,
        args.output,
        args.activity,
        args.points,
        args.degree,
        args.ridge,
        args.standing_radius,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
