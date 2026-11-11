#!/usr/bin/env python3
"""Compare synthetic-real distances with training-subject real-real variability."""

from __future__ import annotations

import argparse
import itertools
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from quality_metrics import forecast_trajectory, pair_distances, percentile_threshold
from study_core import (
    HERE,
    dump_json,
    load_physics_core,
    load_study_config,
    read_json,
    resolve_from,
    resolve_physics_dir,
    write_csv,
)


DISTANCE_METRICS = (
    "normalized_rmse",
    "dtw_normalized",
    "theta_rmse_deg",
    "x_rmse_cm",
    "duration_abs_difference_s",
    "theta_displacement_abs_difference_deg",
    "x_displacement_abs_difference_cm",
    "peak_abs_theta_velocity_abs_difference_deg_s",
    "peak_abs_x_velocity_abs_difference_cm_s",
    "peak_abs_theta_acceleration_abs_difference_deg_s2",
    "peak_abs_x_acceleration_abs_difference_cm_s2",
)


def record_trajectory(record, context_region_s: float):
    return forecast_trajectory(
        record.time_s,
        record.theta_rad,
        record.x_m,
        record.valid_mask,
        context_region_s,
    )


def metric_kwargs(experiment: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase_points": int(settings["phase_normalized_points"]),
        "theta_scale_rad": float(experiment["model"]["theta_scale_rad"]),
        "x_scale_m": float(experiment["model"]["x_scale_m"]),
        "smoothing_window": int(settings["savgol_window_samples"]),
        "polynomial_order": int(settings["savgol_polynomial_order"]),
    }


