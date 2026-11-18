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
from source_ratio_sampler import SourceRatioBatchSampler


def parse_int_list(values: Sequence[str] | None) -> list[int] | None:
    if not values:
        return None
    result: list[int] = []
    for value in values:
        result.extend(int(item) for item in value.split(",") if item.strip())
    return result


def run_one(
    fold_index: int,
    seed: int,
    config: dict[str, Any],
    rows,
    device: torch.device,
    overwrite: bool,
    base_core,
    base_train,
) -> dict[str, Any]:
    experiment_name = str(config["experiment_name"])
    fold_name = config["folds"][fold_index]["name"]
    run_dir = (
        Path(config["output_root"])
        / experiment_name
        / fold_name
        / f"seed_{seed:05d}"
    )
    metrics_path = run_dir / "metrics.json"
    if metrics_path.is_file() and not overwrite:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    if run_dir.exists() and overwrite:
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    base_core.set_reproducible_seed(seed)
    split_rows, partitions = base_core.split_scenario_rows(
        rows,
        config,
        "real_synthetic_fall_real_adl",
        fold_index,
    )
    scaler = base_core.fit_training_scaler(
        split_rows["train"], Path(config["data_root"])
    )
    base_core.write_json(run_dir / "scaler.json", scaler)

    training = base_train.make_dataset(split_rows["train"], config, scaler, training=True)
    validation = base_train.make_dataset(
        split_rows["validation"], config, scaler, training=False
    )
    test = base_train.make_dataset(split_rows["test"], config, scaler, training=False)

    source_kinds: list[str] = []
    subject_groups: list[str] = []
    for spec in training.specs:
        row = training.rows[spec.row_index]
        source_kinds.append(row["source_kind"])
        subject_groups.append(base_core.logical_group(row, config))

    ratio = config["fall_source_ratio"]
    sampler = SourceRatioBatchSampler(
        labels=training.labels,
        source_kinds=source_kinds,
        subject_groups=subject_groups,
        batch_size=int(config["batch_size"]),
        steps=int(config["steps_per_epoch"]),
        seed=seed,
        real_parts=int(ratio["real"]),
        synthetic_parts=int(ratio["synthetic"]),
        subject_balanced_within_source=bool(
            config.get("subject_balanced_within_source", False)
        ),
    )
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
                    "experiment": experiment_name,
                    "fold": fold_name,
                    "seed": seed,
                    "best_epoch": best_epoch,
                    "fall_source_ratio": ratio,
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
    quota_summary = sampler.quota_summary()
    metrics: dict[str, Any] = {
        "scenario": experiment_name,
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
        "training_pool_real_adl_windows": int(pool_counts["real_adl"]),
        "training_pool_real_fall_windows": int(pool_counts["real_fall"]),
        "training_pool_synthetic_fall_windows": int(
            pool_counts["synthetic_fall"]
        ),
        "batch_real_adl_windows": quota_summary["real_adl_per_batch"],
        "batch_fall_windows": quota_summary["falls_per_batch"],
        "batch_real_fall_windows_min": quota_summary["real_fall_per_batch_min"],
        "batch_real_fall_windows_max": quota_summary["real_fall_per_batch_max"],
        "batch_synthetic_fall_windows_min": quota_summary[
            "synthetic_fall_per_batch_min"
        ],
        "batch_synthetic_fall_windows_max": quota_summary[
            "synthetic_fall_per_batch_max"
        ],
        "epoch_real_fall_windows": quota_summary["real_fall_per_epoch"],
        "epoch_synthetic_fall_windows": quota_summary[
            "synthetic_fall_per_epoch"
        ],
        "effective_real_fall_fraction": quota_summary[
            "effective_real_fraction"
        ],
        "effective_synthetic_fall_fraction": quota_summary[
            "effective_synthetic_fraction"
        ],
        "fall_source_ratio_real": int(ratio["real"]),
        "fall_source_ratio_synthetic": int(ratio["synthetic"]),
        "subject_balanced_within_source": bool(
            config.get("subject_balanced_within_source", False)
        ),
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
    validation_windows.to_csv(
        run_dir / "validation_window_predictions.csv", index=False
    )
    validation_trials.to_csv(
        run_dir / "validation_trial_predictions.csv", index=False
    )
    test_windows.to_csv(run_dir / "test_window_predictions.csv", index=False)
    test_trials.to_csv(run_dir / "test_trial_predictions.csv", index=False)
    base_train.plot_history(history, run_dir / "training_history.png")
    base_core.write_json(
        run_dir / "run_configuration.json",
        {
            "experiment": experiment_name,
            "base_training_scenario": "real_synthetic_fall_real_adl",
            "fold": fold_name,
            "seed": seed,
            "device": str(device),
            "fall_source_ratio": ratio,
            "quota_summary": quota_summary,
            "split_groups": {
                key: sorted(value) for key, value in partitions.items()
            },
            "config": config,
        },
    )
    base_core.write_json(metrics_path, metrics)
    print(
        f"[{experiment_name}] {fold_name} seed={seed}: "
        f"balanced_accuracy={metrics['test_trial_balanced_accuracy']:.4f}, "
        f"F1={metrics['test_trial_f1']:.4f}, threshold={threshold:.4f}, "
        f"epoch fall ratio="
        f"{quota_summary['effective_real_fraction']:.4f}:"
        f"{quota_summary['effective_synthetic_fraction']:.4f}"
    )
    return metrics


def refresh_summary(experiment_name: str, output_root: Path, base_core) -> None:
    experiment_dir = output_root / experiment_name
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(experiment_dir.glob("fold_*/seed_*/metrics.json"))
    ]
    if not records:
        return
    frame = pd.DataFrame.from_records(records).sort_values(["fold_index", "seed"])
    frame.to_csv(experiment_dir / "run_summary.csv", index=False)
    summary: dict[str, Any] = {
        "experiment": experiment_name,
        "completed_runs": len(frame),
        "folds": sorted(frame["fold"].unique().tolist()),
        "seeds": sorted(int(value) for value in frame["seed"].unique()),
        "quota_summary": {
            "real_adl_per_batch": int(frame["batch_real_adl_windows"].iloc[0]),
            "falls_per_batch": int(frame["batch_fall_windows"].iloc[0]),
            "real_fall_per_batch_min": int(
                frame["batch_real_fall_windows_min"].iloc[0]
            ),
            "real_fall_per_batch_max": int(
                frame["batch_real_fall_windows_max"].iloc[0]
            ),
            "synthetic_fall_per_batch_min": int(
                frame["batch_synthetic_fall_windows_min"].iloc[0]
            ),
            "synthetic_fall_per_batch_max": int(
                frame["batch_synthetic_fall_windows_max"].iloc[0]
            ),
            "real_fall_per_epoch": int(frame["epoch_real_fall_windows"].iloc[0]),
            "synthetic_fall_per_epoch": int(
                frame["epoch_synthetic_fall_windows"].iloc[0]
            ),
            "effective_real_fraction": float(
                frame["effective_real_fall_fraction"].iloc[0]
            ),
            "effective_synthetic_fraction": float(
                frame["effective_synthetic_fall_fraction"].iloc[0]
            ),
        },
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
    base_core.write_json(experiment_dir / "experiment_summary.json", summary)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Train the fixed 40:60 and 60:40 fall-source ratio experiments."
    )
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json")
    )
    parser.add_argument(
        "--device", default="auto", choices=["auto", "cpu", "mps", "cuda"]
    )
    parser.add_argument("--folds", nargs="*", help="1-based fold numbers")
    parser.add_argument("--seeds", nargs="*", help="Seed values")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-epochs", type=int)
    parser.add_argument("--steps-per-epoch", type=int)
    args = parser.parse_args(argv)

    config_path, raw_config, _ = prepare_base_imports(args.config)
    import detector_core as base_core
    import train_scenario as base_train

    base_config = base_core.load_config(config_path)
    if args.max_epochs is not None:
        base_config["max_epochs"] = args.max_epochs
    if args.steps_per_epoch is not None:
        base_config["steps_per_epoch"] = args.steps_per_epoch
    selected_folds = parse_int_list(args.folds) or list(
        range(1, len(base_config["folds"]) + 1)
    )
    selected_seeds = parse_int_list(args.seeds) or [
        int(value) for value in base_config["seeds"]
    ]
    if any(index < 1 or index > len(base_config["folds"]) for index in selected_folds):
        raise ValueError(
            f"Fold numbers must be between 1 and {len(base_config['folds'])}"
        )
    device = base_core.choose_device(args.device)
    rows = base_core.read_manifest(Path(base_config["data_root"]))
    experiments = list(raw_config["experiments"])
    for experiment in experiments:
        config = dict(base_config)
        config["experiment_name"] = str(experiment["experiment_name"])
        config["fall_source_ratio"] = dict(experiment["fall_source_ratio"])
        ratio = config["fall_source_ratio"]
        print(
            f"\nExperiment: {config['experiment_name']}\n"
            f"Target fall source ratio: {ratio['real']} real : "
            f"{ratio['synthetic']} synthetic\n"
            f"Device: {device}\nFolds: {selected_folds}\nSeeds: {selected_seeds}"
        )
        for fold_number in selected_folds:
            for seed in selected_seeds:
                run_one(
                    fold_number - 1,
                    seed,
                    config,
                    rows,
                    device,
                    args.overwrite,
                    base_core,
                    base_train,
                )
        refresh_summary(
            str(config["experiment_name"]), Path(config["output_root"]), base_core
        )


if __name__ == "__main__":
    main()

