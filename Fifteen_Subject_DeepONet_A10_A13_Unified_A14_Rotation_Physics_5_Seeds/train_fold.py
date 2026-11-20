#!/usr/bin/env python3
"""Train one subject-held-out fold for the planar or A14 rotation model."""

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
    ROOT, batch_to_device, build_dataset, choose_torch_device, create_model,
    dump_json, fold_by_id, infer, iter_batches, load_config, load_real_records,
    metric_names, optimization_seeds, physics_residual_components, real_losses,
    seed_everything, seed_spec,
)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows: return
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = []
    for row in rows:
        for key in row:
            if key not in keys: keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)


def load_state(path: Path, device):
    import torch
    try: return torch.load(path, map_location=device, weights_only=True)
    except TypeError: return torch.load(path, map_location=device)


def validate(model, dataset, config, model_group: str, device, seed: int) -> float:
    import torch
    model.eval(); values = []
    with torch.no_grad():
        for raw in iter_batches(dataset, 1, False, seed):
            batch = batch_to_device(raw, device)
            losses = real_losses(model, batch, config, model_group, False)
            values.append(float(losses["data"].cpu()))
    return float(np.mean(values))


def train(model, train_set, validation_set, config, model_group: str, device, output_dir: Path, mode: str, run_seed: int):
    import torch
    settings = config["training"]
    epochs = 3 if mode == "smoke" else int(settings["epochs"])
    batch_size = min(3, int(settings["batch_size"])) if mode == "smoke" else int(settings["batch_size"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(settings["learning_rate"]), weight_decay=float(settings["weight_decay"]))
    best = float("inf"); best_epoch = -1; history = []; global_batch = 0
    checkpoint = output_dir / "best_model_state.pt"
    for epoch in range(epochs):
        model.train(); epoch_rows = []
        batches = iter_batches(train_set, batch_size, True, run_seed + epoch, str(settings.get("sampling_balance", "none")))
        for raw in batches:
            batch = batch_to_device(raw, device)
            include_physics = global_batch % int(settings["physics_every_batches"]) == 0
            losses = real_losses(model, batch, config, model_group, include_physics)
            optimizer.zero_grad(set_to_none=True); losses["total"].backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(settings["gradient_clip_norm"]))
            optimizer.step(); global_batch += 1
            epoch_rows.append({key: float(value.detach().cpu()) for key, value in losses.items() if key not in {"prediction", "controller", "controller_logvar"}})
        mean = {key: float(np.mean([row[key] for row in epoch_rows])) for key in epoch_rows[0]}
        validation_value = validate(model, validation_set, config, model_group, device, run_seed)
        row = {"epoch": epoch + 1, "validation_forecast_mse": validation_value, **{f"train_{key}": value for key, value in mean.items()}}
        history.append(row)
        if math.isfinite(validation_value) and validation_value < best:
            best = validation_value; best_epoch = epoch; torch.save(model.state_dict(), checkpoint)
        if epoch == 0 or (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            print(f"{model_group} epoch={epoch+1:04d} train={mean['total']:.6f} validation={validation_value:.6f} cartpole={mean['cartpole_physics']:.6f} rotation={mean['rotation_physics']:.6f}")
        if epoch - best_epoch >= int(settings["early_stopping_patience"]):
            print(f"Early stopping at epoch {epoch+1}; best epoch {best_epoch+1}"); break
    if not checkpoint.is_file(): raise RuntimeError("no finite validation checkpoint")
    model.load_state_dict(load_state(checkpoint, device))
    dump_json(output_dir / "training_selection.json", {"best_epoch": best_epoch + 1, "best_validation_forecast_mse": best, "selection_subject_only": True})
    return history


def metric_bundle(target: np.ndarray, prediction: np.ndarray, config: dict, model_group: str) -> dict[str, float]:
    theta_error = prediction[:, 0] - target[:, 0]; x_error = prediction[:, 1] - target[:, 1]
    normalized = (theta_error / float(config["model"]["theta_scale_rad"])) ** 2 + (x_error / float(config["model"]["x_scale_m"])) ** 2
    result = {
        "normalized_mse": float(np.mean(normalized)),
        "theta_rmse_deg": float(np.degrees(np.sqrt(np.mean(theta_error ** 2)))),
        "theta_mae_deg": float(np.degrees(np.mean(np.abs(theta_error)))),
        "x_rmse_cm": float(100 * np.sqrt(np.mean(x_error ** 2))),
        "x_mae_cm": float(100 * np.mean(np.abs(x_error))),
        "theta_w1_deg": float(wasserstein_distance(np.degrees(target[:, 0]), np.degrees(prediction[:, 0]))),
        "x_w1_cm": float(wasserstein_distance(100 * target[:, 1], 100 * prediction[:, 1])),
    }
    if model_group == "rotation":
        yaw_error = prediction[:, 2] - target[:, 2]
        result["normalized_mse"] += float(np.mean((yaw_error / float(config["model"]["yaw_scale_rad"])) ** 2))
        result.update({
            "yaw_rmse_deg": float(np.degrees(np.sqrt(np.mean(yaw_error ** 2)))),
            "yaw_mae_deg": float(np.degrees(np.mean(np.abs(yaw_error)))),
            "yaw_w1_deg": float(wasserstein_distance(np.degrees(target[:, 2]), np.degrees(prediction[:, 2]))),
        })
    return result


def aggregate_rows(rows: list[dict], key: str, model_group: str) -> dict[str, dict[str, float]]:
    output = {}
    for value in sorted({str(row[key]) for row in rows}):
        selected = [row for row in rows if str(row[key]) == value]
        output[value] = {metric: float(np.mean([float(row[metric]) for row in selected])) for metric in metric_names(model_group)}
        for diagnostic in ("angular_residual_rmse", "horizontal_residual_rmse", "yaw_residual_rmse"):
            if diagnostic in selected[0]: output[value][diagnostic] = float(np.mean([float(row[diagnostic]) for row in selected]))
    return output


def evaluate(model, dataset, config, model_group: str, device, output_dir: Path):
    import torch
    model.eval(); rows = []; prediction_dir = output_dir / "test_predictions"; prediction_dir.mkdir(parents=True, exist_ok=True)
    with torch.no_grad():
        for index in range(len(dataset)):
            raw = dataset[index]
            batch = {key: value.unsqueeze(0).to(device) if hasattr(value, "unsqueeze") else [value] for key, value in raw.items()}
            prediction, controller, _ = infer(model, batch, config, model_group)
            time = batch["time_s"][0].cpu().numpy(); valid = batch["valid_mask"][0].cpu().numpy() > 0.5
            forecast = valid & (time >= float(config["model"]["context_region_s"]))
            target_full = np.stack([batch["theta_rad"][0].cpu().numpy(), batch["x_m"][0].cpu().numpy()] + ([batch["yaw_rad"][0].cpu().numpy()] if model_group == "rotation" else []), axis=1)
            predicted_full = prediction[0].cpu().numpy(); target = target_full[forecast]; predicted = predicted_full[forecast]
            metrics = metric_bundle(target, predicted, config, model_group)
            gains = controller * model.gain_scale
            r1, r2, ryaw, residual_mask = physics_residual_components(
                prediction, gains, batch["time_s"], batch["mass_kg"], batch["height_m"], config["physics"], batch["physics_mask"], model_group
            )
            residual_valid = residual_mask[0].cpu().numpy().astype(bool)
            angular = r1[0].cpu().numpy()[residual_valid]; horizontal = r2[0].cpu().numpy()[residual_valid]
            row = {
                "subject": raw["subject"], "trial": raw["trial"], "activity": raw["activity"],
                "forecast_samples": int(forecast.sum()), **metrics,
                "angular_residual_rmse": float(np.sqrt(np.mean(angular ** 2))),
                "horizontal_residual_rmse": float(np.sqrt(np.mean(horizontal ** 2))),
            }
            if model_group == "rotation":
                yaw_values = ryaw[0].cpu().numpy()[residual_valid]
                row["yaw_residual_rmse"] = float(np.sqrt(np.mean(yaw_values ** 2)))
            rows.append(row)
            payload = {"time_s": time[forecast], "target_theta_rad": target[:, 0], "target_x_m": target[:, 1], "predicted_theta_rad": predicted[:, 0], "predicted_x_m": predicted[:, 1], "inferred_gains": gains[0].cpu().numpy()}
            if model_group == "rotation": payload.update({"target_yaw_rad": target[:, 2], "predicted_yaw_rad": predicted[:, 2]})
            np.savez_compressed(prediction_dir / f"{raw['trial']}.npz", **payload)
            panels = 3 if model_group == "rotation" else 2
            fig, axes = plt.subplots(panels, 1, figsize=(9, 3 * panels), sharex=True)
            axes[0].plot(time[forecast], np.degrees(target[:, 0]), label="Real"); axes[0].plot(time[forecast], np.degrees(predicted[:, 0]), "--", label="Predicted"); axes[0].set_ylabel("Theta (deg)")
            axes[1].plot(time[forecast], 100 * target[:, 1], label="Real"); axes[1].plot(time[forecast], 100 * predicted[:, 1], "--", label="Predicted"); axes[1].set_ylabel("x (cm)")
            if model_group == "rotation":
                axes[2].plot(time[forecast], np.degrees(target[:, 2]), label="Real"); axes[2].plot(time[forecast], np.degrees(predicted[:, 2]), "--", label="Predicted"); axes[2].set_ylabel("Yaw (deg)")
            for axis in axes: axis.grid(alpha=.25); axis.legend()
            axes[-1].set_xlabel("Time (s)"); fig.suptitle(f"Held-out {raw['trial']}"); fig.tight_layout(); fig.savefig(prediction_dir / f"{raw['trial']}.png", dpi=160); plt.close(fig)
    write_csv(output_dir / "test_metrics_by_trial.csv", rows)
    subject_metrics = aggregate_rows(rows, "subject", model_group); activity_metrics = aggregate_rows(rows, "activity", model_group)
    subject_rows = [{"subject": subject, **metrics} for subject, metrics in subject_metrics.items()]
    write_csv(output_dir / "test_metrics_by_subject.csv", subject_rows)
    write_csv(output_dir / "test_metrics_by_activity.csv", [{"activity": activity, **metrics} for activity, metrics in activity_metrics.items()])
    return rows, subject_metrics, activity_metrics


def plot_history(history: list[dict], path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8)); series = [("train_total", "Total"), ("validation_forecast_mse", "Validation"), ("train_data", "Data"), ("train_cartpole_physics", "CartPole physics")]
    for axis, (key, title) in zip(axes.flat, series):
        axis.plot([row["epoch"] for row in history], [row.get(key, 0) for row in history]); axis.set_title(title); axis.grid(alpha=.25); axis.set_yscale("symlog", linthresh=1e-7)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json"); parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--model-group", choices=("planar", "rotation"), required=True); parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--seed-index", type=int, default=1); parser.add_argument("--device", choices=("auto", "mps", "cuda", "cpu"), default="auto")
    args = parser.parse_args(); config = load_config(args.config); fold = fold_by_id(config, args.fold)
    base_seed, seed_label = seed_spec(config, args.seed_index); run_seed = base_seed + int(fold["id"]); seed_everything(run_seed); device = choose_torch_device(args.device)
    records = load_real_records(args.mode, args.model_group); limit = 2 if args.mode == "smoke" else None
    train_set = build_dataset(records, list(fold["train"]), limit); validation_set = build_dataset(records, str(fold["validation"])); test_set = build_dataset(records, list(fold["test"]))
    output_dir = ROOT / "results" / args.model_group / args.mode / seed_label / f"fold_{int(fold['id']):02d}"; output_dir.mkdir(parents=True, exist_ok=True)
    dump_json(output_dir / "fold_manifest.json", {"experiment": config["experiment_name"], "model_group": args.model_group, "fold": fold, "seed_index": args.seed_index, "base_seed": base_seed, "effective_seed": run_seed, "device": str(device), "training_trials": len(train_set), "validation_trials": len(validation_set), "test_trials": len(test_set), "physics_enabled": bool(config["training"]["use_physics"])})
    model = create_model(config, args.model_group).to(device); history = train(model, train_set, validation_set, config, args.model_group, device, output_dir, args.mode, run_seed)
    write_csv(output_dir / "training_history.csv", history); plot_history(history, output_dir / "training_history.png")
    rows, subject_metrics, activity_metrics = evaluate(model, test_set, config, args.model_group, device, output_dir)
    import torch; torch.save(model.state_dict(), output_dir / "final_best_model_state.pt")
    summary = {"experiment": config["experiment_name"], "display_name": config["display_name"], "model_group": args.model_group, "fold": int(fold["id"]), "seed_index": args.seed_index, "base_optimization_seed": base_seed, "effective_fold_seed": run_seed, "test_trial_count": len(rows), "test_forecast_sample_count": sum(int(row["forecast_samples"]) for row in rows), "test_subject_mean_metrics": subject_metrics, "test_activity_mean_metrics": activity_metrics, "physics_loss_enabled": bool(config["training"]["use_physics"]), "checkpoint_selected_only_on_validation_subject": True}
    dump_json(output_dir / "summary.json", summary); print(json.dumps(summary, indent=2))


if __name__ == "__main__": main()
