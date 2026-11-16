from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from base_detector_imports import load_raw_config


CONDITIONS = [
    "real_25pct_real_adl",
    "real_25pct_balanced_synthetic_real_adl",
    "real_50pct_real_adl",
    "real_50pct_balanced_synthetic_real_adl",
]
FULL_REAL = "real_fall_real_adl"
FULL_AUGMENTED = "source_balanced_1to1"
ALL_SCENARIOS = [FULL_REAL, *CONDITIONS, FULL_AUGMENTED]
LABELS = {
    FULL_REAL: "100% real",
    "real_25pct_real_adl": "25% real",
    "real_25pct_balanced_synthetic_real_adl": "25% real + synthetic",
    "real_50pct_real_adl": "50% real",
    "real_50pct_balanced_synthetic_real_adl": "50% real + synthetic",
    FULL_AUGMENTED: "100% real + synthetic",
}
SHORT_LABELS = {
    FULL_REAL: "100% Real",
    "real_25pct_real_adl": "25% Real",
    "real_25pct_balanced_synthetic_real_adl": "25% Aug.",
    "real_50pct_real_adl": "50% Real",
    "real_50pct_balanced_synthetic_real_adl": "50% Aug.",
    FULL_AUGMENTED: "100% Aug.",
}
METRIC_LABELS = {
    "test_trial_balanced_accuracy": "Balanced accuracy",
    "test_trial_sensitivity": "Sensitivity",
    "test_trial_specificity": "Specificity",
    "test_trial_f1": "F1",
    "test_trial_auroc": "AUROC",
    "test_trial_auprc": "AUPRC",
    "false_positive_events_per_adl_minute": "FP events / ADL minute",
}
COLORS = {"real": "#1f77b4", "augmented": "#d95f02"}


def resolve(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else config_path.parent / path).resolve()


def holm_adjust(p_values: list[float]) -> list[float]:
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(p_values) - rank) * float(p_values[index]))
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def load_metrics(
    config_path: Path, config: dict[str, Any], prior_csv_override: Path | None
) -> tuple[pd.DataFrame, Path]:
    output_root = resolve(config_path, config["output_root"])
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for condition in CONDITIONS
        for path in sorted((output_root / condition).glob("fold_*/seed_*/metrics.json"))
    ]
    if not records:
        raise FileNotFoundError(
            f"No low-real-data metrics found under {output_root}. Run training first."
        )
    new = pd.DataFrame.from_records(records)
    new["scenario"] = new.get("scenario", new["condition"])

    prior_path = (
        prior_csv_override.expanduser().resolve()
        if prior_csv_override
        else resolve(config_path, config["prior_comparison_csv"])
    )
    if not prior_path.is_file():
        raise FileNotFoundError(
            f"Missing frozen full-data comparison table: {prior_path}. Keep the prior "
            "source-balanced results in the sibling directory, or pass --prior-csv."
        )
    prior = pd.read_csv(prior_path)
    prior = prior[prior["scenario"].isin([FULL_REAL, FULL_AUGMENTED])].copy()
    combined = pd.concat([prior, new], ignore_index=True, sort=False)
    combined = combined[combined["scenario"].isin(ALL_SCENARIOS)].copy()
    return combined, output_root


def retain_matched(frame: pd.DataFrame) -> pd.DataFrame:
    duplicates = frame.duplicated(["scenario", "fold", "seed"], keep=False)
    if duplicates.any():
        raise ValueError("Duplicate scenario/fold/seed rows were found")
    counts = frame.groupby(["fold", "seed"])["scenario"].nunique()
    complete = counts[counts == len(ALL_SCENARIOS)].index
    if len(complete) == 0:
        raise ValueError("No fold/seed setting is complete across all six conditions")
    matched = frame.set_index(["fold", "seed"]).loc[complete].reset_index()
    matched = matched[matched["scenario"].isin(ALL_SCENARIOS)].copy()
    expected_settings = 25
    if len(complete) != expected_settings:
        raise ValueError(
            f"Only {len(complete)}/{expected_settings} fold/seed settings are complete "
            "across all six conditions. Finish or restore the missing runs first."
        )
    for fraction, first, second in (
        (0.25, "real_25pct_real_adl", "real_25pct_balanced_synthetic_real_adl"),
        (0.50, "real_50pct_real_adl", "real_50pct_balanced_synthetic_real_adl"),
    ):
        pair = matched[matched["scenario"].isin([first, second])]
        if "selected_real_fall_digest" not in pair.columns:
            raise ValueError("New metrics are missing selected_real_fall_digest")
        for fold, group in pair.groupby("fold"):
            digests = group["selected_real_fall_digest"].dropna().unique()
            counts_selected = group["selected_real_fall_count"].dropna().unique()
            if len(digests) != 1 or len(counts_selected) != 1:
                raise ValueError(
                    f"{fold} at {fraction:.0%} does not use one fixed paired real-fall subset"
                )
    return matched


