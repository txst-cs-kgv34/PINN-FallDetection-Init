"""Compare retained Stage-1 inverted-pendulum results across activities."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import write_csv


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mean(rows, key):
    return float(np.mean([float(row[key]) for row in rows]))


def summarize_activity(directory):
    directory = Path(directory)
    config = json.loads((directory / "experiment_config.json").read_text())
    rows = read_csv(directory / "fold_metrics.csv")
    best_weight = float(config["selected_best_nonzero_physics_weight"])
    data_rows = [row for row in rows if float(row["physics_weight"]) == 0.0]
    best_rows = [
        row for row in rows if float(row["physics_weight"]) == best_weight
    ]
    data_rmse = mean(data_rows, "model_xy_rmse_m")
    pinn_rmse = mean(best_rows, "model_xy_rmse_m")
    data_theta = mean(data_rows, "model_theta_rmse_deg")
    pinn_theta = mean(best_rows, "model_theta_rmse_deg")
    data_residual = mean(data_rows, "physics_residual_rms_nm")
    pinn_residual = mean(best_rows, "physics_residual_rms_nm")
    paired_wins = sum(
        float(best["model_xy_rmse_m"]) < float(data["model_xy_rmse_m"])
        for best in best_rows
        for data in data_rows
        if best["held_out_trial"] == data["held_out_trial"]
        and best["seed"] == data["seed"]
    )
    unique_trials = sorted({row["held_out_trial"] for row in rows})
    durations = {
        row["held_out_trial"]: float(row["held_out_duration_s"]) for row in rows
    }
    radius_ranges = {
        row["held_out_trial"]: float(row["actual_radius_range_m"]) for row in rows
    }
    return {
        "subject": config.get("subject", "S43"),
        "activity": config["activity"],
        "horizontal_axis": config.get("horizontal_axis", "lateral"),
        "trials": ";".join(unique_trials),
        "trial_count": len(unique_trials),
        "duration_min_s": min(durations.values()),
        "duration_max_s": max(durations.values()),
        "radius_variation_min_m": min(radius_ranges.values()),
        "radius_variation_max_m": max(radius_ranges.values()),
        "data_only_xy_rmse_m": data_rmse,
        "best_nonzero_physics_weight": best_weight,
        "best_pinn_xy_rmse_m": pinn_rmse,
        "trajectory_change_percent": 100 * (pinn_rmse - data_rmse) / data_rmse,
        "matched_pinn_wins": paired_wins,
        "matched_runs": len(best_rows),
        "data_only_theta_rmse_deg": data_theta,
        "best_pinn_theta_rmse_deg": pinn_theta,
        "theta_change_percent": 100 * (pinn_theta - data_theta) / data_theta,
        "data_only_residual_rms_nm": data_residual,
        "best_pinn_residual_rms_nm": pinn_residual,
        "residual_reduction_percent": 100
        * (data_residual - pinn_residual)
        / data_residual,
        "constant_velocity_xy_rmse_m": mean(rows, "constant_velocity_xy_rmse_m"),
        "uncontrolled_pendulum_xy_rmse_m": mean(
            rows, "uncontrolled_pendulum_xy_rmse_m"
        ),
    }


def plot_accuracy(rows, output_path):
    activities = [row["activity"] for row in rows]
    methods = [
        ("Data-only network", "data_only_xy_rmse_m"),
        ("Best PINN", "best_pinn_xy_rmse_m"),
        ("Constant velocity", "constant_velocity_xy_rmse_m"),
        ("Uncontrolled pendulum", "uncontrolled_pendulum_xy_rmse_m"),
    ]
    x = np.arange(len(activities))
    width = 0.19
    colors = ["#6b7a8f", "#176d8a", "#d07326", "#7a5c9e"]
    figure, axis = plt.subplots(figsize=(8.0, 4.8))
    for index, ((label, key), color) in enumerate(zip(methods, colors)):
        axis.bar(
            x + (index - 1.5) * width,
            [row[key] for row in rows],
            width,
            label=label,
            color=color,
        )
    axis.set_xticks(x, activities)
    axis.set_ylabel("Mean held-out horizontal/vertical CoM RMSE (m)")
    axis.set_title("S43 Stage-1 held-out accuracy by activity")
    axis.grid(axis="y", alpha=0.2)
    axis.legend(frameon=False, fontsize=8, ncol=2)
    figure.tight_layout()
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def build_summary(rows, output_path):
    by_activity = {row["activity"]: row for row in rows}
    lines = [
        "# S43 Stage-1 cross-activity comparison",
        "",
        "## Controlled result",
        "",
        "A11 and A13 used the same Stage-1 architecture, losses, optimizer, physics weights, seeds and whole-trial validation. A11 used anterior-posterior CoM; A13 used medial-lateral CoM.",
        "",
        "| Activity | Data-only RMSE | Best PINN RMSE | PINN trajectory change | Residual reduction | Matched PINN wins |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for activity in sorted(by_activity):
        row = by_activity[activity]
        lines.append(
            f"| {activity} | {row['data_only_xy_rmse_m']:.4f} m | "
            f"{row['best_pinn_xy_rmse_m']:.4f} m | "
            f"{row['trajectory_change_percent']:+.1f}% | "
            f"{row['residual_reduction_percent']:.1f}% | "
            f"{row['matched_pinn_wins']} / {row['matched_runs']} |"
        )
    a11 = by_activity.get("A11")
    a13 = by_activity.get("A13")
    lines.extend(
        [
            "",
            "Positive trajectory change means the PINN was worse than the identical data-only network.",
            "",
            "## Interpretation",
            "",
            "- The best nonzero setting was lambda=0.01 for both activities.",
            "- In both activities, physics substantially reduced the angular-equation residual but did not improve aggregate held-out CoM accuracy.",
        ]
    )
    if a11:
        lines.append(
            f"- A11 was the more stable prediction problem: the data-only network achieved {a11['data_only_xy_rmse_m']:.4f} m and beat both simple controls. Its best PINN was {a11['trajectory_change_percent']:.1f}% worse in CoM RMSE, although angle RMSE changed by {a11['theta_change_percent']:+.1f}%."
        )
    if a13:
        lines.append(
            f"- A13 remained dominated by its long T02 extrapolation fold: the data-only network achieved {a13['data_only_xy_rmse_m']:.4f} m, and the best PINN was {a13['trajectory_change_percent']:.1f}% worse."
        )
    lines.extend(
        [
            "- The repeated pattern across two fall directions strengthens the conclusion that lower residual alone is not evidence of more accurate motion.",
            "- RMSE magnitudes across A11 and A13 are descriptive rather than a formal activity ranking because the modeled horizontal direction, trial windows and individual trajectories differ.",
            "- Both activities show large pivot-to-CoM radius changes, so the rigid constant-length single-link assumption remains violated.",
            "",
            "## Decision",
            "",
            "Retain the Stage-1 inverted-pendulum equation as an interpretable auxiliary constraint and diagnostic, but do not increase its weight or use it yet for synthetic fall generation. The next mechanics experiment should relax the fixed-length/fixed-pivot assumption and be tested against the same data-only controls.",
            "",
        ]
    )
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a11", required=True, type=Path)
    parser.add_argument("--a13", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"output already exists: {args.output}")
    args.output.mkdir(parents=True)
    rows = [summarize_activity(args.a11), summarize_activity(args.a13)]
    rows.sort(key=lambda row: row["activity"])
    write_csv(args.output / "activity_comparison.csv", rows)
    plot_accuracy(rows, args.output / "activity_rmse_comparison.png")
    build_summary(rows, args.output / "SUMMARY.md")
    print(json.dumps({"activities": [row["activity"] for row in rows], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
