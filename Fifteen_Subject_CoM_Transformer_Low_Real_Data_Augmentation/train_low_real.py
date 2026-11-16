from __future__ import annotations

import argparse
import json
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from base_detector_imports import prepare_base_imports
from source_balanced_sampler import SourceBalancedBatchSampler
from subset_selection import select_stratified_subset, selection_digest


ALIASES = {
    "real-25": "real_25pct_real_adl",
    "augmented-25": "real_25pct_balanced_synthetic_real_adl",
    "real-50": "real_50pct_real_adl",
    "augmented-50": "real_50pct_balanced_synthetic_real_adl",
}


def parse_int_list(values: Sequence[str] | None) -> list[int] | None:
    if not values:
        return None
    result: list[int] = []
    for value in values:
        result.extend(int(item) for item in value.split(",") if item.strip())
    return result


def canonical_conditions(
    values: Sequence[str] | None, config: dict[str, Any]
) -> list[str]:
    available = list(config["conditions"])
    if not values or values == ["all"]:
        return available
    result: list[str] = []
    for value in values:
        for part in value.split(","):
            name = ALIASES.get(part.strip(), part.strip())
            if name not in available:
                raise ValueError(
                    f"Unknown condition {part!r}. Available: {', '.join(available)}"
                )
            if name not in result:
                result.append(name)
    return result


def select_real_falls(
    base_train_rows: list[dict[str, str]],
    config: dict[str, Any],
    base_core,
    fold_name: str,
    fraction: float,
) -> list[dict[str, str]]:
    real_falls = [row for row in base_train_rows if row["source_kind"] == "real_fall"]
    namespace = f"{config['subset_seed']}|{fold_name}|low-real-data"
    return select_stratified_subset(
        real_falls,
        fraction=fraction,
        group_key=lambda row: base_core.logical_group(row, config),
        item_id=lambda row: row["sample_id"],
        namespace=namespace,
    )