def build_summary(
    runs: pd.DataFrame, fold_means: pd.DataFrame, metrics: list[str]
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for scenario in ALL_SCENARIOS:
        run_group = runs[runs["scenario"] == scenario]
        fold_group = fold_means[fold_means["scenario"] == scenario]
        for metric in metrics:
            records.append(
                {
                    "scenario": scenario,
                    "scenario_name": LABELS[scenario],
                    "metric": metric,
                    "run_count": len(run_group),
                    "run_mean": run_group[metric].mean(),
                    "run_standard_deviation": run_group[metric].std(ddof=1),
                    "fold_mean": fold_group[metric].mean(),
                    "fold_standard_deviation": fold_group[metric].std(ddof=1),
                }
            )
    return pd.DataFrame.from_records(records)


def paired_tests(fold_means: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    pairs = [
        (0.25, "real_25pct_real_adl", "real_25pct_balanced_synthetic_real_adl"),
        (0.50, "real_50pct_real_adl", "real_50pct_balanced_synthetic_real_adl"),
    ]
    records: list[dict[str, object]] = []
    for metric in metrics:
        metric_records: list[dict[str, object]] = []
        for fraction, reference, candidate in pairs:
            pivot = (
                fold_means[fold_means["scenario"].isin([reference, candidate])]
                .pivot(index="fold", columns="scenario", values=metric)
                .dropna()
            )
            difference = pivot[candidate] - pivot[reference]
            if len(pivot) < 2 or np.allclose(difference, 0.0):
                statistic, p_value = 0.0, 1.0
            else:
                result = wilcoxon(pivot[reference], pivot[candidate], alternative="two-sided")
                statistic, p_value = float(result.statistic), float(result.pvalue)
            metric_records.append(
                {
                    "metric": metric,
                    "real_fraction": fraction,
                    "reference_scenario": reference,
                    "candidate_scenario": candidate,
                    "fold_count": len(pivot),
                    "reference_mean": pivot[reference].mean(),
                    "candidate_mean": pivot[candidate].mean(),
                    "mean_difference_candidate_minus_reference": difference.mean(),
                    "wilcoxon_statistic": statistic,
                    "wilcoxon_p_unadjusted": p_value,
                }
            )
        adjusted = holm_adjust(
            [float(record["wilcoxon_p_unadjusted"]) for record in metric_records]
        )
        for record, value in zip(metric_records, adjusted):
            record["wilcoxon_p_holm"] = value
            record["holm_significant_at_0_05"] = bool(value < 0.05)
            records.append(record)
    return pd.DataFrame.from_records(records)


def recovery_table(fold_means: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    pivoted = {
        metric: fold_means.pivot(index="fold", columns="scenario", values=metric)
        for metric in metrics
    }
    records: list[dict[str, object]] = []
    for metric, pivot in pivoted.items():
        higher_is_better = metric != "false_positive_events_per_adl_minute"
        for fraction, reduced, augmented in (
            (0.25, "real_25pct_real_adl", "real_25pct_balanced_synthetic_real_adl"),
            (0.50, "real_50pct_real_adl", "real_50pct_balanced_synthetic_real_adl"),
        ):
            for fold, row in pivot.iterrows():
                full = float(row[FULL_REAL])
                baseline = float(row[reduced])
                candidate = float(row[augmented])
                if higher_is_better:
                    lost = full - baseline
                    recovered = candidate - baseline
                else:
                    lost = baseline - full
                    recovered = baseline - candidate
                recovery_percent = 100.0 * recovered / lost if lost > 1e-12 else np.nan
                records.append(
                    {
                        "metric": metric,
                        "real_fraction": fraction,
                        "fold": fold,
                        "reduced_real_value": baseline,
                        "augmented_value": candidate,
                        "full_real_reference": full,
                        "augmentation_gain_in_better_direction": recovered,
                        "performance_lost_vs_full_real": lost,
                        "percent_of_lost_performance_recovered": recovery_percent,
                    }
                )
    return pd.DataFrame.from_records(records)


def plot_recovery_curves(fold_means: pd.DataFrame, path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(12.5, 5.5), sharex=True)
    for axis, metric in zip(axes, ["test_trial_balanced_accuracy", "test_trial_f1"]):
        for family, scenarios, color, marker in (
            ("Real only", ["real_25pct_real_adl", "real_50pct_real_adl", FULL_REAL], COLORS["real"], "o"),
            ("Synthetic augmented", ["real_25pct_balanced_synthetic_real_adl", "real_50pct_balanced_synthetic_real_adl", FULL_AUGMENTED], COLORS["augmented"], "s"),
        ):
            means, errors = [], []
            for scenario in scenarios:
                values = fold_means.loc[fold_means["scenario"] == scenario, metric]
                means.append(values.mean())
                errors.append(values.std(ddof=1))
            axis.errorbar(
                [25, 50, 100], means, yerr=errors, marker=marker, linewidth=2.2,
                capsize=4, color=color, label=family,
            )
        axis.set_title(METRIC_LABELS[metric])
        axis.set_xlabel("Available real-fall training data (%)")
        axis.set_xticks([25, 50, 100])
        axis.set_ylim(0.45, 1.02)
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Mean ± SD across five fold means")
    axes[0].legend(loc="lower right")
    figure.suptitle("Does synthetic augmentation recover low-real-data performance?")
    figure.tight_layout()
    figure.savefig(path, dpi=220)
    plt.close(figure)


def plot_overview(fold_means: pd.DataFrame, metrics: list[str], path: Path) -> None:
    performance = [metric for metric in metrics if not metric.startswith("false_")]
    x = np.arange(len(performance))
    offsets = np.linspace(-0.32, 0.32, len(ALL_SCENARIOS))
    palette = ["#4c78a8", "#9ecae9", "#fdae6b", "#3182bd", "#e6550d", "#a63603"]
    figure, axis = plt.subplots(figsize=(14.5, 6.8))
    for offset, scenario, color in zip(offsets, ALL_SCENARIOS, palette):
        group = fold_means[fold_means["scenario"] == scenario]
        axis.errorbar(
            x + offset, group[performance].mean().to_numpy(),
            yerr=group[performance].std(ddof=1).to_numpy(), fmt="o", capsize=3,
            linewidth=1.5, markersize=6, color=color, label=SHORT_LABELS[scenario],
        )
    axis.set_xticks(x, [METRIC_LABELS[value] for value in performance])
    axis.set_ylim(0.45, 1.03)
    axis.set_ylabel("Test-trial metric")
    axis.set_title("Low-real-data and frozen full-data comparison")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncol=3, loc="lower left")
    figure.tight_layout()
    figure.savefig(path, dpi=220)
    plt.close(figure)


def plot_foldwise_gain(fold_means: pd.DataFrame, path: Path) -> None:
    metric = "test_trial_balanced_accuracy"
    pivot = fold_means.pivot(index="fold", columns="scenario", values=metric).sort_index()
    folds = pivot.index.tolist()
    x = np.arange(len(folds))
    width = 0.35
    gain25 = 100 * (pivot["real_25pct_balanced_synthetic_real_adl"] - pivot["real_25pct_real_adl"])
    gain50 = 100 * (pivot["real_50pct_balanced_synthetic_real_adl"] - pivot["real_50pct_real_adl"])
    figure, axis = plt.subplots(figsize=(10.5, 5.8))
    axis.bar(x - width / 2, gain25, width, label="25% real", color="#fdae6b")
    axis.bar(x + width / 2, gain50, width, label="50% real", color="#e6550d")
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(x, [fold.replace("fold_0", "F") for fold in folds])
    axis.set_ylabel("Augmented − real-only balanced accuracy (percentage points)")
    axis.set_title("Paired synthetic-augmentation gain by held-out fold")
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=220)
    plt.close(figure)


def plot_false_positives(fold_means: pd.DataFrame, path: Path) -> None:
    metric = "false_positive_events_per_adl_minute"
    order = ALL_SCENARIOS
    values = [fold_means.loc[fold_means["scenario"] == value, metric] for value in order]
    figure, axis = plt.subplots(figsize=(12.5, 5.8))
    boxes = axis.boxplot(values, tick_labels=[SHORT_LABELS[value] for value in order], patch_artist=True)
    for patch, color in zip(boxes["boxes"], ["#4c78a8", "#9ecae9", "#fdae6b", "#3182bd", "#e6550d", "#a63603"]):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
    axis.set_ylabel("False-positive events per ADL minute")
    axis.set_title("False-positive burden across held-out folds (lower is better)")
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=220)
    plt.close(figure)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare the paired low-real-data study.")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--prior-csv", type=Path)
    args = parser.parse_args(argv)

    config_path, config = load_raw_config(args.config)
    all_runs, output_root = load_metrics(config_path, config, args.prior_csv)
    matched = retain_matched(all_runs)
    comparison_dir = output_root / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    matched.to_csv(comparison_dir / "all_six_condition_run_metrics.csv", index=False)

    metrics = [value for value in config["comparison_metrics"] if value in matched.columns]
    fold_means = matched.groupby(["scenario", "fold"], as_index=False)[metrics].mean()
    fold_means.to_csv(comparison_dir / "six_condition_fold_seed_averaged_metrics.csv", index=False)
    summary = build_summary(matched, fold_means, metrics)
    summary.to_csv(comparison_dir / "six_condition_summary.csv", index=False)
    tests = paired_tests(fold_means, metrics)
    tests.to_csv(comparison_dir / "augmentation_vs_real_only_wilcoxon_holm.csv", index=False)
    recovery = recovery_table(fold_means, metrics)
    recovery.to_csv(comparison_dir / "augmentation_recovery_by_fold.csv", index=False)

    plot_recovery_curves(fold_means, comparison_dir / "augmentation_recovery_curves.png")
    plot_overview(fold_means, metrics, comparison_dir / "six_condition_performance_overview.png")
    plot_foldwise_gain(fold_means, comparison_dir / "foldwise_augmentation_gain.png")
    plot_false_positives(fold_means, comparison_dir / "false_positive_burden.png")

    primary = "test_trial_balanced_accuracy"
    primary_rows = summary[summary["metric"] == primary].sort_values("fold_mean", ascending=False)
    winner = primary_rows.iloc[0]
    primary_tests = tests[tests["metric"] == primary].sort_values("real_fraction")
    table = [
        "| Condition | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP/min ↓ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in ALL_SCENARIOS:
        values = summary[summary["scenario"] == scenario].set_index("metric")["fold_mean"]
        table.append(
            f"| {LABELS[scenario]} | {values['test_trial_balanced_accuracy']:.3f} | "
            f"{values['test_trial_sensitivity']:.3f} | {values['test_trial_specificity']:.3f} | "
            f"{values['test_trial_f1']:.3f} | {values['test_trial_auroc']:.3f} | "
            f"{values['test_trial_auprc']:.3f} | {values['false_positive_events_per_adl_minute']:.3f} |"
        )
    test_lines = [
        f"- {int(100 * row.real_fraction)}%: mean augmented-minus-real-only = "
        f"{row.mean_difference_candidate_minus_reference:+.4f}; "
        f"unadjusted p = {row.wilcoxon_p_unadjusted:.4f}; Holm p = {row.wilcoxon_p_holm:.4f}."
        for row in primary_tests.itertuples(index=False)
    ]
    report = [
        "# Low-real-data augmentation comparison",
        "",
        f"Compared {len(matched)} runs across {matched[['fold', 'seed']].drop_duplicates().shape[0]} matched fold/seed settings. The two 100% conditions are frozen references from the completed study.",
        "",
        "## Descriptive result",
        "",
        f"The highest mean test-trial balanced accuracy was **{winner['scenario_name']}** ({winner['fold_mean']:.4f}).",
        "",
        *table,
        "",
        "## Paired augmentation tests for balanced accuracy",
        "",
        *test_lines,
        "",
        "Seeds are averaged within each fold before testing. Holm correction is applied across the 25% and 50% augmentation comparisons separately for each metric. With only five folds, statistical inference is exploratory.",
        "",
        "The recovery percentage is descriptive: it measures how much of the real-only gap to the frozen 100%-real reference was recovered by adding synthetic falls. Values can exceed 100% or be negative.",
        "",
    ]
    (comparison_dir / "COMPARISON.md").write_text("\n".join(report), encoding="utf-8")
    metadata = {
        "scenarios": ALL_SCENARIOS,
        "matched_fold_seed_settings": int(matched[["fold", "seed"]].drop_duplicates().shape[0]),
        "new_run_count": int(matched[matched["scenario"].isin(CONDITIONS)].shape[0]),
        "frozen_reference_run_count": int(matched[matched["scenario"].isin([FULL_REAL, FULL_AUGMENTED])].shape[0]),
        "primary_metric": primary,
        "descriptive_winner": str(winner["scenario"]),
    }
    (comparison_dir / "comparison_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Low-real-data comparison written to {comparison_dir}")


if __name__ == "__main__":
    main()