def build_real_real_rows(
    records,
    experiment: dict[str, Any],
    folds: list[int],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    context = float(experiment["model"]["context_region_s"])
    kwargs = metric_kwargs(experiment, settings)
    rows: list[dict[str, Any]] = []
    for fold_id in folds:
        fold = next(item for item in experiment["folds"] if int(item["id"]) == fold_id)
        train_subjects = set(map(str, fold["train"]))
        grouped: dict[str, list[Any]] = defaultdict(list)
        for record in records:
            if record.subject in train_subjects:
                grouped[record.subject].append(record)
        missing = train_subjects - set(grouped)
        if missing:
            raise ValueError(f"Fold {fold_id} lacks real records for {sorted(missing)}")
        for subject in sorted(grouped):
            subject_records = sorted(grouped[subject], key=lambda item: item.trial)
            for first, second in itertools.combinations(subject_records, 2):
                distances = pair_distances(
                    record_trajectory(first, context),
                    record_trajectory(second, context),
                    **kwargs,
                )
                rows.append(
                    {
                        "comparison_type": "real_real",
                        "fold": fold_id,
                        "subject": subject,
                        "first_trial": first.trial,
                        "second_trial": second.trial,
                        **distances,
                    }
                )
    return rows


def build_synthetic_real_rows(
    generation_root: Path,
    generation_manifest: dict[str, Any],
    records,
    experiment: dict[str, Any],
    settings: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    context = float(experiment["model"]["context_region_s"])
    kwargs = metric_kwargs(experiment, settings)
    record_map = {(record.subject, record.trial): record for record in records}
    rows: list[dict[str, Any]] = []
    synthetic_cache: dict[str, Any] = {}

    for item in generation_manifest["samples"]:
        fold_id = int(item["fold"])
        fold = next(
            fold for fold in experiment["folds"] if int(fold["id"]) == fold_id
        )
        subject = str(item["source_subject"])
        trial = str(item["source_trial"])
        if subject not in set(map(str, fold["train"])):
            raise AssertionError(
                f"Quality input uses non-training subject {subject} in fold {fold_id}"
            )
        if subject == str(fold["validation"]) or subject in set(map(str, fold["test"])):
            raise AssertionError(f"Held-out subject leaked into quality input: {subject}")
        real = record_map.get((subject, trial))
        if real is None:
            raise ValueError(f"Missing source real trajectory for {subject}/{trial}")
        data_file = generation_root / str(item["data_file"])
        if not data_file.is_file():
            raise ValueError(f"Missing synthetic trajectory: {data_file}")
        with np.load(data_file, allow_pickle=False) as data:
            synthetic = forecast_trajectory(
                data["time_s"],
                data["synthetic_theta_rad"],
                data["synthetic_x_m"],
                data["valid_mask"],
                context,
            )
        synthetic_cache[str(item["synthetic_id"])] = synthetic
        distances = pair_distances(
            synthetic,
            record_trajectory(real, context),
            **kwargs,
        )
        rows.append(
            {
                "comparison_type": "synthetic_real",
                "synthetic_id": str(item["synthetic_id"]),
                "fold": fold_id,
                "generator_rank": int(item["generator_rank"]),
                "seed_index": int(item["seed_index"]),
                "base_optimization_seed": int(item["base_optimization_seed"]),
                "validation_subject": str(item["validation_subject"]),
                "source_subject": subject,
                "source_trial": trial,
                "transition_jump_theta_deg": float(item["transition_jump_theta_deg"]),
                "transition_jump_x_cm": float(item["transition_jump_x_cm"]),
                **distances,
            }
        )
    return rows, synthetic_cache


def build_diversity_rows(
    synthetic_rows: list[dict[str, Any]],
    synthetic_cache: dict[str, Any],
    experiment: dict[str, Any],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    kwargs = metric_kwargs(experiment, settings)
    grouped: dict[tuple[int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in synthetic_rows:
        grouped[(row["fold"], row["source_subject"], row["source_trial"])].append(row)
    rows: list[dict[str, Any]] = []
    for (fold, subject, trial), candidates in sorted(grouped.items()):
        for first, second in itertools.combinations(
            sorted(candidates, key=lambda item: item["generator_rank"]), 2
        ):
            distances = pair_distances(
                synthetic_cache[first["synthetic_id"]],
                synthetic_cache[second["synthetic_id"]],
                **kwargs,
            )
            rows.append(
                {
                    "comparison_type": "synthetic_synthetic",
                    "fold": fold,
                    "source_subject": subject,
                    "source_trial": trial,
                    "first_generator_rank": first["generator_rank"],
                    "first_seed_index": first["seed_index"],
                    "second_generator_rank": second["generator_rank"],
                    "second_seed_index": second["seed_index"],
                    **distances,
                }
            )
    return rows


def thresholds_by_fold(
    real_real: list[dict[str, Any]],
    folds: list[int],
    percentile: float,
    minimum_pairs: int,
) -> tuple[list[dict[str, Any]], dict[tuple[int, str], float]]:
    rows: list[dict[str, Any]] = []
    lookup: dict[tuple[int, str], float] = {}
    for fold in folds:
        selected = [row for row in real_real if int(row["fold"]) == fold]
        if len(selected) < minimum_pairs:
            raise ValueError(
                f"Fold {fold} has only {len(selected)} real-real pairs; "
                f"at least {minimum_pairs} are required"
            )
        for metric in DISTANCE_METRICS:
            values = [float(row[metric]) for row in selected]
            threshold = percentile_threshold(values, percentile)
            lookup[(fold, metric)] = threshold
            rows.append(
                {
                    "fold": fold,
                    "reference": "within-subject training real-real pairs",
                    "pair_count": len(selected),
                    "percentile": percentile,
                    "metric": metric,
                    "threshold": threshold,
                    "used_in_automatic_gate": False,
                }
            )
    return rows, lookup


def apply_quality_gate(
    synthetic_rows: list[dict[str, Any]],
    thresholds: dict[tuple[int, str], float],
    shape_metrics: list[str],
    kinematic_metrics: list[str],
    minimum_kinematic_fraction: float,
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for row in synthetic_rows:
        fold = int(row["fold"])
        finite = all(np.isfinite(float(row[metric])) for metric in DISTANCE_METRICS)
        shape_flags = {
            metric: float(row[metric]) <= thresholds[(fold, metric)]
            for metric in shape_metrics
        }
        kinematic_flags = {
            metric: float(row[metric]) <= thresholds[(fold, metric)]
            for metric in kinematic_metrics
        }
        kinematic_fraction = float(
            sum(kinematic_flags.values()) / max(1, len(kinematic_flags))
        )
        shape_pass = bool(shape_flags) and all(shape_flags.values())
        overall = finite and shape_pass and (
            kinematic_fraction >= minimum_kinematic_fraction
        )
        decisions.append(
            {
                **row,
                "finite_trajectory_metrics": finite,
                "shape_gate_pass": shape_pass,
                "shape_metrics_passed": sum(shape_flags.values()),
                "shape_metrics_total": len(shape_flags),
                "kinematic_metrics_passed": sum(kinematic_flags.values()),
                "kinematic_metrics_total": len(kinematic_flags),
                "kinematic_pass_fraction": kinematic_fraction,
                "minimum_kinematic_pass_fraction": minimum_kinematic_fraction,
                "duration_used_in_gate": False,
                "overall_quality_pass": overall,
            }
        )
    return decisions


def generator_summary(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        grouped[(row["fold"], row["generator_rank"], row["seed_index"])].append(row)
    summary = []
    for (fold, rank, seed), rows in sorted(grouped.items()):
        passed = sum(bool(row["overall_quality_pass"]) for row in rows)
        summary.append(
            {
                "fold": fold,
                "generator_rank": rank,
                "seed_index": seed,
                "trajectory_count": len(rows),
                "quality_pass_count": passed,
                "quality_pass_rate": passed / len(rows),
                "mean_normalized_rmse": float(
                    np.mean([row["normalized_rmse"] for row in rows])
                ),
                "mean_dtw_normalized": float(
                    np.mean([row["dtw_normalized"] for row in rows])
                ),
                "mean_theta_rmse_deg": float(
                    np.mean([row["theta_rmse_deg"] for row in rows])
                ),
                "mean_x_rmse_cm": float(
                    np.mean([row["x_rmse_cm"] for row in rows])
                ),
            }
        )
    return summary


def plot_distance_comparison(
    real_real: list[dict[str, Any]],
    synthetic_real: list[dict[str, Any]],
    path: Path,
) -> None:
    panels = (
        ("normalized_rmse", "Normalized RMSE"),
        ("dtw_normalized", "Normalized DTW"),
        ("theta_rmse_deg", "Theta RMSE (°)"),
        ("x_rmse_cm", "CoM x RMSE (cm)"),
    )
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    for axis, (metric, label) in zip(axes.flat, panels):
        boxes = axis.boxplot(
            [
                [float(row[metric]) for row in real_real],
                [float(row[metric]) for row in synthetic_real],
            ],
            labels=["Real–real", "Synthetic–real"],
            patch_artist=True,
            showfliers=True,
        )
        boxes["boxes"][0].set_facecolor("#7A9E9F")
        boxes["boxes"][1].set_facecolor("#3B78A4")
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Training-subject trajectory distances")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_pass_rates(summary: list[dict[str, Any]], path: Path) -> None:
    labels = [
        f"F{row['fold']} R{row['generator_rank']}\nseed {row['seed_index']}"
        for row in summary
    ]
    rates = [100.0 * float(row["quality_pass_rate"]) for row in summary]
    fig, axis = plt.subplots(figsize=(12, 5), constrained_layout=True)
    bars = axis.bar(range(len(rates)), rates, color="#3B78A4")
    axis.set_xticks(range(len(labels)), labels)
    axis.set_ylim(0.0, 105.0)
    axis.set_ylabel("Quality pass rate (%)")
    axis.set_title("Conditional synthetic trajectories passing the predefined gate")
    axis.grid(axis="y", alpha=0.25)
    for bar, rate in zip(bars, rates):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            min(102.0, rate + 2.0),
            f"{rate:.1f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(
    path: Path,
    real_real: list[dict[str, Any]],
    synthetic_real: list[dict[str, Any]],
    summary: list[dict[str, Any]],
    percentile: float,
    minimum_kinematic_fraction: float,
) -> None:
    total = len(synthetic_real)
    passed = sum(int(row["quality_pass_count"]) for row in summary)
    lines = [
        "# Synthetic trajectory quality report",
        "",
        "## Protocol",
        "",
        "- Generator checkpoints were selected only by fold-specific validation-subject loss.",
        "- Synthetic contexts and real-real references use only each fold's 11 training subjects.",
        "- Real-real comparisons pair different trials from the same subject.",
        "- Shape comparisons use phase-normalized forecast trajectories.",
        "- Velocity and acceleration use identical Savitzky–Golay smoothing for real and synthetic signals.",
        f"- Per-fold acceptance thresholds are the {percentile:g}th percentiles of training real-real distances.",
        "- Shape gate: normalized RMSE and DTW must both remain within their reference thresholds.",
        f"- Kinematic gate: at least {100.0 * minimum_kinematic_fraction:.0f}% of displacement, velocity, and acceleration distances must remain within their thresholds.",
        "",
        "## Important duration limitation",
        "",
        "The model predicts theta and x but does not predict contact time. Each synthetic trajectory therefore inherits the apparent-contact endpoint and valid duration of its source context trial. Duration differences are reported for transparency but are excluded from automatic quality decisions.",
        "",
        "## Counts",
        "",
        f"- Real-real reference pairs: {len(real_real)}",
        f"- Synthetic-real comparisons: {total}",
        f"- Synthetic trajectories passing the complete gate: {passed}/{total} ({100.0 * passed / total:.1f}%)",
        "",
        "## Generator summary",
        "",
        "| Fold | Rank | Seed | Trajectories | Pass rate | Mean normalized RMSE | Mean DTW | Theta RMSE | x RMSE |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['fold']} | {row['generator_rank']} | {row['seed_index']} | "
            f"{row['trajectory_count']} | {100.0 * row['quality_pass_rate']:.1f}% | "
            f"{row['mean_normalized_rmse']:.4f} | {row['mean_dtw_normalized']:.4f} | "
            f"{row['mean_theta_rmse_deg']:.3f}° | {row['mean_x_rmse_cm']:.3f} cm |"
        )
    lines.extend(
        [
            "",
            "Passing this gate indicates that a conditional trajectory lies within the predefined training-subject real-real variability envelope. It does not by itself prove downstream fall-detection utility; that must be tested on unseen real subjects.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_quality(
    physics_dir: Path,
    generation_manifest_file: Path,
    output_dir: Path,
    settings: dict[str, Any],
) -> dict[str, Any]:
    core = load_physics_core(physics_dir)
    experiment = core.load_config(physics_dir / "experiment.json")
    records = core.load_real_records("full")
    generation_manifest = read_json(generation_manifest_file)
    if bool(generation_manifest.get("held_out_contexts_used", True)):
        raise ValueError("Generation manifest does not certify training-only contexts")
    folds = sorted({int(item["fold"]) for item in generation_manifest["samples"]})
    real_real = build_real_real_rows(records, experiment, folds, settings)
    synthetic_real, synthetic_cache = build_synthetic_real_rows(
        generation_manifest_file.parent,
        generation_manifest,
        records,
        experiment,
        settings,
    )
    diversity = build_diversity_rows(
        synthetic_real, synthetic_cache, experiment, settings
    )
    percentile = float(settings["real_real_percentile"])
    threshold_rows, threshold_lookup = thresholds_by_fold(
        real_real,
        folds,
        percentile,
        int(settings["minimum_real_real_pairs_per_fold"]),
    )
    gate_metrics = set(map(str, settings["shape_gate_metrics"])) | set(
        map(str, settings["kinematic_gate_metrics"])
    )
    for row in threshold_rows:
        row["used_in_automatic_gate"] = row["metric"] in gate_metrics
    decisions = apply_quality_gate(
        synthetic_real,
        threshold_lookup,
        list(map(str, settings["shape_gate_metrics"])),
        list(map(str, settings["kinematic_gate_metrics"])),
        float(settings["minimum_kinematic_pass_fraction"]),
    )
    summary = generator_summary(decisions)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "real_real_distances.csv", real_real)
    write_csv(output_dir / "synthetic_real_distances.csv", synthetic_real)
    if diversity:
        write_csv(output_dir / "selected_generator_diversity.csv", diversity)
    write_csv(output_dir / "quality_thresholds_by_fold.csv", threshold_rows)
    write_csv(output_dir / "quality_decisions.csv", decisions)
    write_csv(output_dir / "generator_quality_summary.csv", summary)
    plot_distance_comparison(
        real_real, synthetic_real, output_dir / "real_real_vs_synthetic_real.png"
    )
    plot_pass_rates(summary, output_dir / "generator_quality_pass_rates.png")
    write_report(
        output_dir / "QUALITY_REPORT.md",
        real_real,
        decisions,
        summary,
        percentile,
        float(settings["minimum_kinematic_pass_fraction"]),
    )
    payload = {
        "protocol": {
            "reference": "within-subject, training-trial real-real variability computed separately by fold",
            "test_subjects_used": False,
            "validation_subjects_used_for_thresholds": False,
            "threshold_percentile": percentile,
            "phase_normalized_points": int(settings["phase_normalized_points"]),
            "shape_gate_metrics": list(settings["shape_gate_metrics"]),
            "kinematic_gate_metrics": list(settings["kinematic_gate_metrics"]),
            "minimum_kinematic_pass_fraction": float(
                settings["minimum_kinematic_pass_fraction"]
            ),
            "duration_used_in_gate": False,
            "duration_limitation": "synthetic endpoint inherited from the source trial because the model does not predict contact time",
        },
        "counts": {
            "folds": len(folds),
            "real_real_pairs": len(real_real),
            "synthetic_real_pairs": len(synthetic_real),
            "synthetic_synthetic_diversity_pairs": len(diversity),
            "quality_pass": sum(
                bool(row["overall_quality_pass"]) for row in decisions
            ),
        },
        "generator_summary": summary,
    }
    dump_json(output_dir / "quality_summary.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "study_config.json")
    parser.add_argument("--physics-dir", type=Path)
    parser.add_argument("--generation-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_file, config = load_study_config(args.config)
    physics_dir = resolve_physics_dir(config_file, config, args.physics_dir)
    generation_root = resolve_from(
        config_file, str(config["generation_output_directory"])
    )
    generation_manifest = (
        args.generation_manifest.expanduser().resolve()
        if args.generation_manifest
        else generation_root / "synthetic_manifest.json"
    )
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else resolve_from(config_file, str(config["quality_output_directory"]))
    )
    payload = run_quality(
        physics_dir,
        generation_manifest,
        output_dir,
        dict(config["quality"]),
    )
    print(
        f"Compared {payload['counts']['synthetic_real_pairs']} synthetic-real pairs "
        f"with {payload['counts']['real_real_pairs']} training real-real pairs."
    )
    print(
        f"Quality gate passed: {payload['counts']['quality_pass']}/"
        f"{payload['counts']['synthetic_real_pairs']} trajectories."
    )
    print(f"Outputs: {output_dir}")


if __name__ == "__main__":
    main()
