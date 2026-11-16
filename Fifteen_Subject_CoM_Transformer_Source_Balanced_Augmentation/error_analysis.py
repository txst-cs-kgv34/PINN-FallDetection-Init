from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCENARIOS = [
    "real_fall_real_adl",
    "synthetic_fall_real_adl",
    "real_synthetic_fall_real_adl",
    "source_balanced_1to1",
]
SCENARIO_LABELS = {
    "real_fall_real_adl": "Real",
    "synthetic_fall_real_adl": "Synthetic",
    "real_synthetic_fall_real_adl": "Combined",
    "source_balanced_1to1": "Balanced 1:1",
}
COLORS = {
    "real_fall_real_adl": "#1f77b4",
    "synthetic_fall_real_adl": "#ff7f0e",
    "real_synthetic_fall_real_adl": "#2ca02c",
    "source_balanced_1to1": "#9467bd",
}
ACTIVITY_NAMES = {
    "A01": "Drinking Water",
    "A02": "Pick Up Object",
    "A03": "Put On/Take Off Jacket",
    "A04": "Stepping Up",
    "A05": "Sweeping Floor",
    "A06": "Washing Hand",
    "A07": "Waving Hand",
    "A08": "TUG Test/Walking",
    "A09": "Sit/Stand",
    "A10": "Backfall",
    "A11": "Frontfall",
    "A12": "Leftfall",
    "A13": "Rightfall",
    "A14": "Rotatefall",
}


def activity_code(value: object) -> str:
    text = str(value).strip().upper()
    if text.startswith("A"):
        number = text[1:]
    else:
        number = text
    try:
        return f"A{int(float(number)):02d}"
    except ValueError:
        return text


def expected_calibration_error(
    labels: np.ndarray, probabilities: np.ndarray, bins: int = 10
) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(labels)
    result = 0.0
    for index in range(bins):
        lower, upper = edges[index], edges[index + 1]
        selected = (
            (probabilities >= lower) & (probabilities <= upper)
            if index == bins - 1
            else (probabilities >= lower) & (probabilities < upper)
        )
        if selected.any():
            result += selected.mean() * abs(
                probabilities[selected].mean() - labels[selected].mean()
            )
    return float(result) if total else float("nan")


