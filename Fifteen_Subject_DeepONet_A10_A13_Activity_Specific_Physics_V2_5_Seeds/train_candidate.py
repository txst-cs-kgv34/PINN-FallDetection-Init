#!/usr/bin/env python3
"""Train one A10-A13 global-lambda arm from matched initialization."""

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

from calibration_core import (
    calibrated_losses,
    candidate_weights,
    gradient_l2_norm,
    load_torch_state,
    model_state_sha256,
    ramped_weight,
    weight_label,
)
from operator_core import (
    ROOT,
    batch_to_device,
    build_dataset,
    choose_torch_device,
    create_model,
    dump_json,
    fold_by_id,
    iter_batches,
    load_config,
    load_real_records,
    real_losses,
    seed_everything,
    seed_spec,
)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def validate_forecast(model, dataset, config, device, seed: int) -> float:
    import torch

    model.eval()
    grouped: dict[tuple[str, str], list[float]] = {}
    with torch.no_grad():
        for raw in iter_batches(dataset, 1, False, seed):
            batch = batch_to_device(raw, device)
            losses = real_losses(model, batch, config, "planar", False)
            key = (str(raw["subject"][0]), str(raw["activity"][0]))
            grouped.setdefault(key, []).append(float(losses["data"].cpu()))
    # Each available subject-activity cell receives equal selection weight.
    return float(np.mean([np.mean(values) for values in grouped.values()]))


