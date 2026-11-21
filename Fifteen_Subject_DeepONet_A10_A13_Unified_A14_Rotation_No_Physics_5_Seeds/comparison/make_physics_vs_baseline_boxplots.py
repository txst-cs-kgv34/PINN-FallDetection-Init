#!/usr/bin/env python3
"""Create the paired subject-level physics versus no-physics comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon


REGIMES = ("No physics", "Physics")
COLORS = {"No physics": "#A7A9AC", "Physics": "#2F6B9A"}
GROUP_METRICS = {
    "planar": [
        "normalized_mse",
        "theta_rmse_deg",
        "theta_mae_deg",
        "x_rmse_cm",
        "x_mae_cm",
        "theta_w1_deg",
        "x_w1_cm",
        "angular_residual_rmse",
        "horizontal_residual_rmse",
    ],
    "rotation": [
        "normalized_mse",
        "theta_rmse_deg",
        "theta_mae_deg",
        "x_rmse_cm",
        "x_mae_cm",
        "theta_w1_deg",
        "x_w1_cm",
        "yaw_rmse_deg",
        "yaw_mae_deg",
        "yaw_w1_deg",
        "angular_residual_rmse",
        "horizontal_residual_rmse",
        "yaw_residual_rmse",
    ],
}
LABELS = {
    "normalized_mse": "Normalized MSE",
    "theta_rmse_deg": r"$\theta$ RMSE (deg)",
    "theta_mae_deg": r"$\theta$ MAE (deg)",
    "x_rmse_cm": "x RMSE (cm)",
    "x_mae_cm": "x MAE (cm)",
    "theta_w1_deg": r"$\theta$ W1 (deg)",
    "x_w1_cm": "x W1 (cm)",
    "yaw_rmse_deg": "Yaw RMSE (deg)",
    "yaw_mae_deg": "Yaw MAE (deg)",
    "yaw_w1_deg": "Yaw W1 (deg)",
    "angular_residual_rmse": "Angular residual RMSE",
    "horizontal_residual_rmse": "Horizontal residual RMSE",
    "yaw_residual_rmse": "Yaw residual RMSE",
}
PRIMARY_METRICS = {
    "planar": [
        "normalized_mse",
        "theta_rmse_deg",
        "x_rmse_cm",
        "angular_residual_rmse",
        "horizontal_residual_rmse",
    ],
    "rotation": [
        "normalized_mse",
        "theta_rmse_deg",
        "x_rmse_cm",
        "yaw_rmse_deg",
        "angular_residual_rmse",
        "horizontal_residual_rmse",
        "yaw_residual_rmse",
    ],
}
PANELS = [
    ("planar", "normalized_mse", False),
    ("planar", "theta_rmse_deg", False),
    ("planar", "x_rmse_cm", False),
    ("planar", "x_w1_cm", False),
    ("rotation", "normalized_mse", False),
    ("rotation", "theta_rmse_deg", False),
    ("rotation", "x_rmse_cm", False),
    ("rotation", "yaw_rmse_deg", False),
    ("planar", "angular_residual_rmse", True),
    ("planar", "horizontal_residual_rmse", True),
    ("rotation", "horizontal_residual_rmse", True),
    ("rotation", "yaw_residual_rmse", True),
]


def holm_adjust(p_values: list[float]) -> list[float]:
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = (len(p_values) - rank) * float(p_values[index])
        running = max(running, candidate)
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def read_subject_means(root: Path, group: str) -> pd.DataFrame:
    path = root / "results" / group / "full" / "multi_seed_subject_metrics.csv"
    frame = pd.read_csv(path)
    metrics = GROUP_METRICS[group]
    missing = sorted(set(metrics) - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing {missing}")
    return frame.groupby("test_subject", as_index=True)[metrics].mean().sort_index()


def analyze(physics_root: Path, baseline_root: Path):
    subject_frames: dict[tuple[str, str], pd.DataFrame] = {}
    summary_rows: list[dict] = []
    test_rows: list[dict] = []
    long_rows: list[dict] = []
    for group in ("planar", "rotation"):
        physics = read_subject_means(physics_root, group)
        baseline = read_subject_means(baseline_root, group)
        if not physics.index.equals(baseline.index):
            raise ValueError(f"{group}: physics and baseline subjects differ")
        subject_frames[(group, "Physics")] = physics
        subject_frames[(group, "No physics")] = baseline
        for regime, frame in (("No physics", baseline), ("Physics", physics)):
            for subject, row in frame.iterrows():
                long_rows.append(
                    {"model_group": group, "subject": subject, "regime": regime, **row.to_dict()}
                )
        group_tests = []
        for metric in GROUP_METRICS[group]:
            delta = physics[metric] - baseline[metric]
            if np.allclose(delta.to_numpy(), 0.0):
                statistic, p_value = 0.0, 1.0
            else:
                test = wilcoxon(physics[metric], baseline[metric], alternative="two-sided")
                statistic, p_value = float(test.statistic), float(test.pvalue)
            baseline_mean = float(baseline[metric].mean())
            physics_mean = float(physics[metric].mean())
            summary_rows.append(
                {
                    "model_group": group,
                    "metric": metric,
                    "subject_count": len(physics),
                    "baseline_mean": baseline_mean,
                    "physics_mean": physics_mean,
                    "physics_minus_baseline": physics_mean - baseline_mean,
                    "physics_percent_change": 100.0 * (physics_mean - baseline_mean) / baseline_mean,
                    "physics_lower_error_subject_fraction": float((delta < 0).mean()),
                }
            )
            group_tests.append(
                {
                    "model_group": group,
                    "metric": metric,
                    "subject_count": len(physics),
                    "wilcoxon_statistic": statistic,
                    "raw_p_value": p_value,
                }
            )
        adjusted = holm_adjust([row["raw_p_value"] for row in group_tests])
        for row, value in zip(group_tests, adjusted):
            row["holm_adjusted_p_value_within_group"] = value
            row["significant_at_0.05"] = value < 0.05
            test_rows.append(row)
    return subject_frames, pd.DataFrame(summary_rows), pd.DataFrame(test_rows), pd.DataFrame(long_rows)


def plot_boxplots(subject_frames, summary: pd.DataFrame, destination: Path) -> None:
    fig, axes = plt.subplots(3, 4, figsize=(17.0, 13.0))
    for axis, (group, metric, log_scale) in zip(axes.flat, PANELS):
        baseline = subject_frames[(group, "No physics")][metric]
        physics = subject_frames[(group, "Physics")][metric]
        values = [baseline.to_numpy(), physics.to_numpy()]
        boxes = axis.boxplot(
            values,
            positions=[0, 1],
            widths=0.55,
            patch_artist=True,
            showfliers=False,
            medianprops={"color": "#111111", "linewidth": 1.8},
            whiskerprops={"linewidth": 1.2},
            capprops={"linewidth": 1.2},
        )
        for patch, regime in zip(boxes["boxes"], REGIMES):
            patch.set_facecolor(COLORS[regime])
            patch.set_alpha(0.72)
        offsets = np.linspace(-0.045, 0.045, len(baseline))
        for offset, base_value, physics_value in zip(offsets, baseline, physics):
            axis.plot(
                [0 + offset, 1 + offset],
                [base_value, physics_value],
                color="#777777",
                alpha=0.28,
                linewidth=0.75,
                zorder=1,
            )
        axis.scatter(offsets, baseline, s=19, color=COLORS["No physics"], edgecolor="white", linewidth=0.35, zorder=2)
        axis.scatter(1 + offsets, physics, s=19, color=COLORS["Physics"], edgecolor="white", linewidth=0.35, zorder=2)
        axis.set_xticks([0, 1], REGIMES)
        axis.set_ylabel(LABELS[metric])
        axis.set_title(("A10–A13 unified" if group == "planar" else "A14 rotation") + " — " + LABELS[metric])
        axis.grid(axis="y", alpha=0.22)
        if log_scale:
            axis.set_yscale("log")
        row = summary[(summary.model_group == group) & (summary.metric == metric)].iloc[0]
        change = float(row.physics_percent_change)
        axis.text(
            0.98,
            0.97,
            f"Physics change: {change:+.1f}%",
            transform=axis.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            color="#247A3D" if change < 0 else "#A23B3B",
            bbox={"boxstyle": "round,pad=0.24", "facecolor": "white", "edgecolor": "#DDDDDD", "alpha": 0.9},
        )
    fig.suptitle(
        "Physics-informed vs no-physics DeepONet: held-out-subject comparison",
        fontsize=18,
        fontweight="bold",
        y=0.995,
    )
    fig.text(
        0.5,
        0.958,
        "Each paired point is one held-out subject averaged across five optimization seeds; lower is better. Residual panels use log scale.",
        ha="center",
        fontsize=11,
        color="#444444",
    )
    fig.tight_layout(rect=[0.015, 0.02, 0.995, 0.925])
    fig.savefig(destination, dpi=220, bbox_inches="tight")
    plt.close(fig)


def format_p(value: float) -> str:
    return f"{value:.3g}" if value < 0.001 else f"{value:.4f}"


def write_report(output_dir: Path, summary: pd.DataFrame, tests: pd.DataFrame) -> None:
    primary = summary.merge(
        tests[["model_group", "metric", "holm_adjusted_p_value_within_group"]],
        on=["model_group", "metric"],
    )
    lines = [
        "# Physics versus no-physics comparison",
        "",
        "Both conditions completed 25 planar and 25 rotation fold/seed models. The comparison uses the same held-out subjects and first averages the five optimization seeds within each subject. Lower values are better for every reported metric.",
        "",
        "## Primary subject-level results",
        "",
        "| Model | Metric | No physics | Physics | Physics change | Physics lower-error subjects | Holm-adjusted p |",
        "|:--|:--|--:|--:|--:|--:|--:|",
    ]
    for group in ("planar", "rotation"):
        for metric in PRIMARY_METRICS[group]:
            row = primary[(primary.model_group == group) & (primary.metric == metric)].iloc[0]
            lines.append(
                f"| {'A10–A13' if group == 'planar' else 'A14'} | {LABELS[metric]} | "
                f"{row.baseline_mean:.3f} | {row.physics_mean:.3f} | {row.physics_percent_change:+.1f}% | "
                f"{100 * row.physics_lower_error_subject_fraction:.1f}% | {format_p(row.holm_adjusted_p_value_within_group)} |"
            )
    lines += [
        "",
        "## Interpretation",
        "",
        "- **A10–A13:** physics reduced the angular residual by 12.3% and the horizontal residual by 97.2%, but forecast errors increased: normalized MSE by 13.7%, theta RMSE by 9.6%, and x RMSE by 9.4%. The trajectory-error differences remain significant after within-group Holm correction.",
        "- **A14:** physics reduced mean normalized MSE by 10.1%, theta RMSE by 3.0%, x RMSE by 4.3%, and yaw RMSE by 5.9%. These trajectory improvements were not significant after subject-level Holm correction and were not uniform across subjects.",
        "- **A14 dynamics:** the horizontal residual fell by 85.5% and remained significant after correction; angular and yaw residuals also decreased descriptively.",
        "- The result supports physics as a strong dynamics regularizer, but not as a universal trajectory-accuracy improvement at the current fixed weight of 0.01. For A10–A13, the no-physics model is the preferred forecasting model. For A14, the physics model is promising for rotation/yaw modeling, but the gain should be confirmed with a physics-weight ablation.",
        "- Baseline controller gains are not identified by a physics loss, so its residuals are diagnostics of an unconstrained pathway rather than interpretable recovered controller parameters.",
        "",
        "## Statistical unit",
        "",
        "The paired Wilcoxon tests use one value per held-out subject after averaging the five seeds (15 subjects for A10–A13 and 13 eligible subjects for A14). Holm correction is applied separately across all reported metrics within each model group. This avoids treating repeated seeds as independent subjects.",
        "",
        "See `physics_vs_no_physics_subject_boxplots.png`, `physics_vs_no_physics_summary.csv`, `paired_subject_wilcoxon_holm.csv`, and `subject_seed_averaged_metrics.csv` in this directory.",
    ]
    (output_dir / "COMPARISON.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physics-root", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    physics_root = args.physics_root.expanduser().resolve()
    baseline_root = args.baseline_root.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    subject_frames, summary, tests, long_metrics = analyze(physics_root, baseline_root)
    summary.to_csv(output_dir / "physics_vs_no_physics_summary.csv", index=False)
    tests.to_csv(output_dir / "paired_subject_wilcoxon_holm.csv", index=False)
    long_metrics.to_csv(output_dir / "subject_seed_averaged_metrics.csv", index=False)
    plot_boxplots(subject_frames, summary, output_dir / "physics_vs_no_physics_subject_boxplots.png")
    write_report(output_dir, summary, tests)
    metadata = {
        "pairing": "same held-out subject and model group; five seeds averaged within subject",
        "planar_subject_count": len(subject_frames[("planar", "Physics")]),
        "rotation_subject_count": len(subject_frames[("rotation", "Physics")]),
        "lower_is_better": True,
        "holm_family": "all metrics within each model group",
        "physics_root_name": physics_root.name,
        "baseline_root_name": baseline_root.name,
    }
    (output_dir / "comparison_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote paired comparison to {output_dir}")


if __name__ == "__main__":
    main()