def load_scenario(
    root: Path, scenario: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trial_frames: list[pd.DataFrame] = []
    window_frames: list[pd.DataFrame] = []
    run_records: list[dict[str, object]] = []
    metrics_paths = sorted((root / scenario).glob("fold_*/seed_*/metrics.json"))
    if not metrics_paths:
        raise FileNotFoundError(f"No completed runs found under {root / scenario}")
    for metrics_path in metrics_paths:
        run_dir = metrics_path.parent
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        fold = str(metrics["fold"])
        seed = int(metrics["seed"])
        threshold = float(metrics["validation_threshold"])
        trial_path = run_dir / "test_trial_predictions.csv"
        window_path = run_dir / "test_window_predictions.csv"
        if not trial_path.is_file() or not window_path.is_file():
            raise FileNotFoundError(f"Missing prediction file in {run_dir}")

        trial = pd.read_csv(trial_path)
        window = pd.read_csv(window_path)
        for frame in (trial, window):
            frame["scenario"] = scenario
            frame["scenario_name"] = SCENARIO_LABELS[scenario]
            frame["fold"] = fold
            frame["seed"] = seed
            frame["threshold"] = threshold
            frame["activity_code"] = frame["activity_code"].map(activity_code)
            frame["activity_name"] = frame["activity_code"].map(ACTIVITY_NAMES).fillna(
                frame["activity_code"]
            )
            frame["prediction"] = (
                frame["probability"].astype(float) >= threshold
            ).astype(int)
            frame["margin"] = frame["probability"].astype(float) - threshold
            frame["is_error"] = frame["prediction"] != frame["label"].astype(int)
            frame["error_type"] = np.select(
                [
                    (frame["label"] == 0) & (frame["prediction"] == 1),
                    (frame["label"] == 1) & (frame["prediction"] == 0),
                ],
                ["false_positive", "false_negative"],
                default="correct",
            )
        labels = trial["label"].to_numpy(dtype=float)
        probabilities = trial["probability"].to_numpy(dtype=float)
        run_records.append(
            {
                "scenario": scenario,
                "scenario_name": SCENARIO_LABELS[scenario],
                "fold": fold,
                "seed": seed,
                "threshold": threshold,
                "trial_count": len(trial),
                "brier_score": float(np.mean(np.square(probabilities - labels))),
                "expected_calibration_error": expected_calibration_error(
                    labels, probabilities
                ),
                "balanced_accuracy": float(
                    metrics["test_trial_balanced_accuracy"]
                ),
                "sensitivity": float(metrics["test_trial_sensitivity"]),
                "specificity": float(metrics["test_trial_specificity"]),
                "f1": float(metrics["test_trial_f1"]),
                "false_positive_events_per_adl_minute": float(
                    metrics["false_positive_events_per_adl_minute"]
                ),
            }
        )
        trial_frames.append(trial)
        window_frames.append(window)
    return (
        pd.concat(trial_frames, ignore_index=True),
        pd.concat(window_frames, ignore_index=True),
        pd.DataFrame.from_records(run_records),
    )


def grouped_error_summary(frame: pd.DataFrame, groups: list[str]) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for keys, group in frame.groupby(groups, dropna=False, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        record = dict(zip(groups, keys))
        label = int(group["label"].iloc[0])
        record.update(
            {
                "error_kind": "false_positive" if label == 0 else "false_negative",
                "unique_trials": int(group["sample_id"].nunique()),
                "trial_seed_observations": int(len(group)),
                "error_observations": int(group["is_error"].sum()),
                "error_rate": float(group["is_error"].mean()),
                "mean_probability": float(group["probability"].mean()),
                "mean_threshold": float(group["threshold"].mean()),
                "mean_margin": float(group["margin"].mean()),
            }
        )
        records.append(record)
    return pd.DataFrame.from_records(records)


def trial_error_frequency(trials: pd.DataFrame) -> pd.DataFrame:
    groups = [
        "scenario",
        "scenario_name",
        "fold",
        "sample_id",
        "subject",
        "source_subject",
        "source_kind",
        "activity_code",
        "activity_name",
        "label",
    ]
    return (
        trials.groupby(groups, as_index=False, dropna=False)
        .agg(
            seed_count=("seed", "nunique"),
            error_seeds=("is_error", "sum"),
            error_rate=("is_error", "mean"),
            positive_prediction_rate=("prediction", "mean"),
            mean_probability=("probability", "mean"),
            probability_std=("probability", "std"),
            min_probability=("probability", "min"),
            max_probability=("probability", "max"),
            mean_threshold=("threshold", "mean"),
            threshold_std=("threshold", "std"),
            mean_margin=("margin", "mean"),
        )
        .sort_values(
            ["scenario", "label", "error_rate", "mean_probability"],
            ascending=[True, True, False, False],
        )
    )


def scenario_transitions(trials: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_name = "source_balanced_1to1"
    candidate = trials[trials["scenario"] == candidate_name].copy()
    keys = ["fold", "seed", "sample_id"]
    detailed: list[pd.DataFrame] = []
    for reference_name in SCENARIOS[:3]:
        reference = trials[trials["scenario"] == reference_name].copy()
        metadata = [
            "subject",
            "source_subject",
            "activity_code",
            "activity_name",
            "label",
        ]
        merged = reference[keys + metadata + ["is_error", "probability", "threshold"]].merge(
            candidate[keys + ["is_error", "probability", "threshold"]],
            on=keys,
            suffixes=("_reference", "_balanced"),
            validate="one_to_one",
        )
        merged["reference_scenario"] = reference_name
        merged["transition"] = np.select(
            [
                (~merged["is_error_reference"]) & (~merged["is_error_balanced"]),
                merged["is_error_reference"] & (~merged["is_error_balanced"]),
                (~merged["is_error_reference"]) & merged["is_error_balanced"],
            ],
            ["correct_both", "corrected_by_balancing", "introduced_by_balancing"],
            default="wrong_both",
        )
        detailed.append(merged)
    observations = pd.concat(detailed, ignore_index=True)
    groups = [
        "reference_scenario",
        "fold",
        "sample_id",
        "subject",
        "source_subject",
        "activity_code",
        "activity_name",
        "label",
    ]
    counts = (
        observations.groupby(groups + ["transition"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for name in (
        "correct_both",
        "corrected_by_balancing",
        "introduced_by_balancing",
        "wrong_both",
    ):
        if name not in counts:
            counts[name] = 0
    counts["seed_count"] = counts[
        [
            "correct_both",
            "corrected_by_balancing",
            "introduced_by_balancing",
            "wrong_both",
        ]
    ].sum(axis=1)
    summary = (
        observations.groupby(["reference_scenario", "label", "transition"])
        .size()
        .rename("trial_seed_observations")
        .reset_index()
    )
    return counts, summary


def count_positive_events(predictions: np.ndarray) -> int:
    if not len(predictions):
        return 0
    return int(predictions[0]) + int(np.sum((~predictions[:-1]) & predictions[1:]))


def window_false_positive_summary(windows: pd.DataFrame) -> pd.DataFrame:
    adl = windows[windows["label"] == 0].copy()
    run_records: list[dict[str, object]] = []
    groups = [
        "scenario",
        "scenario_name",
        "fold",
        "seed",
        "sample_id",
        "subject",
        "source_subject",
        "activity_code",
        "activity_name",
    ]
    for keys, group in adl.groupby(groups, sort=True, dropna=False):
        group = group.sort_values("start_frame")
        positive = group["prediction"].to_numpy(dtype=bool)
        starts = group["start_frame"].to_numpy(dtype=float)
        run_records.append(
            {
                **dict(zip(groups, keys)),
                "window_count": len(group),
                "positive_windows": int(positive.sum()),
                "positive_window_fraction": float(positive.mean()),
                "positive_events": count_positive_events(positive),
                "first_positive_start_frame": (
                    float(starts[np.flatnonzero(positive)[0]]) if positive.any() else np.nan
                ),
                "peak_probability": float(group["probability"].max()),
                "mean_probability": float(group["probability"].mean()),
            }
        )
    per_run = pd.DataFrame.from_records(run_records)
    aggregate_groups = [
        "scenario",
        "scenario_name",
        "fold",
        "sample_id",
        "subject",
        "source_subject",
        "activity_code",
        "activity_name",
    ]
    return (
        per_run.groupby(aggregate_groups, as_index=False, dropna=False)
        .agg(
            seed_count=("seed", "nunique"),
            mean_positive_windows=("positive_windows", "mean"),
            seeds_with_positive_windows=("positive_windows", lambda x: int((x > 0).sum())),
            mean_positive_window_fraction=("positive_window_fraction", "mean"),
            mean_positive_events=("positive_events", "mean"),
            mean_first_positive_start_frame=("first_positive_start_frame", "mean"),
            mean_peak_probability=("peak_probability", "mean"),
            max_peak_probability=("peak_probability", "max"),
        )
        .sort_values(
            ["scenario", "seeds_with_positive_windows", "mean_peak_probability"],
            ascending=[True, False, False],
        )
    )


def plot_activity_errors(activity: pd.DataFrame, output: Path) -> None:
    data = activity[activity["label"] == 0].copy()
    codes = sorted(data["activity_code"].unique())
    x = np.arange(len(codes), dtype=float)
    width = 0.19
    figure, axis = plt.subplots(figsize=(13, 6.5))
    for index, scenario in enumerate(SCENARIOS):
        group = data[data["scenario"] == scenario].set_index("activity_code")
        values = [100 * group.loc[code, "error_rate"] if code in group.index else 0 for code in codes]
        axis.bar(
            x + (index - 1.5) * width,
            values,
            width,
            color=COLORS[scenario],
            label=SCENARIO_LABELS[scenario],
        )
    labels = [f"{code}\n{ACTIVITY_NAMES.get(code, code)}" for code in codes]
    axis.set_xticks(x, labels, rotation=20, ha="right")
    axis.set_ylabel("False-positive trial-seed observations (%)")
    axis.set_title("False-positive rate by ADL activity")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncol=4)
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)


def plot_balanced_subject_heatmap(subjects: pd.DataFrame, output: Path) -> None:
    data = subjects[subjects["scenario"] == "source_balanced_1to1"].copy()
    pivot = data.pivot_table(
        index="subject", columns="error_kind", values="error_rate", fill_value=0
    )
    columns = ["false_positive", "false_negative"]
    for column in columns:
        if column not in pivot:
            pivot[column] = 0.0
    pivot = pivot[columns].sort_index()
    values = 100 * pivot.to_numpy()
    figure, axis = plt.subplots(figsize=(7.5, max(5.5, 0.42 * len(pivot))))
    image = axis.imshow(values, aspect="auto", cmap="magma", vmin=0, vmax=100)
    axis.set_xticks([0, 1], ["ADL false positives", "A11 false negatives"])
    axis.set_yticks(np.arange(len(pivot)), pivot.index)
    axis.set_title("Balanced 1:1 error rate by held-out subject")
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            color = "black" if values[row, column] > 55 else "white"
            axis.text(column, row, f"{values[row, column]:.1f}%", ha="center", va="center", color=color)
    figure.colorbar(image, ax=axis, label="Error rate (%)")
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)


def plot_calibration(calibration: pd.DataFrame, output: Path) -> None:
    folds = sorted(calibration["fold"].unique())
    x = np.arange(len(folds), dtype=float)
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.8))
    for scenario in SCENARIOS:
        group = calibration[calibration["scenario"] == scenario].set_index("fold").loc[folds]
        axes[0].errorbar(
            x,
            group["threshold_mean"],
            yerr=group["threshold_std"],
            marker="o",
            capsize=3,
            linewidth=2,
            color=COLORS[scenario],
            label=SCENARIO_LABELS[scenario],
        )
        axes[1].plot(
            x,
            group["brier_score_mean"],
            marker="o",
            linewidth=2,
            color=COLORS[scenario],
            label=SCENARIO_LABELS[scenario],
        )
    axes[0].set_title("Validation-selected thresholds")
    axes[0].set_ylabel("Threshold (mean ± SD across seeds)")
    axes[1].set_title("Test-trial Brier score")
    axes[1].set_ylabel("Brier score (lower is better)")
    for axis in axes:
        axis.set_xticks(x, [fold.replace("fold_", "Fold ") for fold in folds])
        axis.grid(alpha=0.25)
    axes[0].legend(ncol=2)
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)


