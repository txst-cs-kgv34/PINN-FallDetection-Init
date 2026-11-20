#!/usr/bin/env python3
"""Aggregate five folds and five seeds for one or both model groups."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t as student_t

from operator_core import ROOT, dump_json, load_config, metric_names, optimization_seeds, seed_spec


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle: return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows: raise ValueError(f"no rows for {path}")
    keys = []
    for row in rows:
        for key in row:
            if key not in keys: keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)


def mean_ci(values: np.ndarray) -> list[float]:
    if len(values) < 2: return [float(values[0]), float(values[0])]
    half = float(student_t.ppf(.975, len(values)-1) * values.std(ddof=1) / np.sqrt(len(values)))
    return [float(values.mean()-half), float(values.mean()+half)]


def aggregate_seed(config: dict, mode: str, group: str, seed_index: int) -> dict:
    base_seed, label = seed_spec(config, seed_index); root = ROOT / "results" / group / mode / label
    subject_rows = []; trial_rows = []
    for fold in config["folds"]:
        fold_id = int(fold["id"]); fold_dir = root / f"fold_{fold_id:02d}"
        summary_path = fold_dir / "summary.json"
        if not summary_path.is_file(): raise FileNotFoundError(summary_path)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for subject, metrics in summary["test_subject_mean_metrics"].items():
            subject_rows.append({"seed_index": seed_index, "base_optimization_seed": base_seed, "fold": fold_id, "test_subject": subject, **metrics})
        for row in read_csv(fold_dir / "test_metrics_by_trial.csv"):
            trial_rows.append({"seed_index": seed_index, "base_optimization_seed": base_seed, "fold": fold_id, **row})
    manifest = json.loads((ROOT / "outputs" / f"real_data_{mode}" / f"{group}_manifest.json").read_text(encoding="utf-8"))
    expected_subjects = {item["subject"] for item in manifest["included_trials"]}
    observed = [row["test_subject"] for row in subject_rows]
    if set(observed) != expected_subjects or len(observed) != len(set(observed)):
        raise ValueError(f"{group}: held-out subjects do not match eligible dataset subjects")
    write_csv(root / "cross_subject_metrics.csv", subject_rows); write_csv(root / "cross_trial_metrics.csv", trial_rows)
    metrics = {}
    for metric in metric_names(group):
        values = np.asarray([float(row[metric]) for row in subject_rows])
        metrics[metric] = {"mean_across_subjects": float(values.mean()), "std_across_subjects": float(values.std(ddof=1)), "median_across_subjects": float(np.median(values))}
    report = {"experiment": config["experiment_name"], "model_group": group, "mode": mode, "seed_index": seed_index, "base_seed": base_seed, "eligible_test_subjects": len(expected_subjects), "held_out_trials": len(trial_rows), "metrics": metrics, "physics_enabled": bool(config["training"]["use_physics"])}
    dump_json(root / "aggregate_summary.json", report)
    return {"subject_rows": subject_rows, "trial_rows": trial_rows, "report": report}


def aggregate_all(config: dict, mode: str, group: str) -> dict:
    seeds = [aggregate_seed(config, mode, group, index) for index in range(1, 6)]
    result_dir = ROOT / "results" / group / mode
    subject_rows = [row for item in seeds for row in item["subject_rows"]]
    trial_rows = [row for item in seeds for row in item["trial_rows"]]
    write_csv(result_dir / "multi_seed_subject_metrics.csv", subject_rows); write_csv(result_dir / "multi_seed_trial_metrics.csv", trial_rows)
    activity_rows = []
    for seed_index in range(1, 6):
        for activity in sorted({row["activity"] for row in trial_rows}):
            selected = [row for row in trial_rows if int(row["seed_index"]) == seed_index and row["activity"] == activity]
            activity_rows.append({"seed_index": seed_index, "activity": activity, "trial_count": len(selected), **{metric: float(np.mean([float(row[metric]) for row in selected])) for metric in metric_names(group)}})
    write_csv(result_dir / "multi_seed_activity_metrics.csv", activity_rows)
    metric_report = {}
    for metric in metric_names(group):
        seed_means = np.asarray([np.mean([float(row[metric]) for row in subject_rows if int(row["seed_index"]) == index]) for index in range(1, 6)])
        metric_report[metric] = {"mean_of_seed_subject_means": float(seed_means.mean()), "std_of_seed_subject_means": float(seed_means.std(ddof=1)), "95pct_t_interval": mean_ci(seed_means), "values_by_seed": {str(i): float(seed_means[i-1]) for i in range(1, 6)}}
    report = {"experiment": config["experiment_name"], "model_group": group, "optimization_seeds": optimization_seeds(config), "trained_fold_models": 25, "held_out_subject_seed_evaluations": len(subject_rows), "held_out_trial_seed_evaluations": len(trial_rows), "metrics": metric_report, "physics_enabled": bool(config["training"]["use_physics"])}
    dump_json(result_dir / "multi_seed_summary.json", report)
    primary = ["normalized_mse", "theta_rmse_deg", "x_rmse_cm"] + (["yaw_rmse_deg"] if group == "rotation" else [])
    fig, axes = plt.subplots(len(primary), 1, figsize=(12, 3.3 * len(primary)), squeeze=False)
    subjects = sorted({row["test_subject"] for row in subject_rows}, key=lambda s: int(s[1:]))
    for axis, metric in zip(axes[:,0], primary):
        values = [[float(row[metric]) for row in subject_rows if row["test_subject"] == subject] for subject in subjects]
        axis.boxplot(values, labels=subjects); axis.set_ylabel(metric); axis.grid(axis="y", alpha=.25)
    fig.suptitle(f"{group}: five-seed held-out-subject results"); fig.tight_layout(); fig.savefig(result_dir / "multi_seed_subject_boxplots.png", dpi=170); plt.close(fig)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default="experiment.json"); parser.add_argument("--mode", choices=("smoke", "full"), default="full"); parser.add_argument("--model-group", choices=("planar", "rotation", "all"), default="all"); parser.add_argument("--seed-index", type=int)
    args = parser.parse_args(); config = load_config(args.config); groups = ("planar", "rotation") if args.model_group == "all" else (args.model_group,)
    reports = {}
    for group in groups:
        reports[group] = aggregate_seed(config, args.mode, group, args.seed_index)["report"] if args.seed_index else aggregate_all(config, args.mode, group)
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
