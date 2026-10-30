#!/usr/bin/env python3
"""Compare measured S57 CoM trajectories with generated pole-PINN trajectories.

The analysis is deliberately post hoc: it reads the saved inputs and synthetic
``.npy`` files, does not retrain a model, and does not modify the preserved
pole-balancing source. Distribution distances use only the time interval shared
by all measured trials and all synthetic trajectories.
"""

from __future__ import annotations

import csv
import json
import math
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import resampy
from scipy.stats import wasserstein_distance


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "data" / "pole_compatible" / "A11"
SYNTH_DIR = ROOT / "results" / "full_run" / "synthetic_subjectB_PINN"
OUTPUT = ROOT / "results" / "full_run_distribution_comparison"

ORIGINAL_RATE_HZ = 250
PROCESSED_RATE_HZ = 100
START_INDEX_RAW = 1024
FALL_ANGLE_DEG = 20.0
PREFALL_MARGIN_S = 0.08
THETA_SCALE_DEG = 25.0
X_SCALE_CM = 25.0
BOOTSTRAP_REPLICATES = 500
BASELINE_REPLICATES = 200
SEED = 20261019


def read_real_trial(path: Path) -> dict[str, np.ndarray | str]:
    """Reproduce the unchanged pole loader's measured-data preprocessing."""
    data = np.genfromtxt(path, delimiter="\t")
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    if data.shape[1] < 6:
        raise ValueError(f"{path} has fewer than six columns")
    x1, y1, z1, x2, y2, z2 = np.hsplit(data[:, :6], 6)
    length = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2) + 1e-10
    theta_rad = np.arcsin(np.clip((x1 - x2) / length, -1.0, 1.0)).reshape(-1)
    x_mm = x2.reshape(-1)
    theta_rad = theta_rad[START_INDEX_RAW:]
    x_mm = x_mm[START_INDEX_RAW:]
    theta_rad = resampy.resample(theta_rad, sr_orig=ORIGINAL_RATE_HZ, sr_new=PROCESSED_RATE_HZ)
    x_m = resampy.resample(x_mm, sr_orig=ORIGINAL_RATE_HZ, sr_new=PROCESSED_RATE_HZ) * 0.001
    baseline_count = min(len(x_m), int(0.5 * PROCESSED_RATE_HZ))
    x_m = x_m - np.median(x_m[:baseline_count])
    crossings = np.flatnonzero(np.abs(np.degrees(theta_rad)) >= FALL_ANGLE_DEG)
    if len(crossings):
        margin = int(round(PREFALL_MARGIN_S * PROCESSED_RATE_HZ))
        usable_end = max(1, int(crossings[0]) - margin)
        theta_rad = theta_rad[:usable_end]
        x_m = x_m[:usable_end]
    time = np.arange(len(theta_rad), dtype=np.float64) / PROCESSED_RATE_HZ
    return {
        "name": path.stem.replace("SubjectB_", ""),
        "time_s": time,
        "theta_deg": np.degrees(theta_rad),
        "x_cm": 100.0 * x_m,
    }


def load_real_trials() -> list[dict[str, np.ndarray | str]]:
    paths = sorted(INPUT_DIR.glob("SubjectB_*.tsv"))
    if not paths:
        raise FileNotFoundError(f"No measured inputs found in {INPUT_DIR}")
    return [read_real_trial(path) for path in paths]


def load_synthetic() -> tuple[list[Path], np.ndarray]:
    paths = sorted(SYNTH_DIR.glob("synth_B_*.npy"))
    if not paths:
        raise FileNotFoundError(f"No synthetic trajectories found in {SYNTH_DIR}")
    trajectories = np.stack([np.load(path) for path in paths])
    if not np.isfinite(trajectories).all():
        raise ValueError("Synthetic trajectories contain non-finite values")
    return paths, trajectories


def percentile_interval(values: np.ndarray) -> tuple[float, float]:
    low, high = np.percentile(values, [2.5, 97.5])
    return float(low), float(high)


