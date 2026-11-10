#!/usr/bin/env python3
"""Create side-by-side Physics vs No-Physics boxplots across five seeds."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


METRICS = (
    ("normalized_mse", "Normalized forecast MSE"),
    ("theta_rmse_deg", "Angle RMSE (deg)"),
    ("x_rmse_cm", "CoM displacement RMSE (cm)"),
)
COLORS = {"physics": "#3274A1", "no_physics": "#E1812C"}
LABELS = {"physics": "Model B (Unified Physics)", "no_physics": "Model B (No Physics)"}


def subject_sort_key(subject: str) -> int:
    return int(subject.lstrip("S"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def values_by_subject(
    rows: list[dict[str, str]], subjects: list[str], model: str, metric: str
) -> list[list[float]]:
    output = []
    for subject in subjects:
        selected = sorted(
            (row for row in rows if row["test_subject"] == subject),
            key=lambda row: int(row["seed_index"]),
        )
        if len(selected) != 5:
            raise ValueError(f"{subject} has {len(selected)} rows; expected five seeds")
        output.append([float(row[f"{model}_{metric}"]) for row in selected])
    return output


def draw_boxplots(
    axis,
    positions: np.ndarray,
    values: list[list[float]],
    offset: float,
    color: str,
) -> None:
    boxes = axis.boxplot(
        values,
        positions=positions + offset,
        widths=0.32,
        patch_artist=True,
        showfliers=False,
        whis=1.5,
        boxprops={"facecolor": color, "edgecolor": color, "alpha": 0.70},
        whiskerprops={"color": color, "linewidth": 1.1},
        capprops={"color": color, "linewidth": 1.1},
        medianprops={"color": "white", "linewidth": 1.7},
    )
    for box in boxes["boxes"]:
        box.set_zorder(2)

    seed_offsets = np.linspace(-0.048, 0.048, 5)
    for subject_index, series in enumerate(values):
        axis.scatter(
            positions[subject_index] + offset + seed_offsets,
            series,
            s=27,
            color=color,
            edgecolors="white",
            linewidths=0.45,
            alpha=0.98,
            zorder=3,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("paired_subject_seed_metrics.csv"),
        help="CSV containing 75 paired subject-seed rows",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("physics_vs_no_physics_five_seed_side_by_side_boxplots.png"),
    )
    args = parser.parse_args()

    rows = read_rows(args.input)
    if len(rows) != 75:
        raise ValueError(f"Expected 75 subject-seed rows, found {len(rows)}")
    subjects = sorted({row["test_subject"] for row in rows}, key=subject_sort_key)
    if len(subjects) != 15:
        raise ValueError(f"Expected 15 subjects, found {len(subjects)}")

    positions = np.arange(len(subjects), dtype=float)
    figure, axes = plt.subplots(
        3,
        1,
        figsize=(20, 15),
        sharex=True,
    )
    figure.subplots_adjust(
        left=0.065,
        right=0.992,
        top=0.945,
        bottom=0.075,
        hspace=0.06,
    )

    for axis, (metric, y_label) in zip(axes, METRICS):
        physics = values_by_subject(rows, subjects, "physics", metric)
        no_physics = values_by_subject(rows, subjects, "no_physics", metric)
        draw_boxplots(axis, positions, physics, -0.19, COLORS["physics"])
        draw_boxplots(axis, positions, no_physics, 0.19, COLORS["no_physics"])
        axis.set_ylabel(y_label, fontsize=12)
        axis.grid(axis="y", alpha=0.22)
        axis.set_axisbelow(True)
        axis.margins(x=0.015)

    legend_handles = [
        Patch(facecolor=COLORS["physics"], edgecolor=COLORS["physics"], alpha=0.70, label=LABELS["physics"]),
        Patch(facecolor=COLORS["no_physics"], edgecolor=COLORS["no_physics"], alpha=0.70, label=LABELS["no_physics"]),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#666666",
            markeredgecolor="white",
            markersize=6,
            label="One subject mean from one optimization seed",
        ),
    ]
    axes[0].legend(
        handles=legend_handles,
        loc="upper left",
        ncol=3,
        frameon=False,
        fontsize=11,
    )

    axes[-1].set_xticks(positions, subjects, rotation=0)
    axes[-1].set_xlabel("Held-out subject", fontsize=12, labelpad=9)
    figure.suptitle(
        "Held-out subject errors across five seeds: Unified Physics vs No Physics",
        fontsize=18,
        y=0.982,
    )
    figure.text(
        0.5,
        0.018,
        "Each box contains five matched optimization-seed values. "
        "White line = median; dots = individual seed-specific subject means.",
        ha="center",
        fontsize=10,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=220, bbox_inches="tight")
    plt.close(figure)
    print(args.output.resolve())


if __name__ == "__main__":
    main()

