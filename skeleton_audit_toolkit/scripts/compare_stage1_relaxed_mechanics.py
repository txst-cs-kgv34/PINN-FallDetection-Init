"""Compare the original Stage-1 and Stage-1.5 mechanics ablations."""

import csv
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_phase_baseline import write_csv


ROOT = Path(__file__).resolve().parents[1]
ANALYSES = ROOT / "analyses"
OUTPUT = ANALYSES / "S43_stage1_5_relaxed_mechanics_comparison"


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mean(rows, key):
    return float(np.mean([float(row[key]) for row in rows]))


def select(rows, weight):
    return [row for row in rows if float(row["physics_weight"]) == weight]


def summarize(activity, variant, label, path, original_data_rows):
    rows = read_rows(path)
    weights = sorted({float(row["physics_weight"]) for row in rows})
    data_rows = select(rows, 0.0)
    best_weight = min(
        (weight for weight in weights if weight > 0),
        key=lambda weight: mean(select(rows, weight), "model_xy_rmse_m"),
    )
    best_rows = select(rows, best_weight)
    matched = {
        (row["held_out_trial"], row["seed"]): float(row["model_xy_rmse_m"])
        for row in data_rows
    }
    original = {
        (row["held_out_trial"], row["seed"]): float(row["model_xy_rmse_m"])
        for row in original_data_rows
    }
    matched_wins = sum(
        float(row["model_xy_rmse_m"])
        < matched[(row["held_out_trial"], row["seed"])]
        for row in best_rows
    )
    original_wins = sum(
        float(row["model_xy_rmse_m"])
        < original[(row["held_out_trial"], row["seed"])]
        for row in best_rows
    )
    data_rmse = mean(data_rows, "model_xy_rmse_m")
    original_rmse = mean(original_data_rows, "model_xy_rmse_m")
    best_rmse = mean(best_rows, "model_xy_rmse_m")
    data_residual = mean(data_rows, "physics_residual_rms_nm")
    best_residual = mean(best_rows, "physics_residual_rms_nm")
    return {
        "activity": activity,
        "variant": variant,
        "label": label,
        "best_physics_weight": best_weight,
        "matched_data_only_xy_rmse_m": data_rmse,
        "original_data_only_xy_rmse_m": original_rmse,
        "best_pinn_xy_rmse_m": best_rmse,
        "change_vs_matched_data_only_pct": 100.0 * (best_rmse - data_rmse) / data_rmse,
        "change_vs_original_data_only_pct": 100.0 * (best_rmse - original_rmse) / original_rmse,
        "matched_fold_seed_wins": matched_wins,
        "original_data_only_fold_seed_wins": original_wins,
        "comparisons": len(best_rows),
        "data_only_residual_rms_nm": data_residual,
        "best_pinn_residual_rms_nm": best_residual,
        "residual_reduction_vs_matched_data_only_pct": 100.0 * (data_residual - best_residual) / data_residual,
        "best_pinn_physics_theta_rmse_deg": mean(
            best_rows,
            "model_physics_theta_rmse_deg"
            if "model_physics_theta_rmse_deg" in best_rows[0]
            else "model_theta_rmse_deg",
        ),
        "best_pinn_radius_rmse_m": (
            mean(best_rows, "model_radius_rmse_m")
            if "model_radius_rmse_m" in best_rows[0]
            else mean(best_rows, "rigid_length_rmse_m")
        ),
    }