def plot_history(history: list[dict[str, Any]], path: Path) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(13, 11))
    series = [
        ("validation_forecast_mse", "Validation forecast MSE"),
        ("train_data", "Training forecast loss"),
        ("train_angular_physics", "Normalized angular residual loss"),
        ("train_horizontal_physics", "Normalized horizontal residual loss"),
        ("current_physics_weight", "Physics-weight ramp"),
        ("physics_to_data_gradient_ratio", "Physics/data gradient-norm ratio"),
    ]
    for axis, (key, title) in zip(axes.flat, series):
        axis.plot([row["epoch"] for row in history], [row.get(key, np.nan) for row in history])
        axis.set_title(title)
        axis.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def train(
    model,
    train_set,
    validation_set,
    config: dict[str, Any],
    target_weight: float,
    device,
    output_dir: Path,
    mode: str,
    run_seed: int,
) -> list[dict[str, Any]]:
    import torch

    calibration = config["calibration"]
    settings = config["training"]
    epochs = 3 if mode == "smoke" else int(calibration["training_epochs"])
    patience = epochs + 1 if mode == "smoke" else int(calibration["early_stopping_patience"])
    ramp_epochs = min(3, int(calibration["ramp_epochs"])) if mode == "smoke" else int(calibration["ramp_epochs"])
    minimum_epochs = epochs if mode == "smoke" else int(calibration["minimum_training_epochs"])
    batch_size = min(3, int(settings["batch_size"])) if mode == "smoke" else int(settings["batch_size"])
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(calibration["learning_rate"]),
        weight_decay=float(settings["weight_decay"]),
    )
    initial_validation = validate_forecast(model, validation_set, config, device, run_seed)
    best = float("inf")
    best_epoch = -1
    checkpoint = output_dir / "best_model_state.pt"
    history: list[dict[str, Any]] = []
    global_batch = 0
    for epoch_index in range(epochs):
        completed_epoch = epoch_index + 1
        current_weight = ramped_weight(target_weight, completed_epoch, ramp_epochs)
        model.train()
        epoch_rows = []
        batches = iter_batches(
            train_set,
            batch_size,
            True,
            run_seed + epoch_index,
            str(settings.get("sampling_balance", "none")),
        )
        for batch_index, raw in enumerate(batches):
            batch = batch_to_device(raw, device)
            losses = calibrated_losses(model, batch, config, current_weight)
            data_gradient = math.nan
            physics_gradient = math.nan
            if batch_index == 0:
                data_gradient = gradient_l2_norm(losses["data"], model.parameters())
                physics_gradient = gradient_l2_norm(losses["cartpole_physics"], model.parameters())
            optimizer.zero_grad(set_to_none=True)
            losses["total"].backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(settings["gradient_clip_norm"]))
            optimizer.step()
            global_batch += 1
            epoch_rows.append({
                key: float(value.detach().cpu())
                for key, value in losses.items()
                if key not in {"prediction", "controller", "controller_logvar"}
            } | {
                "data_gradient_l2": data_gradient,
                "physics_gradient_l2": physics_gradient,
            })
        mean = {
            key: float(np.nanmean([row[key] for row in epoch_rows]))
            for key in epoch_rows[0]
        }
        validation = validate_forecast(model, validation_set, config, device, run_seed)
        gradient_ratio = (
            current_weight * mean["physics_gradient_l2"] / mean["data_gradient_l2"]
            if mean["data_gradient_l2"] > 0.0 else math.nan
        )
        history.append({
            "epoch": completed_epoch,
            "target_physics_weight": target_weight,
            "current_physics_weight": current_weight,
            "validation_forecast_mse": validation,
            "physics_to_data_gradient_ratio": gradient_ratio,
            **{f"train_{key}": value for key, value in mean.items()},
        })
        if math.isfinite(validation) and validation < best:
            best = validation
            best_epoch = completed_epoch
            torch.save(model.state_dict(), checkpoint)
        if completed_epoch == 1 or completed_epoch % 10 == 0 or completed_epoch == epochs:
            print(
                f"lambda={target_weight:g} epoch={completed_epoch:04d} "
                f"ramped={current_weight:.6g} train={mean['total']:.6f} "
                f"validation={validation:.6f} grad_ratio={gradient_ratio:.4g}"
            )
        patience_anchor = max(best_epoch, minimum_epochs)
        if completed_epoch >= minimum_epochs and completed_epoch - patience_anchor >= patience:
            print(f"Early stopping at epoch {completed_epoch}; best epoch {best_epoch}")
            break
    if not checkpoint.is_file():
        raise RuntimeError("no finite validation checkpoint was produced")
    model.load_state_dict(load_torch_state(checkpoint, device))
    dump_json(output_dir / "training_selection.json", {
        "target_physics_weight": target_weight,
        "best_epoch": best_epoch,
        "best_validation_forecast_mse": best,
        "random_initialization_validation_forecast_mse": initial_validation,
        "trained_from_scratch": True,
        "checkpoint_selected_only_on_validation_subjects": True,
        "test_data_accessed": False,
        "residual_scaling": config["calibration"]["residual_scaling"],
    })
    return history


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--seed-index", type=int, default=1)
    parser.add_argument("--target-weight", type=float, required=True)
    parser.add_argument("--device", choices=("auto", "mps", "cuda", "cpu"), default="auto")
    args = parser.parse_args()
    config = load_config(args.config)
    allowed = candidate_weights(config, include_baseline=True)
    if not any(math.isclose(args.target_weight, value, rel_tol=0.0, abs_tol=1e-15) for value in allowed):
        raise ValueError(f"target weight {args.target_weight} is not one of {allowed}")
    target_weight = next(value for value in allowed if math.isclose(args.target_weight, value, rel_tol=0.0, abs_tol=1e-15))
    fold = fold_by_id(config, args.fold)
    base_seed, seed_label = seed_spec(config, args.seed_index)
    run_seed = base_seed + int(fold["id"])
    seed_everything(run_seed)
    device = choose_torch_device(args.device)
    records = load_real_records(args.mode, "planar")
    limit = 2 if args.mode == "smoke" else None
    train_set = build_dataset(records, list(fold["train"]), limit)
    validation_set = build_dataset(records, list(fold["validation"]))
    output_dir = ROOT / "results" / "candidates" / args.mode / weight_label(target_weight) / seed_label / f"fold_{int(fold['id']):02d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    model = create_model(config, "planar").to(device)
    initialization_sha256 = model_state_sha256(model)
    dump_json(output_dir / "candidate_manifest.json", {
        "experiment": config["experiment_name"],
        "fold": fold,
        "seed_index": args.seed_index,
        "base_seed": base_seed,
        "effective_seed": run_seed,
        "device": str(device),
        "target_physics_weight": target_weight,
        "initialization_sha256": initialization_sha256,
        "trained_from_scratch": True,
        "training_trials": len(train_set),
        "validation_trials": len(validation_set),
        "validation_subjects": list(fold["validation"]),
        "validation_metric": config["calibration"]["selection_metric"],
        "activity_specific_controller_heads": list(config["data"]["activities"]),
        "test_data_accessed": False,
        "optimizer": "AdamW",
        "learning_rate": float(config["calibration"]["learning_rate"]),
        "maximum_epochs": int(config["calibration"]["training_epochs"]),
        "early_stopping_patience": int(config["calibration"]["early_stopping_patience"]),
    })
    history = train(model, train_set, validation_set, config, target_weight, device, output_dir, args.mode, run_seed)
    write_csv(output_dir / "training_history.csv", history)
    plot_history(history, output_dir / "training_history.png")
    import torch
    torch.save(model.state_dict(), output_dir / "final_best_model_state.pt")
    print(json.dumps(json.loads((output_dir / "training_selection.json").read_text()), indent=2))


if __name__ == "__main__":
    main()
