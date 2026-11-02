#!/usr/bin/env python3
"""Build a paired four-model comparison after Experiments 1–4 are complete."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


METRICS = (
    "normalized_mse",
    "theta_rmse_deg",
    "theta_mae_deg",
    "x_rmse_cm",
    "x_mae_cm",
    "theta_w1_deg",
    "x_w1_cm",
)
MODEL_INFO = {
    "A": ("Real data-only", "model_"),
    "B": ("Direct unified physics", "model_"),
    "C": ("Subject-PINN distillation", "deeponet_"),
    "D": ("Hybrid", "model_"),
}


def read_rows(path: Path, model_id: str) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing Model {model_id} metrics: {path}")
    _, prefix = MODEL_INFO[model_id]
    with path.open(newline="", encoding="utf-8") as handle:
        raw_rows = list(csv.DictReader(handle))
    rows = []
    for raw in raw_rows:
        rows.append(
            {
                "model_id": model_id,
                "model_name": MODEL_INFO[model_id][0],
                "fold": int(raw["fold"]),
                "test_subject": raw["test_subject"],
                **{metric: float(raw[f"{prefix}{metric}"]) for metric in METRICS},
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-a",
        type=Path,
        default=root.parent
        / "Five_Subject_DeepONet_Experiment3_Real_Data_Only/results/full/cross_fold_metrics.csv",
    )
    parser.add_argument(
        "--model-b",
        type=Path,
        default=root.parent
        / "Five_Subject_DeepONet_Experiment2_Direct_Unified_Physics/results/full/cross_fold_metrics.csv",
    )
    parser.add_argument(
        "--model-c",
        type=Path,
        default=root.parent
        / "Five_Subject_DeepONet_Experiment1/results/full/cross_fold_metrics.csv",
    )
    parser.add_argument(
        "--model-d",
        type=Path,
        default=root / "results/full/cross_fold_metrics.csv",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=root / "results/four_model_comparison"
    )
    args = parser.parse_args()
    paths = {"A": args.model_a, "B": args.model_b, "C": args.model_c, "D": args.model_d}
    by_model = {model_id: read_rows(path.resolve(), model_id) for model_id, path in paths.items()}
    expected = {(row["fold"], row["test_subject"]) for row in by_model["A"]}
    for model_id, rows in by_model.items():
        observed = {(row["fold"], row["test_subject"]) for row in rows}
        if observed != expected:
            raise ValueError(f"Model {model_id} does not use the same fold/test-subject pairs")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    flat_rows = [row for model_id in ("A", "B", "C", "D") for row in by_model[model_id]]
    write_csv(output_dir / "four_model_metrics_by_subject.csv", flat_rows)

    summary = {}
    for model_id, rows in by_model.items():
        summary[model_id] = {
            "name": MODEL_INFO[model_id][0],
            "metrics": {
                metric: {
                    "mean": float(np.mean([row[metric] for row in rows])),
                    "sample_std": float(np.std([row[metric] for row in rows], ddof=1)),
                    "values_by_test_subject": {
                        row["test_subject"]: row[metric] for row in rows
                    },
                }
                for metric in METRICS
            },
        }
    comparisons = {}
    for first, second, label in (
        ("A", "B", "B_over_A_physics_value"),
        ("B", "C", "C_over_B_distillation_vs_direct_real"),
        ("B", "D", "D_over_B_synthetic_addition"),
        ("C", "D", "D_over_C_real_addition"),
    ):
        comparisons[label] = {}
        for metric in METRICS:
            first_mean = summary[first]["metrics"][metric]["mean"]
            second_mean = summary[second]["metrics"][metric]["mean"]
            comparisons[label][metric] = float(100.0 * (first_mean - second_mean) / first_mean)
    report = {
        "aggregation_unit": "held-out test subject; every subject contributes equally",
        "positive_percent_means_second_model_is_better": True,
        "models": summary,
        "paired_mean_percent_improvements": comparisons,
    }
    (output_dir / "four_model_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    subjects = [subject for _, subject in sorted(expected)]
    positions = np.arange(len(subjects))
    width = 0.19
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    for axis, metric, title in zip(
        axes,
        ("normalized_mse", "theta_rmse_deg", "x_rmse_cm"),
        ("Normalized MSE", "Theta RMSE (deg)", "x RMSE (cm)"),
    ):
        for offset, model_id in enumerate(("A", "B", "C", "D")):
            values = {
                row["test_subject"]: row[metric] for row in by_model[model_id]
            }
            axis.bar(
                positions + (offset - 1.5) * width,
                [values[subject] for subject in subjects],
                width,
                label=f"{model_id}: {MODEL_INFO[model_id][0]}",
            )
        axis.set_xticks(positions, subjects)
        axis.set_title(title)
        axis.grid(axis="y", alpha=0.25)
    axes[0].legend(fontsize=8)
    fig.suptitle("Four-model unseen-subject comparison (lower is better)")
    fig.tight_layout()
    fig.savefig(output_dir / "four_model_comparison.png", dpi=180)
    plt.close(fig)
    print(output_dir)


if __name__ == "__main__":
    main()
