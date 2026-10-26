#!/usr/bin/env python3
"""Train and evaluate a physics-informed conditional DeepONet with few-shot gain inference."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as functional

from operator_core import (
    GAIN_NAMES,
    ROOT,
    batch_to_device,
    build_context_windows,
    build_splits,
    choose_torch_device,
    create_model,
    dump_json,
    iter_batches,
    load_config,
    load_teacher_records,
    physics_residual_loss,
    seed_everything,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--device", default="auto", help="auto, cpu, mps, or cuda")
    parser.add_argument(
        "--holdout-teacher",
        choices=("s43_chunk1", "s63_chunk1", "s63_chunk6"),
        default=None,
        help="Optional leave-one-teacher-out test instead of the pooled grouped split.",
    )
    return parser.parse_args()


def output_target(batch: dict[str, Any]) -> torch.Tensor:
    return torch.stack([batch["theta_rad"], batch["x_m"]], dim=2)


def normalized_trajectory_mse(prediction, target, theta_scale: float, x_scale: float):
    theta_error = (prediction[:, :, 0] - target[:, :, 0]) / theta_scale
    x_error = (prediction[:, :, 1] - target[:, :, 1]) / x_scale
    return theta_error.square().mean() + x_error.square().mean()


def gain_nll(mean, log_variance, target):
    return 0.5 * (torch.exp(-log_variance) * (mean - target).square() + log_variance).mean()


def make_context(batch, config, number_windows: int, randomize: bool):
    model_config = config["model"]
    return build_context_windows(
        theta_rad=batch["theta_rad"],
        x_m=batch["x_m"],
        time_s=batch["time_s"],
        number_windows=number_windows,
        maximum_windows=int(model_config["max_context_windows"]),
        window_seconds=float(model_config["context_window_s"]),
        region_seconds=float(model_config["context_region_s"]),
        theta_scale=float(model_config["theta_scale_rad"]),
        x_scale=float(model_config["x_scale_m"]),
        randomize=randomize,
    )


def compute_losses(model, batch, config, number_windows: int, randomize: bool, include_physics: bool):
    contexts, mask = make_context(batch, config, number_windows, randomize)
    output = model(
        contexts,
        mask,
        batch["gains"],
        batch["initial_state"],
        batch["demographics"],
        batch["auxiliary"],
        batch["time_s"],
    )
    target = output_target(batch)
    theta_scale = float(config["model"]["theta_scale_rad"])
    x_scale = float(config["model"]["x_scale_m"])
    target_gain = batch["gains"] / model.gain_scale
    losses = {
        "data": normalized_trajectory_mse(
            output["true_gain_trajectory"], target, theta_scale, x_scale
        ),
        "gain": gain_nll(
            output["predicted_gain_normalized"], output["predicted_gain_logvar"], target_gain
        ),
        "consistency": normalized_trajectory_mse(
            output["predicted_gain_trajectory"], target, theta_scale, x_scale
        ),
    }
    if include_physics:
        losses["physics"] = physics_residual_loss(
            output["true_gain_trajectory"],
            batch["gains"],
            batch["pi_rad"],
            batch["tau_s"],
            batch["time_s"],
            config["physics"],
        )
    else:
        losses["physics"] = target.new_tensor(0.0)
    weights = config["training"]
    total = (
        float(weights["data_weight"]) * losses["data"]
        + float(weights["gain_weight"]) * losses["gain"]
        + float(weights["consistency_weight"]) * losses["consistency"]
        + float(weights["physics_weight"]) * losses["physics"]
    )
    losses["total"] = total
    return losses, output


def mean_values(rows: list[dict[str, float]]) -> dict[str, float]:
    return {
        key: float(np.mean([row[key] for row in rows]))
        for key in rows[0]
    }


def validate(model, dataset, config, device, batch_size: int, seed: int) -> dict[str, float]:
    model.eval()
    rows = []
    maximum_windows = int(config["model"]["max_context_windows"])
    with torch.no_grad():
        for batch in iter_batches(dataset, batch_size, False, seed):
            batch = batch_to_device(batch, device)
            losses, _ = compute_losses(
                model, batch, config, maximum_windows, randomize=False, include_physics=False
            )
            rows.append({key: float(value.detach().cpu()) for key, value in losses.items()})
    return mean_values(rows)


def train(model, train_set, validation_set, config, device, output_dir: Path) -> list[dict[str, float]]:
    settings = config["training"]
    epochs = int(settings["epochs"])
    batch_size = int(settings["batch_size"])
    if config["_run_mode"] == "smoke":
        epochs = 3
        batch_size = min(3, batch_size)
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
    maximum_windows = int(config["model"]["max_context_windows"])

    for epoch in range(epochs):
        model.train()
        epoch_rows = []
        loader = iter_batches(train_set, batch_size, True, int(config["seed"]) + epoch)
        for batch in loader:
            batch = batch_to_device(batch, device)
            number_windows = int(np.random.randint(1, maximum_windows + 1))
            include_physics = global_batch % int(settings["physics_every_batches"]) == 0
            losses, _ = compute_losses(
                model,
                batch,
                config,
                number_windows,
                randomize=True,
                include_physics=include_physics,
            )
            optimizer.zero_grad(set_to_none=True)
            losses["total"].backward()
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), float(settings["gradient_clip_norm"])
            )
            optimizer.step()
            epoch_rows.append({key: float(value.detach().cpu()) for key, value in losses.items()})
            global_batch += 1

        training_mean = mean_values(epoch_rows)
        validation_mean = validate(
            model, validation_set, config, device, batch_size, int(config["seed"])
        )
        row = {"epoch": epoch + 1}
        row.update({f"train_{key}": value for key, value in training_mean.items()})
        row.update({f"validation_{key}": value for key, value in validation_mean.items()})
        history.append(row)

        if validation_mean["total"] < best_validation:
            best_validation = validation_mean["total"]
            best_epoch = epoch
            torch.save(model.state_dict(), output_dir / "best_model_state.pt")
        if epoch == 0 or (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            print(
                f"epoch={epoch + 1:04d} "
                f"train={training_mean['total']:.6f} "
                f"validation={validation_mean['total']:.6f} "
                f"physics={training_mean['physics']:.6f}"
            )
        if epoch - best_epoch >= patience:
            print(f"Early stopping at epoch {epoch + 1}; best epoch was {best_epoch + 1}.")
            break

    model.load_state_dict(torch.load(output_dir / "best_model_state.pt", map_location=device))
    return history


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_history(history: list[dict[str, float]], path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    keys = ("total", "data", "gain", "consistency")
    for ax, key in zip(axes.flat, keys):
        ax.plot([row["epoch"] for row in history], [row[f"train_{key}"] for row in history], label="Train")
        ax.plot(
            [row["epoch"] for row in history],
            [row[f"validation_{key}"] for row in history],
            label="Validation",
        )
        ax.set_title(key.capitalize())
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.set_yscale("symlog", linthresh=1e-5)
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("Unified operator training history")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def evaluate(model, test_set, config, device, output_dir: Path, baseline_gain: np.ndarray):
    model.eval()
    gain_scale = model.gain_scale.detach().cpu().numpy()
    theta_scale = float(config["model"]["theta_scale_rad"])
    x_scale = float(config["model"]["x_scale_m"])
    maximum_windows = int(config["model"]["max_context_windows"])
    shot_counts = sorted({1, 2, maximum_windows})
    region_s = float(config["model"]["context_region_s"])
    rows: list[dict[str, Any]] = []
    examples: dict[str, dict[str, Any]] = {}

    with torch.no_grad():
        for number_windows in shot_counts:
            for index in range(len(test_set)):
                raw = test_set[index]
                batch = {
                    key: value.unsqueeze(0).to(device) if hasattr(value, "unsqueeze") else [value]
                    for key, value in raw.items()
                }
                contexts, mask = make_context(batch, config, number_windows, randomize=False)
                mean_norm, log_variance = model.infer_gains(
                    contexts, mask, batch["demographics"]
                )
                prediction = model.forward_operator(
                    mean_norm,
                    batch["initial_state"],
                    batch["demographics"],
                    batch["auxiliary"],
                    batch["time_s"],
                )
                true_gain_prediction = model.forward_operator(
                    batch["gains"] / model.gain_scale,
                    batch["initial_state"],
                    batch["demographics"],
                    batch["auxiliary"],
                    batch["time_s"],
                )
                baseline_gain_tensor = torch.as_tensor(
                    baseline_gain, dtype=batch["gains"].dtype, device=device
                ).reshape(1, 4)
                baseline_prediction = model.forward_operator(
                    baseline_gain_tensor / model.gain_scale,
                    batch["initial_state"],
                    batch["demographics"],
                    batch["auxiliary"],
                    batch["time_s"],
                )
                predicted_gains = (mean_norm[0].cpu().numpy() * gain_scale)
                gain_std = np.exp(0.5 * log_variance[0].cpu().numpy()) * gain_scale
                true_gains = batch["gains"][0].cpu().numpy()
                time = batch["time_s"][0].cpu().numpy()
                target_theta = batch["theta_rad"][0].cpu().numpy()
                target_x = batch["x_m"][0].cpu().numpy()
                predicted = prediction[0].cpu().numpy()
                true_gain_pred = true_gain_prediction[0].cpu().numpy()
                baseline_pred = baseline_prediction[0].cpu().numpy()
                forecast = time >= region_s
                if not np.any(forecast):
                    forecast = np.ones_like(time, dtype=bool)
                theta_rmse_deg = float(
                    np.degrees(np.sqrt(np.mean((predicted[forecast, 0] - target_theta[forecast]) ** 2)))
                )
                x_rmse_cm = float(
                    100.0 * np.sqrt(np.mean((predicted[forecast, 1] - target_x[forecast]) ** 2))
                )
                oracle_theta_rmse_deg = float(
                    np.degrees(np.sqrt(np.mean((true_gain_pred[forecast, 0] - target_theta[forecast]) ** 2)))
                )
                oracle_x_rmse_cm = float(
                    100.0 * np.sqrt(np.mean((true_gain_pred[forecast, 1] - target_x[forecast]) ** 2))
                )
                baseline_theta_rmse_deg = float(
                    np.degrees(np.sqrt(np.mean((baseline_pred[forecast, 0] - target_theta[forecast]) ** 2)))
                )
                baseline_x_rmse_cm = float(
                    100.0 * np.sqrt(np.mean((baseline_pred[forecast, 1] - target_x[forecast]) ** 2))
                )
                row: dict[str, Any] = {
                    "teacher": raw["teacher_id"],
                    "trajectory_index": int(raw["trajectory_index"]),
                    "context_windows": number_windows,
                    "gain_normalized_rmse": float(
                        np.sqrt(np.mean(((predicted_gains - true_gains) / gain_scale) ** 2))
                    ),
                    "theta_forecast_rmse_deg": theta_rmse_deg,
                    "x_forecast_rmse_cm": x_rmse_cm,
                    "oracle_theta_forecast_rmse_deg": oracle_theta_rmse_deg,
                    "oracle_x_forecast_rmse_cm": oracle_x_rmse_cm,
                    "baseline_gain_normalized_rmse": float(
                        np.sqrt(np.mean(((baseline_gain - true_gains) / gain_scale) ** 2))
                    ),
                    "baseline_theta_forecast_rmse_deg": baseline_theta_rmse_deg,
                    "baseline_x_forecast_rmse_cm": baseline_x_rmse_cm,
                }
                for gain_index, gain_name in enumerate(GAIN_NAMES):
                    row[f"true_{gain_name}"] = float(true_gains[gain_index])
                    row[f"predicted_{gain_name}"] = float(predicted_gains[gain_index])
                    row[f"std_{gain_name}"] = float(gain_std[gain_index])
                rows.append(row)
                teacher = str(raw["teacher_id"])
                if teacher not in examples:
                    examples[teacher] = {
                        "time": time,
                        "target_theta": target_theta,
                        "target_x": target_x,
                    }
                if number_windows in (1, maximum_windows):
                    examples[teacher][f"prediction_{number_windows}"] = predicted

    write_csv(output_dir / "few_shot_per_trajectory.csv", rows)
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["teacher"]), int(row["context_windows"]))].append(row)
    summary_rows = []
    metric_names = (
        "gain_normalized_rmse",
        "theta_forecast_rmse_deg",
        "x_forecast_rmse_cm",
        "oracle_theta_forecast_rmse_deg",
        "oracle_x_forecast_rmse_cm",
        "baseline_gain_normalized_rmse",
        "baseline_theta_forecast_rmse_deg",
        "baseline_x_forecast_rmse_cm",
    )
    for (teacher, shots), group in sorted(grouped.items()):
        summary = {"teacher": teacher, "context_windows": shots, "samples": len(group)}
        for name in metric_names:
            values = np.asarray([float(row[name]) for row in group])
            summary[f"mean_{name}"] = float(values.mean())
            summary[f"std_{name}"] = float(values.std())
        for gain_name in GAIN_NAMES:
            summary[f"true_{gain_name}"] = float(group[0][f"true_{gain_name}"])
            summary[f"mean_predicted_{gain_name}"] = float(
                np.mean([row[f"predicted_{gain_name}"] for row in group])
            )
            summary[f"mean_std_{gain_name}"] = float(
                np.mean([row[f"std_{gain_name}"] for row in group])
            )
        summary_rows.append(summary)
    write_csv(output_dir / "few_shot_summary.csv", summary_rows)
    plot_evaluation(summary_rows, examples, shot_counts, output_dir)
    return rows, summary_rows


def plot_evaluation(summary_rows, examples, shot_counts, output_dir: Path) -> None:
    teachers = sorted({str(row["teacher"]) for row in summary_rows})
    colors = {teacher: color for teacher, color in zip(teachers, ("#3569B0", "#D2693C", "#4A9D69"))}

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    metric_labels = (
        ("mean_gain_normalized_rmse", "mean_baseline_gain_normalized_rmse", "Normalized gain RMSE"),
        ("mean_theta_forecast_rmse_deg", "mean_baseline_theta_forecast_rmse_deg", "Theta forecast RMSE [deg]"),
        ("mean_x_forecast_rmse_cm", "mean_baseline_x_forecast_rmse_cm", "x forecast RMSE [cm]"),
    )
    for ax, (metric, baseline_metric, label) in zip(axes, metric_labels):
        for teacher in teachers:
            selected = sorted(
                [row for row in summary_rows if row["teacher"] == teacher],
                key=lambda row: row["context_windows"],
            )
            ax.plot(
                [row["context_windows"] for row in selected],
                [row[metric] for row in selected],
                marker="o",
                label=teacher,
                color=colors[teacher],
            )
            ax.axhline(
                selected[0][baseline_metric],
                color=colors[teacher],
                linestyle=":",
                alpha=0.65,
            )
        ax.set_xlabel("Context windows")
        ax.set_ylabel(label)
        ax.grid(alpha=0.25)
    axes[0].legend()
    fig.suptitle("Few-shot performance versus number of observed motion windows")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output_dir / "few_shot_error_vs_windows.png", dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(len(teachers), 2, figsize=(13, 3.5 * len(teachers)), squeeze=False)
    for row_index, teacher in enumerate(teachers):
        example = examples[teacher]
        time = example["time"]
        axes[row_index, 0].plot(time, np.degrees(example["target_theta"]), color="black", label="Teacher PINN")
        axes[row_index, 1].plot(time, 100.0 * example["target_x"], color="black", label="Teacher PINN")
        for shots, color in ((1, "#3569B0"), (max(shot_counts), "#D1495B")):
            key = f"prediction_{shots}"
            if key in example:
                axes[row_index, 0].plot(
                    time, np.degrees(example[key][:, 0]), color=color, linestyle="--", label=f"Operator, K={shots}"
                )
                axes[row_index, 1].plot(
                    time, 100.0 * example[key][:, 1], color=color, linestyle="--", label=f"Operator, K={shots}"
                )
        axes[row_index, 0].set_ylabel(f"{teacher}\ntheta [deg]")
        axes[row_index, 1].set_ylabel(f"{teacher}\nx [cm]")
        for ax in axes[row_index]:
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8)
    axes[-1, 0].set_xlabel("Time [s]")
    axes[-1, 1].set_xlabel("Time [s]")
    fig.suptitle("Teacher trajectories and few-shot operator reconstructions")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output_dir / "teacher_vs_operator_examples.png", dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    maximum_shots = max(shot_counts)
    for ax, gain_name in zip(axes.flat, GAIN_NAMES):
        x_positions = np.arange(len(teachers))
        true_values = []
        predicted_values = []
        uncertainty = []
        for teacher in teachers:
            row = next(
                item
                for item in summary_rows
                if item["teacher"] == teacher and item["context_windows"] == maximum_shots
            )
            true_values.append(row[f"true_{gain_name}"])
            predicted_values.append(row[f"mean_predicted_{gain_name}"])
            uncertainty.append(2.0 * row[f"mean_std_{gain_name}"])
        ax.scatter(x_positions, true_values, color="black", marker="x", s=70, label="True teacher gain")
        ax.errorbar(
            x_positions,
            predicted_values,
            yerr=uncertainty,
            fmt="o",
            color="#D1495B",
            capsize=4,
            label="Predicted mean ± 2σ",
        )
        ax.set_xticks(x_positions, teachers, rotation=15)
        ax.set_title(gain_name)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle(f"Few-shot control-gain estimates using K={maximum_shots} windows")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_dir / "few_shot_gain_estimates.png", dpi=200)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    config = copy.deepcopy(config)
    config["_run_mode"] = args.mode
    seed_everything(int(config["seed"]))
    records = load_teacher_records(config, args.mode)
    actual_horizon = float(records[0].time_s[-1])
    config["teacher_generation"]["horizon_s"] = actual_horizon
    if args.mode == "smoke":
        config["model"]["context_window_s"] = min(
            float(config["model"]["context_window_s"]), actual_horizon / 4.0
        )
        config["model"]["context_region_s"] = min(
            float(config["model"]["context_region_s"]), actual_horizon / 2.0
        )

    suffix = "pooled" if args.holdout_teacher is None else f"holdout_{args.holdout_teacher}"
    output_dir = ROOT / "results" / f"{args.mode}_{suffix}"
    output_dir.mkdir(parents=True, exist_ok=True)
    train_set, validation_set, test_set, split_details = build_splits(
        records,
        int(config["seed"]),
        float(config["training"]["train_fraction"]),
        float(config["training"]["validation_fraction"]),
        args.holdout_teacher,
    )
    if min(len(train_set), len(validation_set), len(test_set)) == 0:
        raise ValueError("One or more dataset splits are empty.")
    device = choose_torch_device(args.device)
    print(f"Using device: {device}")
    print(f"Split sizes: train={len(train_set)}, validation={len(validation_set)}, test={len(test_set)}")
    model = create_model(config).to(device)
    history = train(model, train_set, validation_set, config, device, output_dir)
    write_csv(output_dir / "training_history.csv", history)
    plot_history(history, output_dir / "training_history.png")
    baseline_gain = np.mean(
        np.stack([sample["gains"] for sample in train_set.samples]), axis=0
    ).astype(np.float32)
    per_sample, summary_rows = evaluate(
        model, test_set, config, device, output_dir, baseline_gain
    )

    checkpoint = {
        "model_state": model.state_dict(),
        "config": config,
        "split": split_details,
        "gain_names": GAIN_NAMES,
    }
    torch.save(checkpoint, output_dir / "unified_operator.pt")
    dump_json(output_dir / "split_manifest.json", split_details)
    dump_json(
        output_dir / "run_summary.json",
        {
            "experiment": config["experiment_name"],
            "mode": args.mode,
            "device": str(device),
            "holdout_teacher": args.holdout_teacher,
            "best_validation_total": float(min(row["validation_total"] for row in history)),
            "epochs_completed": len(history),
            "test_trajectory_count": len(test_set),
            "training_mean_gain_baseline": {
                name: float(value) for name, value in zip(GAIN_NAMES, baseline_gain)
            },
            "few_shot_summary": summary_rows,
            "limitations": [
                "Only three gain anchors and two human subjects are available.",
                "The pooled split measures held-out initial-condition performance, not new-subject generalization.",
                "Teacher outputs are synthetic PINN trajectories rather than measured ground truth.",
                "Uncertainty estimates are preliminary because gain-anchor diversity is very small.",
            ],
        },
    )
    print(f"Finished. Results: {output_dir}")


if __name__ == "__main__":
    main()
