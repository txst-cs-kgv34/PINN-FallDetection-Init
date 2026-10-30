#!/usr/bin/env python3
"""Reproduce the full-run checkpoint audit and write tables/figures.

This is a post-run analysis. It does not train or alter the preserved source.
Run from anywhere after ``python runner/run_pipeline.py --mode full``.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "pinn_pole_synthetic_data_generation.py"
INPUTS = ROOT / "data" / "pole_compatible" / "A11"
RUN = ROOT / "results" / "full_run"
OUTPUT = ROOT / "results" / "full_run_evaluation"
RUNTIME_OVERRIDES = ROOT / "config" / "S62_runtime_overrides.json"


def load_pipeline():
    spec = importlib.util.spec_from_file_location("unchanged_pole_pipeline_for_evaluation", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.CFG.data_folder = str(INPUTS)
    module.CFG.output_folder = str(RUN)
    overrides = json.loads(RUNTIME_OVERRIDES.read_text(encoding="utf-8"))
    module.CFG.minimum_trial_seconds = float(overrides["minimum_trial_seconds"])
    return module


def build_model(pipeline, weights: Path):
    model = pipeline.ConditionalPolePINN()
    model(np.zeros((1, 5), dtype=np.float32), training=False)
    model.load_weights(weights)
    return model


def predict(pipeline, model, trial):
    theta, x = pipeline.predict_trial(model, trial)
    return np.asarray(theta), np.asarray(x)


def metric_row(name, theta_true, x_true, theta_pred, x_pred, theta_scale, x_scale):
    theta_error = theta_pred - theta_true
    x_error = x_pred - x_true
    return {
        "trial": name,
        "samples": int(len(theta_true)),
        "normalized_loss": float(
            np.mean((theta_error / theta_scale) ** 2)
            + np.mean((x_error / x_scale) ** 2)
        ),
        "theta_rmse_deg": float(np.degrees(np.sqrt(np.mean(theta_error**2)))),
        "theta_mae_deg": float(np.degrees(np.mean(np.abs(theta_error)))),
        "x_rmse_cm": float(100.0 * np.sqrt(np.mean(x_error**2))),
        "x_mae_cm": float(100.0 * np.mean(np.abs(x_error))),
    }


def evaluate_checkpoints(pipeline, trials):
    models = {
        "stage1_best": build_model(pipeline, RUN / "stage1_best.weights.h5"),
        "stage3_best": build_model(pipeline, RUN / "stage3_best.weights.h5"),
    }
    rows = []
    predictions = {}
    for checkpoint, model in models.items():
        all_theta_true, all_x_true, all_theta_pred, all_x_pred = [], [], [], []
        predictions[checkpoint] = {}
        for trial in trials:
            theta_true = trial.theta[:, 0]
            x_true = trial.x[:, 0]
            theta_pred, x_pred = predict(pipeline, model, trial)
            predictions[checkpoint][trial.name] = (theta_pred, x_pred)
            row = metric_row(
                trial.name,
                theta_true,
                x_true,
                theta_pred,
                x_pred,
                pipeline.CFG.theta_output_scale_rad,
                pipeline.CFG.x_output_scale_m,
            )
            row["checkpoint"] = checkpoint
            rows.append(row)
            all_theta_true.append(theta_true)
            all_x_true.append(x_true)
            all_theta_pred.append(theta_pred)
            all_x_pred.append(x_pred)
        pooled = metric_row(
            "POOLED",
            np.concatenate(all_theta_true),
            np.concatenate(all_x_true),
            np.concatenate(all_theta_pred),
            np.concatenate(all_x_pred),
            pipeline.CFG.theta_output_scale_rad,
            pipeline.CFG.x_output_scale_m,
        )
        pooled["checkpoint"] = checkpoint
        rows.append(pooled)
    return rows, predictions


def load_synthetic():
    paths = sorted((RUN / "synthetic_subjectB_PINN").glob("synth_B_*.npy"))
    if not paths:
        raise FileNotFoundError("No synthetic .npy files found")
    arrays = [np.load(path) for path in paths]
    shapes = {array.shape for array in arrays}
    if len(shapes) != 1:
        raise ValueError(f"Synthetic trajectories have inconsistent shapes: {shapes}")
    return paths, np.stack(arrays)


def synthetic_metrics(paths, trajectories):
    rows = []
    for path, data in zip(paths, trajectories):
        time, _, theta_deg, x_m = data.T
        crossings = np.flatnonzero(np.abs(theta_deg) >= 20.0)
        rows.append(
            {
                "file": path.name,
                "theta0_deg": float(theta_deg[0]),
                "max_abs_theta_deg_0_5s": float(np.max(np.abs(theta_deg[time <= 5.0]))),
                "max_abs_x_m_0_5s": float(np.max(np.abs(x_m[time <= 5.0]))),
                "max_abs_theta_deg_0_30s": float(np.max(np.abs(theta_deg))),
                "max_abs_x_m_0_30s": float(np.max(np.abs(x_m))),
                "first_20deg_crossing_s": float(time[crossings[0]]) if len(crossings) else None,
                "finite": bool(np.isfinite(data).all()),
            }
        )
    return rows


def plot_checkpoint_reconstruction(trials, predictions):
    fig, axes = plt.subplots(len(trials), 2, figsize=(13, 3.0 * len(trials)), squeeze=False)
    colors = {"stage1_best": "#2E86AB", "stage3_best": "#D1495B"}
    labels = {"stage1_best": "Stage 1 best", "stage3_best": "After Stage 3"}
    for i, trial in enumerate(trials):
        t = trial.t[:, 0]
        axes[i, 0].plot(t, np.degrees(trial.theta[:, 0]), color="black", lw=1.5, label="Measured")
        axes[i, 1].plot(t, 100 * trial.x[:, 0], color="black", lw=1.5, label="Measured")
        for checkpoint in ("stage1_best", "stage3_best"):
            theta_pred, x_pred = predictions[checkpoint][trial.name]
            axes[i, 0].plot(t, np.degrees(theta_pred), color=colors[checkpoint], lw=1.15, label=labels[checkpoint])
            axes[i, 1].plot(t, 100 * x_pred, color=colors[checkpoint], lw=1.15, label=labels[checkpoint])
        axes[i, 0].set_ylabel("theta [deg]")
        axes[i, 1].set_ylabel("x [cm]")
        axes[i, 0].set_title(trial.name)
        axes[i, 1].set_title(trial.name)
        for ax in axes[i]:
            ax.grid(alpha=0.25)
    for ax in axes[-1]:
        ax.set_xlabel("Time [s]")
    axes[0, 0].legend(ncol=3, fontsize=8)
    axes[0, 1].legend(ncol=3, fontsize=8)
    fig.suptitle("Measured trajectories and the two saved PINN checkpoints")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(OUTPUT / "checkpoint_reconstruction_comparison.png", dpi=200)
    plt.close(fig)


def plot_metric_comparison(rows):
    pooled = {row["checkpoint"]: row for row in rows if row["trial"] == "POOLED"}
    labels = ["Normalized loss", "theta RMSE [deg]", "x RMSE [cm]"]
    stage1 = [pooled["stage1_best"]["normalized_loss"], pooled["stage1_best"]["theta_rmse_deg"], pooled["stage1_best"]["x_rmse_cm"]]
    stage3 = [pooled["stage3_best"]["normalized_loss"], pooled["stage3_best"]["theta_rmse_deg"], pooled["stage3_best"]["x_rmse_cm"]]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    for ax, label, before, after in zip(axes, labels, stage1, stage3):
        ax.bar(["Stage 1 best", "After Stage 3"], [before, after], color=["#2E86AB", "#D1495B"])
        ax.set_title(label)
        ax.grid(axis="y", alpha=0.25)
        ax.tick_params(axis="x", rotation=15)
        for j, value in enumerate((before, after)):
            ax.text(j, value, f"{value:.4g}", ha="center", va="bottom", fontsize=9)
    fig.suptitle("Full-dataset checkpoint evaluation")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUTPUT / "checkpoint_metric_comparison.png", dpi=200)
    plt.close(fig)


def plot_real_vs_synthetic(trials, trajectories):
    time_syn = trajectories[0, :, 0]
    theta_syn = trajectories[:, :, 2]
    x_syn_cm = 100.0 * trajectories[:, :, 3]
    max_real_time = max(float(trial.t[-1, 0]) for trial in trials)
    keep = time_syn <= max_real_time
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for i in range(min(12, len(trajectories))):
        axes[0].plot(time_syn[keep], theta_syn[i, keep], color="#7BB6D9", alpha=0.32, lw=0.8)
        axes[1].plot(time_syn[keep], x_syn_cm[i, keep], color="#7BB6D9", alpha=0.32, lw=0.8)
    for ax, values in ((axes[0], theta_syn), (axes[1], x_syn_cm)):
        q05, median, q95 = np.percentile(values[:, keep], [5, 50, 95], axis=0)
        ax.fill_between(time_syn[keep], q05, q95, color="#2E86AB", alpha=0.16, label="Synthetic 5-95%")
        ax.plot(time_syn[keep], median, color="#2E86AB", lw=2.0, label="Synthetic median")
    real_colors = ["#000000", "#6A4C93", "#F28E2B", "#2A9D8F"]
    for trial, color in zip(trials, real_colors):
        label = trial.name.replace("SubjectB_", "").replace(".tsv", "")
        axes[0].plot(trial.t[:, 0], np.degrees(trial.theta[:, 0]), color=color, lw=1.5, label=f"Measured {label}")
        axes[1].plot(trial.t[:, 0], 100.0 * trial.x[:, 0], color=color, lw=1.5, label=f"Measured {label}")
    axes[0].axhline(20, color="#D1495B", ls="--", lw=0.9)
    axes[0].axhline(-20, color="#D1495B", ls="--", lw=0.9, label="+/-20 deg threshold")
    axes[0].set_ylabel("theta [deg]")
    axes[1].set_ylabel("x [cm]")
    axes[1].set_xlabel("Time [s]")
    axes[0].set_title("Measured trials vs generated trajectories: common observed-time window")
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT / "real_vs_synthetic_short_horizon.png", dpi=200)
    plt.close(fig)


def plot_synthetic_envelope(trajectories):
    t = trajectories[0, :, 0]
    values = [trajectories[:, :, 2], 100.0 * trajectories[:, :, 3]]
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for ax, data, ylabel in zip(axes, values, ("theta [deg]", "x [cm]")):
        for row in data[:20]:
            ax.plot(t, row, color="#7BB6D9", alpha=0.18, lw=0.65)
        q05, median, q95 = np.percentile(data, [5, 50, 95], axis=0)
        ax.fill_between(t, q05, q95, color="#2E86AB", alpha=0.2, label="5-95%")
        ax.plot(t, median, color="#2E86AB", lw=2.0, label="Median")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)
        ax.legend()
    axes[0].axhline(20, color="#D1495B", ls="--", lw=1.0)
    axes[0].axhline(-20, color="#D1495B", ls="--", lw=1.0, label="+/-20 deg")
    axes[0].legend()
    axes[1].set_xlabel("Time [s]")
    axes[0].set_title("All generated trajectories: 30-second extrapolation envelope")
    fig.tight_layout()
    fig.savefig(OUTPUT / "synthetic_trajectory_envelope_30s.png", dpi=200)
    plt.close(fig)


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pipeline = load_pipeline()
    trials = pipeline.load_trials()
    rows, predictions = evaluate_checkpoints(pipeline, trials)
    paths, trajectories = load_synthetic()
    synthetic_rows = synthetic_metrics(paths, trajectories)

    write_csv(OUTPUT / "reconstruction_metrics.csv", rows)
    write_csv(OUTPUT / "synthetic_trajectory_metrics.csv", synthetic_rows)

    pooled = {row["checkpoint"]: row for row in rows if row["trial"] == "POOLED"}
    ratio = pooled["stage3_best"]["normalized_loss"] / pooled["stage1_best"]["normalized_loss"]
    crossings = [row["first_20deg_crossing_s"] for row in synthetic_rows if row["first_20deg_crossing_s"] is not None]
    summary = {
        "provenance": {
            "source_sha256": sha256(SOURCE),
            "stage1_weights_sha256": sha256(RUN / "stage1_best.weights.h5"),
            "stage3_weights_sha256": sha256(RUN / "stage3_best.weights.h5"),
            "final_weights_sha256": sha256(RUN / "conditional_forward_pinn.weights.h5"),
            "stage3_and_final_weights_identical": sha256(RUN / "stage3_best.weights.h5") == sha256(RUN / "conditional_forward_pinn.weights.h5"),
        },
        "evaluation_samples": int(pooled["stage1_best"]["samples"]),
        "normalization": {
            "theta_scale_rad": float(pipeline.CFG.theta_output_scale_rad),
            "theta_scale_deg": float(math.degrees(pipeline.CFG.theta_output_scale_rad)),
            "x_scale_m": float(pipeline.CFG.x_output_scale_m),
            "formula": "mean(((theta_pred-theta_true)/theta_scale)^2) + mean(((x_pred-x_true)/x_scale)^2)",
        },
        "stage1_best": pooled["stage1_best"],
        "stage3_best": pooled["stage3_best"],
        "stage3_to_stage1_normalized_loss_ratio": float(ratio),
        "synthetic": {
            "count": int(len(trajectories)),
            "samples_per_trajectory": int(trajectories.shape[1]),
            "all_finite": bool(np.isfinite(trajectories).all()),
            "global_theta_deg_min": float(np.min(trajectories[:, :, 2])),
            "global_theta_deg_max": float(np.max(trajectories[:, :, 2])),
            "global_x_m_min": float(np.min(trajectories[:, :, 3])),
            "global_x_m_max": float(np.max(trajectories[:, :, 3])),
            "trajectories_crossing_20deg": int(len(crossings)),
            "first_20deg_crossing_s_min": float(np.min(crossings)) if crossings else None,
            "first_20deg_crossing_s_median": float(np.median(crossings)) if crossings else None,
            "first_20deg_crossing_s_max": float(np.max(crossings)) if crossings else None,
        },
    }
    (OUTPUT / "evaluation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    plot_checkpoint_reconstruction(trials, predictions)
    plot_metric_comparison(rows)
    plot_real_vs_synthetic(trials, trajectories)
    plot_synthetic_envelope(trajectories)

    measured_durations = [float(trial.duration) for trial in trials]
    crossing_summary = (
        f"- {len(crossings)} of {len(trajectories)} trajectories cross |theta| = 20 deg; "
        f"their first crossings occur between {np.min(crossings):.2f} and {np.max(crossings):.2f} s "
        f"(median {np.median(crossings):.2f} s)."
        if crossings
        else f"- None of the {len(trajectories)} trajectories crosses |theta| = 20 deg."
    )
    measured_trial_names = ", ".join(trial.name.replace("SubjectB_", "").replace(".tsv", "") for trial in trials)
    report = f"""# S62 full-run checkpoint and synthetic-trajectory audit