def plot(rows, output_path):
    activities = ["A11", "A13"]
    labels = [
        "Original data-only",
        "Original fixed-l PINN",
        "Variable-l PINN",
        "Moving-support diagnostic",
    ]
    values = {label: [] for label in labels}
    for activity in activities:
        activity_rows = {row["variant"]: row for row in rows if row["activity"] == activity}
        values[labels[0]].append(activity_rows["fixed_length_fixed_pivot"]["original_data_only_xy_rmse_m"])
        values[labels[1]].append(activity_rows["fixed_length_fixed_pivot"]["best_pinn_xy_rmse_m"])
        values[labels[2]].append(activity_rows["variable_length_fixed_pivot"]["best_pinn_xy_rmse_m"])
        values[labels[3]].append(activity_rows["variable_length_moving_support"]["best_pinn_xy_rmse_m"])
    x = np.arange(len(activities))
    width = 0.19
    colors = ["#6b7a8f", "#176d8a", "#4c956c", "#d07326"]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    for index, label in enumerate(labels):
        ax.bar(
            x + (index - 1.5) * width,
            values[label],
            width,
            label=label,
            color=colors[index],
        )
    ax.set_xticks(x, ["A11 front fall", "A13 right fall"])
    ax.set_ylabel("Mean held-out CoM XY RMSE (m)")
    ax.set_title("Stage-1.5 relaxed mechanics did not beat original data-only")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    rows = []
    for activity in ["A11", "A13"]:
        baseline_path = ANALYSES / f"S43_{activity}_stage1_inverted_pendulum" / "fold_metrics.csv"
        baseline = read_rows(baseline_path)
        original_data_rows = select(baseline, 0.0)
        rows.append(
            summarize(
                activity,
                "fixed_length_fixed_pivot",
                "Original fixed pivot + fixed length",
                baseline_path,
                original_data_rows,
            )
        )
        rows.append(
            summarize(
                activity,
                "variable_length_fixed_pivot",
                "Fixed pivot + predicted l(t)",
                ANALYSES / f"S43_{activity}_stage1_5_variable_length" / "fold_metrics.csv",
                original_data_rows,
            )
        )
        rows.append(
            summarize(
                activity,
                "variable_length_moving_support",
                "Measured moving support + predicted l(t)",
                ANALYSES / f"S43_{activity}_stage1_5_moving_support_variable_length" / "fold_metrics.csv",
                original_data_rows,
            )
        )

    write_csv(OUTPUT / "mechanics_comparison.csv", rows)
    plot(rows, OUTPUT / "mechanics_rmse_comparison.png")
    by_key = {(row["activity"], row["variant"]): row for row in rows}
    lines = [
        "# S43 Stage-1.5 relaxed-mechanics comparison",
        "",
        "## Decision",
        "",
        "Neither predicted time-varying length nor the observed moving-support diagnostic improved on the original data-only network in both activities. Do not replace the current Stage-1 pipeline with either relaxed model, and do not interpret lower equation residual as validated fall prediction.",
        "",
        "| Activity | Model | Best lambda | XY RMSE | Change vs original data-only | Residual reduction vs matched data-only |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for activity in ["A11", "A13"]:
        for variant in [
            "fixed_length_fixed_pivot",
            "variable_length_fixed_pivot",
            "variable_length_moving_support",
        ]:
            row = by_key[(activity, variant)]
            lines.append(
                f"| {activity} | {row['label']} | {row['best_physics_weight']:g} | {row['best_pinn_xy_rmse_m']:.4f} m | {row['change_vs_original_data_only_pct']:+.1f}% | {row['residual_reduction_vs_matched_data_only_pct']:.1f}% |"
            )
    lines.extend(
        [
            "",
            "Original data-only RMSE was 0.2430 m for A11 and 0.4121 m for A13.",
            "",
            "## Interpretation",
            "",
            "- Fixed pivot plus predicted `l(t)` slightly improved the A11 PINN from 0.2520 to 0.2500 m, but remained 2.9% worse than data-only. For A13 it worsened the PINN from 0.4467 to 0.4857 m and remained dominated by the long T02 extrapolation.",
            "- The measured moving-support diagnostic did not improve A11 and produced 0.3176 m RMSE. For A13 it improved strongly relative to its own poorly generalizing moving-coordinate data-only model, but its 0.4955 m RMSE was still 20.2% worse than the original data-only network.",
            "- A13 support displacement ranged from 0.048 to 0.499 m, with the largest movement in the difficult T02 trial. This confirms that support motion is real, but a raw FOOT midpoint is not a sufficiently stable support-state representation.",
            "- Variable length corrected one violated assumption, but the effective-torque branch and single-link planar model still absorb articulation, contact, out-of-plane motion, and measurement error.",
            "",
            "## Recommendation before Stage 2",
            "",
            "Close Stage 1.5 as a negative ablation and proceed to the framework's Stage-2 parameter-recovery benchmark in simulation. Generate trajectories with known `Kp`, `Kd`, response delay, torque limit, damping, and perturbation input; freeze the simulated plant; then test whether inverse optimization recovers those known values under noise. Do not first interpret controller gains inferred from S43 falls as physiological quantities, because force, CoP, contact state, and perturbation input remain unavailable.",
            "",
            "The S43 Stage-1 models can still be retained as descriptive trajectory and residual diagnostics. If moving support is revisited later, use measured CoP/contact data or a separately validated support-state model rather than the observed FOOT midpoint as an inference-time input.",
            "",
        ]
    )
    (OUTPUT / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
