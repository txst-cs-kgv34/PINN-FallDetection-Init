#!/usr/bin/env python3
"""Plot the 100 saved synthetic pole trajectories for S43 and S63.

The script reads the .npy files directly from each subject's full-run output.
It does not copy or modify either subject's data.

Expected .npy columns
---------------------
0: time [s]
1: pole angle theta [rad]
2: pole angle theta [deg]
3: horizontal position x [m]
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
DEFAULT_S43_DIR = (
    WORKSPACE_DIR
    / "S43_Pole_PINN_Human_Motion"
    / "results"
    / "full_run"
    / "synthetic_subjectB_PINN"
)
DEFAULT_S63_DIR = (
    WORKSPACE_DIR
    / "S63_Pole_PINN_Human_Motion"
    / "results"
    / "full_run"
    / "synthetic_subjectB_PINN"
)
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "plots"


@dataclass(frozen=True)
class SubjectTrajectories:
    subject: str
    files: tuple[Path, ...]
    time_s: np.ndarray
    theta_deg: np.ndarray
    x_cm: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot 100 synthetic trajectories for S43 and S63."
    )
    parser.add_argument(
        "--s43-dir",
        type=Path,
        default=DEFAULT_S43_DIR,
        help=f"S43 directory containing synth_B_*.npy (default: {DEFAULT_S43_DIR})",
    )
    parser.add_argument(
        "--s63-dir",
        type=Path,
        default=DEFAULT_S63_DIR,
        help=f"S63 directory containing synth_B_*.npy (default: {DEFAULT_S63_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Plot destination (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=100,
        help="Required number of trajectories for each subject (default: 100).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=220,
        help="PNG resolution (default: 220 DPI).",
    )
    return parser.parse_args()


def _load_one(path: Path) -> np.ndarray:
    array = np.load(path, allow_pickle=False)
    if array.ndim != 2 or array.shape[1] != 4:
        raise ValueError(
            f"{path} has shape {array.shape}; expected [samples, 4] with "
            "[time_s, theta_rad, theta_deg, x_m]."
        )
    if array.shape[0] < 2:
        raise ValueError(f"{path} has fewer than two samples.")
    if not np.isfinite(array).all():
        raise ValueError(f"{path} contains NaN or infinite values.")
    if not np.all(np.diff(array[:, 0]) > 0):
        raise ValueError(f"{path} does not have strictly increasing time values.")
    if not np.allclose(np.degrees(array[:, 1]), array[:, 2], atol=1e-4, rtol=1e-4):
        raise ValueError(f"{path} has inconsistent radian and degree columns.")
    return array.astype(np.float64, copy=False)


def load_subject(subject: str, directory: Path, expected_count: int) -> SubjectTrajectories:
    directory = directory.expanduser().resolve()
    if not directory.is_dir():
        raise FileNotFoundError(
            f"{subject} trajectory directory was not found: {directory}\n"
            "Pass its location with --s43-dir or --s63-dir."
        )

    files = tuple(sorted(directory.glob("synth_B_*.npy")))
    if len(files) != expected_count:
        raise ValueError(
            f"{subject}: found {len(files)} synth_B_*.npy files in {directory}; "
            f"expected {expected_count}."
        )

    arrays = [_load_one(path) for path in files]
    reference_time = arrays[0][:, 0]
    for path, array in zip(files[1:], arrays[1:]):
        if array.shape[0] != reference_time.size or not np.allclose(
            array[:, 0], reference_time, atol=1e-7, rtol=0.0
        ):
            raise ValueError(
                f"{subject}: {path.name} uses a different time grid. "
                "This plotter requires the common grid produced by the pole pipeline."
            )

    theta_deg = np.stack([array[:, 2] for array in arrays])
    x_cm = 100.0 * np.stack([array[:, 3] for array in arrays])
    return SubjectTrajectories(subject, files, reference_time, theta_deg, x_cm)


def _plot_bundle(
    ax: plt.Axes,
    time_s: np.ndarray,
    values: np.ndarray,
    color: str,
    ylabel: str,
    title: str,
) -> None:
    for trajectory in values:
        ax.plot(time_s, trajectory, color=color, alpha=0.20, linewidth=0.65)
    ax.plot(
        time_s,
        values.mean(axis=0),
        color="black",
        linewidth=2.0,
        label="Mean of 100 trajectories",
        zorder=5,
    )
    ax.axhline(0.0, color="#666666", linewidth=0.7, alpha=0.55)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.22)
    ax.legend(loc="best", fontsize=8)


def save_subject_plot(data: SubjectTrajectories, output_dir: Path, dpi: int) -> Path:
    color = "#3569B0" if data.subject == "S43" else "#D2693C"
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
    _plot_bundle(
        axes[0],
        data.time_s,
        data.theta_deg,
        color,
        "Pole angle, theta [deg]",
        f"{data.subject}: 100 synthetic pole-angle trajectories",
    )
    _plot_bundle(
        axes[1],
        data.time_s,
        data.x_cm,
        color,
        "Horizontal position, x [cm]",
        f"{data.subject}: 100 synthetic horizontal-position trajectories",
    )
    axes[1].set_xlabel("Time [s]")
    fig.suptitle(
        f"{data.subject} — 100 synthetic trajectories from the full pole-PINN run",
        fontsize=15,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path = output_dir / f"{data.subject}_100_synthetic_trajectories.png"
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def save_comparison_plot(
    s43: SubjectTrajectories,
    s63: SubjectTrajectories,
    output_dir: Path,
    dpi: int,
) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex="col", sharey="row")
    _plot_bundle(
        axes[0, 0], s43.time_s, s43.theta_deg, "#3569B0", "theta [deg]", "S43 angle"
    )
    _plot_bundle(
        axes[0, 1], s63.time_s, s63.theta_deg, "#D2693C", "theta [deg]", "S63 angle"
    )
    _plot_bundle(
        axes[1, 0], s43.time_s, s43.x_cm, "#3569B0", "x [cm]", "S43 position"
    )
    _plot_bundle(
        axes[1, 1], s63.time_s, s63.x_cm, "#D2693C", "x [cm]", "S63 position"
    )
    axes[1, 0].set_xlabel("Time [s]")
    axes[1, 1].set_xlabel("Time [s]")
    fig.suptitle(
        "S43 and S63 — comparison of 100 synthetic trajectories per subject",
        fontsize=15,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path = output_dir / "S43_vs_S63_100_synthetic_trajectories.png"
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return path


def _summary_rows(data: SubjectTrajectories) -> list[dict[str, float | int | str]]:
    initial_theta = data.theta_deg[:, 0]
    return [
        {
            "subject": data.subject,
            "trajectory_count": len(data.files),
            "samples_per_trajectory": data.time_s.size,
            "duration_s": data.time_s[-1] - data.time_s[0],
            "sample_interval_s": float(np.median(np.diff(data.time_s))),
            "initial_theta_min_deg": initial_theta.min(),
            "initial_theta_max_deg": initial_theta.max(),
            "all_theta_min_deg": data.theta_deg.min(),
            "all_theta_max_deg": data.theta_deg.max(),
            "all_x_min_cm": data.x_cm.min(),
            "all_x_max_cm": data.x_cm.max(),
        }
    ]


def save_summary_csv(
    datasets: Sequence[SubjectTrajectories], output_dir: Path
) -> Path:
    rows = [row for data in datasets for row in _summary_rows(data)]
    path = output_dir / "trajectory_plot_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> None:
    args = parse_args()
    if args.expected_count <= 0:
        raise ValueError("--expected-count must be positive.")
    if args.dpi <= 0:
        raise ValueError("--dpi must be positive.")

    s43 = load_subject("S43", args.s43_dir, args.expected_count)
    s63 = load_subject("S63", args.s63_dir, args.expected_count)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = [
        save_subject_plot(s43, output_dir, args.dpi),
        save_subject_plot(s63, output_dir, args.dpi),
        save_comparison_plot(s43, s63, output_dir, args.dpi),
        save_summary_csv((s43, s63), output_dir),
    ]

    print("Validated 100 S43 and 100 S63 trajectory files.")
    print("Created:")
    for path in outputs:
        print(f"  {path}")


if __name__ == "__main__":
    main()
