from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
COMPARISON = ROOT / "outputs" / "comparison"

SCENARIOS = [
    "real_fall_real_adl",
    "synthetic_fall_real_adl",
    "real_synthetic_fall_real_adl",
]
LABELS = {
    "real_fall_real_adl": "Real",
    "synthetic_fall_real_adl": "Synthetic",
    "real_synthetic_fall_real_adl": "Combined",
}
COLORS = {
    "real_fall_real_adl": "#1f77b4",
    "synthetic_fall_real_adl": "#ff7f0e",
    "real_synthetic_fall_real_adl": "#2ca02c",
}
PERFORMANCE_METRICS = [
    "test_trial_balanced_accuracy",
    "test_trial_sensitivity",
    "test_trial_specificity",
    "test_trial_f1",
    "test_trial_auroc",
    "test_trial_auprc",
]
METRIC_LABELS = {
    "test_trial_balanced_accuracy": "Balanced\naccuracy",
    "test_trial_sensitivity": "Sensitivity",
    "test_trial_specificity": "Specificity",
    "test_trial_f1": "F1",
    "test_trial_auroc": "AUROC",
    "test_trial_auprc": "AUPRC",
}
FP_METRIC = "false_positive_events_per_adl_minute"


def load_fold_means() -> pd.DataFrame:
    path = COMPARISON / "fold_seed_averaged_metrics.csv"
    frame = pd.read_csv(path)
    expected = set(SCENARIOS)
    if set(frame["scenario"]) != expected:
        raise ValueError(f"Expected scenarios {sorted(expected)}")
    if frame.groupby("scenario")["fold"].nunique().to_dict() != {
        scenario: 5 for scenario in SCENARIOS
    }:
        raise ValueError("Expected five fold means for every scenario")
    return frame


def save_summary_tables(fold_means: pd.DataFrame) -> None:
    records = []
    for scenario in SCENARIOS:
        group = fold_means[fold_means["scenario"] == scenario]
        for metric in PERFORMANCE_METRICS + [FP_METRIC]:
            records.append(
                {
                    "scenario": scenario,
                    "scenario_label": LABELS[scenario],
                    "metric": metric,
                    "fold_count": len(group),
                    "mean_of_fold_means": group[metric].mean(),
                    "fold_standard_deviation": group[metric].std(ddof=1),
                    "minimum_fold_mean": group[metric].min(),
                    "maximum_fold_mean": group[metric].max(),
                }
            )
    pd.DataFrame.from_records(records).to_csv(
        COMPARISON / "fold_level_metric_summary.csv", index=False
    )

    pivot = fold_means.pivot(index="fold", columns="scenario", values=PERFORMANCE_METRICS)
    differences = []
    for fold in sorted(fold_means["fold"].unique()):
        for metric in PERFORMANCE_METRICS:
            real = pivot.loc[fold, (metric, "real_fall_real_adl")]
            for scenario in SCENARIOS[1:]:
                differences.append(
                    {
                        "fold": fold,
                        "metric": metric,
                        "comparison_scenario": scenario,
                        "comparison_label": LABELS[scenario],
                        "comparison_minus_real": pivot.loc[fold, (metric, scenario)] - real,
                    }
                )
    pd.DataFrame.from_records(differences).to_csv(
        COMPARISON / "paired_fold_differences_vs_real.csv", index=False
    )


def plot_performance_overview(fold_means: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(12.5, 6.3))
    x = np.arange(len(PERFORMANCE_METRICS), dtype=float)
    offsets = [-0.18, 0.0, 0.18]
    for offset, scenario in zip(offsets, SCENARIOS):
        group = fold_means[fold_means["scenario"] == scenario]
        means = group[PERFORMANCE_METRICS].mean().to_numpy()
        standard_deviations = group[PERFORMANCE_METRICS].std(ddof=1).to_numpy()
        axis.errorbar(
            x + offset,
            means,
            yerr=standard_deviations,
            fmt="o",
            markersize=8,
            capsize=4,
            linewidth=2,
            color=COLORS[scenario],
            label=LABELS[scenario],
        )
        for x_value, mean in zip(x + offset, means):
            axis.annotate(
                f"{mean:.3f}",
                (x_value, mean),
                xytext=(0, 9),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=COLORS[scenario],
            )
    axis.set_xticks(x, [METRIC_LABELS[metric] for metric in PERFORMANCE_METRICS])
    axis.set_ylim(0.54, 1.035)
    axis.set_ylabel("Test trial metric")
    axis.set_title("Scenario performance: mean ± SD across five fold means")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncol=3, loc="lower left")
    axis.text(
        0.99,
        0.02,
        "Higher is better. Seeds are averaged within each fold.",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        color="#555555",
    )
    figure.tight_layout()
    figure.savefig(COMPARISON / "scenario_performance_overview.png", dpi=220)
    plt.close(figure)


