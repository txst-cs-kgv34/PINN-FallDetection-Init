#!/usr/bin/env python3
"""Train one grouped held-out fold and evaluate its three unseen real subjects."""

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
    METRICS,
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
    optimization_seeds,
    physics_residual_components,
    real_losses,
    seed_everything,
    seed_spec,
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
    keys = sorted({key for row in rows for key in row})
    return {
        key: float(np.mean([row[key] for row in rows if key in row]))
        for key in keys
    }


def tensor_metrics(losses: dict[str, Any], prefix: str = "") -> dict[str, float]:
    result = {}
    for key, value in losses.items():
        if key in {"prediction", "controller", "controller_logvar"}:
            continue
        result[f"{prefix}{key}"] = float(value.detach().cpu())
    return result


def validate_real(model, dataset, config, device, run_seed: int) -> float:
    import torch

    model.eval()
    losses = []
    with torch.no_grad():
        for batch in iter_batches(dataset, 1, False, run_seed):
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


def training_batches(dataset, batch_size: int, seed: int):
    return list(iter_batches(dataset, batch_size, True, seed))


def train(
    model,
    real_train_set,
    synthetic_train_set,
    validation_set,
    config,
    device,
    output_dir: Path,
    mode: str,
    run_seed: int,
):
    import torch

    settings = config["training"]
    regime = str(config["training_regime"])
    epochs = 3 if mode == "smoke" else int(settings["epochs"])
    real_batch_size = min(3, int(settings["real_batch_size"])) if mode == "smoke" else int(
        settings["real_batch_size"]
    )
    synthetic_batch_size = (
        min(4, int(settings["synthetic_batch_size"]))
        if mode == "smoke"
        else int(settings["synthetic_batch_size"])
    )
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
        real_batches = training_batches(
            real_train_set, real_batch_size, run_seed + epoch
        )
        if regime == "hybrid":
            if synthetic_train_set is None:
                raise AssertionError("Hybrid training requires synthetic data")
            synthetic_batches = training_batches(
                synthetic_train_set,
                synthetic_batch_size,
                run_seed + 10000 + epoch,
            )
            steps = max(len(real_batches), len(synthetic_batches))
            for step in range(steps):
                real_batch = batch_to_device(real_batches[step % len(real_batches)], device)
                synthetic_batch = batch_to_device(
                    synthetic_batches[step % len(synthetic_batches)], device
                )
                include_physics = global_batch % int(settings["physics_every_batches"]) == 0
                real_part = real_losses(model, real_batch, config, include_physics)
                synthetic_part = synthetic_losses(
                    model, synthetic_batch, config, include_physics
                )
                total = (
                    float(settings["real_source_weight"]) * real_part["total"]
                    + float(settings["synthetic_source_weight"]) * synthetic_part["total"]
                )
                optimizer.zero_grad(set_to_none=True)
                total.backward()
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(), float(settings["gradient_clip_norm"])
                )
                optimizer.step()
                row = {"total": float(total.detach().cpu())}
                row.update(tensor_metrics(real_part, "real_"))
                row.update(tensor_metrics(synthetic_part, "synthetic_"))
                epoch_rows.append(row)
                global_batch += 1
        else:
            for raw_batch in real_batches:
                batch = batch_to_device(raw_batch, device)
                include_physics = global_batch % int(settings["physics_every_batches"]) == 0
                losses = real_losses(model, batch, config, include_physics)
                optimizer.zero_grad(set_to_none=True)
                losses["total"].backward()
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(), float(settings["gradient_clip_norm"])
                )
                optimizer.step()
                epoch_rows.append(tensor_metrics(losses))
                global_batch += 1

        training_mean = mean_rows(epoch_rows)
        validation_loss = validate_real(model, validation_set, config, device, run_seed)
        row = {"epoch": epoch + 1, "validation_real_forecast_mse": validation_loss}
        row.update({f"train_{key}": value for key, value in training_mean.items()})
        history.append(row)
        if math.isfinite(validation_loss) and validation_loss < best_validation:
            best_validation = validation_loss
            best_epoch = epoch
            torch.save(model.state_dict(), checkpoint)
        if epoch == 0 or (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            physics_value = sum(
                value for key, value in training_mean.items() if key.endswith("physics")
            )
            print(
                f"epoch={epoch + 1:04d} train={training_mean['total']:.6f} "
                f"real_validation={validation_loss:.6f} physics={physics_value:.6f}"
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
            "training_regime": regime,
        },
    )
    return history


