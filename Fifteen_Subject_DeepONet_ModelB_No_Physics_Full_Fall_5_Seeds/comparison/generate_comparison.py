#!/usr/bin/env python3
"""Generate matched full-fall Physics versus B-no-physics comparisons."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from scipy.stats import ttest_rel, wilcoxon


HERE = Path(__file__).resolve().parent
INPUT = HERE / "input"
OUTPUT = HERE / "outputs"
OUTPUT.mkdir(parents=True, exist_ok=True)

PHYSICS_COLOR = "#3B78A4"
NO_PHYSICS_COLOR = "#E1812C"
BETTER_COLOR = "#3A8D5D"
WORSE_COLOR = "#C75146"
PRIMARY = (
    ("normalized_rmse", "Normalized forecast RMSE"),
    ("theta_rmse_deg", "Theta RMSE (°)"),
    ("x_rmse_cm", "CoM x RMSE (cm)"),
)


def subject_sort_key(subject: str) -> int:
    return int("".join(character for character in subject if character.isdigit()))


def add_normalized_rmse(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["normalized_rmse"] = np.sqrt(result["normalized_mse"].clip(lower=0.0))
    return result


def require_exact_keys(left: pd.DataFrame, right: pd.DataFrame, keys: list[str]) -> None:
    left_keys = set(map(tuple, left[keys].itertuples(index=False, name=None)))
    right_keys = set(map(tuple, right[keys].itertuples(index=False, name=None)))
    if left_keys != right_keys:
        raise ValueError(
            f"Comparison keys do not match: physics-only={len(left_keys-right_keys)}, "
            f"no-physics-only={len(right_keys-left_keys)}"
        )


def paired_frame(
    physics: pd.DataFrame,
    no_physics: pd.DataFrame,
    keys: list[str],
) -> pd.DataFrame:
    require_exact_keys(physics, no_physics, keys)
    merged = physics.merge(
        no_physics,
        on=keys,
        suffixes=("_physics", "_no_physics"),
        validate="one_to_one",
    )
    for metric, _ in PRIMARY:
        merged[f"{metric}_difference_no_minus_physics"] = (
            merged[f"{metric}_no_physics"] - merged[f"{metric}_physics"]
        )
    return merged


def holm_adjust(p_values: list[float]) -> list[float]:
    order = np.argsort(p_values)
    adjusted = np.zeros(len(p_values), dtype=float)
    running = 0.0
    count = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, (count - rank) * float(p_values[index]))
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def subject_means(paired_subject_seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subject, selected in paired_subject_seed.groupby("test_subject"):
        row: dict[str, float | int | str] = {
            "test_subject": subject,
            "seed_count": int(len(selected)),
        }
        for metric in ("normalized_mse",) + tuple(item[0] for item in PRIMARY):
            physics = float(selected[f"{metric}_physics"].mean())
            no_physics = float(selected[f"{metric}_no_physics"].mean())
            difference = no_physics - physics
            row[f"{metric}_physics_mean"] = physics
            row[f"{metric}_no_physics_mean"] = no_physics
            row[f"{metric}_difference_no_minus_physics"] = difference
            row[f"{metric}_physics_reduction_percent"] = (
                100.0 * difference / no_physics if no_physics != 0.0 else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        "test_subject", key=lambda values: values.map(subject_sort_key)
    )


def seed_means(paired_subject_seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for seed_index, selected in paired_subject_seed.groupby("seed_index"):
        row: dict[str, float | int] = {"seed_index": int(seed_index)}
        for metric in ("normalized_mse",) + tuple(item[0] for item in PRIMARY):
            physics = float(selected[f"{metric}_physics"].mean())
            no_physics = float(selected[f"{metric}_no_physics"].mean())
            row[f"{metric}_physics_mean"] = physics
            row[f"{metric}_no_physics_mean"] = no_physics
            row[f"{metric}_difference_no_minus_physics"] = no_physics - physics
        rows.append(row)
    return pd.DataFrame(rows).sort_values("seed_index")


def statistical_summary(subject_frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(20261109)
    rows = []
    for metric, label in PRIMARY:
        physics = subject_frame[f"{metric}_physics_mean"].to_numpy(float)
        no_physics = subject_frame[f"{metric}_no_physics_mean"].to_numpy(float)
        difference = no_physics - physics
        bootstrap = difference[
            rng.integers(0, len(difference), size=(20000, len(difference)))
        ].mean(axis=1)
        wilcoxon_p = float(wilcoxon(no_physics, physics, alternative="two-sided").pvalue)
        row = {
            "metric": metric,
            "label": label,
            "independent_subject_count": int(len(difference)),
            "physics_mean": float(physics.mean()),
            "no_physics_mean": float(no_physics.mean()),
            "mean_difference_no_minus_physics": float(difference.mean()),
            "median_difference_no_minus_physics": float(np.median(difference)),
            "physics_reduction_percent": float(100.0 * difference.mean() / no_physics.mean()),
            "subjects_physics_lower_error": int(np.sum(difference > 0.0)),
            "subjects_no_physics_lower_error": int(np.sum(difference < 0.0)),
            "paired_cohen_dz": float(difference.mean() / difference.std(ddof=1)),
            "paired_t_test_p_unadjusted": float(ttest_rel(no_physics, physics).pvalue),
            "wilcoxon_p_unadjusted": wilcoxon_p,
            "bootstrap_mean_difference_95pct_low": float(np.quantile(bootstrap, 0.025)),
            "bootstrap_mean_difference_95pct_high": float(np.quantile(bootstrap, 0.975)),
        }
        rows.append(row)
    adjusted = holm_adjust([row["wilcoxon_p_unadjusted"] for row in rows])
    for row, value in zip(rows, adjusted):
        row["wilcoxon_p_holm_three_primary_metrics"] = value
    frame = pd.DataFrame(rows)
    payload = {
        "primary_unit": "15 independent held-out subjects after averaging each subject over five optimization seeds",
        "difference_direction": "no_physics_minus_physics; positive means Physics has lower error",
        "multiple_comparison_method": "Holm adjustment across the three primary metrics",
        "bootstrap": "20,000 subject-level resamples with seed 20261109",
        "metrics": {row["metric"]: row for row in rows},
    }
    return frame, payload


def style_boxplot(boxes, color: str) -> None:
    for box in boxes["boxes"]:
        box.set_facecolor(color)
        box.set_alpha(0.68)
        box.set_edgecolor(color)
    for median in boxes["medians"]:
        median.set_color("white")
        median.set_linewidth(1.5)
    for item in boxes["whiskers"] + boxes["caps"]:
        item.set_color(color)


def plot_subject_seed_boxplots(paired: pd.DataFrame, path: Path) -> None:
    subjects = sorted(paired["test_subject"].unique(), key=subject_sort_key)
    x = np.arange(len(subjects), dtype=float)
    fig, axes = plt.subplots(3, 1, figsize=(17, 13), sharex=True, constrained_layout=True)
    for axis, (metric, label) in zip(axes, PRIMARY):
        physics = [
            paired.loc[paired.test_subject == subject, f"{metric}_physics"].to_numpy()
            for subject in subjects
        ]
        no_physics = [
            paired.loc[paired.test_subject == subject, f"{metric}_no_physics"].to_numpy()
            for subject in subjects
        ]
        p_boxes = axis.boxplot(
            physics,
            positions=x - 0.18,
            widths=0.30,
            patch_artist=True,
            showmeans=True,
            meanprops={"marker": "o", "markerfacecolor": "white", "markeredgecolor": PHYSICS_COLOR, "markersize": 4},
            flierprops={"marker": "o", "markerfacecolor": PHYSICS_COLOR, "markeredgecolor": "white", "markersize": 3},
        )
        n_boxes = axis.boxplot(
            no_physics,
            positions=x + 0.18,
            widths=0.30,
            patch_artist=True,
            showmeans=True,
            meanprops={"marker": "o", "markerfacecolor": "white", "markeredgecolor": NO_PHYSICS_COLOR, "markersize": 4},
            flierprops={"marker": "o", "markerfacecolor": NO_PHYSICS_COLOR, "markeredgecolor": "white", "markersize": 3},
        )
        style_boxplot(p_boxes, PHYSICS_COLOR)
        style_boxplot(n_boxes, NO_PHYSICS_COLOR)
        for index, values in enumerate(physics):
            jitter = np.linspace(-0.055, 0.055, len(values))
            axis.scatter(x[index] - 0.18 + jitter, values, s=19, color=PHYSICS_COLOR, edgecolor="white", linewidth=0.4, zorder=3)
        for index, values in enumerate(no_physics):
            jitter = np.linspace(-0.055, 0.055, len(values))
            axis.scatter(x[index] + 0.18 + jitter, values, s=19, color=NO_PHYSICS_COLOR, edgecolor="white", linewidth=0.4, zorder=3)
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=0.25)
    axes[0].legend(
        handles=[Patch(facecolor=PHYSICS_COLOR, label="Model B (Physics)"), Patch(facecolor=NO_PHYSICS_COLOR, label="B-no-physics")],
        loc="upper left",
        frameon=False,
        ncol=2,
    )
    axes[0].set_title("Matched full-fall held-out errors by subject: Physics vs no physics")
    axes[-1].set_xticks(x, subjects)
    axes[-1].set_xlabel("Held-out subject (five optimization seeds per model box)")
    fig.savefig(path, dpi=190)
    plt.close(fig)


def plot_subject_differences(subject_frame: pd.DataFrame, path: Path) -> None:
    subjects = subject_frame["test_subject"].tolist()
    x = np.arange(len(subjects))
    fig, axes = plt.subplots(3, 1, figsize=(15, 11), sharex=True, constrained_layout=True)
    for axis, (metric, label) in zip(axes, PRIMARY):
        difference = subject_frame[f"{metric}_difference_no_minus_physics"].to_numpy(float)
        colors = np.where(difference >= 0.0, BETTER_COLOR, WORSE_COLOR)
        axis.bar(x, difference, color=colors, alpha=0.82)
        axis.axhline(0.0, color="black", linewidth=0.9)
        axis.set_ylabel(f"Δ {label}\n(no physics − Physics)")
        axis.grid(axis="y", alpha=0.25)
    axes[0].set_title("Paired subject-mean differences (positive means Physics has lower error)")
    axes[-1].set_xticks(x, subjects)
    axes[-1].set_xlabel("Held-out subject (mean over five seeds)")
    fig.savefig(path, dpi=190)
    plt.close(fig)


def plot_seed_means(seed_frame: pd.DataFrame, path: Path) -> None:
    seeds = seed_frame["seed_index"].to_numpy()
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True, constrained_layout=True)
    for axis, (metric, label) in zip(axes, PRIMARY):
        axis.plot(seeds, seed_frame[f"{metric}_physics_mean"], marker="o", color=PHYSICS_COLOR, label="Model B (Physics)")
        axis.plot(seeds, seed_frame[f"{metric}_no_physics_mean"], marker="o", color=NO_PHYSICS_COLOR, label="B-no-physics")
        axis.set_ylabel(label)
        axis.grid(alpha=0.25)
    axes[0].legend(frameon=False, ncol=2)
    axes[0].set_title("Subject-balanced held-out mean for each optimization seed")
    axes[-1].set_xticks(seeds)
    axes[-1].set_xlabel("Optimization seed index")
    fig.savefig(path, dpi=190)
    plt.close(fig)


def plot_trial_scatter(paired_trial: pd.DataFrame, path: Path) -> None:
    trial_mean = paired_trial.groupby(["subject", "trial"], as_index=False).mean(numeric_only=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    for axis, (metric, label) in zip(axes, PRIMARY):
        x = trial_mean[f"{metric}_physics"].to_numpy(float)
        y = trial_mean[f"{metric}_no_physics"].to_numpy(float)
        lower = min(float(x.min()), float(y.min()))
        upper = max(float(x.max()), float(y.max()))
        axis.scatter(x, y, s=27, color="#6B6B6B", alpha=0.70, edgecolor="white", linewidth=0.4)
        axis.plot([lower, upper], [lower, upper], "--", color="black", linewidth=1.0)
        axis.set_xlabel(f"Physics: {label}")
        axis.set_ylabel(f"No physics: {label}")
        axis.grid(alpha=0.22)
    fig.suptitle("Paired trial means across five seeds (points above diagonal favor Physics)")
    fig.savefig(path, dpi=190)
    plt.close(fig)


def main() -> None:
    physics_subject = add_normalized_rmse(pd.read_csv(INPUT / "physics_multi_seed_subject_metrics.csv"))
    no_subject = add_normalized_rmse(pd.read_csv(INPUT / "no_physics_multi_seed_subject_metrics.csv"))
    physics_trial = add_normalized_rmse(pd.read_csv(INPUT / "physics_multi_seed_trial_metrics.csv"))
    no_trial = add_normalized_rmse(pd.read_csv(INPUT / "no_physics_multi_seed_trial_metrics.csv"))

    paired_subject = paired_frame(physics_subject, no_subject, ["seed_index", "test_subject"])
    paired_trial = paired_frame(physics_trial, no_trial, ["seed_index", "subject", "trial"])
    if len(paired_subject) != 75 or len(paired_trial) != 350:
        raise ValueError("Expected exactly 75 subject-seed and 350 trial-seed pairs")

    subjects = subject_means(paired_subject)
    seeds = seed_means(paired_subject)
    statistics, statistics_json = statistical_summary(subjects)

    paired_subject.to_csv(OUTPUT / "paired_subject_seed_metrics.csv", index=False)
    paired_trial.to_csv(OUTPUT / "paired_trial_seed_metrics.csv", index=False)
    subjects.to_csv(OUTPUT / "subject_mean_comparison.csv", index=False)
    seeds.to_csv(OUTPUT / "seed_mean_comparison.csv", index=False)
    statistics.to_csv(OUTPUT / "statistical_summary.csv", index=False)

    trial_mean = paired_trial.groupby(["subject", "trial"], as_index=False).mean(numeric_only=True)
    trial_counts = {}
    for metric, _ in PRIMARY:
        difference = trial_mean[f"{metric}_no_physics"] - trial_mean[f"{metric}_physics"]
        trial_counts[metric] = {
            "unique_trial_count": int(len(difference)),
            "trials_physics_lower_error": int(np.sum(difference > 0.0)),
            "trials_no_physics_lower_error": int(np.sum(difference < 0.0)),
            "mean_difference_no_minus_physics": float(difference.mean()),
            "interpretation": "exploratory because trials within a subject are not independent people",
        }
    payload = {
        "pairing_validation": {
            "subject_seed_pairs": int(len(paired_subject)),
            "trial_seed_pairs": int(len(paired_trial)),
            "unique_subjects": int(paired_subject["test_subject"].nunique()),
            "unique_trials": int(trial_mean.shape[0]),
            "optimization_seeds": int(paired_subject["seed_index"].nunique()),
        },
        "statistics": statistics_json,
        "exploratory_trial_summary": trial_counts,
        "caution": "Physics residuals are excluded from the primary comparison because the no-physics model's four context coordinates are not physically identified gains.",
    }
    (OUTPUT / "comparison_summary.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

    plot_subject_seed_boxplots(paired_subject, OUTPUT / "physics_vs_no_physics_subject_boxplots.png")
    plot_subject_differences(subjects, OUTPUT / "physics_vs_no_physics_subject_differences.png")
    plot_seed_means(seeds, OUTPUT / "physics_vs_no_physics_seed_means.png")
    plot_trial_scatter(paired_trial, OUTPUT / "physics_vs_no_physics_trial_scatter.png")


if __name__ == "__main__":
    main()
