#!/usr/bin/env python3
"""Compare selected A10-A13 activity-specific V2 with matched lambda=0."""

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
from scipy.stats import wilcoxon

from operator_core import ROOT, dump_json, load_config, seed_spec


PRIMARY = (
    ("normalized_mse", "Normalized forecast MSE"),
    ("theta_rmse_deg", "Theta RMSE (degrees)"),
    ("x_rmse_cm", "CoM-x RMSE (cm)"),
)
ALL_METRICS = (
    "normalized_mse", "theta_rmse_deg", "theta_mae_deg", "x_rmse_cm",
    "x_mae_cm", "theta_w1_deg", "x_w1_cm", "angular_residual_rmse",
    "horizontal_residual_rmse",
)


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


def keyed(rows: list[dict[str, str]], keys: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, str]]:
    result = {tuple(row[key] for key in keys): row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate keys in {keys}")
    return result


def pair_rows(selected: list[dict[str, str]], baseline: list[dict[str, str]], keys: tuple[str, ...]) -> list[dict]:
    left = keyed(selected, keys)
    right = keyed(baseline, keys)
    if set(left) != set(right):
        raise ValueError("selected V2 and matched lambda=0 pairing keys differ")
    rows = []
    for pair_key in sorted(left):
        row = {name: value for name, value in zip(keys, pair_key)}
        if "selected_physics_weight" in left[pair_key]:
            row["selected_physics_weight"] = float(left[pair_key]["selected_physics_weight"])
        for metric in ALL_METRICS:
            selected_value = float(left[pair_key][metric])
            baseline_value = float(right[pair_key][metric])
            improvement = baseline_value - selected_value
            row[f"selected_v2_{metric}"] = selected_value
            row[f"no_physics_{metric}"] = baseline_value
            row[f"selected_v2_improvement_{metric}"] = improvement
            row[f"selected_v2_relative_improvement_pct_{metric}"] = 100.0 * improvement / baseline_value if baseline_value else None
        rows.append(row)
    return rows


def average_subjects(rows: list[dict], expected_seeds: int) -> list[dict]:
    subjects = sorted({row["test_subject"] for row in rows}, key=lambda value: int(value[1:]))
    output = []
    for subject in subjects:
        selected = [row for row in rows if row["test_subject"] == subject]
        if len(selected) != expected_seeds:
            raise ValueError(f"{subject}: expected {expected_seeds} seed rows, found {len(selected)}")
        row = {"test_subject": subject, "seed_count": expected_seeds}
        for metric in ALL_METRICS:
            for prefix in ("selected_v2_", "no_physics_", "selected_v2_improvement_"):
                key = prefix + metric
                row[key] = float(np.mean([float(item[key]) for item in selected]))
        output.append(row)
    return output


def activity_breakdown(rows: list[dict]) -> list[dict]:
    """Descriptive activity results after equalizing trials within subject-seed cells."""
    output = []
    for activity in ("A10", "A11", "A12", "A13"):
        selected = [row for row in rows if row["activity"] == activity]
        cell_keys = sorted({(row["seed_index"], row["subject"]) for row in selected})
        result = {"activity": activity, "subject_seed_cells": len(cell_keys)}
        for metric, _ in PRIMARY:
            selected_cells = []
            baseline_cells = []
            for seed_index, subject in cell_keys:
                cell = [
                    row for row in selected
                    if row["seed_index"] == seed_index and row["subject"] == subject
                ]
                selected_cells.append(np.mean([float(row[f"selected_v2_{metric}"]) for row in cell]))
                baseline_cells.append(np.mean([float(row[f"no_physics_{metric}"]) for row in cell]))
            selected_values = np.asarray(selected_cells)
            baseline_values = np.asarray(baseline_cells)
            improvement = baseline_values - selected_values
            result[f"selected_v2_{metric}"] = float(selected_values.mean())
            result[f"no_physics_{metric}"] = float(baseline_values.mean())
            result[f"selected_v2_improvement_{metric}"] = float(improvement.mean())
            result[f"selected_v2_relative_improvement_pct_{metric}"] = float(
                100.0 * improvement.mean() / baseline_values.mean()
            )
            result[f"selected_v2_cell_wins_{metric}"] = int(np.sum(improvement > 0))
            result[f"no_physics_cell_wins_{metric}"] = int(np.sum(improvement < 0))
        output.append(result)
    return output


def holm_adjust(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values, key=values.get)
    output: dict[str, float] = {}
    running = 0.0
    for rank, metric in enumerate(ordered):
        adjusted = min(1.0, (len(ordered) - rank) * values[metric])
        running = max(running, adjusted)
        output[metric] = running
    return output


def bootstrap_ci(values: np.ndarray, seed: int = 20261121, repeats: int = 20000) -> list[float]:
    generator = np.random.default_rng(seed)
    means = np.asarray([generator.choice(values, size=len(values), replace=True).mean() for _ in range(repeats)])
    return [float(np.quantile(means, .025)), float(np.quantile(means, .975))]


def paired_wilcoxon(values: np.ndarray) -> tuple[float, float]:
    if np.allclose(values, 0.0, rtol=0.0, atol=0.0):
        return 0.0, 1.0
    test = wilcoxon(values, alternative="two-sided", zero_method="wilcox")
    return float(test.statistic), float(test.pvalue)


def plot_boxplots(rows: list[dict], destination: Path, expected_seeds: int) -> None:
    subjects = sorted({row["test_subject"] for row in rows}, key=lambda value: int(value[1:]))
    centers = np.arange(len(subjects), dtype=float) * 2.4 + 1.0
    fig, axes = plt.subplots(3, 1, figsize=(19, 13), sharex=True)
    for axis, (metric, label) in zip(axes, PRIMARY):
        selected = [[float(row[f"selected_v2_{metric}"]) for row in rows if row["test_subject"] == subject] for subject in subjects]
        baseline = [[float(row[f"no_physics_{metric}"]) for row in rows if row["test_subject"] == subject] for subject in subjects]
        first = axis.boxplot(selected, positions=centers - .38, widths=.62, patch_artist=True, manage_ticks=False)
        second = axis.boxplot(baseline, positions=centers + .38, widths=.62, patch_artist=True, manage_ticks=False)
        for patch in first["boxes"]:
            patch.set_facecolor("#4472C4"); patch.set_alpha(.78)
        for patch in second["boxes"]:
            patch.set_facecolor("#ED7D31"); patch.set_alpha(.78)
        axis.plot([], [], color="#4472C4", linewidth=8, alpha=.78, label="Activity-specific V2")
        axis.plot([], [], color="#ED7D31", linewidth=8, alpha=.78, label="Matched from-scratch λ=0")
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=.25)
        axis.legend(loc="upper right")
    axes[-1].set_xticks(centers, subjects)
    axes[-1].set_xlabel(f"Held-out subject; each box contains {expected_seeds} matched seed(s)")
    fig.suptitle("A10-A13 activity-specific physics V2 versus matched λ=0")
    fig.tight_layout()
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def plot_activity_boxplots(rows: list[dict], destination: Path) -> None:
    activities = ("A10", "A11", "A12", "A13")
    centers = np.arange(len(activities), dtype=float) * 2.4 + 1.0
    fig, axes = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    for axis, (metric, label) in zip(axes, PRIMARY):
        selected = [[float(row[f"selected_v2_{metric}"]) for row in rows if row["activity"] == activity] for activity in activities]
        baseline = [[float(row[f"no_physics_{metric}"]) for row in rows if row["activity"] == activity] for activity in activities]
        left = axis.boxplot(selected, positions=centers-.38, widths=.62, patch_artist=True, manage_ticks=False)
        right = axis.boxplot(baseline, positions=centers+.38, widths=.62, patch_artist=True, manage_ticks=False)
        for patch in left["boxes"]: patch.set_facecolor("#4472C4"); patch.set_alpha(.78)
        for patch in right["boxes"]: patch.set_facecolor("#ED7D31"); patch.set_alpha(.78)
        axis.plot([], [], color="#4472C4", linewidth=8, alpha=.78, label="Selected V2")
        axis.plot([], [], color="#ED7D31", linewidth=8, alpha=.78, label="Matched λ=0")
        axis.set_ylabel(label); axis.grid(axis="y", alpha=.25); axis.legend()
    axes[-1].set_xticks(centers, activities)
    axes[-1].set_xlabel("Held-out activity trials")
    fig.suptitle("Activity-specific held-out comparison")
    fig.tight_layout(); fig.savefig(destination, dpi=180); plt.close(fig)


