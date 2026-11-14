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

from base_detector_imports import prepare_base_imports


SCENARIOS = [
    "real_fall_real_adl",
    "synthetic_fall_real_adl",
    "real_synthetic_fall_real_adl",
    "source_balanced_1to1",
]
LABELS = {
    "real_fall_real_adl": "Real",
    "synthetic_fall_real_adl": "Synthetic",
    "real_synthetic_fall_real_adl": "Combined",
    "source_balanced_1to1": "Balanced 1:1",
}
LONG_LABELS = {
    "real_fall_real_adl": "Real falls + real ADL",
    "synthetic_fall_real_adl": "Synthetic falls + real ADL",
    "real_synthetic_fall_real_adl": "Original combined + real ADL",
    "source_balanced_1to1": "Source-balanced 1:1 falls + real ADL",
}
COLORS = {
    "real_fall_real_adl": "#1f77b4",
    "synthetic_fall_real_adl": "#ff7f0e",
    "real_synthetic_fall_real_adl": "#2ca02c",
    "source_balanced_1to1": "#9467bd",
}
METRIC_LABELS = {
    "test_trial_balanced_accuracy": "Balanced\naccuracy",
    "test_trial_sensitivity": "Sensitivity",
    "test_trial_specificity": "Specificity",
    "test_trial_f1": "F1",
    "test_trial_auroc": "AUROC",
    "test_trial_auprc": "AUPRC",
    "false_positive_events_per_adl_minute": "FP events /\nADL minute",
}


def resolve_from_config(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = config_path.parent / path
    return path.resolve()


def holm_adjust(p_values: list[float]) -> list[float]:
    count = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(count, dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = (count - rank) * float(p_values[index])
        running = max(running, candidate)
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def load_metrics(
    config_path: Path,
    config: dict[str, Any],
    prior_override: Path | None,
) -> tuple[pd.DataFrame, Path]:
    prior_root = (
        prior_override.expanduser().resolve()
        if prior_override
        else resolve_from_config(config_path, config["prior_output_root"])
    )
    prior_csv = prior_root / "comparison" / "combined_run_metrics.csv"
    if not prior_csv.is_file():
        raise FileNotFoundError(
            f"Missing prior comparison data: {prior_csv}. Keep the completed original "
            "detector outputs in the sibling directory or pass --prior-output-root."
        )
    prior = pd.read_csv(prior_csv)
    prior = prior[prior["scenario"].isin(SCENARIOS[:3])].copy()

    output_root = resolve_from_config(config_path, config["output_root"])
    experiment = str(config["experiment_name"])
    new_records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(
            (output_root / experiment).glob("fold_*/seed_*/metrics.json")
        )
    ]
    if not new_records:
        raise FileNotFoundError(
            f"No new metrics found under {output_root / experiment}. Run training first."
        )
    new = pd.DataFrame.from_records(new_records)
    combined = pd.concat([prior, new], ignore_index=True, sort=False)
    return combined, output_root


def retain_matched_settings(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame.groupby(["fold", "seed"])["scenario"].nunique()
    complete = counts[counts == len(SCENARIOS)].index
    if not len(complete):
        raise ValueError("No fold/seed setting is complete across all four scenarios")
    matched = frame.set_index(["fold", "seed"]).loc[complete].reset_index()
    return matched[matched["scenario"].isin(SCENARIOS)].copy()


def plot_performance(fold_means: pd.DataFrame, metrics: list[str], path: Path) -> None:
    performance = [metric for metric in metrics if not metric.startswith("false_")]
    x = np.arange(len(performance), dtype=float)
    offsets = np.linspace(-0.27, 0.27, len(SCENARIOS))
    figure, axis = plt.subplots(figsize=(13.5, 6.5))
    for offset, scenario in zip(offsets, SCENARIOS):
        group = fold_means[fold_means["scenario"] == scenario]
        means = group[performance].mean().to_numpy()
        standard_deviations = group[performance].std(ddof=1).to_numpy()
        axis.errorbar(
            x + offset,
            means,
            yerr=standard_deviations,
            fmt="o",
            markersize=7,
            linewidth=1.8,
            capsize=3,
            color=COLORS[scenario],
            label=LABELS[scenario],
        )
    axis.set_xticks(x, [METRIC_LABELS[metric] for metric in performance])
    axis.set_ylim(0.52, 1.035)
    axis.set_ylabel("Test trial metric")
    axis.set_title("Four-scenario comparison: mean ± SD across five fold means")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncol=4, loc="lower left")
    axis.text(
        0.99,
        0.02,
        "Higher is better. Seeds are averaged within each fold.",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        color="#555555",
        fontsize=9,
    )
    figure.tight_layout()
    figure.savefig(path, dpi=220)
    plt.close(figure)


def plot_foldwise(fold_means: pd.DataFrame, path: Path) -> None:
    folds = sorted(fold_means["fold"].unique())
    x = np.arange(len(folds))
    figure, axis = plt.subplots(figsize=(10.5, 6.0))
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
            linewidth=2.2,
            markersize=7,
            color=COLORS[scenario],
            label=LABELS[scenario],
        )
    axis.set_xticks(x, [fold.replace("fold_", "Fold ") for fold in folds])
    axis.set_ylim(0.68, 1.02)
    axis.set_ylabel("Mean test trial balanced accuracy")
    axis.set_title("Held-out subject-fold comparison")
    axis.grid(alpha=0.25)
    axis.legend(ncol=2, loc="lower right")
    figure.tight_layout()
    figure.savefig(path, dpi=220)
    plt.close(figure)


