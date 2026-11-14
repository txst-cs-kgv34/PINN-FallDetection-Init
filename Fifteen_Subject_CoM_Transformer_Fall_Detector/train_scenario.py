from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from detector_core import (
    BalancedBatchSampler,
    TrajectoryWindowDataset,
    aggregate_trials,
    balanced_bce_loss,
    binary_metrics,
    canonical_scenario,
    choose_device,
    collate_windows,
    false_positive_events_per_adl_minute,
    fit_training_scaler,
    json_ready,
    load_config,
    prediction_frame,
    read_manifest,
    select_validation_threshold,
    set_reproducible_seed,
    split_scenario_rows,
    write_json,
)
from model import CoMTemporalTransformer


def build_model(config: dict[str, Any]) -> CoMTemporalTransformer:
    return CoMTemporalTransformer(
        window_length=int(config["window_length"]),
        d_model=int(config["d_model"]),
        nhead=int(config["nhead"]),
        num_layers=int(config["num_transformer_layers"]),
        dim_feedforward=int(config["dim_feedforward"]),
        dropout=float(config["dropout"]),
    )


def make_dataset(
    rows,
    config: dict[str, Any],
    scaler: dict[str, Any],
    training: bool,
) -> TrajectoryWindowDataset:
    return TrajectoryWindowDataset(
        rows=rows,
        data_root=Path(config["data_root"]),
        scaler=scaler,
        window_length=int(config["window_length"]),
        adl_stride=int(config["adl_stride"]),
        training=training,
        max_train_adl_windows_per_trial=(
            int(config["max_train_adl_windows_per_trial"]) if training else None
        ),
    )


