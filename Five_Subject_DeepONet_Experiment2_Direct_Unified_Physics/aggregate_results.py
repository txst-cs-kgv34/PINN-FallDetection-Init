#!/usr/bin/env python3
"""Aggregate five real held-out test-subject folds with equal subject weighting."""

from __future__ import annotations

import argparse
import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from operator_core import METRICS, ROOT, dump_json, load_config


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    args = parser.parse_args()
    config = load_config(args.config)
    result_dir = ROOT / "results" / args.mode
    rows = []
    for fold in config["folds"]:
        path = result_dir / f"fold_{int(fold['id']):02d}" / "summary.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing fold result: {path}")
        summary = json.loads(path.read_text(encoding="utf-8"))
        row = {
            "experiment_name": config["experiment_name"],
            "model_id": config["model_id"],
            "training_regime": config["training_regime"],
            "fold": int(fold["id"]),
            "train_subjects": "+".join(fold["train"]),
            "validation_subject": fold["validation"],
            "test_subject": fold["test"],
            "test_trial_count": int(summary["test_trial_count"]),
            "test_forecast_sample_count": int(summary["test_forecast_sample_count"]),
        }
        for metric in METRICS:
            row[f"model_{metric}"] = float(summary["test_pooled_metrics"][metric])
        rows.append(row)
    write_csv(result_dir / "cross_fold_metrics.csv", rows)

    metrics = {}
    for metric in METRICS:
        values = np.asarray([row[f"model_{metric}"] for row in rows], dtype=float)
        metrics[metric] = {
            "mean_across_test_subjects": float(values.mean()),
            "std_across_test_subjects": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            "values_by_test_subject": {
                row["test_subject"]: float(row[f"model_{metric}"]) for row in rows
            },
        }
    report = {
        "experiment": config["experiment_name"],
        "model_id": config["model_id"],
        "display_name": config["display_name"],
        "training_regime": config["training_regime"],
        "mode": args.mode,
        "fold_count": len(rows),
        "aggregation_unit": "held-out test subject; every subject contributes exactly once",
        "metrics": metrics,
        "physics_loss_enabled": bool(config["training"]["use_physics"]),
        "training_sources": config["training_sources"],
        "limitations": [
            "Five subjects make this a pilot generalization study.",
            "Every checkpoint is selected only on a real validation subject.",
            "Trials shorter than the fixed 0.40-second context are excluded before fitting.",
            "Optimization-seed uncertainty requires repeated full runs with different seeds.",
        ],
    }
    dump_json(result_dir / "aggregate_summary.json", report)

    labels = [row["test_subject"] for row in rows]
    positions = np.arange(len(rows))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for axis, metric, title in zip(
        axes,
        ("normalized_mse", "theta_rmse_deg", "x_rmse_cm"),
        ("Normalized MSE", "Theta RMSE (deg)", "x RMSE (cm)"),
    ):
        axis.bar(positions, [row[f"model_{metric}"] for row in rows], width=0.62)
        axis.set_xticks(positions, labels)
        axis.set_title(title)
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle(f"{config['display_name']}: unseen-subject real-trajectory results")
    fig.tight_layout()
    fig.savefig(result_dir / "cross_fold_results.png", dpi=180)
    plt.close(fig)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