## Checkpoint reconstruction comparison

Both saved checkpoints were evaluated deterministically on the same pooled set of **{summary['evaluation_samples']:,} measured samples** from {measured_trial_names}. The calculation uses the unchanged source's `data_loss` definition:

`mean(((theta_pred-theta_true)/25 deg)^2) + mean(((x_pred-x_true)/0.25 m)^2)`

| Checkpoint | Normalized reconstruction loss | theta RMSE (deg) | x RMSE (cm) |
|---|---:|---:|---:|
| Stage 1 best | {pooled['stage1_best']['normalized_loss']:.9f} | {pooled['stage1_best']['theta_rmse_deg']:.6f} | {pooled['stage1_best']['x_rmse_cm']:.6f} |
| After Stage 3 | {pooled['stage3_best']['normalized_loss']:.9f} | {pooled['stage3_best']['theta_rmse_deg']:.6f} | {pooled['stage3_best']['x_rmse_cm']:.6f} |

The Stage-3-to-Stage-1 normalized-loss ratio is `{pooled['stage3_best']['normalized_loss']:.9f} / {pooled['stage1_best']['normalized_loss']:.9f} = {ratio:.3f}`. Values above 1 mean physics refinement increased reconstruction error; values below 1 mean it reduced it. This checkpoint-level comparison is stronger evidence than comparing stochastic mini-batch losses printed during training.