def bootstrap_wasserstein(real: np.ndarray, synthetic: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    distances = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
    for i in range(BOOTSTRAP_REPLICATES):
        real_indices = rng.integers(0, len(real), size=len(real))
        synth_indices = rng.integers(0, len(synthetic), size=len(synthetic))
        distances[i] = wasserstein_distance(real[real_indices].ravel(), synthetic[synth_indices].ravel())
    return distances


def synthetic_split_baseline(synthetic: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    distances = np.empty(BASELINE_REPLICATES, dtype=np.float64)
    half = len(synthetic) // 2
    for i in range(BASELINE_REPLICATES):
        permutation = rng.permutation(len(synthetic))
        distances[i] = wasserstein_distance(
            synthetic[permutation[:half]].ravel(),
            synthetic[permutation[half : 2 * half]].ravel(),
        )
    return distances


def ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(values.ravel())
    y = np.arange(1, len(x) + 1, dtype=np.float64) / len(x)
    return x, y


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_common_lines(time, real_theta, real_x, synth_theta, synth_x, names):
    colors = plt.get_cmap("tab10")(np.linspace(0, 1, len(names)))
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for row in synth_theta[:20]:
        axes[0].plot(time, row, color="#9ECAE1", lw=0.7, alpha=0.22)
    for row in synth_x[:20]:
        axes[1].plot(time, row, color="#9ECAE1", lw=0.7, alpha=0.22)
    for ax, synthetic in zip(axes, (synth_theta, synth_x)):
        q05, median, q95 = np.percentile(synthetic, [5, 50, 95], axis=0)
        ax.fill_between(time, q05, q95, color="#2E86AB", alpha=0.18, label="Synthetic 5-95%")
        ax.plot(time, median, color="#2E86AB", lw=2.2, label="Synthetic median")
    for i, (name, color) in enumerate(zip(names, colors)):
        axes[0].plot(time, real_theta[i], color=color, lw=1.6, label=f"Original {name}")
        axes[1].plot(time, real_x[i], color=color, lw=1.6, label=f"Original {name}")
    axes[0].set_ylabel("CoM angle theta [deg]")
    axes[1].set_ylabel("Forward CoM x [cm]")
    axes[1].set_xlabel("Time from clip start [s]")
    axes[0].set_title("Original and synthetic CoM trajectories on identical time support")
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT / "original_vs_synthetic_com_lines_common_window.png", dpi=220)
    plt.close(fig)


def plot_matched_lines(real_trials, synthetic_paths, trajectories):
    theta0_syn = trajectories[:, 0, 2]
    fig, axes = plt.subplots(len(real_trials), 2, figsize=(13, 3.0 * len(real_trials)), squeeze=False)
    rows = []
    for i, trial in enumerate(real_trials):
        theta_real = np.asarray(trial["theta_deg"])
        x_real = np.asarray(trial["x_cm"])
        time = np.asarray(trial["time_s"])
        match = int(np.argmin(np.abs(theta0_syn - theta_real[0])))
        theta_syn = trajectories[match, : len(time), 2]
        x_syn = 100.0 * trajectories[match, : len(time), 3]
        label = f"Synthetic {synthetic_paths[match].stem} (theta0={theta0_syn[match]:+.2f} deg)"
        axes[i, 0].plot(time, theta_real, color="#111111", lw=1.7, label="Original")
        axes[i, 0].plot(time, theta_syn, color="#D1495B", lw=1.4, label=label)
        axes[i, 1].plot(time, x_real, color="#111111", lw=1.7, label="Original")
        axes[i, 1].plot(time, x_syn, color="#D1495B", lw=1.4, label=label)
        axes[i, 0].set_ylabel("theta [deg]")
        axes[i, 1].set_ylabel("x [cm]")
        axes[i, 0].set_title(str(trial["name"]))
        axes[i, 1].set_title(str(trial["name"]))
        for ax in axes[i]:
            ax.grid(alpha=0.25)
            ax.legend(fontsize=7)
        rows.append(
            {
                "original_trial": trial["name"],
                "matched_synthetic": synthetic_paths[match].name,
                "original_theta0_deg": float(theta_real[0]),
                "synthetic_theta0_deg": float(theta0_syn[match]),
                "theta0_abs_difference_deg": float(abs(theta_real[0] - theta0_syn[match])),
                "theta_rmse_deg": float(np.sqrt(np.mean((theta_syn - theta_real) ** 2))),
                "x_rmse_cm": float(np.sqrt(np.mean((x_syn - x_real) ** 2))),
            }
        )
    axes[-1, 0].set_xlabel("Time [s]")
    axes[-1, 1].set_xlabel("Time [s]")
    fig.suptitle("Original trials vs synthetic trajectories matched only by initial angle")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(OUTPUT / "matched_initial_angle_trajectory_comparison.png", dpi=220)
    plt.close(fig)
    return rows


def plot_wasserstein_time(time, theta_distance, x_distance):
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for ax, values, ylabel, color, distance_label in (
        (axes[0], theta_distance, "W1(theta) [deg]", "#6A4C93", "W1(original theta, synthetic theta)"),
        (axes[1], x_distance, "W1(x) [cm]", "#2A9D8F", "W1(original x, synthetic x)"),
    ):
        ax.plot(time, values, color=color, lw=2.0, label=distance_label)
        ax.axhline(np.mean(values), color="#D1495B", ls="--", lw=1.2, label=f"Time mean = {np.mean(values):.3f}")
        ax.grid(alpha=0.25)
        ax.set_ylabel(ylabel)
        ax.legend()
    axes[0].set_title("Wasserstein-1 distance between original and synthetic distributions over time")
    axes[1].set_xlabel("Time from clip start [s]")
    fig.tight_layout()
    fig.savefig(OUTPUT / "wasserstein_distance_over_time.png", dpi=220)
    plt.close(fig)


def plot_means_and_wasserstein(time, real_theta, real_x, synth_theta, synth_x):
    """Show the two group means beside their time-resolved distribution distance."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex="col")
    for row, (real, synthetic, ylabel, distance_ylabel, color) in enumerate(
        (
            (real_theta, synth_theta, "CoM angle theta [deg]", "W1(theta) [deg]", "#6A4C93"),
            (real_x, synth_x, "Forward CoM x [cm]", "W1(x) [cm]", "#2A9D8F"),
        )
    ):
        real_mean = np.mean(real, axis=0)
        synthetic_mean = np.mean(synthetic, axis=0)
        real_low, real_high = np.min(real, axis=0), np.max(real, axis=0)
        synth_low, synth_high = np.percentile(synthetic, [5, 95], axis=0)
        distance = np.array(
            [wasserstein_distance(real[:, i], synthetic[:, i]) for i in range(len(time))]
        )

        axes[row, 0].fill_between(time, real_low, real_high, color="#555555", alpha=0.12, label="Real range")
        axes[row, 0].fill_between(time, synth_low, synth_high, color="#2E86AB", alpha=0.16, label="Synthetic 5-95%")
        axes[row, 0].plot(time, real_mean, color="#111111", lw=2.2, label="Real mean")
        axes[row, 0].plot(time, synthetic_mean, color="#2E86AB", lw=2.2, label="Synthetic mean")
        axes[row, 0].set_ylabel(ylabel)
        axes[row, 0].grid(alpha=0.25)
        axes[row, 0].legend(fontsize=8)

        axes[row, 1].plot(time, distance, color=color, lw=2.0, label="Real-vs-synthetic W1")
        axes[row, 1].axhline(
            np.mean(distance),
            color="#D1495B",
            ls="--",
            lw=1.4,
            label=f"Time mean = {np.mean(distance):.3f}",
        )
        axes[row, 1].set_ylabel(distance_ylabel)
        axes[row, 1].grid(alpha=0.25)
        axes[row, 1].legend(fontsize=8)
    axes[0, 0].set_title("Real and synthetic means")
    axes[0, 1].set_title("Distribution distance over time")
    axes[1, 0].set_xlabel("Time from clip start [s]")
    axes[1, 1].set_xlabel("Time from clip start [s]")
    fig.suptitle("S57 real vs synthetic CoM means and Wasserstein-1 distances")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUTPUT / "real_vs_synthetic_means_and_wasserstein.png", dpi=220)
    plt.close(fig)


def plot_ecdfs(real_theta, real_x, synth_theta, synth_x):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, real, synthetic, xlabel in (
        (axes[0], real_theta, synth_theta, "CoM angle theta [deg]"),
        (axes[1], real_x, synth_x, "Forward CoM x [cm]"),
    ):
        x_real, y_real = ecdf(real)
        x_synth, y_synth = ecdf(synthetic)
        ax.plot(x_real, y_real, color="#111111", lw=2.0, label="Original pooled")
        ax.plot(x_synth, y_synth, color="#2E86AB", lw=2.0, label="Synthetic pooled")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Empirical cumulative probability")
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("Empirical distributions over the shared measured interval")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUTPUT / "original_vs_synthetic_distribution_ecdf.png", dpi=220)
    plt.close(fig)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    real_trials = load_real_trials()
    synthetic_paths, trajectories = load_synthetic()
    common_samples = min(len(np.asarray(trial["time_s"])) for trial in real_trials)
    time = np.arange(common_samples, dtype=np.float64) / PROCESSED_RATE_HZ

    real_theta = np.stack([np.asarray(trial["theta_deg"])[:common_samples] for trial in real_trials])
    real_x = np.stack([np.asarray(trial["x_cm"])[:common_samples] for trial in real_trials])
    synth_theta = trajectories[:, :common_samples, 2].astype(np.float64)
    synth_x = (100.0 * trajectories[:, :common_samples, 3]).astype(np.float64)

    theta_w1 = float(wasserstein_distance(real_theta.ravel(), synth_theta.ravel()))
    x_w1 = float(wasserstein_distance(real_x.ravel(), synth_x.ravel()))
    theta_over_time = np.array([wasserstein_distance(real_theta[:, i], synth_theta[:, i]) for i in range(common_samples)])
    x_over_time = np.array([wasserstein_distance(real_x[:, i], synth_x[:, i]) for i in range(common_samples)])
    theta_q05, theta_q95 = np.percentile(synth_theta, [5, 95], axis=0)
    x_q05, x_q95 = np.percentile(synth_x, [5, 95], axis=0)
    theta_envelope_coverage = float(np.mean((real_theta >= theta_q05) & (real_theta <= theta_q95)))
    x_envelope_coverage = float(np.mean((real_x >= x_q05) & (real_x <= x_q95)))

    horizon_rows = []
    comparison_end_s = float(time[-1])
    horizon_targets = sorted({min(comparison_end_s, value) for value in (0.25, 0.5, 1.0, 2.0, comparison_end_s)})
    for horizon_s in horizon_targets:
        count = min(common_samples, int(round(horizon_s * PROCESSED_RATE_HZ)) + 1)
        horizon_rows.append(
            {
                "horizon_s": float(time[count - 1]),
                "samples_per_trajectory": count,
                "theta_w1_deg": float(wasserstein_distance(real_theta[:, :count].ravel(), synth_theta[:, :count].ravel())),
                "x_w1_cm": float(wasserstein_distance(real_x[:, :count].ravel(), synth_x[:, :count].ravel())),
            }
        )

    rng = np.random.default_rng(SEED)
    theta_boot = bootstrap_wasserstein(real_theta, synth_theta, rng)
    x_boot = bootstrap_wasserstein(real_x, synth_x, rng)
    theta_boot_ci = percentile_interval(theta_boot)
    x_boot_ci = percentile_interval(x_boot)

    pair_rows = []
    theta_real_pairwise, x_real_pairwise = [], []
    for left, right in combinations(range(len(real_trials)), 2):
        theta_value = float(wasserstein_distance(real_theta[left], real_theta[right]))
        x_value = float(wasserstein_distance(real_x[left], real_x[right]))
        theta_real_pairwise.append(theta_value)
        x_real_pairwise.append(x_value)
        pair_rows.append(
            {
                "trial_a": real_trials[left]["name"],
                "trial_b": real_trials[right]["name"],
                "theta_w1_deg": theta_value,
                "x_w1_cm": x_value,
            }
        )
    theta_synth_split = synthetic_split_baseline(synth_theta, rng)
    x_synth_split = synthetic_split_baseline(synth_x, rng)

    time_rows = [
        {
            "time_s": float(time[i]),
            "original_count": len(real_trials),
            "synthetic_count": len(trajectories),
            "theta_w1_deg": float(theta_over_time[i]),
            "x_w1_cm": float(x_over_time[i]),
        }
        for i in range(common_samples)
    ]
    metric_rows = [
        {
            "variable": "theta",
            "unit": "deg",
            "pooled_w1": theta_w1,
            "bootstrap_ci_2.5": theta_boot_ci[0],
            "bootstrap_ci_97.5": theta_boot_ci[1],
            "time_mean_w1": float(np.mean(theta_over_time)),
            "time_median_w1": float(np.median(theta_over_time)),
            "time_p95_w1": float(np.percentile(theta_over_time, 95)),
            "time_max_w1": float(np.max(theta_over_time)),
            "time_of_max_s": float(time[np.argmax(theta_over_time)]),
            "real_pairwise_median_w1": float(np.median(theta_real_pairwise)),
            "synthetic_split_median_w1": float(np.median(theta_synth_split)),
            "normalization_scale": THETA_SCALE_DEG,
            "normalized_pooled_w1": theta_w1 / THETA_SCALE_DEG,
            "original_points_inside_synthetic_5_95_pct": 100.0 * theta_envelope_coverage,
        },
        {
            "variable": "x",
            "unit": "cm",
            "pooled_w1": x_w1,
            "bootstrap_ci_2.5": x_boot_ci[0],
            "bootstrap_ci_97.5": x_boot_ci[1],
            "time_mean_w1": float(np.mean(x_over_time)),
            "time_median_w1": float(np.median(x_over_time)),
            "time_p95_w1": float(np.percentile(x_over_time, 95)),
            "time_max_w1": float(np.max(x_over_time)),
            "time_of_max_s": float(time[np.argmax(x_over_time)]),
            "real_pairwise_median_w1": float(np.median(x_real_pairwise)),
            "synthetic_split_median_w1": float(np.median(x_synth_split)),
            "normalization_scale": X_SCALE_CM,
            "normalized_pooled_w1": x_w1 / X_SCALE_CM,
            "original_points_inside_synthetic_5_95_pct": 100.0 * x_envelope_coverage,
        },
    ]

    matched_rows = plot_matched_lines(real_trials, synthetic_paths, trajectories)
    plot_common_lines(
        time,
        real_theta,
        real_x,
        synth_theta,
        synth_x,
        [str(trial["name"]) for trial in real_trials],
    )
    plot_wasserstein_time(time, theta_over_time, x_over_time)
    plot_means_and_wasserstein(time, real_theta, real_x, synth_theta, synth_x)
    plot_ecdfs(real_theta, real_x, synth_theta, synth_x)

    write_csv(OUTPUT / "wasserstein_summary.csv", metric_rows)
    write_csv(OUTPUT / "time_resolved_wasserstein.csv", time_rows)
    write_csv(OUTPUT / "real_trial_pairwise_wasserstein.csv", pair_rows)
    write_csv(OUTPUT / "matched_initial_angle_metrics.csv", matched_rows)
    write_csv(OUTPUT / "horizon_sensitivity_wasserstein.csv", horizon_rows)

    combined_normalized = float(np.mean([theta_w1 / THETA_SCALE_DEG, x_w1 / X_SCALE_CM]))
    summary = {
        "method": {
            "metric": "one-dimensional Wasserstein-1 distance",
            "common_time_start_s": 0.0,
            "common_time_end_s": float(time[-1]),
            "common_samples_per_trajectory": int(common_samples),
            "sample_rate_hz": PROCESSED_RATE_HZ,
            "original_trajectories": len(real_trials),
            "synthetic_trajectories": len(trajectories),
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_unit": "whole trajectory",
            "note": "theta and x are evaluated as separate marginal distributions; no joint multivariate Wasserstein claim is made",
        },
        "theta": metric_rows[0],
        "x": metric_rows[1],
        "mean_normalized_marginal_w1": combined_normalized,
        "horizon_sensitivity": horizon_rows,
    }
    (OUTPUT / "distribution_comparison_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    horizon_table = "\n".join(
        f"| 0-{row['horizon_s']:.2f} s | {row['theta_w1_deg']:.3f} deg | {row['x_w1_cm']:.3f} cm |"
        for row in horizon_rows
    )
    trial_names = ", ".join(str(trial["name"]) for trial in real_trials)
    report = f"""# Original vs synthetic S57 CoM distribution comparison

## Comparison design

The analysis compares the {len(real_trials)} original A11 trials ({trial_names}) with all {len(trajectories)} saved synthetic trajectories. Distances use the **0-{time[-1]:.2f} s shared interval**, where every original and synthetic trajectory is available. This prevents unequal real-trial lengths and the unsupported 30-second extrapolation from dominating the result. Because S57's shortest pre-cutoff trial is brief, this shared-window analysis describes only the early trajectory and must be interpreted accordingly.

Wasserstein-1 distance is computed separately for the marginal distributions of CoM angle `theta` and forward CoM position `x`. Its units are directly interpretable: degrees for `theta` and centimeters for `x`. A value of zero would indicate identical empirical distributions. The reported confidence intervals resample complete trajectories, not individual time points.

## Results

| Variable | Pooled W1 | Trajectory-bootstrap 95% CI | Mean time-resolved W1 | Median real-to-real W1 | Median synthetic split-half W1 |
|---|---:|---:|---:|---:|---:|
| theta | {theta_w1:.3f} deg | [{theta_boot_ci[0]:.3f}, {theta_boot_ci[1]:.3f}] | {np.mean(theta_over_time):.3f} deg | {np.median(theta_real_pairwise):.3f} deg | {np.median(theta_synth_split):.3f} deg |
| x | {x_w1:.3f} cm | [{x_boot_ci[0]:.3f}, {x_boot_ci[1]:.3f}] | {np.mean(x_over_time):.3f} cm | {np.median(x_real_pairwise):.3f} cm | {np.median(x_synth_split):.3f} cm |

### Sensitivity to the comparison horizon

| Shared horizon | theta W1 | x W1 |
|---|---:|---:|
{horizon_table}

Relative to the pole code's output scales, the normalized marginal distances are `{theta_w1 / THETA_SCALE_DEG:.4f}` for `theta` and `{x_w1 / X_SCALE_CM:.4f}` for `x`; their descriptive mean is `{combined_normalized:.4f}`. This is **not** a joint multivariate Wasserstein distance.

## Interpretation

The line plots show that the synthetic ensemble overlaps the early low-motion portion of the original trials, but it does not reproduce the rapid trial-specific terminal CoM excursions consistently. Over the common interval, **{100.0 * theta_envelope_coverage:.1f}%** of original theta samples but only **{100.0 * x_envelope_coverage:.1f}%** of original x samples lie inside the synthetic pointwise 5-95% envelope. The low x coverage, despite a moderate W1 distance, indicates an overly narrow synthetic x distribution rather than broad trial-to-trial coverage. The initial-angle-matched plots reinforce that matching `theta(0)` alone is insufficient because the generator fixes initial velocities to zero while the original trials have measured trial-specific initial derivatives.

For context, compare each pooled W1 with the median real-to-real W1 in the table. A pooled value below that baseline means the marginal real-synthetic mismatch is smaller than typical differences among the real trials; a value above it means the mismatch exceeds that within-subject trial variability. The synthetic split-half baseline indicates how much apparent distance arises merely by dividing the generated set in two. The combined mean-and-distance figure makes these comparisons visible without relying on the W1 curve alone.

The distances quantify distributional mismatch, but they should not be treated as population-level validation: there are only {len(real_trials)} original trials from one subject, and the trajectories used to train the model are also being used here for comparison. A held-out trial or additional subjects would be required for generalization claims.

## Reproduce

```bash
python analysis/compare_original_synthetic_distributions.py
```
"""
    (OUTPUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote results to {OUTPUT}")


if __name__ == "__main__":
    main()
