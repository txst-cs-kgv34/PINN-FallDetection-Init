"""Render the audit CoM, joint-step, limb-scale and pose evidence figures."""

import re
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skeleton_model import PARENTS, LEFT, RIGHT, COLORS


def make_plots(cfg, data, coms, scales, stats, out):
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fps = cfg["fps"]
    # Every available frame appears in these traces. No time normalization or alignment to inferred onset.
    fig, axes = plt.subplots(
        max(1, len(cfg["activities"])),
        3,
        squeeze=False,
        figsize=(14, max(4, 3 * len(cfg["activities"]))),
        layout="constrained",
    )
    for row, (act, label) in enumerate(cfg["activities"].items()):
        trials = [k for k in data if re.search(r"A\d+", k)[0] == act]
        for trial in trials:
            c = coms[trial]
            delta = c - c[0]
            delta[:, 1] *= -1
            t = np.arange(len(c)) / fps
            for j in range(3):
                axes[row, j].plot(
                    t,
                    delta[:, j],
                    lw=1.5,
                    color=COLORS[
                        (int(re.search(r"T(\d+)", trial)[1]) - 1) % len(COLORS)
                    ],
                    label=trial[-3:],
                )
        for col, title in enumerate(
            ["Camera X displacement", "Camera -Y displacement", "Camera Z displacement"]
        ):
            ax = axes[row, col]
            ax.axhline(0, color="#AAB6BC", lw=0.5)
            ax.grid(alpha=0.2)
            ax.set(
                xlabel="Seconds from clip start (nominal)",
                ylabel="CoM proxy displacement (m)",
            )
            if row == 0:
                ax.set_title(title, pad=30, fontweight="bold")
            if col == 0:
                ax.text(
                    0,
                    1.04,
                    f"{act} {label} ({len(trials)} trials)",
                    transform=ax.transAxes,
                    fontweight="bold",
                )
            ax.legend(ncol=max(1, min(5, len(trials))), fontsize=8, loc="best")
    fig.suptitle(
        f"{cfg['subject_id']} real recordings: segment-mass CoM proxy\nCamera axes only; no floor calibration or synthetic data",
        fontsize=17,
    )
    fig.savefig(out / "real_CoM_comparison.png", dpi=140)
    plt.close(fig)
    fig, axes = plt.subplots(
        max(1, len(cfg["activities"])),
        2,
        squeeze=False,
        figsize=(12, max(4, 2.8 * len(cfg["activities"]))),
        layout="constrained",
    )
    for row, (act, label) in enumerate(cfg["activities"].items()):
        for trial, x in data.items():
            if re.search(r"A\d+", trial)[0] != act:
                continue
            t = np.arange(len(x)) / fps
            color = COLORS[(int(re.search(r"T(\d+)", trial)[1]) - 1) % len(COLORS)]
            axes[row, 0].plot(t, scales[trial], color=color, label=trial[-3:])
            axes[row, 1].plot(
                t[1:],
                np.linalg.norm(np.diff(x, axis=0), axis=2).max(1),
                color=color,
                label=trial[-3:],
            )
        axes[row, 0].set(
            title=f"{act} {label}",
            ylabel="Median limb length / trial median",
            xlabel="Nominal seconds",
        )
        axes[row, 1].set(
            ylabel="Largest adjacent-frame joint step (m)", xlabel="Nominal seconds"
        )
        axes[row, 1].axhline(
            cfg["screening"]["joint_step_m"], color="#555", ls="--", lw=0.7
        )
        for ax in axes[row]:
            ax.grid(alpha=0.2)
            ax.legend(ncol=5, fontsize=8)
    fig.suptitle(
        f"{cfg['subject_id']} tracking diagnostics\nDashed line: configured review threshold, not a physical limit",
        fontsize=16,
    )
    fig.savefig(out / "tracking_diagnostics.png", dpi=130)
    plt.close(fig)
    for act, label in cfg["activities"].items():
        trials = [k for k in data if re.search(r"A\d+", k)[0] == act]
        if not trials:
            continue
        fig, axes = plt.subplots(
            len(trials),
            4,
            figsize=(14, 3.1 * len(trials)),
            squeeze=False,
            layout="constrained",
        )
        for row, trial in enumerate(trials):
            x = data[trial]
            c = coms[trial]
            # Fixed origin for a trial; never center each frame independently.
            offset = x[0, 0]
            q = x - offset
            qc = c - offset
            low = np.array([q[:, :, 0].min(), (-q[:, :, 1]).min()])
            high = np.array([q[:, :, 0].max(), (-q[:, :, 1]).max()])
            middle = (low + high) / 2
            rad = max(high - low) / 2 + 0.10
            for col, k in enumerate(np.linspace(0, len(x) - 1, 4, dtype=int)):
                ax = axes[row, col]
                for j, parent in enumerate(PARENTS):
                    if parent < 0:
                        continue
                    ids = [parent, j]
                    color = (
                        "#176D8A"
                        if j in LEFT
                        else "#D07326" if j in RIGHT else "#354955"
                    )
                    ax.plot(q[k, ids, 0], -q[k, ids, 1], color=color, lw=1.3)
                ax.scatter(qc[k, 0], -qc[k, 1], s=28, color="#BC2543", zorder=5)
                ax.set(
                    xlim=(middle[0] - rad, middle[0] + rad),
                    ylim=(middle[1] - rad, middle[1] + rad),
                    aspect="equal",
                    title=f"{trial[-3:]} · f{k} · {k/fps:.2f} s",
                    xlabel="Camera X (m)",
                    ylabel="Camera -Y (m)",
                )
                ax.grid(alpha=0.15)
        fig.suptitle(
            f"{act} {label}: observed poses and CoM proxy (red)\nFixed trial origin; camera projection only, no inferred floor",
            fontsize=15,
        )
        fig.savefig(out / (act + "_skeleton_snapshots.png"), dpi=120)
        plt.close(fig)
