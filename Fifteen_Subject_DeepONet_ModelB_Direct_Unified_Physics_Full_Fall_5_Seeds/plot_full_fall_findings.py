#!/usr/bin/env python3
"""Create subject-level full-fall trajectory/residual summary artifacts."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "full"
INPUT = RESULTS / "multi_seed_subject_metrics.csv"
OUTPUT_CSV = RESULTS / "five_seed_subject_mean_summary.csv"
OUTPUT_FIGURE = RESULTS / "full_fall_physics_residuals_by_subject.png"

METRICS = [
    "normalized_mse",
    "theta_rmse_deg",
    "x_rmse_cm",
    "angular_residual_rmse",
    "horizontal_residual_rmse",
]


def main() -> None:
    frame = pd.read_csv(INPUT)
    subjects = sorted(frame["test_subject"].unique(), key=lambda value: int(value[1:]))
    grouped = frame.groupby("test_subject", sort=False)

    summary = grouped[METRICS].agg(["mean", "std"]).reindex(subjects)
    summary.columns = [f"{metric}_{stat}_across_seeds" for metric, stat in summary.columns]
    summary.insert(0, "subject", summary.index)
    summary.insert(1, "seed_count", grouped.size().reindex(subjects).to_numpy())
    summary.to_csv(OUTPUT_CSV, index=False)

    colors = {"trajectory": "#3B78A4", "angular": "#5A9E6F", "horizontal": "#D9822B"}
    panels = [
        ("normalized_mse", "Normalized forecast MSE", colors["trajectory"]),
        ("angular_residual_rmse", "Angular physics residual RMSE", colors["angular"]),
        ("horizontal_residual_rmse", "Horizontal physics residual RMSE", colors["horizontal"]),
    ]

    fig, axes = plt.subplots(3, 1, figsize=(15, 11), sharex=True, constrained_layout=True)
    x = np.arange(len(subjects))
    for axis, (metric, ylabel, color) in zip(axes, panels):
        values = [frame.loc[frame.test_subject == subject, metric].to_numpy() for subject in subjects]
        boxes = axis.boxplot(
            values,
            positions=x,
            widths=0.62,
            patch_artist=True,
            showmeans=True,
            meanprops={"marker": "o", "markerfacecolor": "white", "markeredgecolor": color, "markersize": 5},
            medianprops={"color": "white", "linewidth": 1.6},
            whiskerprops={"color": color},
            capprops={"color": color},
            flierprops={"marker": "o", "markerfacecolor": color, "markeredgecolor": "white", "markersize": 4},
        )
        for box in boxes["boxes"]:
            box.set_facecolor(color)
            box.set_alpha(0.72)
            box.set_edgecolor(color)
        for index, sample in enumerate(values):
            jitter = np.linspace(-0.10, 0.10, len(sample))
            axis.scatter(x[index] + jitter, sample, s=22, color=color, edgecolor="white", linewidth=0.5, zorder=3)
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.25)

    axes[0].set_title("Five-seed held-out full-fall errors and separated physics residuals by subject")
    axes[-1].set_xticks(x, subjects)
    axes[-1].set_xlabel("Held-out subject (five optimization seeds per box)")
    fig.savefig(OUTPUT_FIGURE, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
