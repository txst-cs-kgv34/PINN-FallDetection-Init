#!/usr/bin/env python3
"""Aggregate five folds with equal weighting across all 15 held-out test subjects."""

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
    subject_rows = []
    fold_rows = []
    for fold in config["folds"]:
        path = result_dir / f"fold_{int(fold['id']):02d}" / "summary.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing fold result: {path}")
        summary = json.loads(path.read_text(encoding="utf-8"))
        fold_row = {
            "fold": int(fold["id"]),
            "train_subjects": "+".join(fold["train"]),
            "validation_subject": fold["validation"],
            "test_subjects": "+".join(fold["test"]),
            "test_trial_count": int(summary["test_trial_count"]),
            "test_forecast_sample_count": int(summary["test_forecast_sample_count"]),
        }
        for metric in METRICS:
            fold_row[metric] = float(summary["test_pooled_metrics"][metric])
        fold_rows.append(fold_row)
        for subject, metrics in summary["test_subject_mean_metrics"].items():
            subject_rows.append(
                {
                    "fold": int(fold["id"]),
                    "test_subject": subject,
                    **{metric: float(metrics[metric]) for metric in METRICS},
                }
            )

    expected = {str(item["id"]) for item in config["subjects"]}
    observed = [str(row["test_subject"]) for row in subject_rows]
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError("Every configured subject must appear exactly once as a test subject")
    if len(observed) != len(set(observed)):
        raise ValueError("A test subject appears in more than one fold")
    subject_rows.sort(key=lambda row: row["test_subject"])
    write_csv(result_dir / "cross_fold_metrics.csv", fold_rows)
    write_csv(result_dir / "cross_subject_metrics.csv", subject_rows)

    metrics = {}
    for metric in METRICS:
        values = np.asarray([row[metric] for row in subject_rows], dtype=float)
        metrics[metric] = {
            "mean_across_test_subjects": float(values.mean()),
            "std_across_test_subjects": float(values.std(ddof=1)),
            "values_by_test_subject": {
                row["test_subject"]: float(row[metric]) for row in subject_rows
            },
        }
    report = {
        "experiment": config["experiment_name"],
        "model_id": config["model_id"],
        "display_name": config["display_name"],
        "training_regime": config["training_regime"],
        "mode": args.mode,
        "fold_count": len(fold_rows),
        "held_out_test_subject_count": len(subject_rows),
        "aggregation_unit": "held-out test subject; all 15 subjects contribute exactly once",
        "metrics": metrics,
        "physics_loss_enabled": bool(config["training"]["use_physics"]),
        "training_sources": config["training_sources"],
        "limitations": [
            "One optimization seed is a pilot; repeat seeds are required for uncertainty estimates.",
            "Each checkpoint is selected only on one real validation subject.",
            "Trials shorter than the fixed 0.40-second context are excluded before fitting.",
            "Apparent contact is skeleton-observed rather than force-plate-confirmed.",
        ],
    }
    dump_json(result_dir / "aggregate_summary.json", report)

    labels = [row["test_subject"] for row in subject_rows]
    positions = np.arange(len(subject_rows))
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    for axis, metric, title in zip(
        axes,
        ("normalized_mse", "theta_rmse_deg", "x_rmse_cm"),
        ("Normalized MSE", "Theta RMSE (deg)", "Forward x RMSE (cm)"),
    ):
        axis.bar(positions, [row[metric] for row in subject_rows], width=0.72)
        axis.set_ylabel(title)
        axis.grid(axis="y", alpha=0.25)
    axes[-1].set_xticks(positions, labels, rotation=45, ha="right")
    fig.suptitle(f"{config['display_name']}: held-out real-subject results")
    fig.tight_layout()
    fig.savefig(result_dir / "cross_subject_results.png", dpi=180)
    plt.close(fig)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
