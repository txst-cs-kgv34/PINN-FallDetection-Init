#!/usr/bin/env python3
"""Held-out A10-A13 evaluation used only after validation selects lambda."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import wasserstein_distance

from operator_core import infer, metric_names, physics_residual_components


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def metric_bundle(target: np.ndarray, prediction: np.ndarray, config: dict) -> dict[str, float]:
    theta_error = prediction[:, 0] - target[:, 0]
    x_error = prediction[:, 1] - target[:, 1]
    normalized = (
        (theta_error / float(config["model"]["theta_scale_rad"])) ** 2
        + (x_error / float(config["model"]["x_scale_m"])) ** 2
    )
    return {
        "normalized_mse": float(np.mean(normalized)),
        "theta_rmse_deg": float(np.degrees(np.sqrt(np.mean(theta_error ** 2)))),
        "theta_mae_deg": float(np.degrees(np.mean(np.abs(theta_error)))),
        "x_rmse_cm": float(100.0 * np.sqrt(np.mean(x_error ** 2))),
        "x_mae_cm": float(100.0 * np.mean(np.abs(x_error))),
        "theta_w1_deg": float(wasserstein_distance(np.degrees(target[:, 0]), np.degrees(prediction[:, 0]))),
        "x_w1_cm": float(wasserstein_distance(100.0 * target[:, 1], 100.0 * prediction[:, 1])),
    }


def aggregate_rows(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, float]]:
    output = {}
    for value in sorted({str(row[key]) for row in rows}):
        selected = [row for row in rows if str(row[key]) == value]
        metrics = {
            metric: float(np.mean([float(row[metric]) for row in selected]))
            for metric in metric_names("planar")
        }
        for diagnostic in ("angular_residual_rmse", "horizontal_residual_rmse"):
            metrics[diagnostic] = float(np.mean([float(row[diagnostic]) for row in selected]))
        output[value] = metrics
    return output


def evaluate(model, dataset, config: dict, device, output_dir: Path):
    import torch

    model.eval()
    rows: list[dict[str, Any]] = []
    prediction_dir = output_dir / "test_predictions"
    prediction_dir.mkdir(parents=True, exist_ok=True)
    with torch.no_grad():
        for index in range(len(dataset)):
            raw = dataset[index]
            batch = {
                key: value.unsqueeze(0).to(device) if hasattr(value, "unsqueeze") else [value]
                for key, value in raw.items()
            }
            prediction, controller, _ = infer(model, batch, config, "planar")
            time = batch["time_s"][0].cpu().numpy()
            valid = batch["valid_mask"][0].cpu().numpy() > 0.5
            forecast = valid & (time >= float(config["model"]["context_region_s"]))
            target_full = np.stack([
                batch["theta_rad"][0].cpu().numpy(),
                batch["x_m"][0].cpu().numpy(),
            ], axis=1)
            predicted_full = prediction[0].cpu().numpy()
            target = target_full[forecast]
            predicted = predicted_full[forecast]
            metrics = metric_bundle(target, predicted, config)
            gains = controller * model.gain_scale
            r1, r2, _, residual_mask = physics_residual_components(
                prediction,
                gains,
                batch["time_s"],
                batch["mass_kg"],
                batch["height_m"],
                config["physics"],
                batch["physics_mask"],
                "planar",
            )
            residual_valid = residual_mask[0].cpu().numpy().astype(bool)
            angular = r1[0].cpu().numpy()[residual_valid]
            horizontal = r2[0].cpu().numpy()[residual_valid]
            row = {
                "subject": raw["subject"],
                "trial": raw["trial"],
                "activity": raw["activity"],
                "activity_head_index": int(raw["activity_vector"].argmax().item()),
                "forecast_samples": int(forecast.sum()),
                **metrics,
                "angular_residual_rmse": float(np.sqrt(np.mean(angular ** 2))),
                "horizontal_residual_rmse": float(np.sqrt(np.mean(horizontal ** 2))),
            }
            rows.append(row)
            np.savez_compressed(
                prediction_dir / f"{raw['trial']}.npz",
                time_s=time[forecast],
                target_theta_rad=target[:, 0],
                target_x_m=target[:, 1],
                predicted_theta_rad=predicted[:, 0],
                predicted_x_m=predicted[:, 1],
                inferred_gains=gains[0].cpu().numpy(),
            )
            fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
            axes[0].plot(time[forecast], np.degrees(target[:, 0]), label="Real")
            axes[0].plot(time[forecast], np.degrees(predicted[:, 0]), "--", label="Prediction")
            axes[0].set_ylabel("Theta (deg)")
            axes[1].plot(time[forecast], 100.0 * target[:, 1], label="Real")
            axes[1].plot(time[forecast], 100.0 * predicted[:, 1], "--", label="Prediction")
            axes[1].set_ylabel("x (cm)")
            for axis in axes:
                axis.grid(alpha=.25)
                axis.legend()
            axes[-1].set_xlabel("Time (s)")
            fig.suptitle(f"Held-out {raw['trial']}")
            fig.tight_layout()
            fig.savefig(prediction_dir / f"{raw['trial']}.png", dpi=160)
            plt.close(fig)
    write_csv(output_dir / "test_metrics_by_trial.csv", rows)
    subject_metrics = aggregate_rows(rows, "subject")
    activity_metrics = aggregate_rows(rows, "activity")
    write_csv(
        output_dir / "test_metrics_by_subject.csv",
        [{"subject": subject, **metrics} for subject, metrics in subject_metrics.items()],
    )
    write_csv(
        output_dir / "test_metrics_by_activity.csv",
        [{"activity": activity, **metrics} for activity, metrics in activity_metrics.items()],
    )
    return rows, subject_metrics, activity_metrics