def plot_history(history: list[dict[str, float]], path: Path, config: dict[str, Any]) -> None:
    regime = str(config["training_regime"])
    if regime == "hybrid":
        series = (
            ("train_total", "Hybrid training total"),
            ("validation_real_forecast_mse", "Real validation forecast MSE"),
            ("train_real_data", "Real-trajectory loss"),
            ("train_synthetic_consistency", "Synthetic inferred-gain consistency"),
        )
    else:
        series = (
            ("train_total", "Training total"),
            ("validation_real_forecast_mse", "Real validation forecast MSE"),
            ("train_data", "Real-trajectory loss"),
            ("train_physics", "Physics residual"),
        )
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for axis, (key, title) in zip(axes.flat, series):
        values = [row.get(key, 0.0) for row in history]
        axis.plot([row["epoch"] for row in history], values)
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


def evaluate_test(model, dataset, config, device, output_dir: Path):
    import torch

    model.eval()
    controller_semantics = str(config["model"]["controller_semantics"])
    display_name = str(config["display_name"])
    rows: list[dict[str, Any]] = []
    pooled = {"target_theta": [], "target_x": [], "prediction": []}
    prediction_dir = output_dir / "test_predictions"
    prediction_dir.mkdir(parents=True, exist_ok=True)

    with torch.no_grad():
        for raw_index in range(len(dataset)):
            raw = dataset[raw_index]
            batch = {
                key: value.unsqueeze(0).to(device) if hasattr(value, "unsqueeze") else [value]
                for key, value in raw.items()
            }
            _, prediction, controller, log_variance = infer_real(model, batch, config)
            time = batch["time_s"][0].cpu().numpy()
            valid = batch["valid_mask"][0].cpu().numpy() > 0.5
            forecast = valid & (time >= float(config["model"]["context_region_s"]))
            if not np.any(forecast):
                raise ValueError(f"No forecast samples for {raw['trial']}")
            target_theta = batch["theta_rad"][0].cpu().numpy()[forecast]
            target_x = batch["x_m"][0].cpu().numpy()[forecast]
            predicted = prediction[0].cpu().numpy()[forecast]
            forecast_time = time[forecast]
            trial = str(raw["trial"])
            subject = str(raw["subject"])
            controller_normalized = controller[0].cpu().numpy()
            controller_values = (
                controller_normalized * model.gain_scale.detach().cpu().numpy()
                if controller_semantics == "physical_gains"
                else controller_normalized
            )
            angular_residual, horizontal_residual, residual_mask = (
                physics_residual_components(
                    prediction,
                    controller * model.gain_scale,
                    batch["pi_rad"],
                    batch["tau_s"],
                    batch["time_s"],
                    config["physics"],
                    batch.get("physics_mask", batch["valid_mask"]),
                )
            )
            angular_residual = angular_residual[0].cpu().numpy()
            horizontal_residual = horizontal_residual[0].cpu().numpy()
            residual_valid = residual_mask[0].cpu().numpy().astype(bool)
            if not np.any(residual_valid):
                raise ValueError(f"No valid physics residual samples for {raw['trial']}")
            angular_values = angular_residual[residual_valid]
            horizontal_values = horizontal_residual[residual_valid]
            metrics = metric_bundle(
                target_theta,
                target_x,
                predicted,
                float(config["model"]["theta_scale_rad"]),
                float(config["model"]["x_scale_m"]),
            )
            target_cross = first_crossing(forecast_time, target_theta)
            predicted_cross = first_crossing(forecast_time, predicted[:, 0])
            row: dict[str, Any] = {
                "subject": subject,
                "trial": trial,
                "forecast_samples": int(forecast.sum()),
                "apparent_contact_time_s": float(time[valid][-1]),
                "forecast_to_contact_duration_s": float(
                    time[valid][-1] - float(config["model"]["context_region_s"])
                ),
                **metrics,
                "target_abs_theta_10deg_crossing_s": target_cross,
                "predicted_abs_theta_10deg_crossing_s": predicted_cross,
                "abs_theta_10deg_crossing_error_s": (
                    abs(predicted_cross - target_cross)
                    if predicted_cross is not None and target_cross is not None
                    else None
                ),
                "physics_residual_samples": int(residual_valid.sum()),
                "angular_residual_rmse": float(np.sqrt(np.mean(angular_values**2))),
                "angular_residual_mae": float(np.mean(np.abs(angular_values))),
                "horizontal_residual_rmse": float(
                    np.sqrt(np.mean(horizontal_values**2))
                ),
                "horizontal_residual_mae": float(np.mean(np.abs(horizontal_values))),
            }
            if controller_semantics == "physical_gains":
                for index, name in enumerate(GAIN_NAMES):
                    row[f"inferred_{name}"] = float(controller_values[index])
            else:
                for index, value in enumerate(controller_values):
                    row[f"inferred_latent_z{index}"] = float(value)
            rows.append(row)
            pooled["target_theta"].append(target_theta)
            pooled["target_x"].append(target_x)
            pooled["prediction"].append(predicted)
            prediction_payload = {
                "time_s": forecast_time,
                "target_theta_rad": target_theta,
                "target_x_m": target_x,
                "predicted_theta_rad": predicted[:, 0],
                "predicted_x_m": predicted[:, 1],
                "inferred_controller": controller_values,
                "controller_semantics": np.asarray(controller_semantics),
                "full_time_s": time,
                "angular_physics_residual": angular_residual,
                "horizontal_physics_residual": horizontal_residual,
                "physics_residual_mask": residual_valid.astype(np.uint8),
            }
            if bool(config["model"]["controller_uncertainty_trained"]):
                prediction_payload["controller_log_variance"] = (
                    log_variance[0].cpu().numpy()
                )
            np.savez_compressed(prediction_dir / f"{trial}.npz", **prediction_payload)
            fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
            axes[0].plot(forecast_time, np.degrees(target_theta), label="Real")
            axes[0].plot(forecast_time, np.degrees(predicted[:, 0]), "--", label=display_name)
            axes[0].set_ylabel("Theta (deg)")
            axes[1].plot(forecast_time, 100.0 * target_x, label="Real")
            axes[1].plot(forecast_time, 100.0 * predicted[:, 1], "--", label=display_name)
            axes[1].set_ylabel("Forward x (cm)")
            axes[1].set_xlabel("Time from pole-compatible clip start (s)")
            for axis in axes:
                axis.grid(alpha=0.25)
                axis.legend()
            fig.suptitle(f"Held-out test: {trial}")
            fig.tight_layout()
            fig.savefig(prediction_dir / f"{trial}.png", dpi=180)
            plt.close(fig)

            fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
            axes[0].plot(
                time[residual_valid], angular_values, color="tab:blue", linewidth=1.2
            )
            axes[0].axhline(0.0, color="black", linewidth=0.8)
            axes[0].set_ylabel("Angular residual")
            axes[1].plot(
                time[residual_valid], horizontal_values, color="tab:orange", linewidth=1.2
            )
            axes[1].axhline(0.0, color="black", linewidth=0.8)
            axes[1].set_ylabel("Horizontal residual")
            axes[1].set_xlabel("Time from clip start (s)")
            for axis in axes:
                axis.grid(alpha=0.25)
            fig.suptitle(f"Physics residuals: {trial}")
            fig.tight_layout()
            fig.savefig(prediction_dir / f"{trial}_physics_residuals.png", dpi=180)
            plt.close(fig)

    write_csv(output_dir / "test_metrics_by_trial.csv", rows)
    subject_rows = []
    subject_metrics = {}
    for subject in sorted({str(row["subject"]) for row in rows}):
        selected = [row for row in rows if str(row["subject"]) == subject]
        metrics = {
            metric: float(np.mean([float(row[metric]) for row in selected]))
            for metric in METRICS
        }
        physics_diagnostics = {
            key: float(np.mean([float(row[key]) for row in selected]))
            for key in (
                "angular_residual_rmse",
                "angular_residual_mae",
                "horizontal_residual_rmse",
                "horizontal_residual_mae",
            )
        }
        subject_metrics[subject] = {**metrics, **physics_diagnostics}
        subject_rows.append(
            {
                "subject": subject,
                "test_trial_count": len(selected),
                "test_forecast_sample_count": int(
                    sum(int(row["forecast_samples"]) for row in selected)
                ),
                **metrics,
                **physics_diagnostics,
            }
        )
    write_csv(output_dir / "test_metrics_by_subject.csv", subject_rows)
    target_theta = np.concatenate(pooled["target_theta"])
    target_x = np.concatenate(pooled["target_x"])
    prediction = np.concatenate(pooled["prediction"], axis=0)
    pooled_metrics = metric_bundle(
        target_theta,
        target_x,
        prediction,
        float(config["model"]["theta_scale_rad"]),
        float(config["model"]["x_scale_m"]),
    )
    trial_mean = {
        key: float(np.mean([float(row[key]) for row in rows])) for key in METRICS
    }
    return rows, pooled_metrics, trial_mean, subject_metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument(
        "--seed-index",
        type=int,
        default=1,
        help="One-based index into experiment.json optimization_seeds",
    )
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cuda", "cpu"))
    args = parser.parse_args()

    config = load_config(args.config)
    fold = fold_by_id(config, args.fold)
    base_seed, seed_label = seed_spec(config, args.seed_index)
    run_seed = base_seed + int(fold["id"])
    seed_everything(run_seed)
    device = choose_torch_device(args.device)
    real_records = load_real_records(args.mode)
    limit = 2 if args.mode == "smoke" else None
    real_train_set = build_real_dataset(
        real_records, list(fold["train"]), config, limit_per_subject=limit
    )
    validation_set = build_real_dataset(real_records, str(fold["validation"]), config)
    test_subjects = (
        list(fold["test"]) if isinstance(fold["test"], list) else [str(fold["test"])]
    )
    test_set = build_real_dataset(real_records, test_subjects, config)
    synthetic_train_set = None
    training_teacher_ids: list[str] = []
    if bool(config["requires_teachers"]):
        teacher_records = load_teacher_records(args.mode)
        training_teachers = [record for record in teacher_records if record.subject in fold["train"]]
        if {record.subject for record in training_teachers} != set(fold["train"]):
            raise ValueError("Fold is missing a training teacher")
        held_out = {str(fold["validation"]), *test_subjects}
        if {record.subject for record in training_teachers} & held_out:
            raise AssertionError("Held-out teacher leakage")
        synthetic_limit = 4 if args.mode == "smoke" else None
        synthetic_train_set = build_synthetic_dataset(
            teacher_records, list(fold["train"]), synthetic_limit
        )
        training_teacher_ids = [record.teacher_id for record in training_teachers]

    output_dir = (
        ROOT
        / "results"
        / args.mode
        / seed_label
        / f"fold_{int(fold['id']):02d}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_json(
        output_dir / "fold_manifest.json",
        {
            "experiment_name": config["experiment_name"],
            "model_id": config["model_id"],
            "training_regime": config["training_regime"],
            "fold": fold,
            "mode": args.mode,
            "seed_index": int(args.seed_index),
            "base_optimization_seed": base_seed,
            "effective_fold_seed": run_seed,
            "all_optimization_seeds": optimization_seeds(config),
            "device": str(device),
            "real_training_trial_count": len(real_train_set),
            "synthetic_training_trajectory_count": (
                len(synthetic_train_set) if synthetic_train_set is not None else 0
            ),
            "training_teacher_ids": training_teacher_ids,
            "validation_real_trial_count": len(validation_set),
            "test_real_trial_count": len(test_set),
            "validation_and_test_subjects_used_for_training": False,
            "test_real_data_used_for_model_selection": False,
            "context_windows": int(config["model"]["context_windows"]),
            "physics_loss_enabled": bool(config["training"]["use_physics"]),
            "controller_semantics": config["model"]["controller_semantics"],
            "fixed_pi_rad": float(config["physics"]["fixed_pi_rad"]),
            "fixed_tau_s": float(config["physics"]["fixed_tau_s"]),
        },
    )

    model = create_model(config).to(device)
    history = train(
        model,
        real_train_set,
        synthetic_train_set,
        validation_set,
        config,
        device,
        output_dir,
        args.mode,
        run_seed,
    )
    write_csv(output_dir / "training_history.csv", history)
    plot_history(history, output_dir / "training_history.png", config)
    rows, pooled_metrics, trial_mean, subject_metrics = evaluate_test(
        model, test_set, config, device, output_dir
    )
    import torch

    torch.save(model.state_dict(), output_dir / "final_best_model_state.pt")
    summary = {
        "experiment_name": config["experiment_name"],
        "model_id": config["model_id"],
        "display_name": config["display_name"],
        "training_regime": config["training_regime"],
        "fold": int(fold["id"]),
        "seed_index": int(args.seed_index),
        "base_optimization_seed": base_seed,
        "effective_fold_seed": run_seed,
        "train_subjects": list(fold["train"]),
        "validation_subject": fold["validation"],
        "test_subjects": test_subjects,
        "test_trial_count": len(rows),
        "test_forecast_sample_count": int(sum(row["forecast_samples"] for row in rows)),
        "test_pooled_metrics": pooled_metrics,
        "test_trial_mean_metrics": trial_mean,
        "test_subject_mean_metrics": subject_metrics,
        "four_window_context": True,
        "context_region_s": float(config["model"]["context_region_s"]),
        "physics_loss_enabled": bool(config["training"]["use_physics"]),
        "checkpoint_selected_only_on_real_validation_subject": True,
    }
    dump_json(output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