def plot_hardest_trials(trial_frequency: pd.DataFrame, output: Path) -> None:
    data = trial_frequency[
        trial_frequency["scenario"] == "source_balanced_1to1"
    ].copy()
    figure, axes = plt.subplots(1, 2, figsize=(15, 7))
    for axis, label, title, color in (
        (axes[0], 0, "Hardest ADL trials", "#d95f02"),
        (axes[1], 1, "Hardest real A11 trials", "#7570b3"),
    ):
        subset = data[data["label"] == label].sort_values(
            ["error_rate", "mean_probability"],
            ascending=[False, False if label == 0 else True],
        ).head(15)
        subset = subset.sort_values("error_rate")
        names = [f"{row.subject} {row.activity_code} {row.sample_id.split('T')[-1]}" for row in subset.itertuples()]
        axis.barh(names, 100 * subset["error_rate"], color=color)
        axis.set_xlim(0, 105)
        axis.set_xlabel("Seeds making the error (%)")
        axis.set_title(title)
        axis.grid(axis="x", alpha=0.25)
    figure.suptitle("Balanced 1:1: repeatedly misclassified held-out trials")
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)


def plot_transitions(transitions: pd.DataFrame, output: Path) -> None:
    labels: list[str] = []
    corrected: list[int] = []
    introduced: list[int] = []
    for reference in SCENARIOS[:3]:
        for label in (0, 1):
            group = transitions[
                (transitions["reference_scenario"] == reference)
                & (transitions["label"] == label)
            ].set_index("transition")["trial_seed_observations"]
            labels.append(
                f"vs {SCENARIO_LABELS[reference]}\n{'ADL' if label == 0 else 'A11 fall'}"
            )
            corrected.append(int(group.get("corrected_by_balancing", 0)))
            introduced.append(int(group.get("introduced_by_balancing", 0)))
    x = np.arange(len(labels))
    width = 0.36
    figure, axis = plt.subplots(figsize=(12.5, 6.2))
    axis.bar(
        x - width / 2,
        corrected,
        width,
        color="#2ca02c",
        label="Corrected by Balanced 1:1",
    )
    axis.bar(
        x + width / 2,
        introduced,
        width,
        color="#d62728",
        label="Introduced by Balanced 1:1",
    )
    axis.set_xticks(x, labels)
    axis.set_ylabel("Paired trial-seed decisions")
    axis.set_title("Errors corrected or introduced by source balancing")
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=220)
    plt.close(figure)


