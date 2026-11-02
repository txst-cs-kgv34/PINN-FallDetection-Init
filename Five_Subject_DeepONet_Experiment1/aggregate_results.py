#!/usr/bin/env python3
"""Aggregate the five held-out test-subject folds without pooling subjects together."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from operator_core import ROOT, dump_json, load_config


METRICS = (
    "normalized_mse",
    "theta_rmse_deg",
    "theta_mae_deg",
    "x_rmse_cm",
    "x_mae_cm",
    "theta_w1_deg",
    "x_w1_cm",
)


def write_csv(path: Path, rows: list[dict]) -> None:
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
            "fold": int(fold["id"]),
            "train_subjects": "+".join(fold["train"]),
            "validation_subject": fold["validation"],
            "test_subject": fold["test"],
            "test_trial_count": int(summary["test_trial_count"]),
            "test_forecast_sample_count": int(summary["test_forecast_sample_count"]),
        }
        for metric in METRICS:
            row[f"deeponet_{metric}"] = float(summary["test_pooled_metrics"][metric])
            row[f"mean_gain_baseline_{metric}"] = float(
                summary["mean_gain_baseline_pooled_metrics"][metric]
            )
        rows.append(row)
    write_csv(result_dir / "cross_fold_metrics.csv", rows)

    aggregate = {}
    for prefix in ("deeponet", "mean_gain_baseline"):
        aggregate[prefix] = {}
        for metric in METRICS:
            values = np.asarray([row[f"{prefix}_{metric}"] for row in rows], dtype=float)
            aggregate[prefix][metric] = {
                "mean_across_test_subjects": float(values.mean()),
                "std_across_test_subjects": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                "values_by_test_subject": {
                    row["test_subject"]: float(row[f"{prefix}_{metric}"]) for row in rows
                },
            }
    improvements = {}
    for metric in METRICS:
        model_mean = aggregate["deeponet"][metric]["mean_across_test_subjects"]
        baseline_mean = aggregate["mean_gain_baseline"][metric]["mean_across_test_subjects"]
        improvements[metric] = float(100.0 * (baseline_mean - model_mean) / baseline_mean)
    report = {
        "experiment": config["experiment_name"],
        "mode": args.mode,
        "fold_count": len(rows),
        "aggregation_unit": "held-out test subject; every subject contributes exactly once",
        "metrics": aggregate,
        "percent_improvement_over_training_mean_gain_baseline": improvements,
        "limitations": [
            "Five subjects make this a pilot generalization study.",
            "Validation and test use real trajectories; training uses only three subjects' PINN trajectories per fold.",
            "Trials shorter than the fixed 0.40-second four-window context are excluded and listed in the real-data manifest.",
        ],
    }
    dump_json(result_dir / "aggregate_summary.json", report)

    labels = [row["test_subject"] for row in rows]
    positions = np.arange(len(rows))
    width = 0.36
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for axis, metric, title in zip(
        axes,
        ("normalized_mse", "theta_rmse_deg", "x_rmse_cm"),
        ("Normalized MSE", "Theta RMSE (deg)", "x RMSE (cm)"),
    ):
        axis.bar(
            positions - width / 2,
            [row[f"deeponet_{metric}"] for row in rows],
            width,
            label="4-window DeepONet",
        )
        axis.bar(
            positions + width / 2,
            [row[f"mean_gain_baseline_{metric}"] for row in rows],
            width,
            label="Training mean gains",
        )
        axis.set_xticks(positions, labels)
        axis.set_title(title)
        axis.grid(axis="y", alpha=0.25)
    axes[0].legend()
    fig.suptitle("Experiment 1: unseen-subject real-trajectory results")
    fig.tight_layout()
    fig.savefig(result_dir / "cross_fold_comparison.png", dpi=180)
    plt.close(fig)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

