#!/usr/bin/env python3
"""Paired five-seed comparison of Model B with and without physics."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import rankdata, t as student_t, wilcoxon


PRIMARY_METRICS = {
    "normalized_mse": "Normalized forecast MSE",
    "theta_rmse_deg": "Angle RMSE (deg)",
    "x_rmse_cm": "CoM displacement RMSE (cm)",
}
ALL_METRICS = (
    "normalized_mse",
    "theta_rmse_deg",
    "theta_mae_deg",
    "x_rmse_cm",
    "x_mae_cm",
    "theta_w1_deg",
    "x_w1_cm",
)
COLORS = {"physics": "#3274A1", "no_physics": "#E1812C"}
SEED_COLORS = plt.cm.tab10(np.linspace(0.0, 0.8, 5))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def subject_number(subject: str) -> int:
    return int(subject.lstrip("S"))


def mean_sd(values: np.ndarray) -> tuple[float, float]:
    return float(values.mean()), float(values.std(ddof=1))


def t_interval(values: np.ndarray) -> list[float]:
    mean = float(values.mean())
    if len(values) < 2:
        return [mean, mean]
    half = float(
        student_t.ppf(0.975, len(values) - 1)
        * values.std(ddof=1)
        / np.sqrt(len(values))
    )
    return [mean - half, mean + half]


def bootstrap_subject_ci(values: np.ndarray, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(100_000, len(values)))
    samples = values[indices].mean(axis=1)
    return [float(value) for value in np.quantile(samples, [0.025, 0.975])]


def matched_rows(
    physics_rows: list[dict[str, str]],
    no_physics_rows: list[dict[str, str]],
    key_fields: tuple[str, ...],
) -> list[dict]:
    def key(row: dict[str, str]) -> tuple[str, ...]:
        return tuple(str(row[field]) for field in key_fields)

    p_map = {key(row): row for row in physics_rows}
    n_map = {key(row): row for row in no_physics_rows}
    if len(p_map) != len(physics_rows) or len(n_map) != len(no_physics_rows):
        raise ValueError(f"Duplicate keys in {key_fields}")
    if set(p_map) != set(n_map):
        missing_n = sorted(set(p_map) - set(n_map))[:5]
        missing_p = sorted(set(n_map) - set(p_map))[:5]
        raise ValueError(
            f"Mismatched {key_fields}: missing no-physics={missing_n}, "
            f"missing physics={missing_p}"
        )

    output: list[dict] = []
    identifier_fields = (
        "seed_index",
        "base_optimization_seed",
        "fold",
        "effective_fold_seed",
        "test_subject",
        "subject",
        "trial",
        "forecast_samples",
        "validation_subject",
        "test_subjects",
    )
    for item in sorted(p_map):
        p_row, n_row = p_map[item], n_map[item]
        row: dict[str, object] = {}
        for field in identifier_fields:
            if field in p_row or field in n_row:
                p_value, n_value = p_row.get(field, ""), n_row.get(field, "")
                if str(p_value) != str(n_value):
                    raise ValueError(f"Mismatched {field} for {item}: {p_value} vs {n_value}")
                row[field] = p_value
        for metric in ALL_METRICS:
            if metric not in p_row or metric not in n_row:
                continue
            p_value = float(p_row[metric])
            n_value = float(n_row[metric])
            difference = n_value - p_value
            row[f"physics_{metric}"] = p_value
            row[f"no_physics_{metric}"] = n_value
            row[f"physics_improvement_{metric}"] = difference
            row[f"physics_relative_improvement_pct_{metric}"] = (
                100.0 * difference / n_value if n_value else float("nan")
            )
        output.append(row)
    return output


def verify_design(physics_root: Path, no_physics_root: Path) -> dict:
    physics = json.loads((physics_root / "experiment.json").read_text(encoding="utf-8"))
    no_physics = json.loads(
        (no_physics_root / "experiment.json").read_text(encoding="utf-8")
    )

    exact_keys = (
        "requires_teachers",
        "training_sources",
        "optimization_seeds",
        "split_seed",
        "randomized_subject_order",
        "subjects",
        "protocol",
        "folds",
        "data",
        "audit_adapter",
        "real_data",
        "model",
        "physics",
    )
    checks = {f"{key}_equal": physics[key] == no_physics[key] for key in exact_keys}

    physics_training = dict(physics["training"])
    no_physics_training = dict(no_physics["training"])
    ablation = {
        "physics_use_physics": physics_training.pop("use_physics"),
        "no_physics_use_physics": no_physics_training.pop("use_physics"),
        "physics_weight": physics_training.pop("physics_weight"),
        "no_physics_weight": no_physics_training.pop("physics_weight"),
    }
    checks["remaining_training_config_equal"] = physics_training == no_physics_training
    checks["no_physics_removed_component_declared"] = (
        no_physics.get("ablation", {}).get("removed_component")
        == "cart_pole_biomechanics_residual"
    )

    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise ValueError(f"Not a matched ablation; failed checks: {failed}")
    expected = {
        "physics_use_physics": True,
        "no_physics_use_physics": False,
        "physics_weight": 0.01,
        "no_physics_weight": 0.0,
    }
    if ablation != expected:
        raise ValueError(f"Unexpected ablation settings: {ablation}")

    return {
        "matched": True,
        "checks": checks,
        "ablation_settings": ablation,
        "optimization_seeds": physics["optimization_seeds"],
        "split_seed": physics["split_seed"],
    }


def prediction_map(root: Path) -> dict[tuple[int, int, str], Path]:
    output = {}
    for path in (root / "results" / "full").glob(
        "seed_*/fold_*/test_predictions/*.npz"
    ):
        seed_index = int(path.parents[2].name.split("_")[1])
        fold = int(path.parents[1].name.split("_")[1])
        key = (seed_index, fold, path.stem)
        if key in output:
            raise ValueError(f"Duplicate prediction key {key}")
        output[key] = path
    return output


def verify_targets(physics_root: Path, no_physics_root: Path) -> dict:
    physics = prediction_map(physics_root)
    no_physics = prediction_map(no_physics_root)
    if set(physics) != set(no_physics):
        raise ValueError("Prediction trial/seed/fold keys differ")

    fields = ("time_s", "target_theta_rad", "target_x_m")
    cross_condition = {field: 0.0 for field in fields}
    within_physics = {field: 0.0 for field in fields}
    within_no_physics = {field: 0.0 for field in fields}
    reference_p: dict[tuple[int, str], dict[str, np.ndarray]] = {}
    reference_n: dict[tuple[int, str], dict[str, np.ndarray]] = {}

    for key in sorted(physics):
        seed_index, fold, trial = key
        with np.load(physics[key]) as p_data, np.load(no_physics[key]) as n_data:
            for field in fields:
                if p_data[field].shape != n_data[field].shape:
                    raise ValueError(f"Target shape mismatch for {key}, {field}")
                cross_condition[field] = max(
                    cross_condition[field],
                    float(np.max(np.abs(p_data[field] - n_data[field]), initial=0.0)),
                )
            reference_key = (fold, trial)
            if reference_key not in reference_p:
                reference_p[reference_key] = {field: p_data[field].copy() for field in fields}
                reference_n[reference_key] = {field: n_data[field].copy() for field in fields}
            else:
                for field in fields:
                    within_physics[field] = max(
                        within_physics[field],
                        float(
                            np.max(
                                np.abs(p_data[field] - reference_p[reference_key][field]),
                                initial=0.0,
                            )
                        ),
                    )
                    within_no_physics[field] = max(
                        within_no_physics[field],
                        float(
                            np.max(
                                np.abs(n_data[field] - reference_n[reference_key][field]),
                                initial=0.0,
                            )
                        ),
                    )

    return {
        "matched_prediction_evaluations": len(physics),
        "unique_trials": len({key[2] for key in physics}),
        "targets_identical_across_conditions": all(
            value == 0.0 for value in cross_condition.values()
        ),
        "targets_identical_across_seeds_within_physics": all(
            value == 0.0 for value in within_physics.values()
        ),
        "targets_identical_across_seeds_within_no_physics": all(
            value == 0.0 for value in within_no_physics.values()
        ),
        "maximum_absolute_cross_condition_difference": cross_condition,
        "maximum_absolute_within_physics_seed_difference": within_physics,
        "maximum_absolute_within_no_physics_seed_difference": within_no_physics,
    }


def aggregate_subjects(subject_seed_rows: list[dict]) -> list[dict]:
    subjects = sorted(
        {str(row["test_subject"]) for row in subject_seed_rows}, key=subject_number
    )
    output = []
    for subject in subjects:
        selected = [row for row in subject_seed_rows if row["test_subject"] == subject]
        row: dict[str, object] = {
            "test_subject": subject,
            "fold": int(selected[0]["fold"]),
            "seed_count": len(selected),
        }
        for metric in ALL_METRICS:
            physics = np.asarray([item[f"physics_{metric}"] for item in selected])
            no_physics = np.asarray([item[f"no_physics_{metric}"] for item in selected])
            difference = no_physics - physics
            row[f"physics_mean_{metric}"], row[f"physics_sd_{metric}"] = mean_sd(physics)
            row[f"no_physics_mean_{metric}"], row[f"no_physics_sd_{metric}"] = mean_sd(
                no_physics
            )
            row[f"mean_physics_improvement_{metric}"], row[
                f"sd_physics_improvement_{metric}"
            ] = mean_sd(difference)
            row[f"physics_seed_wins_{metric}"] = int(np.sum(difference > 0))
            row[f"no_physics_seed_wins_{metric}"] = int(np.sum(difference < 0))
        output.append(row)
    return output


def aggregate_trials(trial_seed_rows: list[dict]) -> list[dict]:
    trials = sorted({str(row["trial"]) for row in trial_seed_rows})
    output = []
    for trial in trials:
        selected = [row for row in trial_seed_rows if row["trial"] == trial]
        row: dict[str, object] = {
            "trial": trial,
            "subject": selected[0]["subject"],
            "fold": int(selected[0]["fold"]),
            "seed_count": len(selected),
        }
        for metric in ALL_METRICS:
            physics = np.asarray([item[f"physics_{metric}"] for item in selected])
            no_physics = np.asarray([item[f"no_physics_{metric}"] for item in selected])
            difference = no_physics - physics
            row[f"physics_mean_{metric}"] = float(physics.mean())
            row[f"no_physics_mean_{metric}"] = float(no_physics.mean())
            row[f"mean_physics_improvement_{metric}"] = float(difference.mean())
            row[f"physics_seed_wins_{metric}"] = int(np.sum(difference > 0))
            row[f"no_physics_seed_wins_{metric}"] = int(np.sum(difference < 0))
        output.append(row)
    return output


def aggregate_seeds(subject_seed_rows: list[dict]) -> list[dict]:
    seed_indices = sorted({int(row["seed_index"]) for row in subject_seed_rows})
    output = []
    for seed_index in seed_indices:
        selected = [
            row for row in subject_seed_rows if int(row["seed_index"]) == seed_index
        ]
        row: dict[str, object] = {
            "seed_index": seed_index,
            "base_optimization_seed": int(selected[0]["base_optimization_seed"]),
            "held_out_subject_count": len(selected),
        }
        for metric in ALL_METRICS:
            physics = np.asarray([item[f"physics_{metric}"] for item in selected])
            no_physics = np.asarray([item[f"no_physics_{metric}"] for item in selected])
            difference = no_physics - physics
            row[f"physics_subject_mean_{metric}"] = float(physics.mean())
            row[f"no_physics_subject_mean_{metric}"] = float(no_physics.mean())
            row[f"physics_improvement_{metric}"] = float(difference.mean())
            row[f"physics_subject_wins_{metric}"] = int(np.sum(difference > 0))
            row[f"no_physics_subject_wins_{metric}"] = int(np.sum(difference < 0))
        output.append(row)
    return output


def rank_biserial(differences: np.ndarray) -> float:
    selected = differences[differences != 0.0]
    if not len(selected):
        return 0.0
    ranks = rankdata(np.abs(selected))
    total = float(ranks.sum())
    return float((ranks[selected > 0].sum() - ranks[selected < 0].sum()) / total)


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=p_values.get)
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for index, metric in enumerate(ordered):
        value = min(1.0, (count - index) * p_values[metric])
        running = max(running, value)
        adjusted[metric] = running
    return adjusted


def summarize(
    subject_seed_rows: list[dict],
    subject_rows: list[dict],
    trial_seed_rows: list[dict],
    trial_rows: list[dict],
    seed_rows: list[dict],
) -> dict:
    raw_p_values = {}
    metric_reports = {}
    for offset, metric in enumerate(PRIMARY_METRICS):
        subject_differences = np.asarray(
            [row[f"mean_physics_improvement_{metric}"] for row in subject_rows],
            dtype=float,
        )
        physics_subject = np.asarray(
            [row[f"physics_mean_{metric}"] for row in subject_rows], dtype=float
        )
        no_physics_subject = np.asarray(
            [row[f"no_physics_mean_{metric}"] for row in subject_rows], dtype=float
        )
        seed_differences = np.asarray(
            [row[f"physics_improvement_{metric}"] for row in seed_rows], dtype=float
        )
        trial_differences = np.asarray(
            [row[f"mean_physics_improvement_{metric}"] for row in trial_rows],
            dtype=float,
        )
        all_subject_seed_differences = np.asarray(
            [row[f"physics_improvement_{metric}"] for row in subject_seed_rows],
            dtype=float,
        )
        all_trial_seed_differences = np.asarray(
            [row[f"physics_improvement_{metric}"] for row in trial_seed_rows],
            dtype=float,
        )

        if np.all(subject_differences == 0.0):
            statistic, p_value = 0.0, 1.0
        else:
            result = wilcoxon(
                subject_differences, zero_method="wilcox", alternative="two-sided"
            )
            statistic, p_value = float(result.statistic), float(result.pvalue)
        raw_p_values[metric] = p_value

        difference_mean = float(subject_differences.mean())
        largest_index = int(np.argmax(np.abs(subject_differences)))
        leave_one_out = np.asarray(
            [
                np.delete(subject_differences, index).mean()
                for index in range(len(subject_differences))
            ]
        )
        metric_reports[metric] = {
            "physics_five_seed_subject_mean": float(physics_subject.mean()),
            "no_physics_five_seed_subject_mean": float(no_physics_subject.mean()),
            "mean_physics_improvement": difference_mean,
            "median_subject_improvement": float(np.median(subject_differences)),
            "relative_improvement_pct": float(
                100.0 * difference_mean / no_physics_subject.mean()
            ),
            "largest_absolute_subject_effect": {
                "subject": subject_rows[largest_index]["test_subject"],
                "physics_improvement": float(subject_differences[largest_index]),
            },
            "mean_improvement_excluding_largest_absolute_subject": float(
                np.delete(subject_differences, largest_index).mean()
            ),
            "leave_one_subject_out_mean_improvement_range": [
                float(leave_one_out.min()),
                float(leave_one_out.max()),
            ],
            "subject_bootstrap_95pct_ci_for_mean_improvement": bootstrap_subject_ci(
                subject_differences, 20261109 + offset
            ),
            "seed_level_improvements": [float(value) for value in seed_differences],
            "mean_seed_level_improvement": float(seed_differences.mean()),
            "sd_across_seed_level_improvements": float(seed_differences.std(ddof=1)),
            "descriptive_95pct_t_interval_across_seed_improvements": t_interval(
                seed_differences
            ),
            "physics_seed_wins": int(np.sum(seed_differences > 0)),
            "no_physics_seed_wins": int(np.sum(seed_differences < 0)),
            "physics_subject_wins_based_on_five_seed_mean": int(
                np.sum(subject_differences > 0)
            ),
            "no_physics_subject_wins_based_on_five_seed_mean": int(
                np.sum(subject_differences < 0)
            ),
            "subject_ties": int(np.sum(subject_differences == 0)),
            "subjects_where_physics_won_all_five_seeds": int(
                sum(
                    int(row[f"physics_seed_wins_{metric}"]) == 5
                    for row in subject_rows
                )
            ),
            "subjects_where_no_physics_won_all_five_seeds": int(
                sum(
                    int(row[f"no_physics_seed_wins_{metric}"]) == 5
                    for row in subject_rows
                )
            ),
            "wilcoxon_signed_rank_statistic_on_15_subject_seed_averages": statistic,
            "wilcoxon_two_sided_raw_p_value": p_value,
            "paired_rank_biserial_correlation": rank_biserial(subject_differences),
            "paired_cohens_dz": float(
                subject_differences.mean() / subject_differences.std(ddof=1)
            ),
            "physics_trial_wins_based_on_five_seed_mean_descriptive": int(
                np.sum(trial_differences > 0)
            ),
            "no_physics_trial_wins_based_on_five_seed_mean_descriptive": int(
                np.sum(trial_differences < 0)
            ),
            "physics_subject_seed_wins_descriptive": int(
                np.sum(all_subject_seed_differences > 0)
            ),
            "no_physics_subject_seed_wins_descriptive": int(
                np.sum(all_subject_seed_differences < 0)
            ),
            "physics_trial_seed_wins_descriptive": int(
                np.sum(all_trial_seed_differences > 0)
            ),
            "no_physics_trial_seed_wins_descriptive": int(
                np.sum(all_trial_seed_differences < 0)
            ),
        }

    adjusted = holm_adjust(raw_p_values)
    for metric in PRIMARY_METRICS:
        metric_reports[metric]["holm_adjusted_p_value_across_three_primary_metrics"] = (
            adjusted[metric]
        )
    return metric_reports


def compare_training_selection(physics_root: Path, no_physics_root: Path) -> list[dict]:
    rows = []
    for seed_index in range(1, 6):
        seed_label = f"seed_{seed_index:02d}_{20261100 + seed_index}"
        for fold in range(1, 6):
            p_path = (
                physics_root
                / "results"
                / "full"
                / seed_label
                / f"fold_{fold:02d}"
                / "training_selection.json"
            )
            n_path = (
                no_physics_root
                / "results"
                / "full"
                / seed_label
                / f"fold_{fold:02d}"
                / "training_selection.json"
            )
            p = json.loads(p_path.read_text(encoding="utf-8"))
            n = json.loads(n_path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "seed_index": seed_index,
                    "base_optimization_seed": 20261100 + seed_index,
                    "fold": fold,
                    "physics_best_epoch": p["best_epoch"],
                    "no_physics_best_epoch": n["best_epoch"],
                    "physics_best_validation_normalized_mse": p[
                        "best_validation_value"
                    ],
                    "no_physics_best_validation_normalized_mse": n[
                        "best_validation_value"
                    ],
                }
            )
    return rows


def summarize_folds(fold_rows: list[dict]) -> dict:
    report = {}
    for fold in range(1, 6):
        selected = [row for row in fold_rows if int(row["fold"]) == fold]
        report[str(fold)] = {
            "test_subjects": selected[0]["test_subjects"],
            "mean_physics_improvement_across_seeds": {
                metric: float(
                    np.mean(
                        [row[f"physics_improvement_{metric}"] for row in selected]
                    )
                )
                for metric in PRIMARY_METRICS
            },
        }
    return report


def plot_seed_means(seed_rows: list[dict], output: Path) -> None:
    x = np.arange(1, 6)
    labels = [f"{row['seed_index']}\n{row['base_optimization_seed']}" for row in seed_rows]
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 11), sharex=True, constrained_layout=True)
    for axis, (metric, label) in zip(axes, PRIMARY_METRICS.items()):
        physics = np.asarray([row[f"physics_subject_mean_{metric}"] for row in seed_rows])
        no_physics = np.asarray(
            [row[f"no_physics_subject_mean_{metric}"] for row in seed_rows]
        )
        for index in range(5):
            axis.plot(
                [x[index] - 0.08, x[index] + 0.08],
                [physics[index], no_physics[index]],
                color="#A0A0A0",
                linewidth=1.2,
            )
        axis.scatter(
            x - 0.08,
            physics,
            color=COLORS["physics"],
            s=58,
            label="Unified Physics",
            zorder=3,
        )
        axis.scatter(
            x + 0.08,
            no_physics,
            color=COLORS["no_physics"],
            s=58,
            label="No Physics",
            zorder=3,
        )
        difference = no_physics - physics
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=0.24)
        axis.text(
            0.99,
            0.94,
            f"Mean paired difference = {difference.mean():.3f}\n"
            f"Physics wins {int(np.sum(difference > 0))}/5 seeds",
            transform=axis.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "#DDDDDD", "alpha": 0.9},
        )
    axes[0].legend(frameon=False, ncol=2, loc="upper left")
    axes[-1].set_xticks(x, labels)
    axes[-1].set_xlabel("Seed index and base optimization seed")
    fig.suptitle("Paired held-out-subject mean error for every seed")
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_subject_means(subject_rows: list[dict], output: Path) -> None:
    subjects = [row["test_subject"] for row in subject_rows]
    x = np.arange(len(subjects))
    fig, axes = plt.subplots(3, 1, figsize=(17, 12), sharex=True, constrained_layout=True)
    for axis, (metric, label) in zip(axes, PRIMARY_METRICS.items()):
        physics = np.asarray([row[f"physics_mean_{metric}"] for row in subject_rows])
        no_physics = np.asarray(
            [row[f"no_physics_mean_{metric}"] for row in subject_rows]
        )
        p_sd = np.asarray([row[f"physics_sd_{metric}"] for row in subject_rows])
        n_sd = np.asarray([row[f"no_physics_sd_{metric}"] for row in subject_rows])
        for index in range(len(subjects)):
            axis.plot(
                [x[index] - 0.12, x[index] + 0.12],
                [physics[index], no_physics[index]],
                color="#A0A0A0",
                linewidth=1,
            )
        axis.errorbar(
            x - 0.12,
            physics,
            yerr=p_sd,
            fmt="o",
            color=COLORS["physics"],
            capsize=2.5,
            label="Unified Physics mean ± seed SD",
        )
        axis.errorbar(
            x + 0.12,
            no_physics,
            yerr=n_sd,
            fmt="o",
            color=COLORS["no_physics"],
            capsize=2.5,
            label="No Physics mean ± seed SD",
        )
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=0.24)
    axes[0].legend(frameon=False, ncol=2, loc="upper left")
    axes[-1].set_xticks(x, subjects, rotation=45, ha="right")
    fig.suptitle("Five-seed mean error for each held-out subject")
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_subject_difference_boxplots(
    subject_seed_rows: list[dict], output: Path
) -> None:
    subjects = sorted(
        {str(row["test_subject"]) for row in subject_seed_rows}, key=subject_number
    )
    positions = np.arange(len(subjects))
    fig, axes = plt.subplots(3, 1, figsize=(17, 12), sharex=True, constrained_layout=True)
    for axis, (metric, label) in zip(axes, PRIMARY_METRICS.items()):
        values = [
            [
                row[f"physics_improvement_{metric}"]
                for row in subject_seed_rows
                if row["test_subject"] == subject
            ]
            for subject in subjects
        ]
        boxes = axis.boxplot(
            values,
            positions=positions,
            widths=0.56,
            patch_artist=True,
            showfliers=False,
            medianprops={"color": "white", "linewidth": 1.6},
        )
        for box in boxes["boxes"]:
            box.set(facecolor="#55A868", alpha=0.68)
        for seed_index in range(1, 6):
            seed_values = [
                next(
                    row[f"physics_improvement_{metric}"]
                    for row in subject_seed_rows
                    if row["test_subject"] == subject
                    and int(row["seed_index"]) == seed_index
                )
                for subject in subjects
            ]
            axis.scatter(
                positions + (seed_index - 3) * 0.045,
                seed_values,
                s=28,
                color=SEED_COLORS[seed_index - 1],
                edgecolors="white",
                linewidths=0.4,
                label=f"Seed {seed_index}",
                zorder=3,
            )
        axis.axhline(0.0, color="black", linewidth=1, linestyle="--")
        axis.set_ylabel(f"No physics − physics\n{label}")
        axis.grid(axis="y", alpha=0.24)
    axes[0].legend(frameon=False, ncol=5, loc="upper left")
    axes[-1].set_xticks(positions, subjects, rotation=45, ha="right")
    axes[-1].set_xlabel("Positive values favor Unified Physics")
    fig.suptitle("Distribution of paired physics improvement across five seeds")
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_fold_heatmaps(fold_rows: list[dict], output: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.6), constrained_layout=True)
    for axis, (metric, label) in zip(axes, PRIMARY_METRICS.items()):
        matrix = np.zeros((5, 5))
        for row in fold_rows:
            matrix[int(row["seed_index"]) - 1, int(row["fold"]) - 1] = row[
                f"physics_improvement_{metric}"
            ]
        limit = max(abs(float(matrix.min())), abs(float(matrix.max())))
        image = axis.imshow(matrix, cmap="RdBu", vmin=-limit, vmax=limit, aspect="auto")
        for row_index in range(5):
            for column_index in range(5):
                value = matrix[row_index, column_index]
                axis.text(
                    column_index,
                    row_index,
                    f"{value:.3f}" if metric == "normalized_mse" else f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if abs(value) > 0.62 * limit else "black",
                )
        axis.set_xticks(range(5), [f"Fold {value}" for value in range(1, 6)])
        axis.set_yticks(range(5), [f"Seed {value}" for value in range(1, 6)])
        axis.set_title(label)
        fig.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    fig.suptitle(
        "Paired fold difference: no-physics error − physics error\n"
        "Blue/positive favors physics; red/negative favors no physics"
    )
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_subject_scatter(subject_rows: list[dict], output: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.3), constrained_layout=True)
    for axis, (metric, label) in zip(axes, PRIMARY_METRICS.items()):
        physics = np.asarray([row[f"physics_mean_{metric}"] for row in subject_rows])
        no_physics = np.asarray(
            [row[f"no_physics_mean_{metric}"] for row in subject_rows]
        )
        lower = min(float(physics.min()), float(no_physics.min()))
        upper = max(float(physics.max()), float(no_physics.max()))
        padding = 0.06 * (upper - lower if upper > lower else 1.0)
        axis.plot(
            [lower - padding, upper + padding],
            [lower - padding, upper + padding],
            color="black",
            linestyle="--",
            linewidth=1,
        )
        axis.scatter(no_physics, physics, color="#4C78A8", s=48)
        for row, x_value, y_value in zip(subject_rows, no_physics, physics):
            axis.annotate(
                row["test_subject"],
                (x_value, y_value),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=7,
            )
        axis.set_xlabel(f"No Physics: {label}")
        axis.set_ylabel(f"Unified Physics: {label}")
        axis.set_xlim(lower - padding, upper + padding)
        axis.set_ylim(lower - padding, upper + padding)
        axis.grid(alpha=0.22)
    fig.suptitle("Held-out subject five-seed means (below diagonal favors physics)")
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physics-results", type=Path, required=True)
    parser.add_argument("--no-physics-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    physics_root = args.physics_results.resolve()
    no_physics_root = args.no_physics_results.resolve()
    output = args.output.resolve()
    figures = output / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    design = verify_design(physics_root, no_physics_root)
    targets = verify_targets(physics_root, no_physics_root)

    subject_seed_rows = matched_rows(
        read_csv(physics_root / "results/full/multi_seed_subject_metrics.csv"),
        read_csv(no_physics_root / "results/full/multi_seed_subject_metrics.csv"),
        ("seed_index", "fold", "test_subject"),
    )
    trial_seed_rows = matched_rows(
        read_csv(physics_root / "results/full/multi_seed_trial_metrics.csv"),
        read_csv(no_physics_root / "results/full/multi_seed_trial_metrics.csv"),
        ("seed_index", "fold", "subject", "trial"),
    )
    fold_seed_rows = matched_rows(
        read_csv(physics_root / "results/full/multi_seed_fold_metrics.csv"),
        read_csv(no_physics_root / "results/full/multi_seed_fold_metrics.csv"),
        ("seed_index", "fold"),
    )

    if (len(subject_seed_rows), len(trial_seed_rows), len(fold_seed_rows)) != (
        75,
        330,
        25,
    ):
        raise ValueError(
            "Unexpected paired row counts: "
            f"{len(subject_seed_rows)}, {len(trial_seed_rows)}, {len(fold_seed_rows)}"
        )

    subject_rows = aggregate_subjects(subject_seed_rows)
    trial_rows = aggregate_trials(trial_seed_rows)
    seed_rows = aggregate_seeds(subject_seed_rows)
    training_rows = compare_training_selection(physics_root, no_physics_root)
    metrics = summarize(
        subject_seed_rows, subject_rows, trial_seed_rows, trial_rows, seed_rows
    )

    write_csv(output / "paired_subject_seed_metrics.csv", subject_seed_rows)
    write_csv(output / "paired_subject_metrics.csv", subject_rows)
    write_csv(output / "paired_trial_seed_metrics.csv", trial_seed_rows)
    write_csv(output / "paired_trial_metrics.csv", trial_rows)
    write_csv(output / "paired_fold_seed_metrics.csv", fold_seed_rows)
    write_csv(output / "paired_seed_metrics.csv", seed_rows)
    write_csv(output / "training_selection_comparison.csv", training_rows)

    report = {
        "comparison": "Model B Unified Physics versus paired B-no-physics ablation, five seeds",
        "difference_definition": "no_physics_error - physics_error; positive values favor Unified Physics",
        "primary_analysis_unit": "15 held-out subjects after averaging each subject across the same five seeds",
        "counts": {
            "independent_human_subjects": len(subject_rows),
            "optimization_seeds": len(seed_rows),
            "trained_models_per_condition": len(fold_seed_rows),
            "paired_subject_seed_evaluations": len(subject_seed_rows),
            "unique_held_out_trials": len(trial_rows),
            "paired_trial_seed_evaluations": len(trial_seed_rows),
        },
        "design_verification": design,
        "target_verification": targets,
        "metrics": metrics,
        "fold_analysis": summarize_folds(fold_seed_rows),
        "inference_note": (
            "Wilcoxon tests use 15 paired subject-level differences after averaging "
            "over the five matched optimization seeds. Holm correction covers the "
            "three primary metrics. Seed t intervals and trial win counts are descriptive."
        ),
        "controller_note": (
            "The four no-physics controller outputs are unsupervised latent variables "
            "and are not comparable as biomechanical gains."
        ),
        "limitations": [
            "There are 15 independent subjects; five seeds quantify optimization variability but do not create 75 independent people.",
            "The five-seed t intervals are descriptive and imprecise.",
            "Trials within a subject are correlated, so trial-level win counts are descriptive.",
            "Apparent contact is based on skeleton/video phase marking rather than force-plate contact.",
        ],
    }
    (output / "comparison_summary.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    plot_seed_means(seed_rows, figures / "paired_seed_means.png")
    plot_subject_means(subject_rows, figures / "paired_subject_means.png")
    plot_subject_difference_boxplots(
        subject_seed_rows, figures / "paired_subject_difference_boxplots.png"
    )
    plot_fold_heatmaps(fold_seed_rows, figures / "paired_fold_difference_heatmaps.png")
    plot_subject_scatter(subject_rows, figures / "paired_subject_scatter.png")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

