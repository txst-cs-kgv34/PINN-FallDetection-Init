#!/usr/bin/env python3
"""Paired five-seed comparison for the A11 physics diagnostic."""

from __future__ import annotations

import argparse
import csv
import json
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
ALL_TRAJECTORY_METRICS = (
    "normalized_mse", "theta_rmse_deg", "theta_mae_deg", "x_rmse_cm",
    "x_mae_cm", "theta_w1_deg", "x_w1_cm",
)
DIAGNOSTICS = ("angular_residual_rmse", "horizontal_residual_rmse")


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
    output = {tuple(row[key] for key in keys): row for row in rows}
    if len(output) != len(rows):
        raise ValueError(f"duplicate keys in table: {keys}")
    return output


def paired_table(
    physics_rows: list[dict[str, str]],
    baseline_rows: list[dict[str, str]],
    keys: tuple[str, ...],
    metrics: tuple[str, ...],
) -> list[dict]:
    physics = keyed(physics_rows, keys)
    baseline = keyed(baseline_rows, keys)
    if set(physics) != set(baseline):
        raise ValueError(
            f"paired keys differ; physics-only={sorted(set(physics)-set(baseline))[:5]}, "
            f"no-physics-only={sorted(set(baseline)-set(physics))[:5]}"
        )
    rows = []
    for pair_key in sorted(physics):
        row = {name: value for name, value in zip(keys, pair_key)}
        for metric in metrics:
            physics_value = float(physics[pair_key][metric])
            baseline_value = float(baseline[pair_key][metric])
            improvement = baseline_value - physics_value
            row[f"physics_{metric}"] = physics_value
            row[f"no_physics_{metric}"] = baseline_value
            row[f"physics_improvement_{metric}"] = improvement
            row[f"physics_relative_improvement_pct_{metric}"] = (
                100.0 * improvement / baseline_value if baseline_value else None
            )
        rows.append(row)
    return rows


def average_subjects(subject_seed_rows: list[dict]) -> list[dict]:
    subjects = sorted({row["test_subject"] for row in subject_seed_rows}, key=lambda value: int(value[1:]))
    rows = []
    for subject in subjects:
        selected = [row for row in subject_seed_rows if row["test_subject"] == subject]
        if len(selected) != 5:
            raise ValueError(f"{subject}: expected five paired seeds, found {len(selected)}")
        row = {"test_subject": subject, "seed_count": 5}
        for metric in ALL_TRAJECTORY_METRICS + DIAGNOSTICS:
            for prefix in ("physics_", "no_physics_", "physics_improvement_"):
                key = prefix + metric
                row[key] = float(np.mean([float(item[key]) for item in selected]))
        rows.append(row)
    return rows


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=p_values.get)
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for rank, metric in enumerate(ordered):
        value = min(1.0, (count - rank) * p_values[metric])
        running = max(running, value)
        adjusted[metric] = running
    return adjusted


def bootstrap_ci(values: np.ndarray, seed: int = 20261121, repeats: int = 20000) -> list[float]:
    generator = np.random.default_rng(seed)
    means = np.empty(repeats, dtype=np.float64)
    for index in range(repeats):
        means[index] = generator.choice(values, size=len(values), replace=True).mean()
    return [float(np.quantile(means, .025)), float(np.quantile(means, .975))]


def verify_targets(config: dict, trial_seed_rows: list[dict]) -> dict:
    maximum = {"time_s": 0.0, "target_theta_rad": 0.0, "target_x_m": 0.0}
    for row in trial_seed_rows:
        seed_index = int(row["seed_index"])
        _, seed_label = seed_spec(config, seed_index)
        fold = int(row["fold"])
        trial = row["trial"]
        relative = Path("full") / seed_label / f"fold_{fold:02d}" / "test_predictions" / f"{trial}.npz"
        physics_path = ROOT / "results" / "physics" / relative
        baseline_path = ROOT / "results" / "no_physics" / relative
        with np.load(physics_path, allow_pickle=False) as physics, np.load(baseline_path, allow_pickle=False) as baseline:
            for key in maximum:
                if physics[key].shape != baseline[key].shape:
                    raise ValueError(f"{trial} seed {seed_index}: target shape differs for {key}")
                difference = float(np.max(np.abs(physics[key] - baseline[key]))) if physics[key].size else 0.0
                maximum[key] = max(maximum[key], difference)
    if any(value != 0.0 for value in maximum.values()):
        raise ValueError(f"physics/no-physics targets are not exactly identical: {maximum}")
    return {
        "matched_prediction_evaluations": len(trial_seed_rows),
        "targets_exactly_identical": True,
        "maximum_absolute_difference": maximum,
    }