`stage3_best.weights.h5` and `conditional_forward_pinn.weights.h5` are byte-identical, so the Stage 3 checkpoint is also the final model used to generate the trajectories. SHA-256 provenance is recorded in `evaluation_summary.json`.

## Synthetic trajectories

- {len(trajectories)} files were found; each contains {trajectories.shape[1]} rows over 30 s.
- All saved values are finite.
- Across the complete extrapolation, theta spans {summary['synthetic']['global_theta_deg_min']:.3f} to {summary['synthetic']['global_theta_deg_max']:.3f} deg and x spans {summary['synthetic']['global_x_m_min']:.3f} to {summary['synthetic']['global_x_m_max']:.3f} m.
{crossing_summary}

The short-horizon figure is a qualitative overlay, not a held-out predictive validation: the synthetic curves use randomized initial angles and zero initial velocities, whereas each real trial has its own measured initial conditions. The 30-second envelope is extrapolation far beyond the {min(measured_durations):.2f}-{max(measured_durations):.2f} s measured pre-cutoff windows and must not be interpreted as validated human biomechanics.

## Reproduce

```bash
python analysis/evaluate_full_run.py
python analysis/visualize_trajectories.py --horizon 5
python analysis/visualize_trajectories.py --horizon 30 --count 20
```
"""
    (OUTPUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote evaluation to {OUTPUT}")


if __name__ == "__main__":
    main()
