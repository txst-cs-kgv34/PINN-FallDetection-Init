#!/usr/bin/env python3
"""Train one leave-two-subjects-out DeepONet fold and evaluate the real test subject."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import wasserstein_distance

from operator_core import (
    GAIN_NAMES,
    ROOT,
    batch_to_device,
    build_real_dataset,
    build_synthetic_dataset,
    choose_torch_device,
    create_model,
    dump_json,
    fold_by_id,
    infer_real,
    iter_batches,
    load_config,
    load_real_records,
    load_teacher_records,
    seed_everything,
    synthetic_losses,
)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def mean_rows(rows: list[dict[str, float]]) -> dict[str, float]:
    return {key: float(np.mean([row[key] for row in rows])) for key in rows[0]}


def validate_real(model, dataset, config, device) -> float:
    import torch

    model.eval()
    losses = []
    with torch.no_grad():
        for batch in iter_batches(dataset, 1, False, int(config["seed"])):
            batch = batch_to_device(batch, device)
            loss, _, _, _ = infer_real(model, batch, config)
            losses.append(float(loss.detach().cpu()))
    return float(np.mean(losses))


def load_state(path: Path, device):
    import torch

    try:
        return torch.load(path, map_location=device, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=device)


def train(model, train_set, validation_set, config, device, output_dir: Path, mode: str):
    import torch

    settings = config["training"]
    epochs = 3 if mode == "smoke" else int(settings["epochs"])
    batch_size = min(4, int(settings["batch_size"])) if mode == "smoke" else int(settings["batch_size"])
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(settings["learning_rate"]),
        weight_decay=float(settings["weight_decay"]),
    )
    best_validation = float("inf")
    best_epoch = -1
    patience = int(settings["early_stopping_patience"])
    history: list[dict[str, float]] = []
    global_batch = 0
    checkpoint = output_dir / "best_model_state.pt"

    for epoch in range(epochs):
        model.train()
        epoch_rows: list[dict[str, float]] = []
        for batch in iter_batches(
            train_set, batch_size, True, int(config["seed"]) + epoch
        ):
            batch = batch_to_device(batch, device)
            include_physics = global_batch % int(settings["physics_every_batches"]) == 0
            losses = synthetic_losses(model, batch, config, include_physics)
            optimizer.zero_grad(set_to_none=True)
            losses["total"].backward()
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), float(settings["gradient_clip_norm"])
            )
            optimizer.step()
            epoch_rows.append(
                {key: float(value.detach().cpu()) for key, value in losses.items()}
            )
            global_batch += 1

        training_mean = mean_rows(epoch_rows)
        validation_loss = validate_real(model, validation_set, config, device)
        row = {"epoch": epoch + 1, "validation_real_forecast_mse": validation_loss}
        row.update({f"train_{key}": value for key, value in training_mean.items()})
        history.append(row)
        if math.isfinite(validation_loss) and validation_loss < best_validation:
            best_validation = validation_loss
            best_epoch = epoch
            torch.save(model.state_dict(), checkpoint)
        if epoch == 0 or (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            print(
                f"epoch={epoch + 1:04d} train={training_mean['total']:.6f} "
                f"real_validation={validation_loss:.6f} physics={training_mean['physics']:.6f}"
            )
        if epoch - best_epoch >= patience:
            print(f"Early stopping at epoch {epoch + 1}; best epoch was {best_epoch + 1}")
            break

    if not checkpoint.is_file():
        raise RuntimeError("No finite validation checkpoint was produced")
    model.load_state_dict(load_state(checkpoint, device))
    dump_json(
        output_dir / "training_selection.json",
        {
            "selection_metric": "real validation-subject forecast normalized MSE",
            "best_epoch": best_epoch + 1,
            "best_validation_value": best_validation,
            "test_subject_used_for_selection": False,
        },
    )
    return history


def plot_history(history: list[dict[str, float]], path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    series = (
        ("train_total", "Synthetic training total"),
        ("validation_real_forecast_mse", "Real validation forecast MSE"),
        ("train_gain", "Gain NLL"),
        ("train_consistency", "Predicted-gain consistency"),
    )
    for axis, (key, title) in zip(axes.flat, series):
        axis.plot([row["epoch"] for row in history], [row[key] for row in history])
        axis.set_title(title)
        axis.set_xlabel("Epoch")
        axis.grid(alpha=0.25)
        axis.set_yscale("symlog", linthresh=1e-6)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def first_crossing(time: np.ndarray, theta: np.ndarray, threshold_deg: float = 10.0):
    indices = np.flatnonzero(np.abs(np.degrees(theta)) >= threshold_deg)
    return float(time[indices[0]]) if len(indices) else None


def metric_bundle(
    target_theta: np.ndarray,
    target_x: np.ndarray,
    prediction: np.ndarray,
    theta_scale: float,
    x_scale: float,
) -> dict[str, float]:
    theta_error = prediction[:, 0] - target_theta
    x_error = prediction[:, 1] - target_x
    return {
        "normalized_mse": float(
            np.mean((theta_error / theta_scale) ** 2 + (x_error / x_scale) ** 2)
        ),
        "theta_rmse_deg": float(np.degrees(np.sqrt(np.mean(theta_error**2)))),
        "theta_mae_deg": float(np.degrees(np.mean(np.abs(theta_error)))),
        "x_rmse_cm": float(100.0 * np.sqrt(np.mean(x_error**2))),
        "x_mae_cm": float(100.0 * np.mean(np.abs(x_error))),
        "theta_w1_deg": float(
            wasserstein_distance(np.degrees(target_theta), np.degrees(prediction[:, 0]))
        ),
        "x_w1_cm": float(wasserstein_distance(100.0 * target_x, 100.0 * prediction[:, 1])),
    }


def evaluate_test(
    model,
    dataset,
    config,
    device,
    output_dir: Path,
    mean_gain: np.ndarray,
):
    import torch

    model.eval()
    gain_scale = model.gain_scale.detach().cpu().numpy()
    rows: list[dict[str, Any]] = []
    pooled = {"target_theta": [], "target_x": [], "prediction": [], "baseline": []}
    prediction_dir = output_dir / "test_predictions"
    prediction_dir.mkdir(parents=True, exist_ok=True)

    with torch.no_grad():
        for raw_index in range(len(dataset)):
            raw = dataset[raw_index]
            batch = {
                key: value.unsqueeze(0).to(device) if hasattr(value, "unsqueeze") else [value]
                for key, value in raw.items()
            }
            _, prediction, mean_norm, log_variance = infer_real(model, batch, config)
            baseline_gain = torch.as_tensor(
                mean_gain, dtype=batch["theta_rad"].dtype, device=device
            ).reshape(1, 4)
            baseline_prediction = model.forward_operator(
                baseline_gain / model.gain_scale,
                batch["initial_state"],
                batch["demographics"],
                batch["auxiliary"],
                batch["time_s"],
            )
            time = batch["time_s"][0].cpu().numpy()
            valid = batch["valid_mask"][0].cpu().numpy() > 0.5
            forecast = valid & (time >= float(config["model"]["context_region_s"]))
            if not np.any(forecast):
                raise ValueError(f"No forecast samples for {raw['trial']}")
            target_theta = batch["theta_rad"][0].cpu().numpy()[forecast]
            target_x = batch["x_m"][0].cpu().numpy()[forecast]
            predicted = prediction[0].cpu().numpy()[forecast]
            baseline = baseline_prediction[0].cpu().numpy()[forecast]
            forecast_time = time[forecast]
            trial = str(raw["trial"])
            subject = str(raw["subject"])
            predicted_gains = mean_norm[0].cpu().numpy() * gain_scale
            predicted_std = np.exp(0.5 * log_variance[0].cpu().numpy()) * gain_scale
            metrics = metric_bundle(
                target_theta,
                target_x,
                predicted,
                float(config["model"]["theta_scale_rad"]),
                float(config["model"]["x_scale_m"]),
            )
            baseline_metrics = metric_bundle(
                target_theta,
                target_x,
                baseline,
                float(config["model"]["theta_scale_rad"]),
                float(config["model"]["x_scale_m"]),
            )
            target_cross = first_crossing(forecast_time, target_theta)
            predicted_cross = first_crossing(forecast_time, predicted[:, 0])
            row: dict[str, Any] = {
                "subject": subject,
                "trial": trial,
                "forecast_samples": int(forecast.sum()),
                **metrics,
                **{f"mean_gain_baseline_{key}": value for key, value in baseline_metrics.items()},
                "target_abs_theta_10deg_crossing_s": target_cross,
                "predicted_abs_theta_10deg_crossing_s": predicted_cross,
                "abs_theta_10deg_crossing_error_s": (
                    abs(predicted_cross - target_cross)
                    if predicted_cross is not None and target_cross is not None
                    else None
                ),
            }
            for index, name in enumerate(GAIN_NAMES):
                row[f"predicted_{name}"] = float(predicted_gains[index])
                row[f"predicted_std_{name}"] = float(predicted_std[index])
            rows.append(row)
            pooled["target_theta"].append(target_theta)
            pooled["target_x"].append(target_x)
            pooled["prediction"].append(predicted)
            pooled["baseline"].append(baseline)
            np.savez_compressed(
                prediction_dir / f"{trial}.npz",
                time_s=forecast_time,
                target_theta_rad=target_theta,
                target_x_m=target_x,
                predicted_theta_rad=predicted[:, 0],
                predicted_x_m=predicted[:, 1],
                mean_gain_baseline_theta_rad=baseline[:, 0],
                mean_gain_baseline_x_m=baseline[:, 1],
                predicted_gains=predicted_gains,
                predicted_gain_std=predicted_std,
            )
            fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
            axes[0].plot(forecast_time, np.degrees(target_theta), label="Real")
            axes[0].plot(forecast_time, np.degrees(predicted[:, 0]), "--", label="DeepONet")
            axes[0].plot(forecast_time, np.degrees(baseline[:, 0]), ":", label="Mean-gain baseline")
            axes[0].set_ylabel("Theta (deg)")
            axes[1].plot(forecast_time, 100.0 * target_x, label="Real")
            axes[1].plot(forecast_time, 100.0 * predicted[:, 1], "--", label="DeepONet")
            axes[1].plot(forecast_time, 100.0 * baseline[:, 1], ":", label="Mean-gain baseline")
            axes[1].set_ylabel("Forward x (cm)")
            axes[1].set_xlabel("Time from pole-compatible clip start (s)")
            for axis in axes:
                axis.grid(alpha=0.25)
                axis.legend()
            fig.suptitle(f"Held-out test: {trial}")
            fig.tight_layout()
            fig.savefig(prediction_dir / f"{trial}.png", dpi=180)
            plt.close(fig)

    write_csv(output_dir / "test_metrics_by_trial.csv", rows)
    target_theta = np.concatenate(pooled["target_theta"])
    target_x = np.concatenate(pooled["target_x"])
    prediction = np.concatenate(pooled["prediction"], axis=0)
    baseline = np.concatenate(pooled["baseline"], axis=0)
    pooled_metrics = metric_bundle(
        target_theta,
        target_x,
        prediction,
        float(config["model"]["theta_scale_rad"]),
        float(config["model"]["x_scale_m"]),
    )
    pooled_baseline = metric_bundle(
        target_theta,
        target_x,
        baseline,
        float(config["model"]["theta_scale_rad"]),
        float(config["model"]["x_scale_m"]),
    )
    trial_mean = {
        key: float(np.mean([float(row[key]) for row in rows]))
        for key in (
            "normalized_mse",
            "theta_rmse_deg",
            "theta_mae_deg",
            "x_rmse_cm",
            "x_mae_cm",
            "theta_w1_deg",
            "x_w1_cm",
        )
    }
    return rows, pooled_metrics, pooled_baseline, trial_mean


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cuda", "cpu"))
    args = parser.parse_args()

    config = load_config(args.config)
    fold = fold_by_id(config, args.fold)
    seed = int(config["seed"]) + int(fold["id"])
    seed_everything(seed)
    device = choose_torch_device(args.device)
    teacher_records = load_teacher_records(args.mode)
    real_records = load_real_records(args.mode)
    training_teachers = [record for record in teacher_records if record.subject in fold["train"]]
    if {record.subject for record in training_teachers} != set(fold["train"]):
        raise ValueError("Fold is missing a training teacher")
    held_out = {str(fold["validation"]), str(fold["test"])}
    if {record.subject for record in training_teachers} & held_out:
        raise AssertionError("Held-out teacher leakage")
    mean_gain = np.mean([record.gains for record in training_teachers], axis=0).astype(np.float32)
    mean_pi = float(np.mean([record.pi_rad for record in training_teachers]))
    mean_tau = float(np.mean([record.tau_s for record in training_teachers]))
    limit = 4 if args.mode == "smoke" else None
    train_set = build_synthetic_dataset(teacher_records, list(fold["train"]), limit)
    validation_set = build_real_dataset(
        real_records, str(fold["validation"]), mean_pi, mean_tau
    )
    test_set = build_real_dataset(real_records, str(fold["test"]), mean_pi, mean_tau)
    output_dir = ROOT / "results" / args.mode / f"fold_{int(fold['id']):02d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_json(
        output_dir / "fold_manifest.json",
        {
            "fold": fold,
            "mode": args.mode,
            "seed": seed,
            "device": str(device),
            "training_teacher_ids": [record.teacher_id for record in training_teachers],
            "training_trajectory_count": len(train_set),
            "validation_real_trial_count": len(validation_set),
            "test_real_trial_count": len(test_set),
            "training_mean_gain": mean_gain.tolist(),
            "training_mean_pi_rad": mean_pi,
            "training_mean_tau_s": mean_tau,
            "validation_and_test_teacher_data_used": False,
            "test_real_data_used_for_model_selection": False,
            "context_windows": int(config["model"]["context_windows"]),
        },
    )

    model = create_model(config).to(device)
    history = train(model, train_set, validation_set, config, device, output_dir, args.mode)
    write_csv(output_dir / "training_history.csv", history)
    plot_history(history, output_dir / "training_history.png")
    rows, pooled_metrics, pooled_baseline, trial_mean = evaluate_test(
        model, test_set, config, device, output_dir, mean_gain
    )
    torch_path = output_dir / "final_best_model_state.pt"
    import torch

    torch.save(model.state_dict(), torch_path)
    summary = {
        "fold": int(fold["id"]),
        "train_subjects": list(fold["train"]),
        "validation_subject": fold["validation"],
        "test_subject": fold["test"],
        "test_trial_count": len(rows),
        "test_forecast_sample_count": int(sum(row["forecast_samples"] for row in rows)),
        "test_pooled_metrics": pooled_metrics,
        "mean_gain_baseline_pooled_metrics": pooled_baseline,
        "test_trial_mean_metrics": trial_mean,
        "four_window_context": True,
        "context_region_s": float(config["model"]["context_region_s"]),
        "checkpoint_selected_only_on_real_validation_subject": True,
    }
    dump_json(output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