def prepare_condition_rows(
    base_train_rows: list[dict[str, str]],
    config: dict[str, Any],
    base_core,
    fold_name: str,
    condition: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    settings = config["conditions"][condition]
    fraction = float(settings["real_fraction"])
    selected_real = select_real_falls(
        base_train_rows, config, base_core, fold_name, fraction
    )
    selected_ids = {row["sample_id"] for row in selected_real}
    result = [row for row in base_train_rows if row["source_kind"] == "real_adl"]
    result.extend(
        row
        for row in base_train_rows
        if row["source_kind"] == "real_fall" and row["sample_id"] in selected_ids
    )
    if bool(settings["use_synthetic"]):
        result.extend(
            row for row in base_train_rows if row["source_kind"] == "synthetic_fall"
        )
    return sorted(result, key=lambda row: row["sample_id"]), selected_real


def write_subset_audit(
    rows: list[dict[str, str]], config: dict[str, Any], base_core
) -> Path:
    records: list[dict[str, object]] = []
    for fold_index, fold in enumerate(config["folds"]):
        split_rows, _ = base_core.split_scenario_rows(
            rows, config, "real_synthetic_fall_real_adl", fold_index
        )
        real_falls = [
            row for row in split_rows["train"] if row["source_kind"] == "real_fall"
        ]
        selections = {
            fraction: {
                row["sample_id"]
                for row in select_real_falls(
                    split_rows["train"], config, base_core, fold["name"], fraction
                )
            }
            for fraction in config["real_fall_fractions"]
        }
        for row in sorted(real_falls, key=lambda value: value["sample_id"]):
            records.append(
                {
                    "fold": fold["name"],
                    "sample_id": row["sample_id"],
                    "subject": row["subject"],
                    "source_subject": row["source_subject"],
                    "logical_group": base_core.logical_group(row, config),
                    "selected_25pct": row["sample_id"] in selections[0.25],
                    "selected_50pct": row["sample_id"] in selections[0.5],
                    "subset_seed": int(config["subset_seed"]),
                }
            )
    output = Path(config["output_root"])
    output.mkdir(parents=True, exist_ok=True)
    path = output / "real_fall_subset_audit.csv"
    pd.DataFrame.from_records(records).to_csv(path, index=False)
    return path


def run_one(
    condition: str,
    fold_index: int,
    seed: int,
    config: dict[str, Any],
    rows: list[dict[str, str]],
    device: torch.device,
    overwrite: bool,
    base_core,
    base_train,
) -> dict[str, Any]:
    fold_name = config["folds"][fold_index]["name"]
    run_dir = Path(config["output_root"]) / condition / fold_name / f"seed_{seed:05d}"
    metrics_path = run_dir / "metrics.json"
    if metrics_path.is_file() and not overwrite:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    if run_dir.exists() and overwrite:
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    base_core.set_reproducible_seed(seed)
    base_split, partitions = base_core.split_scenario_rows(
        rows, config, "real_synthetic_fall_real_adl", fold_index
    )
    training_rows, selected_real = prepare_condition_rows(
        base_split["train"], config, base_core, fold_name, condition
    )
    settings = config["conditions"][condition]
    use_synthetic = bool(settings["use_synthetic"])
    fraction = float(settings["real_fraction"])
    selected_ids = sorted(row["sample_id"] for row in selected_real)

    scaler = base_core.fit_training_scaler(training_rows, Path(config["data_root"]))
    base_core.write_json(run_dir / "scaler.json", scaler)
    training = base_train.make_dataset(training_rows, config, scaler, training=True)
    validation = base_train.make_dataset(
        base_split["validation"], config, scaler, training=False
    )
    test = base_train.make_dataset(base_split["test"], config, scaler, training=False)

    source_kinds = [
        training.rows[spec.row_index]["source_kind"] for spec in training.specs
    ]
    subject_groups = [
        base_core.logical_group(training.rows[spec.row_index], config)
        for spec in training.specs
    ]
    if use_synthetic:
        sampler = SourceBalancedBatchSampler(
            labels=training.labels,
            source_kinds=source_kinds,
            subject_groups=subject_groups,
            batch_size=int(config["batch_size"]),
            steps=int(config["steps_per_epoch"]),
            seed=seed,
            subject_balanced_within_source=bool(
                config.get("subject_balanced_within_source", False)
            ),
        )
        composition = sampler.batch_composition()
    else:
        sampler = base_core.BalancedBatchSampler(
            training.labels,
            batch_size=int(config["batch_size"]),
            steps=int(config["steps_per_epoch"]),
            seed=seed,
        )
        composition = {
            "real_adl": int(config["batch_size"]) // 2,
            "real_fall": int(config["batch_size"]) // 2,
            "synthetic_fall": 0,
            "total": int(config["batch_size"]),
        }
    training_loader = DataLoader(
        training,
        batch_sampler=sampler,
        num_workers=int(config.get("num_workers", 0)),
        collate_fn=base_core.collate_windows,
    )
    evaluation_batch_size = max(128, int(config["batch_size"]))
    validation_loader = DataLoader(
        validation,
        batch_size=evaluation_batch_size,
        shuffle=False,
        num_workers=int(config.get("num_workers", 0)),
        collate_fn=base_core.collate_windows,
    )
    test_loader = DataLoader(
        test,
        batch_size=evaluation_batch_size,
        shuffle=False,
        num_workers=int(config.get("num_workers", 0)),
        collate_fn=base_core.collate_windows,
    )

    model = base_train.build_model(config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.5,
        patience=max(2, int(config["early_stopping_patience"]) // 3),
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
        training_losses: list[float] = []
        for features, masks, labels, _ in training_loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(features.to(device), masks.to(device))
            loss = criterion(logits, labels.to(device))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                model.parameters(), float(config["gradient_clip_norm"])
            )
            optimizer.step()
            training_losses.append(float(loss.item()))
        validation_loss, _ = base_train.evaluate(model, validation_loader, device)
        scheduler.step(validation_loss)
        history_records.append(
            {
                "epoch": epoch,
                "train_loss": float(np.mean(training_losses)),
                "validation_balanced_loss": validation_loss,
                "learning_rate": float(optimizer.param_groups[0]["lr"]),
            }
        )
        if validation_loss < best_loss - 1e-6:
            best_loss = validation_loss
            best_epoch = epoch
            epochs_without_improvement = 0
            state = {
                key: value.detach().cpu() for key, value in model.state_dict().items()
            }
            torch.save(
                {
                    "model_state_dict": state,
                    "condition": condition,
                    "fold": fold_name,
                    "seed": seed,
                    "best_epoch": best_epoch,
                    "real_fraction": fraction,
                    "use_synthetic": use_synthetic,
                    "selected_real_fall_digest": selection_digest(selected_real),
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
    validation_loss, validation_windows = base_train.evaluate(
        model, validation_loader, device
    )
    test_loss, test_windows = base_train.evaluate(model, test_loader, device)
    validation_trials = base_core.aggregate_trials(validation_windows)
    threshold = base_core.select_validation_threshold(
        validation_trials["label"], validation_trials["probability"]
    )
    test_trials = base_core.aggregate_trials(test_windows)
    for frame in (validation_windows, validation_trials, test_windows, test_trials):
        frame["prediction"] = (frame["probability"] >= threshold).astype(int)

    validation_window_metrics = base_core.binary_metrics(
        validation_windows["label"], validation_windows["probability"], threshold
    )
    validation_trial_metrics = base_core.binary_metrics(
        validation_trials["label"], validation_trials["probability"], threshold
    )
    test_window_metrics = base_core.binary_metrics(
        test_windows["label"], test_windows["probability"], threshold
    )
    test_trial_metrics = base_core.binary_metrics(
        test_trials["label"], test_trials["probability"], threshold
    )
    fp_rate, fp_events, adl_minutes = base_core.false_positive_events_per_adl_minute(
        test_windows, threshold
    )
    pool_counts = Counter(source_kinds)
    metrics: dict[str, Any] = {
        "scenario": condition,
        "condition": condition,
        "fold": fold_name,
        "fold_index": fold_index + 1,
        "seed": seed,
        "device": str(device),
        "real_fraction": fraction,
        "use_synthetic": use_synthetic,
        "subset_seed": int(config["subset_seed"]),
        "selected_real_fall_count": len(selected_real),
        "available_real_fall_count": sum(
            row["source_kind"] == "real_fall" for row in base_split["train"]
        ),
        "selected_real_fall_digest": selection_digest(selected_real),
        "best_epoch": best_epoch,
        "epochs_completed": len(history_records),
        "best_validation_balanced_loss": best_loss,
        "final_validation_balanced_loss": validation_loss,
        "test_balanced_loss": test_loss,
        "validation_threshold": threshold,
        "elapsed_seconds": time.time() - started,
        "train_trajectory_count": len(training_rows),
        "validation_trajectory_count": len(base_split["validation"]),
        "test_trajectory_count": len(base_split["test"]),
        "train_window_count": len(training),
        "validation_window_count": len(validation),
        "test_window_count": len(test),
        "training_pool_real_adl_windows": int(pool_counts["real_adl"]),
        "training_pool_real_fall_windows": int(pool_counts["real_fall"]),
        "training_pool_synthetic_fall_windows": int(pool_counts["synthetic_fall"]),
        "batch_real_adl_windows": composition["real_adl"],
        "batch_real_fall_windows": composition["real_fall"],
        "batch_synthetic_fall_windows": composition["synthetic_fall"],
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
    base_train.plot_history(history, run_dir / "training_history.png")
    base_core.write_json(
        run_dir / "run_configuration.json",
        {
            "condition": condition,
            "fold": fold_name,
            "seed": seed,
            "device": str(device),
            "real_fraction": fraction,
            "use_synthetic": use_synthetic,
            "selected_real_fall_ids": selected_ids,
            "selected_real_fall_digest": selection_digest(selected_real),
            "batch_composition": composition,
            "split_groups": {key: sorted(value) for key, value in partitions.items()},
            "config": config,
        },
    )
    base_core.write_json(metrics_path, metrics)
    print(
        f"[{condition}] {fold_name} seed={seed}: "
        f"balanced_accuracy={metrics['test_trial_balanced_accuracy']:.4f}, "
        f"F1={metrics['test_trial_f1']:.4f}, threshold={threshold:.4f}, "
        f"real_falls={len(selected_real)}, batch={composition}"
    )
    return metrics


def refresh_summary(condition: str, output_root: Path, base_core) -> None:
    condition_dir = output_root / condition
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(condition_dir.glob("fold_*/seed_*/metrics.json"))
    ]
    if not records:
        return
    frame = pd.DataFrame.from_records(records).sort_values(["fold_index", "seed"])
    frame.to_csv(condition_dir / "run_summary.csv", index=False)
    summary: dict[str, Any] = {
        "condition": condition,
        "completed_runs": len(frame),
        "folds": sorted(frame["fold"].unique().tolist()),
        "seeds": sorted(int(value) for value in frame["seed"].unique()),
        "real_fraction": float(frame["real_fraction"].iloc[0]),
        "use_synthetic": bool(frame["use_synthetic"].iloc[0]),
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
    base_core.write_json(condition_dir / "experiment_summary.json", summary)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Train the fixed 25%/50% low-real-data augmentation study."
    )
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json")
    )
    parser.add_argument(
        "--device", default="auto", choices=["auto", "cpu", "mps", "cuda"]
    )
    parser.add_argument("--conditions", nargs="*", default=["all"])
    parser.add_argument("--folds", nargs="*", help="1-based fold numbers")
    parser.add_argument("--seeds", nargs="*", help="Seed values")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-epochs", type=int)
    parser.add_argument("--steps-per-epoch", type=int)
    args = parser.parse_args(argv)

    config_path, _, _ = prepare_base_imports(args.config)
    import detector_core as base_core
    import train_scenario as base_train

    config = base_core.load_config(config_path)
    if args.max_epochs is not None:
        config["max_epochs"] = args.max_epochs
    if args.steps_per_epoch is not None:
        config["steps_per_epoch"] = args.steps_per_epoch
    conditions = canonical_conditions(args.conditions, config)
    selected_folds = parse_int_list(args.folds) or list(
        range(1, len(config["folds"]) + 1)
    )
    selected_seeds = parse_int_list(args.seeds) or [
        int(value) for value in config["seeds"]
    ]
    if any(index < 1 or index > len(config["folds"]) for index in selected_folds):
        raise ValueError(f"Fold numbers must be between 1 and {len(config['folds'])}")
    device = base_core.choose_device(args.device)
    rows = base_core.read_manifest(Path(config["data_root"]))
    audit_path = write_subset_audit(rows, config, base_core)
    print(
        f"Conditions: {conditions}\nDevice: {device}\nFolds: {selected_folds}\n"
        f"Seeds: {selected_seeds}\nSubset audit: {audit_path}"
    )
    for condition in conditions:
        for fold_number in selected_folds:
            for seed in selected_seeds:
                run_one(
                    condition,
                    fold_number - 1,
                    seed,
                    config,
                    rows,
                    device,
                    args.overwrite,
                    base_core,
                    base_train,
                )
        refresh_summary(condition, Path(config["output_root"]), base_core)


if __name__ == "__main__":
    main()