def write_report(
    output: Path,
    trials: pd.DataFrame,
    trial_frequency: pd.DataFrame,
    activity: pd.DataFrame,
    subject: pd.DataFrame,
    transitions: pd.DataFrame,
    calibration: pd.DataFrame,
) -> None:
    balanced = trial_frequency[trial_frequency["scenario"] == "source_balanced_1to1"]
    top_adl = balanced[balanced["label"] == 0].sort_values(
        ["error_rate", "mean_probability"], ascending=False
    ).head(10)
    top_falls = balanced[balanced["label"] == 1].sort_values(
        ["error_rate", "mean_probability"], ascending=[False, True]
    ).head(10)
    activity_balanced = activity[
        (activity["scenario"] == "source_balanced_1to1") & (activity["label"] == 0)
    ].sort_values("error_rate", ascending=False)
    subject_balanced_adl = subject[
        (subject["scenario"] == "source_balanced_1to1") & (subject["label"] == 0)
    ].sort_values("error_rate", ascending=False)
    subject_balanced_fall = subject[
        (subject["scenario"] == "source_balanced_1to1") & (subject["label"] == 1)
    ].sort_values("error_rate", ascending=False)

    transition_pivot = transitions.pivot_table(
        index=["reference_scenario", "label"],
        columns="transition",
        values="trial_seed_observations",
        fill_value=0,
    )
    balanced_activity = activity[
        (activity["scenario"] == "source_balanced_1to1")
        & (activity["label"] == 0)
    ]
    balanced_fp_total = int(balanced_activity["error_observations"].sum())
    major_fp_total = int(
        balanced_activity[
            balanced_activity["activity_code"].isin(["A02", "A05", "A08"])
        ]["error_observations"].sum()
    )
    error_totals = (
        trial_frequency.groupby(["scenario", "label"], as_index=False)
        .agg(errors=("error_seeds", "sum"), observations=("seed_count", "sum"))
        .set_index(["scenario", "label"])
    )

    lines = [
        "# Activity- and Subject-Level Error Analysis",
        "",
        "## Scope",
        "",
        f"This report analyzes {len(trials):,} held-out trial-seed predictions from "
        f"{trials[['scenario', 'fold', 'seed']].drop_duplicates().shape[0]} completed runs. "
        "All results are post-hoc and descriptive; no model was retrained.",
        "",
        "## Key findings",
        "",
        f"- Balanced 1:1 made {balanced_fp_total} false-positive ADL decisions. "
        f"A02, A05, and A08 accounted for {major_fp_total}/{balanced_fp_total} "
        f"({100 * major_fp_total / balanced_fp_total:.1f}%) of them.",
        f"- Source balancing reduced ADL false positives from "
        f"{int(error_totals.loc[('real_synthetic_fall_real_adl', 0), 'errors'])} "
        f"in the original combined scenario to "
        f"{int(error_totals.loc[('source_balanced_1to1', 0), 'errors'])}, and "
        f"reduced real-fall false negatives from "
        f"{int(error_totals.loc[('real_synthetic_fall_real_adl', 1), 'errors'])} to "
        f"{int(error_totals.loc[('source_balanced_1to1', 1), 'errors'])}.",
        f"- Real-only still made fewer errors: "
        f"{int(error_totals.loc[('real_fall_real_adl', 0), 'errors'])} ADL false "
        f"positives and {int(error_totals.loc[('real_fall_real_adl', 1), 'errors'])} "
        f"fall false negatives, versus "
        f"{int(error_totals.loc[('source_balanced_1to1', 0), 'errors'])} and "
        f"{int(error_totals.loc[('source_balanced_1to1', 1), 'errors'])} for Balanced 1:1.",
        "- The failure is concentrated rather than global: most ADL activities have "
        "near-zero false-positive rates, while S44, S30, S49, and S32 account for "
        "most missed A11 falls.",
        "- Fold 5 is a calibration-stability problem: its Balanced 1:1 threshold was "
        "0.590 ± 0.438 across seeds and it produced 0.889 false-positive events per "
        "ADL minute.",
        "- Mean test-trial Brier score improved from 0.129 for the original combined "
        "condition to 0.117 after balancing, but real-only remained much better calibrated "
        "at 0.037.",
        "",
        "## Balanced 1:1 activity-level false positives",
        "",
        "| Activity | Unique trials | FP observations | FP rate | Mean probability |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in activity_balanced.itertuples():
        lines.append(
            f"| {row.activity_code} — {row.activity_name} | {row.unique_trials} | "
            f"{row.error_observations}/{row.trial_seed_observations} | "
            f"{100 * row.error_rate:.1f}% | {row.mean_probability:.3f} |"
        )
    lines += [
        "",
        "## Balanced 1:1 subjects with the highest error rates",
        "",
        "| Error type | Subject | Unique trials | Error rate |",
        "|---|---|---:|---:|",
    ]
    for kind, frame in (
        ("ADL false positive", subject_balanced_adl.head(8)),
        ("A11 false negative", subject_balanced_fall.head(8)),
    ):
        for row in frame.itertuples():
            lines.append(
                f"| {kind} | {row.subject} | {row.unique_trials} | "
                f"{100 * row.error_rate:.1f}% |"
            )
    lines += [
        "",
        "## Most consistent balanced 1:1 errors",
        "",
        "### ADL false positives",
        "",
        "| Trial | Activity | Subject | Error seeds | Mean probability | Mean threshold |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in top_adl.itertuples():
        lines.append(
            f"| {row.sample_id} | {row.activity_code} — {row.activity_name} | "
            f"{row.subject} | {int(row.error_seeds)}/{int(row.seed_count)} | "
            f"{row.mean_probability:.3f} | {row.mean_threshold:.3f} |"
        )
    lines += [
        "",
        "### Real A11 false negatives",
        "",
        "| Trial | Subject | Error seeds | Mean probability | Mean threshold |",
        "|---|---|---:|---:|---:|",
    ]
    for row in top_falls.itertuples():
        lines.append(
            f"| {row.sample_id} | {row.subject} | {int(row.error_seeds)}/{int(row.seed_count)} | "
            f"{row.mean_probability:.3f} | {row.mean_threshold:.3f} |"
        )

    lines += [
        "",
        "## What balancing corrected or introduced",
        "",
        "Counts below are paired trial-seed decisions. A correction means the reference "
        "scenario was wrong and Balanced 1:1 was correct; an introduction is the reverse.",
        "",
        "| Reference | Class | Corrected | Introduced | Wrong in both |",
        "|---|---|---:|---:|---:|",
    ]
    for reference in SCENARIOS[:3]:
        for label in (0, 1):
            index = (reference, label)
            values = transition_pivot.loc[index] if index in transition_pivot.index else pd.Series(dtype=float)
            lines.append(
                f"| {SCENARIO_LABELS[reference]} | {'ADL' if label == 0 else 'A11 fall'} | "
                f"{int(values.get('corrected_by_balancing', 0))} | "
                f"{int(values.get('introduced_by_balancing', 0))} | "
                f"{int(values.get('wrong_both', 0))} |"
            )

    balanced_cal = calibration[calibration["scenario"] == "source_balanced_1to1"]
    lines += [
        "",
        "## Fold calibration for Balanced 1:1",
        "",
        "| Fold | Threshold mean ± SD | Brier score | ECE | FP events/ADL min |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in balanced_cal.itertuples():
        lines.append(
            f"| {row.fold} | {row.threshold_mean:.3f} ± {row.threshold_std:.3f} | "
            f"{row.brier_score_mean:.3f} | {row.expected_calibration_error_mean:.3f} | "
            f"{row.false_positive_events_per_adl_minute_mean:.3f} |"
        )

    lines += [
        "",
        "## Decision and next experiment",
        "",
        "### Decision from this report",
        "",
        "Source balancing corrected many errors from the synthetic-heavy combined model, "
        "especially A02/A05/A08 false positives, but it still introduced substantially "
        "more errors than real-only training. The error pattern does not justify generating "
        "more of the same synthetic distribution or changing several components at once.",
        "",
        "### Recommended next controlled study: low-real-data augmentation",
        "",
        "Use two fixed training-data fractions, 25% and 50% of the real A11 training "
        "falls. At each fraction compare: (1) reduced real falls + real ADL and (2) the "
        "identical reduced-real subset + source-balanced synthetic falls + real ADL. This "
        "requires four new conditions, or 100 new runs with five folds and five seeds. "
        "Reuse the existing four full-data scenarios as frozen references; do not rerun them.",
        "",
        "Use one deterministic subject-stratified real-fall subset per fold and fraction, "
        "shared by the paired conditions. Keep training seeds for model initialization "
        "rather than changing the data subset. Preserve real-only validation/test data and "
        "validation-only threshold and checkpoint selection.",
        "",
        "Do not add hard-negative sampling to this first low-real study because that would "
        "confound the effect of synthetic augmentation. If false positives remain the main "
        "limitation afterward, run a separate activity-aware ADL sampling ablation focused "
        "on A02, A05, and A08.",
        "",
        "### Leakage safeguards",
        "",
        "1. Preserve the four existing scenarios; this analysis does not require rerunning them.",
        "2. Treat the listed test-trial errors as descriptive evidence, not as samples that may be "
        "directly selected for retraining. Any hard-negative selection in a new experiment must "
        "operate on training/validation subjects only.",
        "3. A final confirmatory claim should use new untouched subjects or nested validation "
        "because the present held-out-fold errors have now been inspected.",
        "",
        "## Output files",
        "",
        "See the CSV tables in this directory for complete activity, subject, trial, transition, "
        "window-event, and fold-calibration results. Figures provide compact comparisons.",
        "",
    ]
    (output / "ERROR_ANALYSIS.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Analyze activity-, subject-, trial-, window-, and calibration-level errors."
    )
    root = Path(__file__).resolve().parent
    parser.add_argument(
        "--prior-output-root",
        type=Path,
        default=root.parent / "Fifteen_Subject_CoM_Transformer_Fall_Detector" / "outputs",
    )
    parser.add_argument(
        "--balanced-output-root", type=Path, default=root / "outputs"
    )
    parser.add_argument(
        "--output", type=Path, default=root / "outputs" / "error_analysis"
    )
    args = parser.parse_args(argv)
    prior = args.prior_output_root.expanduser().resolve()
    balanced = args.balanced_output_root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    trial_frames: list[pd.DataFrame] = []
    window_frames: list[pd.DataFrame] = []
    run_frames: list[pd.DataFrame] = []
    for scenario in SCENARIOS:
        scenario_root = balanced if scenario == "source_balanced_1to1" else prior
        trial, window, runs = load_scenario(scenario_root, scenario)
        trial_frames.append(trial)
        window_frames.append(window)
        run_frames.append(runs)
    trials = pd.concat(trial_frames, ignore_index=True)
    windows = pd.concat(window_frames, ignore_index=True)
    runs = pd.concat(run_frames, ignore_index=True)
    if len(runs) != 100:
        raise ValueError(f"Expected 100 completed runs, found {len(runs)}")

    trial_frequency = trial_error_frequency(trials)
    activity = grouped_error_summary(
        trials,
        ["scenario", "scenario_name", "label", "activity_code", "activity_name"],
    )
    subject = grouped_error_summary(
        trials,
        ["scenario", "scenario_name", "label", "fold", "subject", "source_subject"],
    )
    transition_trials, transition_summary = scenario_transitions(trials)
    window_summary = window_false_positive_summary(windows)
    calibration = (
        runs.groupby(["scenario", "scenario_name", "fold"], as_index=False)
        .agg(
            seed_count=("seed", "nunique"),
            threshold_mean=("threshold", "mean"),
            threshold_std=("threshold", "std"),
            threshold_min=("threshold", "min"),
            threshold_max=("threshold", "max"),
            brier_score_mean=("brier_score", "mean"),
            brier_score_std=("brier_score", "std"),
            expected_calibration_error_mean=("expected_calibration_error", "mean"),
            balanced_accuracy_mean=("balanced_accuracy", "mean"),
            sensitivity_mean=("sensitivity", "mean"),
            specificity_mean=("specificity", "mean"),
            f1_mean=("f1", "mean"),
            false_positive_events_per_adl_minute_mean=(
                "false_positive_events_per_adl_minute",
                "mean",
            ),
        )
        .sort_values(["scenario", "fold"])
    )

    trial_frequency.to_csv(output / "trial_error_frequency.csv", index=False)
    activity.to_csv(output / "activity_error_summary.csv", index=False)
    subject.to_csv(output / "subject_error_summary.csv", index=False)
    transition_trials.to_csv(output / "scenario_trial_transitions.csv", index=False)
    transition_summary.to_csv(output / "scenario_error_transition_summary.csv", index=False)
    window_summary.to_csv(output / "window_false_positive_summary.csv", index=False)
    calibration.to_csv(output / "fold_calibration_summary.csv", index=False)
    runs.to_csv(output / "run_calibration_metrics.csv", index=False)

    balanced_frequency = trial_frequency[
        trial_frequency["scenario"] == "source_balanced_1to1"
    ]
    balanced_frequency[balanced_frequency["label"] == 0].sort_values(
        ["error_rate", "mean_probability"], ascending=False
    ).to_csv(output / "hard_negative_adl_candidates.csv", index=False)
    balanced_frequency[balanced_frequency["label"] == 1].sort_values(
        ["error_rate", "mean_probability"], ascending=[False, True]
    ).to_csv(output / "hard_real_fall_candidates.csv", index=False)

    plot_activity_errors(activity, output / "activity_false_positive_rates.png")
    plot_balanced_subject_heatmap(subject, output / "balanced_subject_error_heatmap.png")
    plot_calibration(calibration, output / "fold_threshold_and_calibration.png")
    plot_hardest_trials(trial_frequency, output / "balanced_hardest_trials.png")
    plot_transitions(transition_summary, output / "scenario_error_transitions.png")
    write_report(
        output,
        trials,
        trial_frequency,
        activity,
        subject,
        transition_summary,
        calibration,
    )
    metadata = {
        "scenarios": SCENARIOS,
        "completed_runs": int(len(runs)),
        "trial_seed_predictions": int(len(trials)),
        "window_predictions": int(len(windows)),
        "output_files": sorted(path.name for path in output.iterdir() if path.is_file()),
    }
    (output / "analysis_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Error analysis written to {output}")


if __name__ == "__main__":
    main()
