"""Audit exact consecutive repeats and shared limb scaling; no data repair."""

from pathlib import Path
import json
import argparse
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skeleton_model import LIMBS
from audit_data import dump, write_csv


def repeat_runs(a):
    """Inclusive frame ranges for constant runs of at least two identical rows."""
    boundaries = np.r_[0, np.flatnonzero(np.any(a[1:] != a[:-1], axis=1)) + 1, len(a)]
    return [
        (int(start), int(end - 1))
        for start, end in zip(boundaries[:-1], boundaries[1:])
        if end - start >= 2
    ]


def audit_temporal(run):
    cfg = json.loads((run / "config.json").read_text())
    fps = cfg["fps"]
    trials = sorted(
        (
            r
            for r in json.loads((run / "results/trial_summary.json").read_text())
            if r["frames"]
        ),
        key=lambda r: r["trial"],
    )
    rows = []
    events = []
    normalized = {}
    for r in trials:
        trial = r["trial"]
        a = np.loadtxt(run / "raw" / (trial + ".csv"), delimiter=",", ndmin=2)
        x = a.reshape(-1, 32, 3) * {"mm": 0.001, "m": 1}[cfg["coordinate_units"]]
        runs = repeat_runs(a)
        adj = sum(end - start for start, end in runs)
        lengths = np.stack(
            [np.linalg.norm(x[:, i] - x[:, j], axis=1) for i, j in LIMBS.values()],
            axis=1,
        )
        normalized[trial] = lengths / np.median(lengths, axis=0)
        longest = max(runs, key=lambda v: v[1] - v[0], default=None)
        rows.append(
            {
                "trial": trial,
                "frames": len(a),
                "distinct_rows": len(np.unique(a, axis=0)),
                "adjacent_repeat_transitions": adj,
                "repeat_transition_percent": 100 * adj / (len(a) - 1),
                "longest_constant_run_frames": (
                    longest[1] - longest[0] + 1 if longest else 1
                ),
                "longest_constant_run_span_s": (
                    (longest[1] - longest[0]) / fps if longest else 0
                ),
                "longest_run_start_frame0": longest[0] if longest else None,
                "longest_run_end_frame0": longest[1] if longest else None,
                "max_normalized_limb_spread": float(
                    np.ptp(normalized[trial], axis=1).max()
                ),
            }
        )
        for start, end in runs:
            events.append(
                {
                    "trial": trial,
                    "start_frame0": start,
                    "end_frame0": end,
                    "frames": end - start + 1,
                    "nominal_span_s": (end - start) / fps,
                }
            )
    dump(run / "results/temporal_summary.json", rows)
    write_csv(run / "results/temporal_summary.csv", rows)
    dump(run / "results/constant_pose_runs.json", events)
    write_csv(run / "results/constant_pose_runs.csv", events)
    if not rows:
        return
    fig, axes = plt.subplots(
        1, 2, figsize=(13, max(5, len(rows) * 0.27)), layout="constrained"
    )
    y = np.arange(len(rows))
    axes[0].barh(y, [r["repeat_transition_percent"] for r in rows], color="#176D8A")
    axes[1].barh(y, [r["longest_constant_run_span_s"] for r in rows], color="#D07326")
    for ax in axes:
        ax.set_yticks(y, [r["trial"] for r in rows])
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.2)
    axes[0].set_xlabel("Exactly repeated adjacent transitions (%)")
    axes[1].set_xlabel("Longest constant-pose span (nominal s)")
    fig.suptitle(
        cfg["subject_id"]
        + " temporal audit: identical exported coordinates, cause unconfirmed"
    )
    fig.savefig(run / "results/plots/temporal_repeats.png", dpi=140)
    plt.close(fig)
    # Select extremes by explicit metrics; deterministic and reusable for other subjects.
    selected = list(
        dict.fromkeys(
            [
                max(rows, key=lambda r: r["longest_constant_run_span_s"])["trial"],
                max(trials, key=lambda r: r["limb_scale_range_pct"])["trial"],
            ]
        )
    )
    fig, axes = plt.subplots(
        len(selected),
        1,
        squeeze=False,
        figsize=(12, 3.4 * len(selected)),
        layout="constrained",
    )
    for ax, trial in zip(axes[:, 0], selected):
        ratio = normalized[trial]
        t = np.arange(len(ratio)) / fps
        for j, name in enumerate(LIMBS):
            ax.plot(
                t,
                ratio[:, j],
                label=name,
                lw=1,
                alpha=0.7,
                ls=["-", "--", ":", "-."][j % 4],
            )
        ax.set(
            title=trial, xlabel="Nominal seconds", ylabel="Limb length / trial median"
        )
        ax.legend(ncol=4, fontsize=8)
        ax.grid(alpha=0.2)
    fig.suptitle(
        "Shared limb-scale variation: eight traces overlap when scaling is common"
    )
    fig.savefig(run / "results/plots/shared_limb_scaling.png", dpi=140)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    audit_temporal(p.parse_args().run)


if __name__ == "__main__":
    main()
