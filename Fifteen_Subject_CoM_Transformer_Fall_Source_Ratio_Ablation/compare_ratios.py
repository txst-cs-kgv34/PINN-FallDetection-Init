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
    "source_ratio_40real_60synthetic",
    "source_balanced_1to1",
    "source_ratio_60real_40synthetic",
]
RATIO_SCENARIOS = [
    "source_ratio_40real_60synthetic",
    "source_balanced_1to1",
    "source_ratio_60real_40synthetic",
]
LABELS = {
    "real_fall_real_adl": "Real only",
    "synthetic_fall_real_adl": "Synthetic only",
    "real_synthetic_fall_real_adl": "Original combined",
    "source_ratio_40real_60synthetic": "40:60",
    "source_balanced_1to1": "50:50",
    "source_ratio_60real_40synthetic": "60:40",
}
LONG_LABELS = {
    "real_fall_real_adl": "Real falls + real ADL",
    "synthetic_fall_real_adl": "Synthetic falls + real ADL",
    "real_synthetic_fall_real_adl": "Original combined falls + real ADL",
    "source_ratio_40real_60synthetic": "40:60 real:synthetic falls + real ADL",
    "source_balanced_1to1": "50:50 real:synthetic falls + real ADL",
    "source_ratio_60real_40synthetic": "60:40 real:synthetic falls + real ADL",
}
COLORS = {
    "real_fall_real_adl": "#1f77b4",
    "synthetic_fall_real_adl": "#ff7f0e",
    "real_synthetic_fall_real_adl": "#2ca02c",
    "source_ratio_40real_60synthetic": "#d62728",
    "source_balanced_1to1": "#9467bd",
    "source_ratio_60real_40synthetic": "#8c564b",
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


def resolve(config_path: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (config_path.parent / path).resolve()


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


def metrics_from_tree(root: Path, experiment: str) -> pd.DataFrame:
    records = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / experiment).glob("fold_*/seed_*/metrics.json"))
    ]
    if not records:
        raise FileNotFoundError(f"No metrics found under {root / experiment}")
    frame = pd.DataFrame.from_records(records)
    frame["scenario"] = experiment
    return frame


def load_all(
    config_path: Path,
    config: dict[str, Any],
    prior_override: Path | None,
    balanced_override: Path | None,
) -> tuple[pd.DataFrame, Path]:
    prior_root = (
        prior_override.expanduser().resolve()
        if prior_override
        else resolve(config_path, config["prior_output_root"])
    )
    prior_csv = prior_root / "comparison" / "combined_run_metrics.csv"
    if not prior_csv.is_file():
        raise FileNotFoundError(f"Missing original results table: {prior_csv}")
    prior = pd.read_csv(prior_csv)
    prior = prior[prior["scenario"].isin(SCENARIOS[:3])].copy()

    balanced_root = (
        balanced_override.expanduser().resolve()
        if balanced_override
        else resolve(config_path, config["balanced_1to1_output_root"])
    )
    balanced = metrics_from_tree(balanced_root, "source_balanced_1to1")

    output_root = resolve(config_path, config["output_root"])
    new_frames = [
        metrics_from_tree(output_root, str(item["experiment_name"]))
        for item in config["experiments"]
    ]
    return pd.concat([prior, balanced, *new_frames], ignore_index=True, sort=False), output_root