@torch.no_grad()
def evaluate(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> tuple[float, pd.DataFrame]:
    model.eval()
    all_logits: list[torch.Tensor] = []
    all_labels: list[torch.Tensor] = []
    all_metadata: list[dict[str, Any]] = []
    for features, masks, labels, metadata in loader:
        logits = model(features.to(device), masks.to(device))
        all_logits.append(logits.detach().cpu())
        all_labels.append(labels.detach().cpu())
        all_metadata.extend(metadata)
    logits = torch.cat(all_logits)
    labels = torch.cat(all_labels)
    loss = float(balanced_bce_loss(logits, labels).item())
    probabilities = torch.sigmoid(logits).numpy()
    frame = prediction_frame(probabilities, labels.numpy().astype(int), all_metadata)
    return loss, frame


def plot_history(history: pd.DataFrame, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(7, 4.2))
    axis.plot(history["epoch"], history["train_loss"], label="training")
    axis.plot(history["epoch"], history["validation_balanced_loss"], label="validation")
    axis.set_xlabel("Epoch")
    axis.set_ylabel("Balanced binary cross-entropy")
    axis.set_title("Training history")
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def run_one(
    scenario: str,
    fold_index: int,
    seed: int,
    config: dict[str, Any],
    rows,
    device: torch.device,
    overwrite: bool,
) -> dict[str, Any]:
    fold_name = config["folds"][fold_index]["name"]
    run_dir = Path(config["output_root"]) / scenario / fold_name / f"seed_{seed:05d}"
    metrics_path = run_dir / "metrics.json"
    if metrics_path.is_file() and not overwrite:
        return json.loads(metrics_path.read_text())
    if run_dir.exists() and overwrite:
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    set_reproducible_seed(seed)
    split_rows, partitions = split_scenario_rows(rows, config, scenario, fold_index)
    scaler = fit_training_scaler(split_rows["train"], Path(config["data_root"]))
    write_json(run_dir / "scaler.json", scaler)

    training = make_dataset(split_rows["train"], config, scaler, training=True)
    validation = make_dataset(split_rows["validation"], config, scaler, training=False)
    test = make_dataset(split_rows["test"], config, scaler, training=False)

    sampler = BalancedBatchSampler(
        training.labels,
        batch_size=int(config["batch_size"]),
        steps=int(config["steps_per_epoch"]),
        seed=seed,
    )
    training_loader = DataLoader(
        training,
        batch_sampler=sampler,
        num_workers=int(config.get("num_workers", 0)),
        collate_fn=collate_windows,
    )
    evaluation_batch_size = max(128, int(config["batch_size"]))
    validation_loader = DataLoader(
        validation,
        batch_size=evaluation_batch_size,
        shuffle=False,
        num_workers=int(config.get("num_workers", 0)),
        collate_fn=collate_windows,
    )
    test_loader = DataLoader(
        test,
        batch_size=evaluation_batch_size,
        shuffle=False,
        num_workers=int(config.get("num_workers", 0)),
        collate_fn=collate_windows,
    )

    model = build_model(config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=max(2, int(config["early_stopping_patience"]) // 3)
    )
    criterion = torch.nn.BCEWithLogitsLoss()
    best_loss = float("inf")
    best_epoch = 0
    epochs_without_improvement = 0
    history_records: list[dict[str, float | int]] = []
    checkpoint_path = run_dir / "best_model.pt"
    started = time.time()

    for epoch in range(1, int(config["max_epochs"]) + 1):
        model.train()
        train_losses: list[float] = []
        for features, masks, labels, _ in training_loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(features.to(device), masks.to(device))
            loss = criterion(logits, labels.to(device))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), float(config["gradient_clip_norm"])
            )
            optimizer.step()
            train_losses.append(float(loss.item()))
        validation_loss, _ = evaluate(model, validation_loader, device)
        scheduler.step(validation_loss)
        history_records.append(
            {
                "epoch": epoch,
                "train_loss": float(np.mean(train_losses)),
                "validation_balanced_loss": validation_loss,
                "learning_rate": float(optimizer.param_groups[0]["lr"]),
            }
        )
        if validation_loss < best_loss - 1e-6:
            best_loss = validation_loss
            best_epoch = epoch
            epochs_without_improvement = 0
            state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
            torch.save(
                {
                    "model_state_dict": state,
                    "scenario": scenario,
                    "fold": fold_name,
                    "seed": seed,
                    "best_epoch": best_epoch,
                },
                checkpoint_path,
            )
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= int(config["early_stopping_patience"]):
                break

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    validation_loss, validation_windows = evaluate(model, validation_loader, device)
    test_loss, test_windows = evaluate(model, test_loader, device)
    validation_trials = aggregate_trials(validation_windows)
    threshold = select_validation_threshold(
        validation_trials["label"], validation_trials["probability"]
    )
    test_trials = aggregate_trials(test_windows)

    validation_windows["prediction"] = (
        validation_windows["probability"] >= threshold
    ).astype(int)
    validation_trials["prediction"] = (
        validation_trials["probability"] >= threshold
    ).astype(int)
    test_windows["prediction"] = (test_windows["probability"] >= threshold).astype(int)
    test_trials["prediction"] = (test_trials["probability"] >= threshold).astype(int)

    validation_window_metrics = binary_metrics(
        validation_windows["label"], validation_windows["probability"], threshold
    )
    validation_trial_metrics = binary_metrics(
        validation_trials["label"], validation_trials["probability"], threshold
    )
    test_window_metrics = binary_metrics(
        test_windows["label"], test_windows["probability"], threshold
    )
    test_trial_metrics = binary_metrics(
        test_trials["label"], test_trials["probability"], threshold
    )
    fp_rate, fp_events, adl_minutes = false_positive_events_per_adl_minute(
        test_windows, threshold
    )

    metrics: dict[str, Any] = {
        "scenario": scenario,
        "fold": fold_name,
        "fold_index": fold_index + 1,
        "seed": seed,
        "device": str(device),
        "best_epoch": best_epoch,
        "epochs_completed": len(history_records),
        "best_validation_balanced_loss": best_loss,
        "final_validation_balanced_loss": validation_loss,
        "test_balanced_loss": test_loss,
        "validation_threshold": threshold,
        "elapsed_seconds": time.time() - started,
        "train_trajectory_count": len(split_rows["train"]),
        "validation_trajectory_count": len(split_rows["validation"]),
        "test_trajectory_count": len(split_rows["test"]),
        "train_window_count": len(training),
        "validation_window_count": len(validation),
        "test_window_count": len(test),
        "train_positive_windows": int(sum(training.labels)),
        "train_negative_windows": int(len(training.labels) - sum(training.labels)),
        "false_positive_events_per_adl_minute": fp_rate,
        "false_positive_events": fp_events,
        "test_adl_minutes": adl_minutes,
    }
    for prefix, values in (
        ("validation_window", validation_window_metrics),
        ("validation_trial", validation_trial_metrics),
        ("test_window", test_window_metrics),
        ("test_trial", test_trial_metrics),
    ):
        metrics.update({f"{prefix}_{key}": value for key, value in values.items()})

    history = pd.DataFrame.from_records(history_records)
    history.to_csv(run_dir / "history.csv", index=False)
    validation_windows.to_csv(run_dir / "validation_window_predictions.csv", index=False)
    validation_trials.to_csv(run_dir / "validation_trial_predictions.csv", index=False)
    test_windows.to_csv(run_dir / "test_window_predictions.csv", index=False)
    test_trials.to_csv(run_dir / "test_trial_predictions.csv", index=False)
    plot_history(history, run_dir / "training_history.png")
    write_json(
        run_dir / "run_configuration.json",
        {
            "scenario": scenario,
            "fold": fold_name,
            "seed": seed,
            "device": str(device),
            "split_groups": {key: sorted(value) for key, value in partitions.items()},
            "config": config,
        },
    )
    write_json(metrics_path, metrics)
    print(
        f"[{scenario}] {fold_name} seed={seed}: "
        f"balanced_accuracy={metrics['test_trial_balanced_accuracy']:.4f}, "
        f"F1={metrics['test_trial_f1']:.4f}, threshold={threshold:.4f}"
    )
    return metrics


