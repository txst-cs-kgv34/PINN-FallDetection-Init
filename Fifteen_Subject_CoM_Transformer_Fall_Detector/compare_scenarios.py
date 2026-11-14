from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

from detector_core import SCENARIO_SOURCES, load_config, write_json


DISPLAY_NAMES = {
    "real_fall_real_adl": "Real falls + real ADL",
    "synthetic_fall_real_adl": "Synthetic falls + real ADL",
    "real_synthetic_fall_real_adl": "Real + synthetic falls + real ADL",
}


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


def load_runs(output_root: Path) -> pd.DataFrame:
    records = []
    for scenario in SCENARIO_SOURCES:
        for path in sorted((output_root / scenario).glob("fold_*/seed_*/metrics.json")):
            records.append(json.loads(path.read_text()))
    if not records:
        raise FileNotFoundError(f"No completed run metrics were found under {output_root}")
    return pd.DataFrame.from_records(records)


def ensure_complete_pairs(frame: pd.DataFrame) -> pd.DataFrame:
    keys = ["fold", "seed"]
    counts = frame.groupby(keys)["scenario"].nunique()
    complete = counts[counts == len(SCENARIO_SOURCES)].index
    if not len(complete):
        raise ValueError("No fold/seed combination is complete across all three scenarios")
    indexed = frame.set_index(keys)
    return indexed.loc[complete].reset_index()


