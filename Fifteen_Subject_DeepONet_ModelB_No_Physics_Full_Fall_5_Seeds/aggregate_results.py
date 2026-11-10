#!/usr/bin/env python3
"""Aggregate the five folds within each seed and then aggregate all five seeds."""

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

from operator_core import (
    METRICS,
    ROOT,
    dump_json,
    load_config,
    optimization_seeds,
    seed_spec,
)


PRIMARY_METRICS = (
    ("normalized_mse", "Normalized forecast MSE"),
    ("theta_rmse_deg", "Angle RMSE (deg)"),
    ("x_rmse_cm", "CoM displacement RMSE (cm)"),
)

PHYSICS_DIAGNOSTICS = (
    "angular_residual_rmse",
    "angular_residual_mae",
    "horizontal_residual_rmse",
    "horizontal_residual_mae",
)
SUBJECT_METRICS = METRICS + PHYSICS_DIAGNOSTICS


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows available for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def subject_sort_key(subject: str) -> tuple[int, str]:
    digits = "".join(character for character in subject if character.isdigit())
    return (int(digits) if digits else 10**9, subject)


def plot_single_seed(subject_rows: list[dict], path: Path, title: str) -> None:
    labels = [str(row["test_subject"]) for row in subject_rows]
    positions = np.arange(len(subject_rows))
    fig, axes = plt.subplots(3, 1, figsize=(15, 12), sharex=True, constrained_layout=True)
    for axis, (metric, y_label) in zip(axes, PRIMARY_METRICS):
        axis.bar(positions, [float(row[metric]) for row in subject_rows], width=0.72)
        axis.set_ylabel(y_label)
        axis.grid(axis="y", alpha=0.25)
    axes[-1].set_xticks(positions, labels, rotation=45, ha="right")
    fig.suptitle(title)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def aggregate_one_seed(config: dict, mode: str, seed_index: int) -> dict:
    base_seed, seed_label = seed_spec(config, seed_index)
    result_dir = ROOT / "results" / mode / seed_label
    subject_rows: list[dict] = []
    fold_rows: list[dict] = []
    trial_rows: list[dict] = []

    for fold in config["folds"]:
        fold_id = int(fold["id"])
        fold_dir = result_dir / f"fold_{fold_id:02d}"
        summary_path = fold_dir / "summary.json"
        if not summary_path.is_file():
            raise FileNotFoundError(f"Missing fold result: {summary_path}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if int(summary.get("seed_index", -1)) != seed_index:
            raise ValueError(f"Seed metadata mismatch in {summary_path}")
        if int(summary.get("base_optimization_seed", -1)) != base_seed:
            raise ValueError(f"Base seed metadata mismatch in {summary_path}")

        fold_row = {
            "seed_index": seed_index,
            "base_optimization_seed": base_seed,
            "fold": fold_id,
            "effective_fold_seed": base_seed + fold_id,
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
                    "seed_index": seed_index,
                    "base_optimization_seed": base_seed,
                    "fold": fold_id,
                    "test_subject": subject,
                    **{metric: float(metrics[metric]) for metric in SUBJECT_METRICS},
                }
            )

        trial_path = fold_dir / "test_metrics_by_trial.csv"
        if not trial_path.is_file():
            raise FileNotFoundError(f"Missing trial metrics: {trial_path}")
        for row in read_csv(trial_path):
            trial_rows.append(
                {
                    "seed_index": seed_index,
                    "base_optimization_seed": base_seed,
                    "fold": fold_id,
                    **row,
                }
            )

    expected = {str(item["id"]) for item in config["subjects"]}
    observed = [str(row["test_subject"]) for row in subject_rows]
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError("Every configured subject must appear exactly once per seed")
    if len(observed) != len(set(observed)):
        raise ValueError("A test subject appears in more than one fold within a seed")

    subject_rows.sort(key=lambda row: subject_sort_key(str(row["test_subject"])))
    trial_rows.sort(key=lambda row: (subject_sort_key(str(row["subject"])), str(row["trial"])))
    write_csv(result_dir / "cross_fold_metrics.csv", fold_rows)
    write_csv(result_dir / "cross_subject_metrics.csv", subject_rows)
    write_csv(result_dir / "cross_trial_metrics.csv", trial_rows)

    metrics = {}
    for metric in SUBJECT_METRICS:
        values = np.asarray([float(row[metric]) for row in subject_rows], dtype=float)
        metrics[metric] = {
            "mean_across_test_subjects": float(values.mean()),
            "std_across_test_subjects": float(values.std(ddof=1)),
            "median_across_test_subjects": float(np.median(values)),
            "values_by_test_subject": {
                str(row["test_subject"]): float(row[metric]) for row in subject_rows
            },
        }
    report = {
        "experiment": config["experiment_name"],
        "model_id": config["model_id"],
        "display_name": config["display_name"],
        "training_regime": config["training_regime"],
        "mode": mode,
        "seed_index": seed_index,
        "base_optimization_seed": base_seed,
        "effective_fold_seeds": {
            str(int(fold["id"])): base_seed + int(fold["id"]) for fold in config["folds"]
        },
        "fold_count": len(fold_rows),
        "held_out_test_subject_count": len(subject_rows),
        "held_out_test_trial_count": len(trial_rows),
        "aggregation_unit": "held-out test subject; all 15 subjects contribute exactly once",
        "metrics": metrics,
        "physics_loss_enabled": bool(config["training"]["use_physics"]),
        "physics_residual_diagnostics_posthoc": True,
        "training_sources": config["training_sources"],
    }
    dump_json(result_dir / "aggregate_summary.json", report)
    plot_single_seed(
        subject_rows,
        result_dir / "cross_subject_results.png",
        f"{config['display_name']}: seed {seed_index} ({base_seed})",
    )
    return {
        "seed_index": seed_index,
        "base_seed": base_seed,
        "seed_label": seed_label,
        "subject_rows": subject_rows,
        "fold_rows": fold_rows,
        "trial_rows": trial_rows,
        "report": report,
    }