def plot_balanced_differences(fold_means: pd.DataFrame, path: Path) -> None:
    pivot = fold_means.pivot(
        index="fold", columns="scenario", values="test_trial_balanced_accuracy"
    ).sort_index()
    folds = pivot.index.tolist()
    references = SCENARIOS[:3]
    x = np.arange(len(folds))
    width = 0.23
    figure, axis = plt.subplots(figsize=(10.5, 6.0))
    for position, reference in enumerate(references):
        difference = 100 * (
            pivot["source_balanced_1to1"] - pivot[reference]
        )
        axis.bar(
            x + (position - 1) * width,
            difference,
            width,
            label=f"Balanced 1:1 − {LABELS[reference]}",
            color=COLORS[reference],
        )
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(x, [fold.replace("fold_0", "F") for fold in folds])
    axis.set_ylabel("Balanced-accuracy difference (percentage points)")
    axis.set_title("Paired fold differences for the source-balanced experiment")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncol=1, loc="best")
    axis.text(
        0.99,
        0.02,
        "Positive values favor Balanced 1:1.",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        color="#555555",
        fontsize=9,
    )
    figure.tight_layout()
    figure.savefig(path, dpi=220)
    plt.close(figure)


def plot_false_positives(fold_means: pd.DataFrame, path: Path) -> None:
    metric = "false_positive_events_per_adl_minute"
    folds = sorted(fold_means["fold"].unique())
    x = np.arange(len(folds))
    width = 0.19
    figure, axis = plt.subplots(figsize=(10.5, 6.0))
    for position, scenario in enumerate(SCENARIOS):
        values = (
            fold_means[fold_means["scenario"] == scenario]
            .set_index("fold")
            .loc[folds, metric]
        )
        axis.bar(
            x + (position - 1.5) * width,
            values,
            width,
            color=COLORS[scenario],
            label=LABELS[scenario],
        )
    axis.set_xticks(x, [fold.replace("fold_", "Fold ") for fold in folds])
    axis.set_ylabel("False-positive detection events per ADL minute")
    axis.set_title("False-positive burden by held-out subject fold")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncol=4)
    axis.text(
        0.99,
        0.02,
        "Lower is better.",
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        color="#555555",
        fontsize=9,
    )
    figure.tight_layout()
    figure.savefig(path, dpi=220)
    plt.close(figure)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compare source-balanced 1:1 with the three prior experiments."
    )
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json")
    )
    parser.add_argument("--prior-output-root", type=Path)
    args = parser.parse_args(argv)

    config_path, raw_config, _ = prepare_base_imports(args.config)

    all_metrics, output_root = load_metrics(
        config_path, raw_config, args.prior_output_root
    )
    matched = retain_matched_settings(all_metrics)
    comparison_dir = output_root / "comparison_with_prior"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    matched.to_csv(comparison_dir / "four_scenario_run_metrics.csv", index=False)

    metrics = [
        metric
        for metric in raw_config["comparison_metrics"]
        if metric in matched.columns
    ]
    fold_means = matched.groupby(["scenario", "fold"], as_index=False)[metrics].mean()
    fold_means.to_csv(
        comparison_dir / "four_scenario_fold_seed_averaged_metrics.csv", index=False
    )

    summary_records = []
    for scenario in SCENARIOS:
        group = matched[matched["scenario"] == scenario]
        fold_group = fold_means[fold_means["scenario"] == scenario]
        for metric in metrics:
            summary_records.append(
                {
                    "scenario": scenario,
                    "scenario_name": LONG_LABELS[scenario],
                    "metric": metric,
                    "run_count": len(group),
                    "run_mean": group[metric].mean(),
                    "run_standard_deviation": group[metric].std(ddof=1),
                    "fold_mean": fold_group[metric].mean(),
                    "fold_standard_deviation": fold_group[metric].std(ddof=1),
                }
            )
    summary = pd.DataFrame.from_records(summary_records)
    summary.to_csv(comparison_dir / "four_scenario_summary.csv", index=False)

    test_records = []
    new_scenario = "source_balanced_1to1"
    for metric in metrics:
        per_metric = []
        new_values = fold_means[fold_means["scenario"] == new_scenario].set_index(
            "fold"
        )[metric]
        for reference in SCENARIOS[:3]:
            reference_values = fold_means[
                fold_means["scenario"] == reference
            ].set_index("fold")[metric]
            paired = pd.concat(
                [reference_values.rename("reference"), new_values.rename("balanced")],
                axis=1,
            ).dropna()
            differences = paired["balanced"] - paired["reference"]
            if len(paired) < 2 or np.allclose(differences, 0.0):
                statistic, p_value = 0.0, 1.0
            else:
                result = wilcoxon(
                    paired["reference"], paired["balanced"], alternative="two-sided"
                )
                statistic, p_value = float(result.statistic), float(result.pvalue)
            per_metric.append(
                {
                    "metric": metric,
                    "reference_scenario": reference,
                    "candidate_scenario": new_scenario,
                    "fold_count": len(paired),
                    "reference_mean": paired["reference"].mean(),
                    "candidate_mean": paired["balanced"].mean(),
                    "mean_difference_candidate_minus_reference": differences.mean(),
                    "wilcoxon_statistic": statistic,
                    "wilcoxon_p_unadjusted": p_value,
                }
            )
        adjusted = holm_adjust(
            [record["wilcoxon_p_unadjusted"] for record in per_metric]
        )
        for record, adjusted_p in zip(per_metric, adjusted):
            record["wilcoxon_p_holm"] = adjusted_p
            record["holm_significant_at_0_05"] = bool(adjusted_p < 0.05)
            test_records.append(record)
    statistical = pd.DataFrame.from_records(test_records)
    statistical.to_csv(
        comparison_dir / "source_balanced_vs_prior_wilcoxon_holm.csv", index=False
    )

    plot_performance(
        fold_means, metrics, comparison_dir / "four_scenario_performance_overview.png"
    )
    plot_foldwise(
        fold_means,
        comparison_dir / "four_scenario_foldwise_balanced_accuracy.png",
    )
    plot_balanced_differences(
        fold_means,
        comparison_dir / "source_balanced_paired_differences.png",
    )
    plot_false_positives(
        fold_means,
        comparison_dir / "four_scenario_false_positive_events.png",
    )

    primary = "test_trial_balanced_accuracy"
    primary_summary = summary[summary["metric"] == primary].sort_values(
        "fold_mean", ascending=False
    )
    winner = primary_summary.iloc[0]
    table_lines = [
        "| Scenario | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP/min ↓ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in SCENARIOS:
        values = summary[summary["scenario"] == scenario].set_index("metric")[
            "fold_mean"
        ]
        table_lines.append(
            f"| {LONG_LABELS[scenario]} | "
            f"{values['test_trial_balanced_accuracy']:.3f} | "
            f"{values['test_trial_sensitivity']:.3f} | "
            f"{values['test_trial_specificity']:.3f} | "
            f"{values['test_trial_f1']:.3f} | "
            f"{values['test_trial_auroc']:.3f} | "
            f"{values['test_trial_auprc']:.3f} | "
            f"{values['false_positive_events_per_adl_minute']:.3f} |"
        )
    report = [
        "# Source-balanced 1:1 comparison",
        "",
        f"Compared {len(matched)} completed scenario runs across "
        f"{matched[['fold', 'seed']].drop_duplicates().shape[0]} matched fold/seed settings.",
        "",
        "## Descriptive winner",
        "",
        f"The highest mean test-trial balanced accuracy was produced by "
        f"**{winner['scenario_name']}** ({winner['fold_mean']:.4f}).",
        "",
        *table_lines,
        "",
        "## Interpretation rule",
        "",
        "The 1:1 ratio was fixed before this test run, so this is a confirmatory comparison "
        "rather than test-set selection among several mixture ratios. Check the paired fold "
        "differences and Holm-adjusted tests before claiming an improvement.",
        "",
        "Seeds are averaged within each fold before paired Wilcoxon tests. Holm correction "
        "is applied across the three comparisons between Balanced 1:1 and the prior scenarios "
        "for each metric. With five folds, inference remains exploratory.",
        "",
    ]
    (comparison_dir / "COMPARISON.md").write_text(
        "\n".join(report), encoding="utf-8"
    )
    metadata = {
            "scenarios": SCENARIOS,
            "matched_fold_seed_settings": int(
                matched[["fold", "seed"]].drop_duplicates().shape[0]
            ),
            "metrics": metrics,
            "primary_metric": primary,
            "descriptive_winner": str(winner["scenario"]),
        }
    (comparison_dir / "comparison_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Four-scenario comparison written to {comparison_dir}")


if __name__ == "__main__":
    main()

