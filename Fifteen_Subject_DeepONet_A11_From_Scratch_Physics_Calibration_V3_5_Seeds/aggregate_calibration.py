#!/usr/bin/env python3
"""Aggregate selected V3 and matched from-scratch lambda=0 results."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import t as student_t

from operator_core import ROOT, dump_json, load_config, metric_names, optimization_seeds, seed_spec

DIAGNOSTICS = ("angular_residual_rmse", "horizontal_residual_rmse")
CONDITIONS = ("selected", "matched_no_physics")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    keys = []
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


def aggregate_seed(config: dict, condition: str, seed_index: int) -> dict:
    base_seed, seed_label = seed_spec(config, seed_index)
    root = ROOT / "results" / condition / "full" / seed_label
    subject_rows, trial_rows, selection_rows = [], [], []
    for fold in config["folds"]:
        fold_id = int(fold["id"])
        fold_dir = root / f"fold_{fold_id:02d}"
        summary = json.loads((fold_dir / "summary.json").read_text(encoding="utf-8"))
        if condition == "selected":
            selection = json.loads((fold_dir / "weight_selection.json").read_text(encoding="utf-8"))
            selection_rows.append({
                "seed_index": seed_index, "base_optimization_seed": base_seed,
                "fold": fold_id, "validation_subject": fold["validation"],
                "selected_physics_weight": float(selection["selected_weight"]),
                "selected_validation_forecast_mse": float(selection["selected_validation_forecast_mse"]),
                "selected_best_epoch": int(selection["selected_best_epoch"]),
                "initialization_sha256": summary["initialization_sha256"],
            })
        for subject, metrics in summary["test_subject_mean_metrics"].items():
            subject_rows.append({
                "seed_index": seed_index, "base_optimization_seed": base_seed,
                "fold": fold_id, "test_subject": subject,
                "physics_weight": float(summary["physics_weight"]), **metrics,
            })
        for row in read_csv(fold_dir / "test_metrics_by_trial.csv"):
            trial_rows.append({
                "seed_index": seed_index, "base_optimization_seed": base_seed,
                "fold": fold_id, "physics_weight": float(summary["physics_weight"]), **row,
            })
    observed = [row["test_subject"] for row in subject_rows]
    if set(observed) != set(config["subjects"]) or len(observed) != len(set(observed)):
        raise ValueError(f"{condition}: every subject must occur exactly once")
    write_csv(root / "cross_subject_metrics.csv", subject_rows)
    write_csv(root / "cross_trial_metrics.csv", trial_rows)
    if selection_rows:
        write_csv(root / "weight_selections.csv", selection_rows)
    report = {
        "experiment": config["experiment_name"], "condition": condition,
        "seed_index": seed_index, "base_seed": base_seed,
        "held_out_subjects": len(subject_rows), "held_out_trials": len(trial_rows),
        "metrics": {metric: float(np.mean([float(row[metric]) for row in subject_rows])) for metric in metric_names("planar") + DIAGNOSTICS},
    }
    if selection_rows:
        report["selected_weight_counts"] = dict(sorted(Counter(str(row["selected_physics_weight"]) for row in selection_rows).items()))
    dump_json(root / "aggregate_summary.json", report)
    return {"subjects": subject_rows, "trials": trial_rows, "selections": selection_rows, "report": report}


def aggregate_condition(config: dict, condition: str, seed_indices: list[int]) -> dict:
    per_seed = [aggregate_seed(config, condition, index) for index in seed_indices]
    root = ROOT / "results" / condition / "full"
    subjects = [row for item in per_seed for row in item["subjects"]]
    trials = [row for item in per_seed for row in item["trials"]]
    selections = [row for item in per_seed for row in item["selections"]]
    write_csv(root / "multi_seed_subject_metrics.csv", subjects)
    write_csv(root / "multi_seed_trial_metrics.csv", trials)
    if selections:
        write_csv(root / "multi_seed_weight_selections.csv", selections)
    metrics = {}
    for metric in metric_names("planar") + DIAGNOSTICS:
        seed_means = np.asarray([
            np.mean([float(row[metric]) for row in subjects if int(row["seed_index"]) == index])
            for index in seed_indices
        ])
        metrics[metric] = {
            "mean_of_seed_subject_means": float(seed_means.mean()),
            "std_of_seed_subject_means": float(seed_means.std(ddof=1)) if len(seed_means) > 1 else 0.0,
            "95pct_t_interval": mean_ci(seed_means),
            "values_by_seed": {str(index): float(value) for index, value in zip(seed_indices, seed_means)},
        }
    report = {
        "experiment": config["experiment_name"], "condition": condition,
        "optimization_seeds": [optimization_seeds(config)[index - 1] for index in seed_indices],
        "evaluated_fold_models": len(seed_indices) * 5,
        "held_out_subject_seed_evaluations": len(subjects),
        "held_out_trial_seed_evaluations": len(trials), "metrics": metrics,
    }
    if selections:
        report["selected_weight_counts"] = dict(sorted(Counter(str(row["selected_physics_weight"]) for row in selections).items()))
    dump_json(root / "multi_seed_summary.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--seed-index", type=int)
    args = parser.parse_args()
    config = load_config(args.config)
    indices = [args.seed_index] if args.seed_index else list(range(1, 6))
    reports = {condition: aggregate_condition(config, condition, indices) for condition in CONDITIONS}
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
