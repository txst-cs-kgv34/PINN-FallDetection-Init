#!/usr/bin/env python3
"""Plot saved synthetic trajectories without loading TensorFlow or retraining."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "results" / "full_run" / "synthetic_subjectB_PINN"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Directory containing synth_B_*.npy")
    parser.add_argument("--horizon", type=float, default=30.0, help="Maximum time shown in seconds")
    parser.add_argument("--count", type=int, default=20, help="Number of individual curves shown")
    parser.add_argument("--output", type=Path, default=None, help="Output PNG path")
    args = parser.parse_args()

    paths = sorted(args.input.glob("synth_B_*.npy"))
    if not paths:
        raise FileNotFoundError(f"No synth_B_*.npy files in {args.input}")
    trajectories = np.stack([np.load(path) for path in paths])
    time = trajectories[0, :, 0]
    keep = time <= args.horizon
    output = args.output or (ROOT / "results" / "full_run_evaluation" / f"synthetic_trajectories_{args.horizon:g}s.png")
    output.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    values = (trajectories[:, :, 2], 100.0 * trajectories[:, :, 3])
    for ax, data, ylabel in zip(axes, values, ("theta [deg]", "x [cm]")):
        for row in data[: min(args.count, len(data))]:
            ax.plot(time[keep], row[keep], color="#7BB6D9", alpha=0.22, lw=0.8)
        q05, median, q95 = np.percentile(data[:, keep], [5, 50, 95], axis=0)
        ax.fill_between(time[keep], q05, q95, color="#2E86AB", alpha=0.2, label="5-95%")
        ax.plot(time[keep], median, color="#2E86AB", lw=2.0, label="Median")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)
        ax.legend()
    axes[0].axhline(20, color="#D1495B", ls="--", lw=1.0)
    axes[0].axhline(-20, color="#D1495B", ls="--", lw=1.0, label="+/-20 deg")
    axes[0].legend()
    axes[1].set_xlabel("Time [s]")
    axes[0].set_title(f"Saved synthetic trajectories (n={len(trajectories)}, shown through {args.horizon:g} s)")
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
