#!/usr/bin/env python3
"""Aggregate validation-selected A11 calibration results over folds and seeds."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t as student_t

from operator_core import ROOT, dump_json, load_config, metric_names, optimization_seeds, seed_spec


DIAGNOSTICS = ("angular_residual_rmse", "horizontal_residual_rmse")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
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


def mean_ci(values: np.ndarray) -> list[float]:
    if len(values) < 2:
        return [float(values[0]), float(values[0])]
    half = float(student_t.ppf(.975, len(values) - 1) * values.std(ddof=1) / np.sqrt(len(values)))
    return [float(values.mean() - half), float(values.mean() + half)]


def aggregate_seed(config: dict, seed_index: int) -> dict:
    base_seed, seed_label = seed_spec(config, seed_index)
    root = ROOT / "results" / "selected" / "full" / seed_label
    subject_rows: list[dict] = []
    trial_rows: list[dict] = []
    selection_rows: list[dict] = []
    for fold in config["folds"]:
        fold_id = int(fold["id"])
        fold_dir = root / f"fold_{fold_id:02d}"
        summary_path = fold_dir / "summary.json"
        selection_path = fold_dir / "weight_selection.json"
        if not summary_path.is_file() or not selection_path.is_file():
            raise FileNotFoundError(f"selected fold is incomplete: {fold_dir}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        weight = float(selection["selected_weight"])
        selection_rows.append({
            "seed_index": seed_index,
            "base_optimization_seed": base_seed,
            "fold": fold_id,
            "validation_subject": fold["validation"],
            "selected_physics_weight": weight,
            "selected_source": selection["selected_source"],
            "selected_validation_forecast_mse": selection["selected_validation_forecast_mse"],
            "selected_best_epoch_after_warm_start": selection["selected_best_epoch_after_warm_start"],
        })
        for subject, metrics in summary["test_subject_mean_metrics"].items():
            subject_rows.append({
                "seed_index": seed_index,
                "base_optimization_seed": base_seed,
                "fold": fold_id,
                "test_subject": subject,
                "selected_physics_weight": weight,
                **metrics,
            })
        for row in read_csv(fold_dir / "test_metrics_by_trial.csv"):
            trial_rows.append({
                "seed_index": seed_index,
                "base_optimization_seed": base_seed,
                "fold": fold_id,
                "selected_physics_weight": weight,
                **row,
            })
    expected = set(config["subjects"])
    observed = [row["test_subject"] for row in subject_rows]
    if set(observed) != expected or len(observed) != len(set(observed)):
        raise ValueError("selected results do not contain every held-out subject exactly once")
    write_csv(root / "cross_subject_metrics.csv", subject_rows)
    write_csv(root / "cross_trial_metrics.csv", trial_rows)
    write_csv(root / "weight_selections.csv", selection_rows)
    report = {
        "experiment": config["experiment_name"],
        "seed_index": seed_index,
        "base_seed": base_seed,
        "held_out_subjects": len(subject_rows),
        "held_out_trials": len(trial_rows),
        "selected_weight_counts": dict(sorted(Counter(str(row["selected_physics_weight"]) for row in selection_rows).items())),
        "metrics": {
            metric: float(np.mean([float(row[metric]) for row in subject_rows]))
            for metric in metric_names("planar") + DIAGNOSTICS
        },
    }
    dump_json(root / "aggregate_summary.json", report)
    return {"subjects": subject_rows, "trials": trial_rows, "selections": selection_rows, "report": report}


def aggregate_all(config: dict) -> dict:
    per_seed = [aggregate_seed(config, index) for index in range(1, 6)]
    root = ROOT / "results" / "selected" / "full"
    subject_rows = [row for item in per_seed for row in item["subjects"]]
    trial_rows = [row for item in per_seed for row in item["trials"]]
    selection_rows = [row for item in per_seed for row in item["selections"]]
    write_csv(root / "multi_seed_subject_metrics.csv", subject_rows)
    write_csv(root / "multi_seed_trial_metrics.csv", trial_rows)
    write_csv(root / "multi_seed_weight_selections.csv", selection_rows)
    metrics = {}
    for metric in metric_names("planar") + DIAGNOSTICS:
        seed_means = np.asarray([
            np.mean([float(row[metric]) for row in subject_rows if int(row["seed_index"]) == index])
            for index in range(1, 6)
        ])
        metrics[metric] = {
            "mean_of_seed_subject_means": float(seed_means.mean()),
            "std_of_seed_subject_means": float(seed_means.std(ddof=1)),
            "95pct_t_interval": mean_ci(seed_means),
            "values_by_seed": {str(index): float(seed_means[index - 1]) for index in range(1, 6)},
        }
    report = {
        "experiment": config["experiment_name"],
        "optimization_seeds": optimization_seeds(config),
        "selected_fold_models": len(selection_rows),
        "held_out_subject_seed_evaluations": len(subject_rows),
        "held_out_trial_seed_evaluations": len(trial_rows),
        "selected_weight_counts": dict(sorted(Counter(str(row["selected_physics_weight"]) for row in selection_rows).items())),
        "metrics": metrics,
        "selection_used_test_data": False,
    }
    dump_json(root / "multi_seed_summary.json", report)
    primary = ("normalized_mse", "theta_rmse_deg", "x_rmse_cm")
    subjects = sorted(set(config["subjects"]), key=lambda value: int(value[1:]))
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    for axis, metric in zip(axes, primary):
        values = [[float(row[metric]) for row in subject_rows if row["test_subject"] == subject] for subject in subjects]
        axis.boxplot(values, labels=subjects)
        axis.set_ylabel(metric)
        axis.grid(axis="y", alpha=.25)
    fig.suptitle("A11 calibration V2: validation-selected five-seed results")
    fig.tight_layout()
    fig.savefig(root / "multi_seed_subject_boxplots.png", dpi=170)
    plt.close(fig)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--seed-index", type=int)
    args = parser.parse_args()
    config = load_config(args.config)
    result = aggregate_seed(config, args.seed_index)["report"] if args.seed_index else aggregate_all(config)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
