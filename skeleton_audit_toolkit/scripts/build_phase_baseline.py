"""Build a raw, phase-aligned real-trial baseline before PINN training."""

import argparse
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from foot_geometry import compute_foot_geometry
from phase_annotations import (
    DYNAMICS_PHASE_ORDER,
    PHASE_ORDER,
    read_json,
    validate_phase_notes,
)
from skeleton_model import COLORS, com_proxy, segment_model

AXES = ("camera_x", "camera_y", "camera_z")


def write_csv(path, rows):
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_review_flags(run_dir, trial, frame_count):
    path = Path(run_dir) / "results" / "com" / f"{trial}_com_proxy.csv"
    flags = np.zeros(frame_count, dtype=bool)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            flags[int(row["frame0"])] = row["review_flag"].lower() == "true"
    return flags


def longest_true_run(values):
    longest = current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def interpolate_trajectory(values, start, end, grid):
    source = np.linspace(0.0, 1.0, end - start + 1)
    clipped = values[start : end + 1]
    return np.column_stack(
        [np.interp(grid, source, clipped[:, axis]) for axis in range(clipped.shape[1])]
    )


def plot_activity(activity, description, trajectories, grid, output_path):
    labels = ("Camera X", "Camera Y", "Camera Z")
    figure, axes = plt.subplots(3, 1, figsize=(7.4, 7.5), sharex=True)
    stack = np.stack([item["com_delta"] for item in trajectories])
    mean = stack.mean(axis=0)
    spread = stack.std(axis=0, ddof=1) if len(stack) > 1 else np.zeros_like(mean)
    for axis_index, axis in enumerate(axes):
        for trial_index, item in enumerate(trajectories):
            axis.plot(
                grid,
                item["com_delta"][:, axis_index],
                color=COLORS[trial_index % len(COLORS)],
                alpha=0.65,
                linewidth=1.0,
                label=item["trial"] if axis_index == 0 else None,
            )
        axis.fill_between(
            grid,
            mean[:, axis_index] - spread[:, axis_index],
            mean[:, axis_index] + spread[:, axis_index],
            color="#1d3557",
            alpha=0.14,
            label="mean ± 1 SD" if axis_index == 0 else None,
        )
        axis.plot(grid, mean[:, axis_index], color="#1d3557", linewidth=2.4)
        axis.axhline(0, color="#777777", linewidth=0.7)
        axis.set_ylabel(f"{labels[axis_index]}\nΔCoM (m)")
        axis.grid(alpha=0.2)
    axes[0].legend(ncol=2, fontsize=8, frameon=False)
    axes[-1].set_xlabel("Normalized fall phase: onset = 0, apparent contact = 1")
    figure.suptitle(f"{activity} — {description}: annotated raw trials", fontsize=12)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def build_report(output_dir, config, windows, quality_rows, baseline_rows):
    by_activity = defaultdict(list)
    for row in quality_rows:
        by_activity[row["activity"]].append(row)
    baseline_by_activity = defaultdict(list)
    for row in baseline_rows:
        baseline_by_activity[row["activity"]].append(row)

    activity_summary = []
    for activity in sorted(by_activity):
        rows = by_activity[activity]
        baseline = baseline_by_activity[activity]
        median_burden = float(
            np.median([float(row["screening_burden"]) for row in rows])
        )
        median_rmse = float(
            np.median([float(row["loo_3d_rmse_m"]) for row in baseline])
        )
        activity_summary.append((median_burden, median_rmse, activity, len(rows)))
    recommended = min(activity_summary)[2]
    post_fall_count = sum(row["post_fall_frame0"] is not None for row in windows)
    recommended_count = sum(row["activity"] == recommended for row in windows)

    lines = [
        f"# {config['subject_id']} phase-aligned real-trial baseline",
        "",
        "## Outcome",
        "",
        f"Validated {len(windows)} dynamics-complete raw trials across "
        f"{len(by_activity)} fall types. Each dynamics window runs from the manual "
        "`fall_onset` mark through the manual `apparent_contact` mark, inclusive. "
        f"{post_fall_count} trials also have a post-fall mark; post-fall is optional "
        "for this dynamics-only baseline.",
        "",
        f"**Recommended first modeling family: {recommended} — "
        f"{config['activities'].get(recommended, recommended)}.** This is a data-screening "
        "priority based on the median burden of existing audit flags and exact repeated "
        "transitions among the annotated trials. It is not a biomechanical quality label.",
        "",
        "## Activity summary",
        "",
        "| Activity | Description | Annotated trials | Median onset→contact (s) | Median screening burden | Median leave-one-out 3D RMSE (m) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for burden, rmse, activity, count in activity_summary:
        activity_windows = [row for row in windows if row["activity"] == activity]
        duration = np.median(
            [row["onset_to_apparent_contact_s"] for row in activity_windows]
        )
        lines.append(
            f"| {activity} | {config['activities'].get(activity, '')} | {count} | "
            f"{duration:.3f} | {burden:.3f} | {rmse:.4f} |"
        )
    recommended_baseline = baseline_by_activity[recommended]
    largest_difference = max(
        recommended_baseline, key=lambda row: float(row["loo_3d_rmse_m"])
    )
    duration_by_trial = {
        row["trial"]: row["onset_to_apparent_contact_s"] for row in windows
    }
    lines.extend(
        [
            "",
            "## Recommended-family review",
            "",
            f"{largest_difference['trial']} has the largest leave-one-out difference "
            f"within {recommended}: {float(largest_difference['loo_3d_rmse_m']):.4f} m "
            f"3D RMSE and {duration_by_trial[largest_difference['trial']]:.3f} s from "
            "onset to apparent contact. Retain it as observed variability unless an "
            "independent data-quality reason supports exclusion.",
            "",
            "## What the baseline means",
            "",
            "- Coordinates are the original supplied skeleton coordinates converted to metres. No filter is used.",
            "- CoM is the toolkit's documented sex-specific segment-mass proxy. Each trajectory is expressed as displacement from its own onset frame.",
            "- Phase normalization interpolates each onset-to-apparent-contact window to 101 points. It supports shape comparison but removes absolute duration; durations remain in `phase_windows.csv`.",
            "- The leave-one-out reference for a trial is the mean normalized trajectory of the other annotated trials in the same activity. It is a simple comparison benchmark, not a trained model.",
            "- Screening burden is `review_flag_fraction + exact_repeat_transition_fraction` inside the dynamics window. Its only purpose is transparent prioritization.",
            "",
            "## Scientific limits",
            "",
            "`apparent_contact` is a manual skeleton observation. There are no force plates, contact labels, timestamps, videos or camera/floor calibration, so it must not be described as measured impact. Camera X/Y/Z are not verified world-horizontal/vertical axes. These outputs do not identify joint forces, torques or perturbations.",
            "",
            "## Files",
            "",
            "- `phase_windows.csv`: validated phase frames, nominal times and durations.",
            "- `trial_priority.csv`: within-activity screening ranks for the annotated windows.",
            "- `phase_aligned_com.csv`: 101-point CoM and foot-relative CoM trajectories.",
            "- `leave_one_out_baseline.csv`: reference-only comparison errors.",
            "- `plots/`: real-trial overlays and activity mean ± one standard deviation.",
            "- `phase_validation.json`: annotation provenance and validation result.",
            "",
            "## Next modeling step",
            "",
            f"Start with {recommended} using a pre-specified {recommended_count}-fold "
            "leave-one-trial-out pilot. In each fold, keep the held-out trial entirely "
            "unseen. Fit a kinematic reconstruction baseline first, then introduce a "
            "PINN state model using CoM position/velocity and an explicitly documented "
            "external-perturbation assumption. With so few trials, do not tune filtering, "
            "phase boundaries or loss weights against the held-out results.",
            "",
        ]
    )
    (output_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    return recommended


def build_phase_baseline(
    run_dir, config_path, selection_path, notes_path, output_dir, points=101
):
    run_dir = Path(run_dir)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    config = read_json(config_path)
    selection = read_json(selection_path)
    payload, windows = validate_phase_notes(notes_path, run_dir, config, selection)
    output_dir.mkdir(parents=True)
    (output_dir / "plots").mkdir()
    shutil.copy2(notes_path, output_dir / f"{config['subject_id']}_phase_notes.json")

    unit_scale = {"mm": 0.001, "m": 1.0}[config["coordinate_units"]]
    segments = segment_model(config["sex"])
    grid = np.linspace(0.0, 1.0, points)
    trajectories = []
    quality_rows = []

    for window in windows:
        trial = window["trial"]
        pose = np.loadtxt(run_dir / "raw" / f"{trial}.csv", delimiter=",", ndmin=2)
        pose = pose.reshape(len(pose), 32, 3) * unit_scale
        com = com_proxy(pose, segments)[0]
        geometry = compute_foot_geometry(pose, com)
        onset = window["fall_onset_frame0"]
        contact = window["apparent_contact_frame0"]
        com_delta = interpolate_trajectory(com - com[onset], onset, contact, grid)
        relative = geometry["com_relative_to_foot_midpoint"]
        relative_delta = interpolate_trajectory(
            relative - relative[onset], onset, contact, grid
        )
        trajectories.append(
            {
                "trial": trial,
                "activity": window["activity"],
                "com_delta": com_delta,
                "relative_delta": relative_delta,
            }
        )

        exact_repeat = np.all(pose[1:] == pose[:-1], axis=(1, 2))
        dynamic_repeats = exact_repeat[onset:contact]
        flags = load_review_flags(run_dir, trial, len(pose))
        dynamic_flags = flags[onset + 1 : contact + 1]
        transitions = contact - onset
        repeat_fraction = float(dynamic_repeats.mean()) if transitions else 0.0
        flag_fraction = float(dynamic_flags.mean()) if transitions else 0.0
        quality_rows.append(
            {
                "trial": trial,
                "activity": window["activity"],
                "onset_frame0": onset,
                "apparent_contact_frame0": contact,
                "dynamic_transitions": transitions,
                "duration_s": window["onset_to_apparent_contact_s"],
                "exact_repeat_transitions": int(dynamic_repeats.sum()),
                "exact_repeat_transition_fraction": repeat_fraction,
                "longest_exact_repeat_run_transitions": longest_true_run(
                    dynamic_repeats
                ),
                "review_flagged_transitions": int(dynamic_flags.sum()),
                "review_flag_fraction": flag_fraction,
                "screening_burden": repeat_fraction + flag_fraction,
            }
        )

    for activity in sorted({row["activity"] for row in quality_rows}):
        activity_rows = [row for row in quality_rows if row["activity"] == activity]
        activity_rows.sort(key=lambda row: (row["screening_burden"], row["trial"]))
        for rank, row in enumerate(activity_rows, 1):
            row["within_activity_screening_rank"] = rank
    quality_rows.sort(key=lambda row: row["trial"])

    aligned_rows = []
    for item in trajectories:
        for index, phase in enumerate(grid):
            row = {
                "trial": item["trial"],
                "activity": item["activity"],
                "normalized_phase": phase,
            }
            for axis_index, axis in enumerate(AXES):
                row[f"com_delta_{axis}_m"] = item["com_delta"][index, axis_index]
                row[f"com_relative_foot_midpoint_delta_{axis}_m"] = item[
                    "relative_delta"
                ][index, axis_index]
            aligned_rows.append(row)

    baseline_rows = []
    for item in trajectories:
        peers = [
            other["com_delta"]
            for other in trajectories
            if other["activity"] == item["activity"] and other["trial"] != item["trial"]
        ]
        if not peers:
            continue
        reference = np.stack(peers).mean(axis=0)
        error = item["com_delta"] - reference
        axis_rmse = np.sqrt(np.mean(error**2, axis=0))
        baseline_rows.append(
            {
                "trial": item["trial"],
                "activity": item["activity"],
                "reference_peer_trials": len(peers),
                "loo_camera_x_rmse_m": axis_rmse[0],
                "loo_camera_y_rmse_m": axis_rmse[1],
                "loo_camera_z_rmse_m": axis_rmse[2],
                "loo_3d_rmse_m": np.sqrt(np.mean(np.sum(error**2, axis=1))),
                "loo_apparent_contact_endpoint_error_m": np.linalg.norm(error[-1]),
            }
        )

    for activity in sorted({item["activity"] for item in trajectories}):
        activity_trajectories = [
            item for item in trajectories if item["activity"] == activity
        ]
        plot_activity(
            activity,
            config["activities"].get(activity, activity),
            activity_trajectories,
            grid,
            output_dir / "plots" / f"{activity}_phase_aligned_com.png",
        )

    write_csv(output_dir / "phase_windows.csv", windows)
    write_csv(output_dir / "trial_priority.csv", quality_rows)
    write_csv(output_dir / "phase_aligned_com.csv", aligned_rows)
    write_csv(output_dir / "leave_one_out_baseline.csv", baseline_rows)
    recommended = build_report(output_dir, config, windows, quality_rows, baseline_rows)
    validation = {
        "status": "valid",
        "subject": payload["subject"],
        "nominal_fps": payload["nominal_fps"],
        "annotation_status": "manual provisional skeleton observation",
        "annotated_trials": len(windows),
        "annotations": len(payload["notes"]),
        "required_dynamics_phases": list(DYNAMICS_PHASE_ORDER),
        "optional_context_phases": ["post_fall"],
        "phase_window": "fall_onset through apparent_contact, inclusive",
        "interpolation_points": points,
        "coordinate_source": "raw supplied coordinates converted to metres; no filter",
        "recommended_first_activity": recommended,
        "contact_caution": "apparent_contact is not measured ground contact",
    }
    (output_dir / "phase_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--phase-notes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--points", type=int, default=101)
    args = parser.parse_args()
    if args.points < 2:
        parser.error("--points must be at least 2")
    result = build_phase_baseline(
        args.run,
        args.config,
        args.selection,
        args.phase_notes,
        args.output,
        args.points,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