def findings_markdown(summary: dict) -> str:
    scope = "five-seed confirmation" if summary["counts"]["optimization_seeds"] == 5 else "one-seed pilot"
    lines = [
        f"# A10-A13 activity-specific physics V2 — {scope}",
        "",
        "Positive improvement means `matched λ=0 − selected V2`; positive values favor selected V2.",
        "",
        "| Metric | Selected V2 | Matched λ=0 | V2 improvement | Relative | Subject wins V2/N | Holm p |",
        "|:--|--:|--:|--:|--:|--:|--:|",
    ]
    for metric, label in PRIMARY:
        item = summary["primary_metrics"][metric]
        suffix = "°" if metric == "theta_rmse_deg" else (" cm" if metric == "x_rmse_cm" else "")
        lines.append(
            f"| {label} | {item['selected_v2_mean']:.4f}{suffix} | {item['no_physics_mean']:.4f}{suffix} | "
            f"{item['mean_v2_improvement']:+.4f}{suffix} | {item['relative_improvement_pct']:+.2f}% | "
            f"{item['v2_subject_wins']}/{item['no_physics_subject_wins']} | {item['holm_adjusted_p_value']:.4f} |"
        )
    lines += [
        "",
        f"Selected weight counts across fold-seed models: `{summary['weight_selection']['counts']}`.",
        "",
        "## Descriptive activity results",
        "",
        "Positive percentages favor selected V2. These activity rows are descriptive; subject-level inference remains primary.",
        "",
        "| Activity | Normalized MSE | Theta RMSE | CoM-x RMSE |",
        "|:--|--:|--:|--:|",
    ]
    for row in summary["descriptive_activity_results"]:
        lines.append(
            f"| {row['activity']} | {row['selected_v2_relative_improvement_pct_normalized_mse']:+.2f}% | "
            f"{row['selected_v2_relative_improvement_pct_theta_rmse_deg']:+.2f}% | "
            f"{row['selected_v2_relative_improvement_pct_x_rmse_cm']:+.2f}% |"
        )
    lines += [
        "",
        "Weights and checkpoints were selected only from the two validation subjects using subject-activity-balanced forecast MSE. Test subjects were evaluated after selection.",
        "",
        "All four arms were trained from scratch with the same initialization, optimizer, schedule, data order, and checkpoint rule within each seed-fold.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--seed-index", type=int)
    args = parser.parse_args()
    config = load_config(args.config)
    base = ROOT / "results" / "matched_no_physics" / "full"
    if args.seed_index:
        _, label = seed_spec(config, args.seed_index)
        selected_rows = read_csv(ROOT / "results" / "selected" / "full" / label / "cross_subject_metrics.csv")
        baseline_rows = read_csv(base / label / "cross_subject_metrics.csv")
        selections = read_csv(ROOT / "results" / "selected" / "full" / label / "weight_selections.csv")
        selected_trials = read_csv(ROOT / "results" / "selected" / "full" / label / "cross_trial_metrics.csv")
        baseline_trials = read_csv(base / label / "cross_trial_metrics.csv")
        expected_seeds = 1
        destination = ROOT / "comparison" / f"pilot_seed_{args.seed_index:02d}"
    else:
        selected_rows = read_csv(ROOT / "results" / "selected" / "full" / "multi_seed_subject_metrics.csv")
        baseline_rows = read_csv(base / "multi_seed_subject_metrics.csv")
        selections = read_csv(ROOT / "results" / "selected" / "full" / "multi_seed_weight_selections.csv")
        selected_trials = read_csv(ROOT / "results" / "selected" / "full" / "multi_seed_trial_metrics.csv")
        baseline_trials = read_csv(base / "multi_seed_trial_metrics.csv")
        expected_seeds = 5
        destination = ROOT / "comparison" / "full"
    paired = pair_rows(selected_rows, baseline_rows, ("seed_index", "test_subject"))
    paired_trials = pair_rows(
        selected_trials, baseline_trials,
        ("seed_index", "subject", "activity", "trial"),
    )
    activity_rows = activity_breakdown(paired_trials)
    subject_rows = average_subjects(paired, expected_seeds)
    raw_p: dict[str, float] = {}
    primary = {}
    for metric, _ in PRIMARY:
        selected = np.asarray([row[f"selected_v2_{metric}"] for row in subject_rows])
        baseline = np.asarray([row[f"no_physics_{metric}"] for row in subject_rows])
        improvement = baseline - selected
        statistic, p_value = paired_wilcoxon(improvement)
        raw_p[metric] = p_value
        primary[metric] = {
            "selected_v2_mean": float(selected.mean()),
            "no_physics_mean": float(baseline.mean()),
            "mean_v2_improvement": float(improvement.mean()),
            "median_v2_improvement": float(np.median(improvement)),
            "relative_improvement_pct": float(100.0 * improvement.mean() / baseline.mean()),
            "v2_subject_wins": int(np.sum(improvement > 0)),
            "no_physics_subject_wins": int(np.sum(improvement < 0)),
            "ties": int(np.sum(improvement == 0)),
            "wilcoxon_statistic": statistic,
            "wilcoxon_raw_p_value": p_value,
            "subject_bootstrap_95pct_ci": bootstrap_ci(improvement),
        }
    adjusted = holm_adjust(raw_p)
    for metric in primary:
        primary[metric]["holm_adjusted_p_value"] = adjusted[metric]
    weight_counts = dict(sorted(Counter(str(row["selected_physics_weight"]) for row in selections).items()))
    summary = {
        "experiment": config["experiment_name"],
        "comparison": "validation-selected A10-A13 activity-specific V2 versus matched from-scratch lambda=0",
        "difference_definition": "matched_lambda_0_error - selected_v2_error; positive favors selected V2",
        "primary_analysis_unit": f"15 held-out subjects after averaging {expected_seeds} matched seed(s)",
        "counts": {
            "independent_subjects": len(subject_rows),
            "optimization_seeds": expected_seeds,
            "selected_fold_models": len(selections),
            "paired_subject_seed_evaluations": len(paired),
        },
        "primary_metrics": primary,
        "weight_selection": {
            "counts": weight_counts,
            "used_validation_only": True,
            "included_matched_from_scratch_lambda_zero": True,
        },
        "descriptive_activity_results": activity_rows,
        "inference_note": "Wilcoxon tests use held-out subjects as the independent unit; Holm correction covers three primary endpoints.",
    }
    destination.mkdir(parents=True, exist_ok=True)
    write_csv(destination / "paired_subject_seed_metrics.csv", paired)
    write_csv(destination / "paired_subject_metrics.csv", subject_rows)
    write_csv(destination / "paired_trial_seed_metrics.csv", paired_trials)
    write_csv(destination / "activity_comparison.csv", activity_rows)
    write_csv(destination / "weight_selections.csv", selections)
    dump_json(destination / "comparison_summary.json", summary)
    (destination / "FINDINGS.md").write_text(findings_markdown(summary), encoding="utf-8")
    plot_boxplots(paired, destination / "selected_v2_vs_matched_lambda_0_subject_boxplots.png", expected_seeds)
    plot_activity_boxplots(paired_trials, destination / "selected_v2_vs_matched_lambda_0_activity_boxplots.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