def mean_ci(values: np.ndarray) -> tuple[float, float]:
    if len(values) < 2:
        return (float(values[0]), float(values[0]))
    sem = float(values.std(ddof=1) / np.sqrt(len(values)))
    half_width = float(student_t.ppf(0.975, df=len(values) - 1) * sem)
    mean = float(values.mean())
    return mean - half_width, mean + half_width


def plot_across_subjects(rows: list[dict], path: Path) -> None:
    subjects = sorted({str(row["test_subject"]) for row in rows}, key=subject_sort_key)
    positions = np.arange(len(subjects), dtype=float)
    rng = np.random.default_rng(20261109)
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=True, constrained_layout=True)
    for axis, (metric, y_label) in zip(axes, PRIMARY_METRICS):
        values = [
            [float(row[metric]) for row in rows if str(row["test_subject"]) == subject]
            for subject in subjects
        ]
        boxes = axis.boxplot(values, positions=positions, widths=0.55, patch_artist=True)
        for box in boxes["boxes"]:
            box.set(facecolor="#4C78A8", alpha=0.58)
        for median in boxes["medians"]:
            median.set(color="white", linewidth=1.7)
        for index, series in enumerate(values):
            jitter = rng.uniform(-0.10, 0.10, size=len(series))
            axis.scatter(positions[index] + jitter, series, s=30, color="#1F4E79", zorder=3)
        axis.set_ylabel(y_label)
        axis.grid(axis="y", alpha=0.25)
    axes[-1].set_xticks(positions, subjects, rotation=45, ha="right")
    fig.suptitle("Five-seed held-out subject errors (one point per seed)")
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)


def plot_seed_means(seed_results: list[dict], path: Path) -> None:
    x = np.arange(1, len(seed_results) + 1)
    labels = [f"{item['seed_index']}\n{item['base_seed']}" for item in seed_results]
    fig, axes = plt.subplots(3, 1, figsize=(11, 11), sharex=True, constrained_layout=True)
    for axis, (metric, y_label) in zip(axes, PRIMARY_METRICS):
        values = np.asarray(
            [
                np.mean([float(row[metric]) for row in item["subject_rows"]])
                for item in seed_results
            ],
            dtype=float,
        )
        axis.plot(x, values, marker="o", linewidth=1.6, color="#4C78A8")
        axis.axhline(values.mean(), linestyle="--", color="#E1812C", label="Five-seed mean")
        axis.set_ylabel(y_label)
        axis.grid(alpha=0.25)
        axis.legend(frameon=False)
    axes[-1].set_xticks(x, labels)
    axes[-1].set_xlabel("Seed index and base optimization seed")
    fig.suptitle("Held-out-subject mean error for each optimization seed")
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)