def plot_subject_boxplots(subject_seed_rows: list[dict], destination: Path) -> None:
    subjects = sorted({row["test_subject"] for row in subject_seed_rows}, key=lambda value: int(value[1:]))
    centers = np.arange(len(subjects), dtype=float) * 2.4 + 1.0
    fig, axes = plt.subplots(3, 1, figsize=(19, 13), sharex=True)
    for axis, (metric, label) in zip(axes, PRIMARY):
        physics = [[float(row[f"physics_{metric}"]) for row in subject_seed_rows if row["test_subject"] == subject] for subject in subjects]
        baseline = [[float(row[f"no_physics_{metric}"]) for row in subject_seed_rows if row["test_subject"] == subject] for subject in subjects]
        first = axis.boxplot(physics, positions=centers - .38, widths=.62, patch_artist=True, manage_ticks=False)
        second = axis.boxplot(baseline, positions=centers + .38, widths=.62, patch_artist=True, manage_ticks=False)
        for patch in first["boxes"]:
            patch.set_facecolor("#4472C4")
            patch.set_alpha(.78)
        for patch in second["boxes"]:
            patch.set_facecolor("#ED7D31")
            patch.set_alpha(.78)
        axis.plot([], [], color="#4472C4", linewidth=8, alpha=.78, label="Physics")
        axis.plot([], [], color="#ED7D31", linewidth=8, alpha=.78, label="No physics")
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=.25)
        axis.legend(loc="upper right")
    axes[-1].set_xticks(centers, subjects)
    axes[-1].set_xlabel("Held-out subject; each box contains five matched seeds")
    fig.suptitle("A11 current-data diagnostic: Physics versus No physics")
    fig.tight_layout()
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def plot_seed_means(subject_seed_rows: list[dict], destination: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    seeds = sorted({int(row["seed_index"]) for row in subject_seed_rows})
    for axis, (metric, label) in zip(axes, PRIMARY):
        physics = [np.mean([float(row[f"physics_{metric}"]) for row in subject_seed_rows if int(row["seed_index"]) == seed]) for seed in seeds]
        baseline = [np.mean([float(row[f"no_physics_{metric}"]) for row in subject_seed_rows if int(row["seed_index"]) == seed]) for seed in seeds]
        axis.plot(seeds, physics, marker="o", label="Physics", color="#4472C4")
        axis.plot(seeds, baseline, marker="o", label="No physics", color="#ED7D31")
        axis.set_title(label)
        axis.set_xlabel("Seed index")
        axis.grid(alpha=.25)
        axis.legend()
    fig.tight_layout()
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def findings_markdown(summary: dict) -> str:
    lines = [
        "# A11 current-data physics diagnostic — completed comparison",
        "",
        "Positive improvement means `no physics − physics`, so positive values favor physics.",
        "",
        "| Metric | Physics | No physics | Physics improvement | Relative | Subject wins P/N | Holm p |",
        "|:--|--:|--:|--:|--:|--:|--:|",
    ]
    for metric, label in PRIMARY:
        value = summary["primary_metrics"][metric]
        suffix = "°" if metric == "theta_rmse_deg" else (" cm" if metric == "x_rmse_cm" else "")
        lines.append(
            f"| {label} | {value['physics_mean']:.4f}{suffix} | {value['no_physics_mean']:.4f}{suffix} | "
            f"{value['mean_physics_improvement']:+.4f}{suffix} | {value['relative_improvement_pct']:+.2f}% | "
            f"{value['physics_subject_wins']}/{value['no_physics_subject_wins']} | {value['holm_adjusted_p_value']:.4f} |"
        )
    lines += [
        "",
        "Interpret the held-out trajectory endpoints above as primary. The residual diagnostics only show agreement with the specified CartPole equations.",
        "",
        f"All {summary['counts']['paired_trial_seed_evaluations']} paired prediction targets were verified exactly identical between conditions.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    args = parser.parse_args()
    config = load_config(args.config)
    physics_dir = ROOT / "results" / "physics" / "full"
    baseline_dir = ROOT / "results" / "no_physics" / "full"
    metrics = ALL_TRAJECTORY_METRICS + DIAGNOSTICS
    subject_seed_rows = paired_table(
        read_csv(physics_dir / "multi_seed_subject_metrics.csv"),
        read_csv(baseline_dir / "multi_seed_subject_metrics.csv"),
        ("seed_index", "test_subject"),
        metrics,
    )
    trial_seed_rows = paired_table(
        read_csv(physics_dir / "multi_seed_trial_metrics.csv"),
        read_csv(baseline_dir / "multi_seed_trial_metrics.csv"),
        ("seed_index", "fold", "trial"),
        metrics,
    )
    subject_rows = average_subjects(subject_seed_rows)
    raw_p_values = {}
    primary_summary = {}
    for metric, _ in PRIMARY:
        physics = np.asarray([float(row[f"physics_{metric}"]) for row in subject_rows])
        baseline = np.asarray([float(row[f"no_physics_{metric}"]) for row in subject_rows])
        improvement = baseline - physics
        test = wilcoxon(improvement, alternative="two-sided", zero_method="wilcox")
        raw_p_values[metric] = float(test.pvalue)
        primary_summary[metric] = {
            "physics_mean": float(physics.mean()),
            "no_physics_mean": float(baseline.mean()),
            "mean_physics_improvement": float(improvement.mean()),
            "median_physics_improvement": float(np.median(improvement)),
            "relative_improvement_pct": float(100.0 * improvement.mean() / baseline.mean()),
            "physics_subject_wins": int(np.sum(improvement > 0)),
            "no_physics_subject_wins": int(np.sum(improvement < 0)),
            "subject_ties": int(np.sum(improvement == 0)),
            "wilcoxon_statistic": float(test.statistic),
            "wilcoxon_raw_p_value": float(test.pvalue),
            "subject_bootstrap_95pct_ci": bootstrap_ci(improvement),
            "physics_seed_wins": int(sum(
                np.mean([float(row[f"physics_{metric}"]) for row in subject_seed_rows if int(row["seed_index"]) == seed])
                < np.mean([float(row[f"no_physics_{metric}"]) for row in subject_seed_rows if int(row["seed_index"]) == seed])
                for seed in range(1, 6)
            )),
        }
    adjusted = holm_adjust(raw_p_values)
    for metric in primary_summary:
        primary_summary[metric]["holm_adjusted_p_value"] = adjusted[metric]
    diagnostic_summary = {}
    for metric in DIAGNOSTICS:
        physics = np.asarray([float(row[f"physics_{metric}"]) for row in subject_rows])
        baseline = np.asarray([float(row[f"no_physics_{metric}"]) for row in subject_rows])
        diagnostic_summary[metric] = {
            "physics_mean": float(physics.mean()),
            "no_physics_mean": float(baseline.mean()),
            "relative_change_pct": float(100.0 * (physics.mean() - baseline.mean()) / baseline.mean()),
        }
    target_verification = verify_targets(config, trial_seed_rows)
    summary = {
        "experiment": config["experiment_name"],
        "comparison": "A11 current-data Physics versus paired No physics",
        "difference_definition": "no_physics_error - physics_error; positive favors Physics",
        "primary_analysis_unit": "15 held-out subjects after averaging each over five matched seeds",
        "counts": {
            "independent_subjects": len(subject_rows),
            "optimization_seeds": 5,
            "trained_models_per_condition": 25,
            "paired_subject_seed_evaluations": len(subject_seed_rows),
            "paired_trial_seed_evaluations": len(trial_seed_rows),
            "unique_trials": len({row["trial"] for row in trial_seed_rows}),
        },
        "target_verification": target_verification,
        "primary_metrics": primary_summary,
        "residual_diagnostics": diagnostic_summary,
        "inference_note": "Wilcoxon tests use 15 subject-level five-seed means; Holm correction covers the three primary trajectory endpoints.",
        "residual_note": "No-physics controller outputs are unsupervised latent coordinates, so residual comparisons are descriptive rather than identified physiological parameters.",
    }
    destination = ROOT / "comparison"
    destination.mkdir(exist_ok=True)
    write_csv(destination / "paired_subject_seed_metrics.csv", subject_seed_rows)
    write_csv(destination / "paired_subject_metrics.csv", subject_rows)
    write_csv(destination / "paired_trial_seed_metrics.csv", trial_seed_rows)
    dump_json(destination / "comparison_summary.json", summary)
    (destination / "FINDINGS.md").write_text(findings_markdown(summary), encoding="utf-8")
    plot_subject_boxplots(subject_seed_rows, destination / "physics_vs_no_physics_subject_boxplots.png")
    plot_seed_means(subject_seed_rows, destination / "physics_vs_no_physics_seed_means.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