def refresh_scenario_summary(scenario: str, output_root: Path) -> None:
    scenario_dir = output_root / scenario
    records = []
    for path in sorted(scenario_dir.glob("fold_*/seed_*/metrics.json")):
        records.append(json.loads(path.read_text()))
    if not records:
        return
    frame = pd.DataFrame.from_records(records).sort_values(["fold_index", "seed"])
    frame.to_csv(scenario_dir / "run_summary.csv", index=False)
    summary: dict[str, Any] = {
        "scenario": scenario,
        "completed_runs": len(frame),
        "folds": sorted(frame["fold"].unique().tolist()),
        "seeds": sorted(int(value) for value in frame["seed"].unique()),
        "metrics": {},
    }
    for column in frame.columns:
        if column.startswith("test_trial_") or column == "false_positive_events_per_adl_minute":
            numeric = pd.to_numeric(frame[column], errors="coerce")
            summary["metrics"][column] = {
                "mean": float(numeric.mean()),
                "standard_deviation": float(numeric.std(ddof=1)),
                "minimum": float(numeric.min()),
                "maximum": float(numeric.max()),
            }
    write_json(scenario_dir / "scenario_summary.json", summary)


def parse_int_list(values: Sequence[str] | None) -> list[int] | None:
    if not values:
        return None
    result: list[int] = []
    for value in values:
        result.extend(int(item) for item in value.split(",") if item.strip())
    return result


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Train one CoM fall-detector scenario.")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    parser.add_argument("--folds", nargs="*", help="1-based fold numbers, e.g. --folds 1 2")
    parser.add_argument("--seeds", nargs="*", help="Seed values, e.g. --seeds 11 22")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-epochs", type=int)
    parser.add_argument("--steps-per-epoch", type=int)
    args = parser.parse_args(argv)

    scenario = canonical_scenario(args.scenario)
    config = load_config(args.config)
    if args.max_epochs is not None:
        config["max_epochs"] = args.max_epochs
    if args.steps_per_epoch is not None:
        config["steps_per_epoch"] = args.steps_per_epoch
    selected_folds = parse_int_list(args.folds) or list(range(1, len(config["folds"]) + 1))
    selected_seeds = parse_int_list(args.seeds) or [int(value) for value in config["seeds"]]
    if any(index < 1 or index > len(config["folds"]) for index in selected_folds):
        raise ValueError(f"Fold numbers must be between 1 and {len(config['folds'])}")
    device = choose_device(args.device)
    rows = read_manifest(Path(config["data_root"]))
    print(
        f"Scenario: {scenario}\nDevice: {device}\n"
        f"Folds: {selected_folds}\nSeeds: {selected_seeds}"
    )
    for fold_number in selected_folds:
        for seed in selected_seeds:
            run_one(
                scenario,
                fold_number - 1,
                seed,
                config,
                rows,
                device,
                args.overwrite,
            )
    refresh_scenario_summary(scenario, Path(config["output_root"]))


if __name__ == "__main__":
    main()