def aggregate_all_seeds(config: dict, mode: str, seed_results: list[dict]) -> dict:
    result_dir = ROOT / "results" / mode
    all_subject_rows = [row for item in seed_results for row in item["subject_rows"]]
    all_fold_rows = [row for item in seed_results for row in item["fold_rows"]]
    all_trial_rows = [row for item in seed_results for row in item["trial_rows"]]
    write_csv(result_dir / "multi_seed_subject_metrics.csv", all_subject_rows)
    write_csv(result_dir / "multi_seed_fold_metrics.csv", all_fold_rows)
    write_csv(result_dir / "multi_seed_trial_metrics.csv", all_trial_rows)

    metric_reports = {}
    for metric in SUBJECT_METRICS:
        seed_means = np.asarray(
            [
                np.mean([float(row[metric]) for row in item["subject_rows"]])
                for item in seed_results
            ],
            dtype=float,
        )
        subject_reports = {}
        subjects = sorted(
            {str(row["test_subject"]) for row in all_subject_rows}, key=subject_sort_key
        )
        for subject in subjects:
            selected = np.asarray(
                [
                    float(row[metric])
                    for row in all_subject_rows
                    if str(row["test_subject"]) == subject
                ],
                dtype=float,
            )
            subject_reports[subject] = {
                "mean_across_seeds": float(selected.mean()),
                "std_across_seeds": float(selected.std(ddof=1)),
                "values_by_seed_index": {
                    str(row["seed_index"]): float(row[metric])
                    for row in all_subject_rows
                    if str(row["test_subject"]) == subject
                },
            }
        metric_reports[metric] = {
            "mean_of_seed_level_subject_means": float(seed_means.mean()),
            "std_of_seed_level_subject_means": float(seed_means.std(ddof=1)),
            "median_of_seed_level_subject_means": float(np.median(seed_means)),
            "95pct_t_interval_across_seed_level_means": [float(value) for value in mean_ci(seed_means)],
            "subject_mean_by_seed_index": {
                str(item["seed_index"]): float(seed_means[index])
                for index, item in enumerate(seed_results)
            },
            "test_subject_statistics": subject_reports,
        }

    report = {
        "experiment": config["experiment_name"],
        "model_id": config["model_id"],
        "display_name": config["display_name"],
        "training_regime": config["training_regime"],
        "mode": mode,
        "optimization_seed_count": len(seed_results),
        "optimization_seeds": optimization_seeds(config),
        "folds_per_seed": len(config["folds"]),
        "total_trained_fold_models": len(seed_results) * len(config["folds"]),
        "held_out_subject_evaluations": len(all_subject_rows),
        "unique_held_out_subjects": len({row["test_subject"] for row in all_subject_rows}),
        "held_out_trial_evaluations": len(all_trial_rows),
        "primary_analysis": "For each seed, average equally over 15 held-out subject means; summarize those five seed-level means.",
        "seed_pairing_rule": "The same base optimization seeds and fold-specific +fold_id offsets are used by the matched full-fall physics condition.",
        "metrics": metric_reports,
        "physics_loss_enabled": bool(config["training"]["use_physics"]),
        "physics_residual_diagnostics_posthoc": True,
        "limitations": [
            "Five seeds characterize optimization variability but do not create additional independent human subjects.",
            "Each checkpoint is selected using one real validation subject per fold.",
            "Intervals across five seeds are descriptive and have low precision.",
            "Trials shorter than the fixed 0.40-second context are excluded before fitting.",
            "Apparent contact is skeleton-observed rather than force-plate-confirmed.",
            "Physics residuals are post-hoc diagnostics and were not optimized in this condition.",
        ],
    }
    dump_json(result_dir / "multi_seed_summary.json", report)
    plot_across_subjects(all_subject_rows, result_dir / "multi_seed_subject_boxplots.png")
    plot_seed_means(seed_results, result_dir / "multi_seed_seed_means.png")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    parser.add_argument(
        "--seed-index",
        type=int,
        help="Aggregate one seed only; omit to aggregate all configured seeds",
    )
    args = parser.parse_args()
    config = load_config(args.config)

    if args.seed_index is not None:
        result = aggregate_one_seed(config, args.mode, args.seed_index)
        print(json.dumps(result["report"], indent=2))
        return

    seed_results = [
        aggregate_one_seed(config, args.mode, index)
        for index in range(1, len(optimization_seeds(config)) + 1)
    ]
    report = aggregate_all_seeds(config, args.mode, seed_results)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
