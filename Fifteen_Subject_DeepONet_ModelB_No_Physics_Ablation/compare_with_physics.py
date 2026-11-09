#!/usr/bin/env python3
"""Create a paired physics-versus-no-physics comparison from two result trees."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import wilcoxon


PRIMARY_METRICS = {
    "normalized_mse": "Normalized forecast MSE",
    "theta_rmse_deg": r"Angle RMSE ($^\circ$)",
    "x_rmse_cm": "CoM displacement RMSE (cm)",
}
COLORS = {"physics": "#3274A1", "no_physics": "#E1812C"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def collect_trials(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted((root / "results" / "full").glob("fold_*/test_metrics_by_trial.csv")):
        fold = int(path.parent.name.split("_")[-1])
        for row in read_csv(path):
            row = dict(row)
            row["fold"] = fold
            rows.append(row)
    return rows


def collect_subjects(root: Path) -> list[dict[str, str]]:
    return read_csv(root / "results" / "full" / "cross_subject_metrics.csv")


def verify_design(physics_root: Path, no_physics_root: Path) -> dict:
    physics = json.loads((physics_root / "experiment.json").read_text(encoding="utf-8"))
    no_physics = json.loads((no_physics_root / "experiment.json").read_text(encoding="utf-8"))
    checks = {
        "seed_equal": physics["seed"] == no_physics["seed"],
        "split_seed_equal": physics["split_seed"] == no_physics["split_seed"],
        "subjects_equal": physics["subjects"] == no_physics["subjects"],
        "folds_equal": physics["folds"] == no_physics["folds"],
        "model_equal": physics["model"] == no_physics["model"],
        "data_equal": physics["data"] == no_physics["data"],
        "real_data_equal": physics["real_data"] == no_physics["real_data"],
    }
    training_p = dict(physics["training"])
    training_n = dict(no_physics["training"])
    removed = {
        "physics_use_physics": training_p.pop("use_physics"),
        "no_physics_use_physics": training_n.pop("use_physics"),
        "physics_weight": training_p.pop("physics_weight"),
        "no_physics_weight": training_n.pop("physics_weight"),
    }
    checks["remaining_training_config_equal"] = training_p == training_n
    if not all(checks.values()):
        raise ValueError(f"Experiments are not a matched ablation: {checks}")
    if removed != {
        "physics_use_physics": True,
        "no_physics_use_physics": False,
        "physics_weight": 0.01,
        "no_physics_weight": 0.0,
    }:
        raise ValueError(f"Unexpected ablation settings: {removed}")
    return {"checks": checks, "ablation_settings": removed}


def verify_targets(physics_root: Path, no_physics_root: Path) -> dict:
    def prediction_map(root: Path) -> dict[str, Path]:
        return {
            path.stem: path
            for path in (root / "results" / "full").glob("fold_*/test_predictions/*.npz")
        }

    p_map = prediction_map(physics_root)
    n_map = prediction_map(no_physics_root)
    if set(p_map) != set(n_map):
        raise ValueError("The evaluated trial sets differ between experiments")
    max_abs = {"time_s": 0.0, "target_theta_rad": 0.0, "target_x_m": 0.0}
    for trial in sorted(p_map):
        with np.load(p_map[trial]) as p_data, np.load(n_map[trial]) as n_data:
            for key in max_abs:
                if p_data[key].shape != n_data[key].shape:
                    raise ValueError(f"Shape mismatch for {trial} {key}")
                max_abs[key] = max(
                    max_abs[key], float(np.max(np.abs(p_data[key] - n_data[key]), initial=0.0))
                )
    return {
        "matched_trial_count": len(p_map),
        "targets_identical": all(value == 0.0 for value in max_abs.values()),
        "maximum_absolute_target_difference": max_abs,
    }


def bootstrap_mean_ci(differences: np.ndarray, rng: np.random.Generator) -> list[float]:
    indices = rng.integers(0, len(differences), size=(100_000, len(differences)))
    means = differences[indices].mean(axis=1)
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def paired_rows(
    physics_rows: list[dict[str, str]],
    no_physics_rows: list[dict[str, str]],
    key: str,
) -> list[dict]:
    p_map = {row[key]: row for row in physics_rows}
    n_map = {row[key]: row for row in no_physics_rows}
    if set(p_map) != set(n_map):
        raise ValueError(f"Mismatched keys for {key}")
    output = []
    for item in sorted(p_map):
        p_row, n_row = p_map[item], n_map[item]
        row = {key: item}
        for common in ("fold", "subject", "test_subject", "forecast_samples"):
            if common in p_row or common in n_row:
                p_value = p_row.get(common, "")
                n_value = n_row.get(common, "")
                if str(p_value) != str(n_value):
                    raise ValueError(f"Mismatched {common} for {item}")
                row[common] = p_value
        for metric in PRIMARY_METRICS:
            p_value = float(p_row[metric])
            n_value = float(n_row[metric])
            row[f"physics_{metric}"] = p_value
            row[f"no_physics_{metric}"] = n_value
            row[f"physics_improvement_{metric}"] = n_value - p_value
            row[f"physics_relative_improvement_pct_{metric}"] = (
                100.0 * (n_value - p_value) / n_value if n_value != 0.0 else np.nan
            )
        output.append(row)
    return output


def summarize(subject_rows: list[dict], trial_rows: list[dict]) -> dict:
    rng = np.random.default_rng(20261109)
    summary = {}
    for metric in PRIMARY_METRICS:
        p = np.array([row[f"physics_{metric}"] for row in subject_rows], dtype=float)
        n = np.array([row[f"no_physics_{metric}"] for row in subject_rows], dtype=float)
        diff = n - p
        statistic, p_value = wilcoxon(diff, zero_method="wilcox", alternative="two-sided")
        trial_diff = np.array(
            [row[f"physics_improvement_{metric}"] for row in trial_rows], dtype=float
        )
        summary[metric] = {
            "physics_subject_mean": float(p.mean()),
            "physics_subject_median": float(np.median(p)),
            "no_physics_subject_mean": float(n.mean()),
            "no_physics_subject_median": float(np.median(n)),
            "mean_physics_improvement": float(diff.mean()),
            "mean_physics_improvement_95pct_subject_bootstrap_ci": bootstrap_mean_ci(diff, rng),
            "relative_change_of_subject_mean_pct": float(100.0 * diff.mean() / n.mean()),
            "subject_wins_physics": int(np.sum(diff > 0)),
            "subject_wins_no_physics": int(np.sum(diff < 0)),
            "subject_ties": int(np.sum(diff == 0)),
            "wilcoxon_signed_rank_statistic_subject_level": float(statistic),
            "wilcoxon_signed_rank_two_sided_p_value_subject_level": float(p_value),
            "trial_wins_physics_descriptive_only": int(np.sum(trial_diff > 0)),
            "trial_wins_no_physics_descriptive_only": int(np.sum(trial_diff < 0)),
            "trial_ties_descriptive_only": int(np.sum(trial_diff == 0)),
        }
    return summary


def grouped_trial_boxplots(trial_rows: list[dict], output: Path) -> None:
    subjects = sorted({row["subject"] for row in trial_rows}, key=lambda value: int(value[1:]))
    fig, axes = plt.subplots(3, 1, figsize=(17, 13), constrained_layout=True)
    rng = np.random.default_rng(42)
    for ax, (metric, label) in zip(axes, PRIMARY_METRICS.items()):
        positions = np.arange(len(subjects), dtype=float)
        for model, offset, color in (
            ("physics", -0.19, COLORS["physics"]),
            ("no_physics", 0.19, COLORS["no_physics"]),
        ):
            values = [
                [row[f"{model}_{metric}"] for row in trial_rows if row["subject"] == subject]
                for subject in subjects
            ]
            bp = ax.boxplot(
                values,
                positions=positions + offset,
                widths=0.32,
                patch_artist=True,
                showfliers=False,
                medianprops={"color": "white", "linewidth": 1.5},
                whiskerprops={"color": color},
                capprops={"color": color},
            )
            for box in bp["boxes"]:
                box.set(facecolor=color, edgecolor=color, alpha=0.70)
            for index, series in enumerate(values):
                jitter = rng.uniform(-0.045, 0.045, size=len(series))
                ax.scatter(
                    positions[index] + offset + jitter,
                    series,
                    color=color,
                    edgecolors="white",
                    linewidths=0.35,
                    s=22,
                    alpha=0.95,
                    zorder=3,
                )
        ax.set_ylabel(label)
        ax.set_xticks(positions, subjects)
        ax.grid(axis="y", alpha=0.22)
    handles = [
        plt.Line2D([0], [0], marker="s", linestyle="", color=color, markersize=10, label=label)
        for color, label in ((COLORS["physics"], "Model B (physics)"), (COLORS["no_physics"], "B-no-physics"))
    ]
    axes[0].legend(handles=handles, loc="upper left", ncol=2, frameon=False)
    fig.suptitle("Held-out trial errors by subject: physics vs no-physics", fontsize=16, y=1.01)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def paired_subject_plot(subject_rows: list[dict], output: Path) -> None:
    subjects = [row["test_subject"] for row in subject_rows]
    x = np.arange(len(subjects))
    fig, axes = plt.subplots(3, 1, figsize=(17, 12), constrained_layout=True)
    for ax, (metric, label) in zip(axes, PRIMARY_METRICS.items()):
        p = np.array([row[f"physics_{metric}"] for row in subject_rows])
        n = np.array([row[f"no_physics_{metric}"] for row in subject_rows])
        for index in range(len(subjects)):
            ax.plot([x[index] - 0.13, x[index] + 0.13], [p[index], n[index]], color="#9A9A9A", lw=1.2)
        ax.scatter(x - 0.13, p, color=COLORS["physics"], s=42, label="Model B (physics)", zorder=3)
        ax.scatter(x + 0.13, n, color=COLORS["no_physics"], s=42, label="B-no-physics", zorder=3)
        ax.set_ylabel(label)
        ax.set_xticks(x, subjects)
        ax.grid(axis="y", alpha=0.22)
    axes[0].legend(loc="upper left", frameon=False, ncol=2)
    fig.suptitle("Paired mean error for each held-out subject", fontsize=16, y=1.015)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--physics-results", type=Path, required=True)
    parser.add_argument("--no-physics-results", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=Path("comparison"))
    args = parser.parse_args()
    physics_root = args.physics_results.resolve()
    no_physics_root = args.no_physics_results.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    design = verify_design(physics_root, no_physics_root)
    targets = verify_targets(physics_root, no_physics_root)
    subject_rows = paired_rows(collect_subjects(physics_root), collect_subjects(no_physics_root), "test_subject")
    trial_rows = paired_rows(collect_trials(physics_root), collect_trials(no_physics_root), "trial")
    summary = summarize(subject_rows, trial_rows)

    subject_fields = list(subject_rows[0])
    trial_fields = list(trial_rows[0])
    write_csv(output / "paired_subject_metrics.csv", subject_rows, subject_fields)
    write_csv(output / "paired_trial_metrics.csv", trial_rows, trial_fields)

    training_rows = []
    for fold in range(1, 6):
        p = json.loads((physics_root / f"results/full/fold_{fold:02d}/training_selection.json").read_text())
        n = json.loads((no_physics_root / f"results/full/fold_{fold:02d}/training_selection.json").read_text())
        training_rows.append({
            "fold": fold,
            "validation_subject": json.loads((physics_root / "experiment.json").read_text())["folds"][fold - 1]["validation"],
            "physics_best_epoch": p["best_epoch"],
            "no_physics_best_epoch": n["best_epoch"],
            "physics_best_validation_normalized_mse": p["best_validation_value"],
            "no_physics_best_validation_normalized_mse": n["best_validation_value"],
        })
    write_csv(output / "training_selection_comparison.csv", training_rows, list(training_rows[0]))

    report = {
        "comparison": "Model B direct unified physics versus matched B-no-physics ablation",
        "primary_analysis_unit": "held-out test subject",
        "subject_count": len(subject_rows),
        "matched_trial_count": len(trial_rows),
        "difference_definition": "no_physics_error - physics_error; positive values favor physics",
        "design_verification": design,
        "target_verification": targets,
        "metrics": summary,
        "inference_note": "Wilcoxon tests and bootstrap CIs use 15 paired subject means. Trial win counts are descriptive because trials within a subject are not independent.",
        "limitations": [
            "This is one optimization seed per condition.",
            "With only 15 paired subjects, uncertainty is wide and subject-specific effects are influential.",
            "The four controller outputs are not supervised or identifiable as measured human gains; compare forecast accuracy, not gain magnitudes.",
        ],
    }
    (output / "comparison_summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    grouped_trial_boxplots(trial_rows, output / "physics_vs_no_physics_trial_boxplots.png")
    paired_subject_plot(subject_rows, output / "physics_vs_no_physics_paired_subject_means.png")


if __name__ == "__main__":
    main()