def create_plot(frame: pd.DataFrame, metrics: list[str], path: Path) -> None:
    selected = metrics[:6]
    columns = 3
    rows = int(np.ceil(len(selected) / columns))
    figure, axes = plt.subplots(rows, columns, figsize=(14, 4.2 * rows), squeeze=False)
    scenario_order = list(SCENARIO_SOURCES)
    labels = [DISPLAY_NAMES[name] for name in scenario_order]
    for axis, metric in zip(axes.flat, selected):
        values = [
            pd.to_numeric(frame.loc[frame["scenario"] == scenario, metric], errors="coerce").dropna()
            for scenario in scenario_order
        ]
        axis.boxplot(values, tick_labels=["Real", "Synthetic", "Combined"], showmeans=True)
        axis.set_title(metric.replace("test_trial_", "").replace("_", " ").title())
        axis.grid(axis="y", alpha=0.25)
    for axis in axes.flat[len(selected) :]:
        axis.axis("off")
    figure.suptitle("CoM fall-detector scenario comparison", fontsize=14)
    figure.tight_layout()
    figure.savefig(path, dpi=190)
    plt.close(figure)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare completed fall-detector scenarios.")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    args = parser.parse_args(argv)
    config = load_config(args.config)
    output_root = Path(config["output_root"])
    comparison_dir = output_root / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    all_runs = load_runs(output_root)
    complete = ensure_complete_pairs(all_runs)
    metrics = [metric for metric in config["comparison_metrics"] if metric in complete.columns]
    if not metrics:
        raise ValueError("No configured comparison metrics are available")
    complete.to_csv(comparison_dir / "combined_run_metrics.csv", index=False)

    summary_records = []
    for scenario, group in complete.groupby("scenario", sort=False):
        for metric in metrics:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            summary_records.append(
                {
                    "scenario": scenario,
                    "scenario_name": DISPLAY_NAMES[scenario],
                    "metric": metric,
                    "run_count": len(values),
                    "mean": values.mean(),
                    "standard_deviation": values.std(ddof=1),
                    "median": values.median(),
                    "minimum": values.min(),
                    "maximum": values.max(),
                }
            )
    summary = pd.DataFrame.from_records(summary_records)
    summary.to_csv(comparison_dir / "scenario_summary.csv", index=False)

    # Seeds are averaged inside each fold before the exploratory paired test.
    fold_means = complete.groupby(["scenario", "fold"], as_index=False)[metrics].mean()
    pairwise_records = []
    scenarios = list(SCENARIO_SOURCES)
    for metric in metrics:
        metric_records = []
        for scenario_a, scenario_b in itertools.combinations(scenarios, 2):
            a = fold_means[fold_means["scenario"] == scenario_a].set_index("fold")[metric]
            b = fold_means[fold_means["scenario"] == scenario_b].set_index("fold")[metric]
            paired = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
            differences = paired["b"] - paired["a"]
            if len(paired) < 2 or np.allclose(differences, 0.0):
                statistic, p_value = 0.0, 1.0
            else:
                result = wilcoxon(paired["a"], paired["b"], alternative="two-sided")
                statistic, p_value = float(result.statistic), float(result.pvalue)
            metric_records.append(
                {
                    "metric": metric,
                    "scenario_a": scenario_a,
                    "scenario_b": scenario_b,
                    "fold_count": len(paired),
                    "mean_a": paired["a"].mean(),
                    "mean_b": paired["b"].mean(),
                    "mean_difference_b_minus_a": differences.mean(),
                    "wilcoxon_statistic": statistic,
                    "wilcoxon_p_unadjusted": p_value,
                }
            )
        adjusted = holm_adjust([record["wilcoxon_p_unadjusted"] for record in metric_records])
        for record, p_adjusted in zip(metric_records, adjusted):
            record["wilcoxon_p_holm"] = p_adjusted
            record["holm_significant_at_0_05"] = bool(p_adjusted < 0.05)
            pairwise_records.append(record)
    pairwise = pd.DataFrame.from_records(pairwise_records)
    pairwise.to_csv(comparison_dir / "paired_wilcoxon_holm.csv", index=False)
    fold_means.to_csv(comparison_dir / "fold_seed_averaged_metrics.csv", index=False)
    create_plot(complete, metrics, comparison_dir / "scenario_metric_boxplots.png")

    primary = "test_trial_balanced_accuracy"
    primary_rows = summary[summary["metric"] == primary].sort_values("mean", ascending=False)
    best = primary_rows.iloc[0]
    report_lines = [
        "# Fall-detector scenario comparison",
        "",
        f"Compared {len(complete)} completed fold/seed runs "
        f"({complete[['fold', 'seed']].drop_duplicates().shape[0]} matched settings per scenario).",
        "",
        "## Descriptive result",
        "",
        f"The highest mean test trial balanced accuracy was produced by "
        f"**{best['scenario_name']}** ({best['mean']:.4f} ± {best['standard_deviation']:.4f}).",
        "",
        "This is a descriptive comparison, not permission to tune the model on the test set. "
        "Architecture and hyperparameter changes must be chosen using validation results only.",
        "",
        "## Statistical tables",
        "",
        "`paired_wilcoxon_holm.csv` averages the repeated seeds within each fold, performs "
        "paired Wilcoxon tests across folds, and applies Holm correction across the three "
        "scenario comparisons for each metric. With only five folds, these tests are exploratory "
        "and effect sizes plus fold-level consistency should receive more emphasis than p-values.",
        "",
        "## Files",
        "",
        "- `scenario_summary.csv`: descriptive mean, standard deviation, median, and range.",
        "- `paired_wilcoxon_holm.csv`: paired differences and corrected p-values.",
        "- `fold_seed_averaged_metrics.csv`: values supplied to the paired tests.",
        "- `combined_run_metrics.csv`: all matched fold/seed run metrics.",
        "- `scenario_metric_boxplots.png`: visual comparison.",
        "",
    ]
    (comparison_dir / "COMPARISON.md").write_text("\n".join(report_lines), encoding="utf-8")
    write_json(
        comparison_dir / "comparison_metadata.json",
        {
            "scenarios": scenarios,
            "matched_fold_seed_settings": int(
                complete[["fold", "seed"]].drop_duplicates().shape[0]
            ),
            "metrics": metrics,
            "primary_metric": primary,
            "best_descriptive_scenario": str(best["scenario"]),
        },
    )
    print(f"Comparison written to {comparison_dir}")


if __name__ == "__main__":
    main()