def plot_foldwise_balanced_accuracy(fold_means: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(9.5, 5.8))
    folds = sorted(fold_means["fold"].unique())
    x = np.arange(len(folds))
    for scenario in SCENARIOS:
        values = (
            fold_means[fold_means["scenario"] == scenario]
            .set_index("fold")
            .loc[folds, "test_trial_balanced_accuracy"]
        )
        axis.plot(
            x,
            values,
            marker="o",
            markersize=8,
            linewidth=2.4,
            label=LABELS[scenario],
            color=COLORS[scenario],
        )
    axis.set_xticks(x, [fold.replace("fold_", "Fold ") for fold in folds])
    axis.set_ylim(0.68, 1.02)
    axis.set_ylabel("Mean test trial balanced accuracy")
    axis.set_title("Subject-fold consistency after averaging the five seeds")
    axis.grid(alpha=0.25)
    axis.legend(ncol=3, loc="lower right")
    figure.tight_layout()
    figure.savefig(COMPARISON / "foldwise_balanced_accuracy.png", dpi=220)
    plt.close(figure)


def plot_paired_differences(fold_means: pd.DataFrame) -> None:
    pivot = fold_means.pivot(
        index="fold", columns="scenario", values="test_trial_balanced_accuracy"
    ).sort_index()
    folds = pivot.index.tolist()
    x = np.arange(len(folds))
    width = 0.34
    synthetic_difference = 100 * (
        pivot["synthetic_fall_real_adl"] - pivot["real_fall_real_adl"]
    )
    combined_difference = 100 * (
        pivot["real_synthetic_fall_real_adl"] - pivot["real_fall_real_adl"]
    )
    figure, axis = plt.subplots(figsize=(10.5, 5.8))
    axis.bar(
        x - width / 2,
        synthetic_difference,
        width,
        label="Synthetic − Real",
        color=COLORS["synthetic_fall_real_adl"],
    )
    axis.bar(
        x + width / 2,
        combined_difference,
        width,
        label="Combined − Real",
        color=COLORS["real_synthetic_fall_real_adl"],
    )
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(x, [fold.replace("fold_0", "F") for fold in folds])
    axis.set_ylabel("Balanced-accuracy difference (percentage points)")
    axis.set_title("Paired fold differences relative to real-fall training")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncol=2)
    axis.text(
        0.99,
        0.02,
        "Negative values favor Real.",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        color="#555555",
    )
    figure.tight_layout()
    figure.savefig(COMPARISON / "paired_balanced_accuracy_differences.png", dpi=220)
    plt.close(figure)


def plot_false_positive_rates(fold_means: pd.DataFrame) -> None:
    folds = sorted(fold_means["fold"].unique())
    x = np.arange(len(folds))
    width = 0.24
    figure, axis = plt.subplots(figsize=(9.5, 5.8))
    for index, scenario in enumerate(SCENARIOS):
        values = (
            fold_means[fold_means["scenario"] == scenario]
            .set_index("fold")
            .loc[folds, FP_METRIC]
        )
        axis.bar(
            x + (index - 1) * width,
            values,
            width,
            label=LABELS[scenario],
            color=COLORS[scenario],
        )
    axis.set_xticks(x, [fold.replace("fold_", "Fold ") for fold in folds])
    axis.set_ylabel("False-positive detection events per ADL minute")
    axis.set_title("False-positive burden by held-out subject fold")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncol=3)
    axis.text(
        0.99,
        0.02,
        "Lower is better. Seeds are averaged within each fold.",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        color="#555555",
    )
    figure.tight_layout()
    figure.savefig(COMPARISON / "false_positive_events_by_fold.png", dpi=220)
    plt.close(figure)


def main() -> None:
    fold_means = load_fold_means()
    save_summary_tables(fold_means)
    plot_performance_overview(fold_means)
    plot_foldwise_balanced_accuracy(fold_means)
    plot_paired_differences(fold_means)
    plot_false_positive_rates(fold_means)
    print(f"Wrote enhanced comparison figures to {COMPARISON}")


if __name__ == "__main__":
    main()
