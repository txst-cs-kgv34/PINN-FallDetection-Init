#!/usr/bin/env python3
"""Run controlled Stage-3 gain experiments for one subject's A11 data.

The preserved pole-PINN source is imported without modification.  Every chunk:

* starts from the same saved Stage-1 checkpoint;
* fixes Pi and tau;
* manually assigns Kp/Kd for theta and x;
* runs the original Stage-3 training function independently;
* predicts each real trial from that trial's measured initial conditions; and
* reports paired reconstruction MSE and real-vs-synthetic distribution metrics.

Chunks 1-10 linearly interpolate between the current subject's controller
identified in its clean completed run and the Subject-B paper reference.
Chunk 11 is the exact
Subject-A paper Kp/Kd set.  Pi and tau remain fixed for every chunk so that only
the four controller gains change.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import random
import re
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from scipy.stats import wasserstein_distance


ROOT = Path(__file__).resolve().parents[2]
SUBJECT_MATCH = re.match(r"^(S\d+)_Pole_PINN_Human_Motion$", ROOT.name)
if SUBJECT_MATCH is None:
    raise RuntimeError(f"Cannot infer subject ID from project directory: {ROOT.name}")
SUBJECT_ID = SUBJECT_MATCH.group(1)
SOURCE = ROOT / "source" / "pinn_pole_synthetic_data_generation.py"
INPUTS = ROOT / "data" / "pole_compatible" / "A11"
SCOPE = ROOT / "config" / f"{SUBJECT_ID}_A11_experiment_scope.json"
RUNTIME_OVERRIDES = ROOT / "config" / f"{SUBJECT_ID}_runtime_overrides.json"
FULL_RUN = ROOT / "results" / "full_run"
STAGE1_WEIGHTS = FULL_RUN / "stage1_best.weights.h5"
IDENTIFIED_PARAMETERS = FULL_RUN / "identified_parameters.json"
FULL_RUN_MODE = FULL_RUN / "run_mode.json"
FULL_RUN_MODEL = FULL_RUN / "conditional_forward_pinn.weights.h5"
FULL_RUN_CONFIGURATION = FULL_RUN / "configuration.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results"

SEED = 1234
SUBJECT_B_PAPER_GAINS = {
    "kp_theta": 240.0,
    "kd_theta": 30.0,
    "kp_x": 13.0,
    "kd_x": 30.0,
}
SUBJECT_A_PAPER_GAINS = {
    "kp_theta": 120.0,
    "kd_theta": 28.0,
    "kp_x": 14.0,
    "kd_x": 19.0,
}
# The supplied paper table values are provenance only. The sweep keeps the
# subject's identified Pi and tau fixed so Kp/Kd are the only changed values.
PAPER_PI_REPORTED = {"subject_a": 1.75, "subject_b": 3.00}
CHUNK_COUNT = 11
GAIN_NAMES = ("kp_theta", "kd_theta", "kp_x", "kd_x")


def expected_input_names() -> list[str]:
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    if scope["subject"] != SUBJECT_ID:
        raise ValueError(f"{SCOPE} targets {scope['subject']}, expected {SUBJECT_ID}")
    return [f"SubjectB_{trial}.tsv" for trial in scope["included_trials"]]


def validate_input_inventory() -> list[str]:
    expected = sorted(expected_input_names())
    actual = sorted(path.name for path in INPUTS.glob("SubjectB_*.tsv"))
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        raise RuntimeError(
            "Subject input inventory is not clean. "
            f"Missing={missing}; unexpected={unexpected}. Run the corrected build "
            "from a freshly extracted project before training."
        )
    return actual


def load_baseline_parameters() -> dict[str, float]:
    required_files = (
        IDENTIFIED_PARAMETERS,
        STAGE1_WEIGHTS,
        FULL_RUN_MODE,
        FULL_RUN_MODEL,
        FULL_RUN_CONFIGURATION,
    )
    if not all(path.is_file() for path in required_files):
        raise FileNotFoundError(
            "The clean full run is missing. Complete './run_on_mac.sh full' before the gain sweep."
        )
    generated = list((FULL_RUN / "synthetic_subjectB_PINN").glob("synth_B_*.npy"))
    if len(generated) != 100:
        raise RuntimeError(
            f"The clean full run is incomplete: expected 100 generated trajectories, found {len(generated)}."
        )
    run_mode = json.loads(FULL_RUN_MODE.read_text(encoding="utf-8"))
    expected = validate_input_inventory()
    if not run_mode.get("input_inventory_validated") or run_mode.get("input_files") != expected:
        raise RuntimeError(
            "The full-run checkpoint lacks clean subject-only input provenance. "
            "Do not reuse an earlier mixed-subject checkpoint; rerun the corrected full pipeline."
        )
    payload = json.loads(IDENTIFIED_PARAMETERS.read_text(encoding="utf-8"))
    required = (*GAIN_NAMES, "pi_deg", "tau_s")
    missing = [name for name in required if name not in payload]
    if missing:
        raise KeyError(f"Missing identified parameters: {missing}")
    values = {name: float(payload[name]) for name in required}
    if not all(np.isfinite(value) for value in values.values()):
        raise ValueError("Identified parameters contain non-finite values")
    return values


def load_pipeline():
    spec = importlib.util.spec_from_file_location("unchanged_pole_pipeline_gain_sweep", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.CFG.data_folder = str(INPUTS)
    overrides = json.loads(RUNTIME_OVERRIDES.read_text(encoding="utf-8"))
    module.CFG.minimum_trial_seconds = float(overrides["minimum_trial_seconds"])
    return module


def reset_random_state(pipeline) -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    tf.random.set_seed(SEED)
    pipeline.random.seed(SEED)
    pipeline.np.random.seed(SEED)
    pipeline.tf.random.set_seed(SEED)


def gain_sets(baseline: dict[str, float]) -> list[dict]:
    rows = []
    for index, alpha in enumerate(np.linspace(0.0, 1.0, 10), start=1):
        row = {"chunk": index, "alpha": float(alpha)}
        for name in GAIN_NAMES:
            row[name] = float(
                (1.0 - alpha) * baseline[name]
                + alpha * SUBJECT_B_PAPER_GAINS[name]
            )
        rows.append(row)
    rows.append({"chunk": 11, "alpha": None, **SUBJECT_A_PAPER_GAINS})
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows supplied for {path}")
    names = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def build_model(pipeline):
    model = pipeline.ConditionalPolePINN()
    model(np.zeros((1, 5), dtype=np.float32), training=False)
    model.load_weights(STAGE1_WEIGHTS)
    return model


def assign_controller(pipeline, gains: dict, baseline: dict[str, float]):
    pipeline.CFG.initial_pi_deg = baseline["pi_deg"]
    controller = pipeline.ControllerParameters()
    controller.kp_theta.assign(gains["kp_theta"])
    controller.kd_theta.assign(gains["kd_theta"])
    controller.kp_x.assign(gains["kp_x"])
    controller.kd_x.assign(gains["kd_x"])
    return controller


def metric_row(pipeline, name, theta_true, x_true, theta_pred, x_pred):
    theta_error_rad = theta_pred - theta_true
    x_error_m = x_pred - x_true
    theta_error_deg = np.degrees(theta_error_rad)
    x_error_cm = 100.0 * x_error_m
    return {
        "trial": name,
        "samples": int(len(theta_true)),
        "theta_mse_deg2": float(np.mean(theta_error_deg**2)),
        "theta_rmse_deg": float(np.sqrt(np.mean(theta_error_deg**2))),
        "theta_mae_deg": float(np.mean(np.abs(theta_error_deg))),
        "x_mse_cm2": float(np.mean(x_error_cm**2)),
        "x_rmse_cm": float(np.sqrt(np.mean(x_error_cm**2))),
        "x_mae_cm": float(np.mean(np.abs(x_error_cm))),
        "normalized_mse": float(
            np.mean((theta_error_rad / pipeline.CFG.theta_output_scale_rad) ** 2)
            + np.mean((x_error_m / pipeline.CFG.x_output_scale_m) ** 2)
        ),
    }


def interpolate_trial(time_grid, trial, theta_pred, x_pred):
    time = trial.t[:, 0]
    return {
        "real_theta_deg": np.interp(time_grid, time, np.degrees(trial.theta[:, 0])),
        "synthetic_theta_deg": np.interp(time_grid, time, np.degrees(theta_pred)),
        "real_x_cm": np.interp(time_grid, time, 100.0 * trial.x[:, 0]),
        "synthetic_x_cm": np.interp(time_grid, time, 100.0 * x_pred),
    }


def common_window_arrays(trials, predictions):
    end_time = min(float(trial.t[-1, 0]) for trial in trials)
    time_grid = np.arange(0.0, end_time + 1e-9, 0.01)
    series = [
        interpolate_trial(time_grid, trial, *predictions[trial.name])
        for trial in trials
    ]
    arrays = {
        key: np.stack([item[key] for item in series])
        for key in series[0]
    }
    return time_grid, arrays


def distribution_metrics(time_grid, arrays):
    theta_w1 = np.array(
        [
            wasserstein_distance(arrays["real_theta_deg"][:, i], arrays["synthetic_theta_deg"][:, i])
            for i in range(len(time_grid))
        ]
    )
    x_w1 = np.array(
        [
            wasserstein_distance(arrays["real_x_cm"][:, i], arrays["synthetic_x_cm"][:, i])
            for i in range(len(time_grid))
        ]
    )
    theta_mean_abs = np.abs(
        arrays["real_theta_deg"].mean(axis=0) - arrays["synthetic_theta_deg"].mean(axis=0)
    )
    x_mean_abs = np.abs(arrays["real_x_cm"].mean(axis=0) - arrays["synthetic_x_cm"].mean(axis=0))
    return {
        "theta_w1_deg": theta_w1,
        "x_w1_cm": x_w1,
        "theta_absolute_mean_difference_deg": theta_mean_abs,
        "x_absolute_mean_difference_cm": x_mean_abs,
    }


def plot_trial_reconstructions(chunk_dir, trials, predictions):
    fig, axes = plt.subplots(len(trials), 2, figsize=(13, 3.0 * len(trials)), squeeze=False)
    for row, trial in enumerate(trials):
        time = trial.t[:, 0]
        theta_pred, x_pred = predictions[trial.name]
        axes[row, 0].plot(time, np.degrees(trial.theta[:, 0]), color="#202124", lw=1.8, label="Real")
        axes[row, 0].plot(time, np.degrees(theta_pred), color="#D1495B", lw=1.5, label="Synthetic forward simulation")
        axes[row, 1].plot(time, 100.0 * trial.x[:, 0], color="#202124", lw=1.8, label="Real")
        axes[row, 1].plot(time, 100.0 * x_pred, color="#2A9D8F", lw=1.5, label="Synthetic forward simulation")
        axes[row, 0].set_title(trial.name)
        axes[row, 1].set_title(trial.name)
        axes[row, 0].set_ylabel("CoM angle [deg]")
        axes[row, 1].set_ylabel("Forward CoM [cm]")
        for ax in axes[row]:
            ax.grid(alpha=0.25)
    axes[0, 0].legend()
    axes[0, 1].legend()
    axes[-1, 0].set_xlabel("Time from marked onset [s]")
    axes[-1, 1].set_xlabel("Time from marked onset [s]")
    fig.suptitle(f"Real {SUBJECT_ID} trials and matched synthetic forward simulations")
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(chunk_dir / "real_vs_synthetic_com_by_trial.png", dpi=220)
    plt.close(fig)


def _plot_mean_band(ax, time, real, synthetic, ylabel):
    real_mean = real.mean(axis=0)
    synthetic_mean = synthetic.mean(axis=0)
    real_min, real_max = real.min(axis=0), real.max(axis=0)
    synthetic_min, synthetic_max = synthetic.min(axis=0), synthetic.max(axis=0)
    trial_count = real.shape[0]
    ax.fill_between(time, real_min, real_max, color="#4E79A7", alpha=0.16, label=f"Real range across {trial_count} trials")
    ax.fill_between(
        time,
        synthetic_min,
        synthetic_max,
        color="#E15759",
        alpha=0.14,
        label=f"Synthetic range across {trial_count} matched simulations",
    )
    ax.plot(time, real_mean, color="#1F4E79", lw=2.3, label="Real mean")
    ax.plot(time, synthetic_mean, color="#B22222", lw=2.0, label="Synthetic mean")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)


def plot_means_and_distances(chunk_dir, time, arrays, distances):
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex="col")
    _plot_mean_band(
        axes[0, 0],
        time,
        arrays["real_theta_deg"],
        arrays["synthetic_theta_deg"],
        "CoM angle [deg]",
    )
    _plot_mean_band(
        axes[0, 1],
        time,
        arrays["real_x_cm"],
        arrays["synthetic_x_cm"],
        "Forward CoM [cm]",
    )
    axes[0, 0].set_title("Real and synthetic angle means")
    axes[0, 1].set_title("Real and synthetic forward-CoM means")
    axes[0, 0].legend(fontsize=8, ncol=2)
    axes[0, 1].legend(fontsize=8, ncol=2)

    distance_specs = (
        (
            axes[1, 0],
            distances["theta_w1_deg"],
            distances["theta_absolute_mean_difference_deg"],
            "Distance [deg]",
            "Angle distribution and mean distance",
        ),
        (
            axes[1, 1],
            distances["x_w1_cm"],
            distances["x_absolute_mean_difference_cm"],
            "Distance [cm]",
            "Forward-CoM distribution and mean distance",
        ),
    )
    for ax, w1, mean_difference, ylabel, title in distance_specs:
        ax.plot(time, w1, color="#6A4C93", lw=2.0, label="W1 distribution distance")
        ax.plot(time, mean_difference, color="#F28E2B", lw=1.8, label="Absolute difference between means")
        ax.axhline(
            float(np.mean(w1)),
            color="#6A4C93",
            ls="--",
            lw=1.2,
            label=f"Average W1 = {np.mean(w1):.3f}",
        )
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Time from marked onset [s]")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("Real vs synthetic CoM means and distribution distances")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(chunk_dir / "real_vs_synthetic_means_and_distances.png", dpi=220)
    plt.close(fig)


def save_trial_csvs(chunk_dir, trials, predictions):
    trial_dir = chunk_dir / "synthetic_com"
    trial_dir.mkdir(parents=True, exist_ok=True)
    for trial in trials:
        theta_pred, x_pred = predictions[trial.name]
        data = np.column_stack(
            [
                trial.t[:, 0],
                np.degrees(trial.theta[:, 0]),
                np.degrees(theta_pred),
                100.0 * trial.x[:, 0],
                100.0 * x_pred,
            ]
        )
        np.savetxt(
            trial_dir / f"{trial.name}_real_vs_synthetic.csv",
            data,
            delimiter=",",
            header="time_s,real_theta_deg,synthetic_theta_deg,real_x_cm,synthetic_x_cm",
            comments="",
            fmt="%.10f",
        )


def evaluate_model(pipeline, model, trials, chunk_dir):
    predictions = {}
    trial_rows = []
    all_theta_true, all_x_true, all_theta_pred, all_x_pred = [], [], [], []
    for trial in trials:
        theta_pred, x_pred = pipeline.predict_trial(model, trial)
        theta_pred = np.asarray(theta_pred)
        x_pred = np.asarray(x_pred)
        predictions[trial.name] = (theta_pred, x_pred)
        theta_true = trial.theta[:, 0]
        x_true = trial.x[:, 0]
        trial_rows.append(metric_row(pipeline, trial.name, theta_true, x_true, theta_pred, x_pred))
        all_theta_true.append(theta_true)
        all_x_true.append(x_true)
        all_theta_pred.append(theta_pred)
        all_x_pred.append(x_pred)

    pooled = metric_row(
        pipeline,
        "POOLED",
        np.concatenate(all_theta_true),
        np.concatenate(all_x_true),
        np.concatenate(all_theta_pred),
        np.concatenate(all_x_pred),
    )
    trial_rows.append(pooled)
    write_csv(chunk_dir / "mse_by_trial.csv", trial_rows)
    save_trial_csvs(chunk_dir, trials, predictions)
    plot_trial_reconstructions(chunk_dir, trials, predictions)

    time_grid, arrays = common_window_arrays(trials, predictions)
    distances = distribution_metrics(time_grid, arrays)
    distance_rows = []
    for index, time_value in enumerate(time_grid):
        distance_rows.append(
            {
                "time_s": float(time_value),
                "real_theta_mean_deg": float(arrays["real_theta_deg"][:, index].mean()),
                "synthetic_theta_mean_deg": float(arrays["synthetic_theta_deg"][:, index].mean()),
                "theta_w1_deg": float(distances["theta_w1_deg"][index]),
                "theta_absolute_mean_difference_deg": float(
                    distances["theta_absolute_mean_difference_deg"][index]
                ),
                "real_x_mean_cm": float(arrays["real_x_cm"][:, index].mean()),
                "synthetic_x_mean_cm": float(arrays["synthetic_x_cm"][:, index].mean()),
                "x_w1_cm": float(distances["x_w1_cm"][index]),
                "x_absolute_mean_difference_cm": float(distances["x_absolute_mean_difference_cm"][index]),
            }
        )
    write_csv(chunk_dir / "time_resolved_means_and_distances.csv", distance_rows)
    plot_means_and_distances(chunk_dir, time_grid, arrays, distances)

    distribution_summary = {
        "common_window_end_s": float(time_grid[-1]),
        "theta_pooled_w1_deg": float(
            wasserstein_distance(arrays["real_theta_deg"].ravel(), arrays["synthetic_theta_deg"].ravel())
        ),
        "x_pooled_w1_cm": float(
            wasserstein_distance(arrays["real_x_cm"].ravel(), arrays["synthetic_x_cm"].ravel())
        ),
        "theta_time_mean_w1_deg": float(np.mean(distances["theta_w1_deg"])),
        "x_time_mean_w1_cm": float(np.mean(distances["x_w1_cm"])),
        "theta_time_mean_absolute_mean_difference_deg": float(
            np.mean(distances["theta_absolute_mean_difference_deg"])
        ),
        "x_time_mean_absolute_mean_difference_cm": float(
            np.mean(distances["x_absolute_mean_difference_cm"])
        ),
    }
    return pooled, trial_rows, distribution_summary


def run_chunk(pipeline, trials, real_data, gains, baseline, output_root, epochs, batch_size, force):
    chunk_dir = output_root / f"chunk_{gains['chunk']:02d}"
    completion = chunk_dir / "result.json"
    if completion.exists() and not force:
        print(f"Skipping completed {chunk_dir.name}")
        return json.loads(completion.read_text(encoding="utf-8"))
    if chunk_dir.exists() and force:
        shutil.rmtree(chunk_dir)
    chunk_dir.mkdir(parents=True, exist_ok=True)

    reset_random_state(pipeline)
    pipeline.CFG.output_folder = str(chunk_dir)
    pipeline.CFG.stage3_epochs = epochs
    pipeline.CFG.stage3_batch_size = batch_size
    pipeline.CFG.print_every = max(1, min(250, epochs // 10 if epochs >= 10 else 1))
    pipeline.CFG.tau_s = baseline["tau_s"]

    model = build_model(pipeline)
    controller = assign_controller(pipeline, gains, baseline)
    stage3_history = pipeline.train_stage_3(model=model, controller=controller, real_data=real_data)
    model.save_weights(chunk_dir / "final_stage3.weights.h5")
    np.savetxt(
        chunk_dir / "stage3_loss_history.csv",
        np.column_stack([np.arange(len(stage3_history)), stage3_history]),
        delimiter=",",
        header="epoch,total_stage3_loss",
        comments="",
        fmt=["%d", "%.10e"],
    )

    pooled, _, distribution = evaluate_model(pipeline, model, trials, chunk_dir)
    result = {
        **gains,
        "subject": SUBJECT_ID,
        "fixed_pi_deg": baseline["pi_deg"],
        "fixed_tau_s": baseline["tau_s"],
        "stage3_epochs": epochs,
        "stage3_batch_size": batch_size,
        "stage3_best_objective": float(np.min(stage3_history)),
        **pooled,
        **distribution,
    }
    completion.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def plot_aggregate_metrics(output_root: Path, rows: list[dict]) -> None:
    chunks = np.array([row["chunk"] for row in rows])
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    specs = (
        ("theta_mse_deg2", "Angle MSE [deg²]", "#6A4C93"),
        ("x_mse_cm2", "Forward CoM MSE [cm²]", "#2A9D8F"),
        ("normalized_mse", "Combined normalized MSE", "#D1495B"),
    )
    for ax, (key, ylabel, color) in zip(axes, specs):
        values = np.array([row[key] for row in rows])
        best = int(np.argmin(values))
        ax.plot(chunks, values, marker="o", color=color, lw=2.0)
        ax.scatter(chunks[best], values[best], s=75, color="#111111", zorder=3, label=f"Minimum: chunk {chunks[best]}")
        ax.set_xlabel("Gain chunk")
        ax.set_ylabel(ylabel)
        ax.set_xticks(chunks)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("Matched real-versus-synthetic forward-simulation error by gain chunk")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output_root / "mse_by_gain_chunk.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, pooled_key, mean_key, ylabel, title in (
        (
            axes[0],
            "theta_pooled_w1_deg",
            "theta_time_mean_w1_deg",
            "W1 distance [deg]",
            "Angle distribution distance",
        ),
        (
            axes[1],
            "x_pooled_w1_cm",
            "x_time_mean_w1_cm",
            "W1 distance [cm]",
            "Forward-CoM distribution distance",
        ),
    ):
        ax.plot(chunks, [row[pooled_key] for row in rows], marker="o", lw=2.0, label="Pooled real-vs-synthetic W1")
        ax.plot(chunks, [row[mean_key] for row in rows], marker="s", lw=1.8, label="Mean of time-resolved W1")
        ax.set_xlabel("Gain chunk")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.set_xticks(chunks)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("Real-versus-synthetic Wasserstein distance by gain chunk")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(output_root / "wasserstein_by_gain_chunk.png", dpi=220)
    plt.close(fig)


def aggregate(output_root: Path, expected_chunks: list[int]) -> list[dict]:
    rows = []
    for chunk in expected_chunks:
        path = output_root / f"chunk_{chunk:02d}" / "result.json"
        if path.exists():
            rows.append(json.loads(path.read_text(encoding="utf-8")))
    if not rows:
        raise RuntimeError("No completed chunk results were found")
    rows.sort(key=lambda row: row["chunk"])
    write_csv(output_root / "gain_sweep_metrics.csv", rows)
    plot_aggregate_metrics(output_root, rows)

    ranked = sorted(rows, key=lambda row: row["normalized_mse"])
    best = ranked[0]
    best_source = output_root / f"chunk_{best['chunk']:02d}" / "real_vs_synthetic_means_and_distances.png"
    if best_source.exists():
        shutil.copy2(best_source, output_root / "best_chunk_real_vs_synthetic_means_and_distances.png")

    summary = {
        "subject": SUBJECT_ID,
        "completed_chunks": len(rows),
        "expected_chunks": expected_chunks,
        "ranking_metric": f"pooled normalized MSE on the same {best['samples']} measured samples",
        "best_chunk": best,
        "ranked_chunks": [
            {
                "rank": rank,
                "chunk": row["chunk"],
                "normalized_mse": row["normalized_mse"],
                "theta_mse_deg2": row["theta_mse_deg2"],
                "x_mse_cm2": row["x_mse_cm2"],
            }
            for rank, row in enumerate(ranked, start=1)
        ],
    }
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Stage-3 fixed-gain sweep results",
        "",
        f"Completed {len(rows)} of {len(expected_chunks)} requested chunks.",
        "",
        "Each chunk started from the same Stage-1 weights and used the original Stage-3 training function. Only the four Kp/Kd gains changed. Pi and tau remained fixed.",
        "",
        f"The current minimum pooled normalized MSE is chunk {best['chunk']} at {best['normalized_mse']:.6g}.",
        "",
        "## Ranked pooled reconstruction metrics",
        "",
        "| Rank | Chunk | Normalized MSE | Theta MSE (deg^2) | x MSE (cm^2) | Theta pooled W1 (deg) | x pooled W1 (cm) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rank, row in enumerate(ranked, start=1):
        lines.append(
            f"| {rank} | {row['chunk']} | {row['normalized_mse']:.6f} | {row['theta_mse_deg2']:.6f} | {row['x_mse_cm2']:.6f} | {row['theta_pooled_w1_deg']:.6f} | {row['x_pooled_w1_cm']:.6f} |"
        )
    lines.extend(
        [
            "",
            "The Wasserstein figures show both real and synthetic means, their ranges, the time-resolved W1 distribution distance, and the absolute difference between the means. W1 and mean difference answer different questions and are labeled separately.",
            "",
        ]
    )
    (output_root / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return rows


def parse_chunk_selection(value: str) -> list[int]:
    if value.strip().lower() == "all":
        return list(range(1, CHUNK_COUNT + 1))
    selected = sorted({int(item.strip()) for item in value.split(",") if item.strip()})
    if not selected or any(item < 1 or item > CHUNK_COUNT for item in selected):
        raise argparse.ArgumentTypeError(
            f"chunks must be 'all' or comma-separated integers from 1 to {CHUNK_COUNT}"
        )
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", default="all", help="all or comma-separated chunk numbers")
    parser.add_argument("--epochs", type=int, default=5000)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true", help="rerun completed selected chunks")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument(
        "--skip-aggregate",
        action="store_true",
        help="leave aggregate tables/figures for a later --analyze-only call",
    )
    args = parser.parse_args()

    selected = parse_chunk_selection(args.chunks)
    input_files = validate_input_inventory()
    baseline = load_baseline_parameters()
    args.output.mkdir(parents=True, exist_ok=True)
    gains = gain_sets(baseline)
    gain_path = args.output / "gain_sets.csv"
    # Rewrite the configuration table on every invocation from the clean
    # subject-specific baseline stored by the completed full run.
    write_csv(gain_path, gains)

    manifest = {
        "source_file": str(SOURCE.relative_to(ROOT)),
        "source_modified": False,
        "stage1_checkpoint": str(STAGE1_WEIGHTS.relative_to(ROOT)),
        "input_folder": str(INPUTS.relative_to(ROOT)),
        "seed_reset_for_every_chunk": SEED,
        "fixed_pi_deg": baseline["pi_deg"],
        "fixed_tau_s": baseline["tau_s"],
        "stage3_epochs": args.epochs,
        "stage3_batch_size": args.batch_size,
        "selected_chunks": selected,
        "subject": SUBJECT_ID,
        "validated_input_files": input_files,
        "subject_identified_endpoint": {name: baseline[name] for name in GAIN_NAMES},
        "fixed_subject_pi_deg": baseline["pi_deg"],
        "fixed_subject_tau_s": baseline["tau_s"],
        "subject_b_paper_endpoint": SUBJECT_B_PAPER_GAINS,
        "subject_a_paper_comparison": SUBJECT_A_PAPER_GAINS,
        "paper_pi_reported_reference_only": PAPER_PI_REPORTED,
        "gain_construction": (
            f"chunks 1-10 are equally spaced {SUBJECT_ID}-identified-to-Subject-B interpolations; "
            "chunk 11 is the exact Subject-A Kp/Kd set"
        ),
    }
    selection_label = (
        "all"
        if selected == list(range(1, CHUNK_COUNT + 1))
        else "_".join(f"{item:02d}" for item in selected)
    )
    (args.output / f"run_manifest_{selection_label}.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    if not args.analyze_only:
        pipeline = load_pipeline()
        pipeline.CFG.data_folder = str(INPUTS)
        trials = pipeline.load_trials()
        loaded_names = sorted(trial.name for trial in trials)
        if loaded_names != input_files:
            raise RuntimeError(
                f"Loader accepted {loaded_names}, expected exactly {input_files}. "
                "Do not start the sweep with a rejected or extra trial."
            )
        real_data = pipeline.concatenate_trials(trials)
        for chunk in selected:
            row = gains[chunk - 1]
            print("\n" + "=" * 78)
            print(f"GAIN SWEEP CHUNK {chunk:02d}/{CHUNK_COUNT}")
            print(json.dumps(row, indent=2))
            run_chunk(
                pipeline,
                trials,
                real_data,
                row,
                baseline,
                args.output,
                args.epochs,
                args.batch_size,
                args.force,
            )
            tf.keras.backend.clear_session()

    if not args.skip_aggregate:
        rows = aggregate(args.output, list(range(1, CHUNK_COUNT + 1)))
        print(f"\nCompleted result aggregation for {len(rows)} chunk(s): {args.output.resolve()}")


if __name__ == "__main__":
    main()