def retain_matched(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame[frame["scenario"].isin(SCENARIOS)].copy()
    counts = frame.groupby(["fold", "seed"])["scenario"].nunique()
    complete = counts[counts == len(SCENARIOS)].index
    if not len(complete):
        raise ValueError("No fold/seed setting is complete across all six scenarios")
    matched = frame.set_index(["fold", "seed"]).loc[complete].reset_index()
    duplicates = matched.duplicated(["scenario", "fold", "seed"], keep=False)
    if duplicates.any():
        raise ValueError("Duplicate scenario/fold/seed rows were found")
    return matched


def plot_overview(fold_means: pd.DataFrame, metrics: list[str], path: Path) -> None:
    performance = [metric for metric in metrics if not metric.startswith("false_")]
    x = np.arange(len(performance), dtype=float)
    offsets = np.linspace(-0.32, 0.32, len(SCENARIOS))
    fig, ax = plt.subplots(figsize=(14.5, 7.0))
    for offset, scenario in zip(offsets, SCENARIOS):
        group = fold_means[fold_means["scenario"] == scenario]
        ax.errorbar(
            x + offset,
            group[performance].mean().to_numpy(),
            yerr=group[performance].std(ddof=1).to_numpy(),
            fmt="o",
            markersize=6.5,
            linewidth=1.6,
            capsize=3,
            color=COLORS[scenario],
            label=LABELS[scenario],
        )
    ax.set_xticks(x, [METRIC_LABELS[item] for item in performance])
    ax.set_ylim(0.50, 1.04)
    ax.set_ylabel("Test trial metric")
    ax.set_title("Six-scenario detector comparison: mean ± SD across five fold means")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(ncol=3, loc="lower left")
    ax.text(
        0.99,
        0.02,
        "Higher is better. Seeds are averaged within each fold.",
        transform=ax.transAxes,
        ha="right",
        color="#555555",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_ratio_metrics(fold_means: pd.DataFrame, metrics: list[str], path: Path) -> None:
    performance = [metric for metric in metrics if not metric.startswith("false_")]
    x = np.arange(len(performance), dtype=float)
    offsets = [-0.18, 0.0, 0.18]
    fig, ax = plt.subplots(figsize=(13.0, 6.5))
    for offset, scenario in zip(offsets, RATIO_SCENARIOS):
        group = fold_means[fold_means["scenario"] == scenario]
        ax.errorbar(
            x + offset,
            group[performance].mean().to_numpy(),
            yerr=group[performance].std(ddof=1).to_numpy(),
            fmt="o",
            markersize=8,
            linewidth=2,
            capsize=4,
            color=COLORS[scenario],
            label=f"{LABELS[scenario]} real:synthetic",
        )
    ax.set_xticks(x, [METRIC_LABELS[item] for item in performance])
    ax.set_ylim(0.50, 1.04)
    ax.set_ylabel("Test trial metric")
    ax.set_title("Fall-source ratio comparison")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(ncol=3, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_foldwise(fold_means: pd.DataFrame, path: Path) -> None:
    folds = sorted(fold_means["fold"].unique())
    x = np.arange(len(folds))
    fig, ax = plt.subplots(figsize=(10.5, 6.0))
    for scenario in RATIO_SCENARIOS:
        values = (
            fold_means[fold_means["scenario"] == scenario]
            .set_index("fold")
            .loc[folds, "test_trial_balanced_accuracy"]
        )
        ax.plot(
            x,
            values,
            marker="o",
            linewidth=2.2,
            markersize=7,
            color=COLORS[scenario],
            label=f"{LABELS[scenario]} real:synthetic",
        )
    ax.set_xticks(x, [fold.replace("fold_", "Fold ") for fold in folds])
    ax.set_ylim(0.65, 1.02)
    ax.set_ylabel("Mean test trial balanced accuracy")
    ax.set_title("Source-ratio performance by held-out subject fold")
    ax.grid(alpha=0.25)
    ax.legend(ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_differences(fold_means: pd.DataFrame, path: Path) -> None:
    pivot = fold_means.pivot(
        index="fold", columns="scenario", values="test_trial_balanced_accuracy"
    ).sort_index()
    folds = pivot.index.tolist()
    x = np.arange(len(folds))
    width = 0.32
    fig, ax = plt.subplots(figsize=(10.5, 6.0))
    for offset, scenario in zip([-0.5, 0.5], RATIO_SCENARIOS[::2]):
        differences = 100 * (pivot[scenario] - pivot["source_balanced_1to1"])
        ax.bar(
            x + offset * width,
            differences,
            width,
            color=COLORS[scenario],
            label=f"{LABELS[scenario]} − 50:50",
        )
    ax.axhline(0, color="black", linewidth=1)
    ax.set_xticks(x, [fold.replace("fold_0", "F") for fold in folds])
    ax.set_ylabel("Balanced-accuracy difference (percentage points)")
    ax.set_title("Paired fold differences relative to the 50:50 baseline")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_false_positives(fold_means: pd.DataFrame, path: Path) -> None:
    metric = "false_positive_events_per_adl_minute"
    folds = sorted(fold_means["fold"].unique())
    x = np.arange(len(folds))
    width = 0.25
    fig, ax = plt.subplots(figsize=(10.5, 6.0))
    for position, scenario in enumerate(RATIO_SCENARIOS):
        values = (
            fold_means[fold_means["scenario"] == scenario]
            .set_index("fold")
            .loc[folds, metric]
        )
        ax.bar(
            x + (position - 1) * width,
            values,
            width,
            color=COLORS[scenario],
            label=f"{LABELS[scenario]} real:synthetic",
        )
    ax.set_xticks(x, [fold.replace("fold_", "Fold ") for fold in folds])
    ax.set_ylabel("False-positive events per ADL minute")
    ax.set_title("False-positive burden for the three source ratios")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def paired_tests(fold_means: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    pairs = [
        ("source_ratio_40real_60synthetic", "source_balanced_1to1"),
        ("source_ratio_60real_40synthetic", "source_balanced_1to1"),
        ("source_ratio_40real_60synthetic", "source_ratio_60real_40synthetic"),
        ("source_ratio_40real_60synthetic", "real_fall_real_adl"),
        ("source_ratio_60real_40synthetic", "real_fall_real_adl"),
    ]
    records = []
    for metric in metrics:
        per_metric = []
        pivot = fold_means.pivot(index="fold", columns="scenario", values=metric)
        for candidate, reference in pairs:
            paired = pivot[[reference, candidate]].dropna()
            differences = paired[candidate] - paired[reference]
            if len(paired) < 2 or np.allclose(differences, 0.0):
                statistic, p_value = 0.0, 1.0
            else:
                result = wilcoxon(
                    paired[reference], paired[candidate], alternative="two-sided"
                )
                statistic, p_value = float(result.statistic), float(result.pvalue)
            per_metric.append(
                {
                    "metric": metric,
                    "reference_scenario": reference,
                    "candidate_scenario": candidate,
                    "fold_count": len(paired),
                    "reference_mean": float(paired[reference].mean()),
                    "candidate_mean": float(paired[candidate].mean()),
                    "mean_difference_candidate_minus_reference": float(
                        differences.mean()
                    ),
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
            records.append(record)
    return pd.DataFrame.from_records(records)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compare 40:60 and 60:40 with 50:50 and frozen baselines."
    )
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json")
    )
    parser.add_argument("--prior-output-root", type=Path)
    parser.add_argument("--balanced-1to1-output-root", type=Path)
    args = parser.parse_args(argv)

    config_path, raw_config, _ = prepare_base_imports(args.config)
    all_metrics, output_root = load_all(
        config_path,
        raw_config,
        args.prior_output_root,
        args.balanced_1to1_output_root,
    )
    matched = retain_matched(all_metrics)
    comparison_dir = output_root / "ratio_comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    matched.to_csv(comparison_dir / "six_scenario_run_metrics.csv", index=False)

    metrics = [
        metric for metric in raw_config["comparison_metrics"] if metric in matched.columns
    ]
    fold_means = matched.groupby(["scenario", "fold"], as_index=False)[metrics].mean()
    fold_means.to_csv(
        comparison_dir / "six_scenario_fold_seed_averaged_metrics.csv", index=False
    )

    summaries = []
    for scenario in SCENARIOS:
        run_group = matched[matched["scenario"] == scenario]
        fold_group = fold_means[fold_means["scenario"] == scenario]
        for metric in metrics:
            summaries.append(
                {
                    "scenario": scenario,
                    "scenario_name": LONG_LABELS[scenario],
                    "metric": metric,
                    "run_count": len(run_group),
                    "run_mean": run_group[metric].mean(),
                    "run_standard_deviation": run_group[metric].std(ddof=1),
                    "fold_mean": fold_group[metric].mean(),
                    "fold_standard_deviation": fold_group[metric].std(ddof=1),
                }
            )
    summary = pd.DataFrame.from_records(summaries)
    summary.to_csv(comparison_dir / "six_scenario_summary.csv", index=False)
    statistical = paired_tests(fold_means, metrics)
    statistical.to_csv(
        comparison_dir / "ratio_paired_wilcoxon_holm.csv", index=False
    )

    plot_overview(fold_means, metrics, comparison_dir / "six_scenario_overview.png")
    plot_ratio_metrics(fold_means, metrics, comparison_dir / "three_ratio_overview.png")
    plot_foldwise(fold_means, comparison_dir / "three_ratio_foldwise_balanced_accuracy.png")
    plot_differences(fold_means, comparison_dir / "ratio_differences_vs_50to50.png")
    plot_false_positives(fold_means, comparison_dir / "three_ratio_false_positives.png")

    primary = "test_trial_balanced_accuracy"
    primary_summary = summary[summary["metric"] == primary].sort_values(
        "fold_mean", ascending=False
    )
    winner = primary_summary.iloc[0]
    ratio_primary = primary_summary[
        primary_summary["scenario"].isin(RATIO_SCENARIOS)
    ].iloc[0]
    table = [
        "| Scenario | Balanced accuracy | Sensitivity | Specificity | F1 | AUROC | AUPRC | FP/min ↓ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in SCENARIOS:
        values = summary[summary["scenario"] == scenario].set_index("metric")[
            "fold_mean"
        ]
        table.append(
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
        "# Fall-source ratio comparison",
        "",
        f"Compared {len(matched)} runs across "
        f"{matched[['fold', 'seed']].drop_duplicates().shape[0]} matched fold/seed settings.",
        "",
        "## Descriptive results",
        "",
        f"The overall descriptive winner by balanced accuracy was "
        f"**{winner['scenario_name']}** ({winner['fold_mean']:.4f}).",
        f"The best mixed-source ratio was **{ratio_primary['scenario_name']}** "
        f"({ratio_primary['fold_mean']:.4f}).",
        "",
        *table,
        "",
        "## Interpretation",
        "",
        "The new 40:60 and 60:40 ratios are exploratory because they were requested "
        "after the existing held-out results had already been inspected. Use validation "
        "performance or a new untouched subject set to select a ratio for a final "
        "confirmatory claim.",
        "",
        "Seeds are averaged within each fold before paired Wilcoxon testing. Holm "
        "correction is applied across five planned pairwise comparisons per metric. "
        "With only five independent folds, emphasize effect sizes and fold consistency.",
        "",
    ]
    (comparison_dir / "COMPARISON.md").write_text(
        "\n".join(report), encoding="utf-8"
    )
    metadata = {
        "scenarios": SCENARIOS,
        "ratio_scenarios": RATIO_SCENARIOS,
        "matched_fold_seed_settings": int(
            matched[["fold", "seed"]].drop_duplicates().shape[0]
        ),
        "metrics": metrics,
        "primary_metric": primary,
        "descriptive_overall_winner": str(winner["scenario"]),
        "descriptive_ratio_winner": str(ratio_primary["scenario"]),
        "status": "exploratory_post_hoc_ratio_ablation",
    }
    (comparison_dir / "comparison_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Six-scenario and three-ratio comparisons written to {comparison_dir}")


if __name__ == "__main__":
    main()
