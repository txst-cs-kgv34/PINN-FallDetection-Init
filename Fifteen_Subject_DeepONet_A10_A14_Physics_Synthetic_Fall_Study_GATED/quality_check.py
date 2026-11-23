#!/usr/bin/env python3
"""Apply activity-aware GATE checks to A10-A13 and A14 synthetic trajectories."""

from __future__ import annotations

import argparse
import csv
import itertools
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from quality_metrics import (
    boundary_continuity_metrics,
    boundary_metric_names,
    direction_consistent,
    forecast_trajectory,
    kinematic_distance_metric_names,
    pair_distances,
    percentile_threshold,
)
from study_core import (
    GROUPS,
    HERE,
    dump_json,
    load_physics_core,
    load_study_config,
    read_json,
    resolve_from,
    resolve_physics_dir,
    write_csv,
)


SHAPE_METRICS = ("normalized_rmse", "dtw_normalized")
PHYSICS_METRICS = {
    "planar": ("angular_scaled_rmse", "horizontal_scaled_rmse"),
    "rotation": ("angular_scaled_rmse", "horizontal_scaled_rmse", "yaw_residual_rmse"),
}


def record_trajectory(record, group: str, context_region_s: float):
    return forecast_trajectory(
        record.time_s,
        record.theta_rad,
        record.x_m,
        record.valid_mask,
        context_region_s,
        record.yaw_rad if group == "rotation" else None,
    )


def metric_kwargs(experiment: dict[str, Any], group: str, settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase_points": int(settings["phase_normalized_points"]),
        "theta_scale_rad": float(experiment["model"]["theta_scale_rad"]),
        "x_scale_m": float(experiment["model"]["x_scale_m"]),
        "yaw_scale_rad": (
            float(experiment["model"]["yaw_scale_rad"]) if group == "rotation" else None
        ),
        "smoothing_window": int(settings["savgol_window_samples"]),
        "polynomial_order": int(settings["savgol_polynomial_order"]),
    }


def build_real_references(
    group: str,
    records,
    experiment: dict[str, Any],
    folds: set[int],
    settings: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context = float(experiment["model"]["context_region_s"])
    kwargs = metric_kwargs(experiment, group, settings)
    pair_rows: list[dict[str, Any]] = []
    boundary_rows: list[dict[str, Any]] = []
    for fold_id in sorted(folds):
        fold = next(item for item in experiment["folds"] if int(item["id"]) == fold_id)
        train = set(map(str, fold["train"]))
        grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)
        for record in records:
            if record.subject in train:
                grouped[(record.subject, record.activity)].append(record)
                boundary_rows.append(
                    {
                        "model_group": group,
                        "fold": fold_id,
                        "activity": record.activity,
                        "subject": record.subject,
                        "trial": record.trial,
                        **boundary_continuity_metrics(
                            record.time_s,
                            record.theta_rad,
                            record.x_m,
                            record.valid_mask,
                            context,
                            record.yaw_rad if group == "rotation" else None,
                        ),
                    }
                )
        for (subject, activity), subject_records in sorted(grouped.items()):
            for first, second in itertools.combinations(
                sorted(subject_records, key=lambda item: item.trial), 2
            ):
                pair_rows.append(
                    {
                        "comparison_type": "real_real",
                        "model_group": group,
                        "fold": fold_id,
                        "activity": activity,
                        "subject": subject,
                        "first_trial": first.trial,
                        "second_trial": second.trial,
                        **pair_distances(
                            record_trajectory(first, group, context),
                            record_trajectory(second, group, context),
                            **kwargs,
                        ),
                    }
                )
    return pair_rows, boundary_rows


def load_synthetic_trajectory(data_file: Path, group: str, context: float):
    with np.load(data_file, allow_pickle=False) as data:
        trajectory = forecast_trajectory(
            data["time_s"],
            data["synthetic_theta_rad"],
            data["synthetic_x_m"],
            data["valid_mask"],
            context,
            data["synthetic_yaw_rad"] if group == "rotation" else None,
        )
        boundary = boundary_continuity_metrics(
            data["time_s"],
            data["synthetic_theta_rad"],
            data["synthetic_x_m"],
            data["valid_mask"],
            context,
            data["synthetic_yaw_rad"] if group == "rotation" else None,
        )
    return trajectory, boundary


def build_synthetic_rows(
    generation_root: Path,
    manifest: dict[str, Any],
    group_context: dict[str, tuple[Any, dict[str, Any]]],
    settings: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    record_maps = {
        group: {(record.subject, record.trial): record for record in records}
        for group, (records, _) in group_context.items()
    }
    rows: list[dict[str, Any]] = []
    cache: dict[str, Any] = {}
    for item in manifest["samples"]:
        group = str(item["model_group"])
        activity = str(item["activity"])
        fold_id = int(item["fold"])
        records, experiment = group_context[group]
        fold = next(value for value in experiment["folds"] if int(value["id"]) == fold_id)
        subject = str(item["source_subject"])
        trial = str(item["source_trial"])
        if subject not in set(map(str, fold["train"])):
            raise AssertionError(f"non-training source in quality input: {group}/{subject}")
        if subject in set(map(str, fold["test"])):
            raise AssertionError(f"test source in quality input: {group}/{subject}")
        validation = fold["validation"]
        validation_set = {validation} if isinstance(validation, str) else set(validation)
        if subject in validation_set:
            raise AssertionError(f"validation source in quality input: {group}/{subject}")
        source_record = record_maps[group].get((subject, trial))
        if source_record is None or source_record.activity != activity:
            raise ValueError(f"missing or mismatched source record for {group}/{subject}/{trial}")
        context = float(experiment["model"]["context_region_s"])
        synthetic, boundary = load_synthetic_trajectory(
            generation_root / str(item["data_file"]), group, context
        )
        source = record_trajectory(source_record, group, context)
        cache[str(item["synthetic_id"])] = synthetic
        distances = pair_distances(
            synthetic,
            source,
            **metric_kwargs(experiment, group, settings),
        )
        rows.append(
            {
                "comparison_type": "synthetic_real",
                "synthetic_id": str(item["synthetic_id"]),
                "model_group": group,
                "fold": fold_id,
                "activity": activity,
                "generator_rank": int(item["generator_rank"]),
                "seed_index": int(item["seed_index"]),
                "physics_weight": float(item["physics_weight"]),
                "source_subject": subject,
                "source_trial": trial,
                "trajectory_sha256": str(item["trajectory_sha256"]),
                "direction_consistent": direction_consistent(
                    synthetic,
                    source,
                    float(settings["direction_minimum_source_displacement_cm"]),
                ),
                **{
                    key: float(value)
                    for key, value in item.items()
                    if key.startswith("real_physics_") or key.startswith("synthetic_physics_")
                },
                **boundary,
                **distances,
            }
        )
    return rows, cache


def build_diversity_rows(
    rows: list[dict[str, Any]],
    cache: dict[str, Any],
    group_context: dict[str, tuple[Any, dict[str, Any]]],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["model_group"], row["fold"], row["source_subject"], row["source_trial"])].append(row)
    output = []
    for (group, fold, subject, trial), candidates in sorted(grouped.items()):
        experiment = group_context[group][1]
        for first, second in itertools.combinations(
            sorted(candidates, key=lambda value: value["generator_rank"]), 2
        ):
            output.append(
                {
                    "comparison_type": "synthetic_synthetic",
                    "model_group": group,
                    "fold": fold,
                    "activity": first["activity"],
                    "source_subject": subject,
                    "source_trial": trial,
                    "first_generator_rank": first["generator_rank"],
                    "second_generator_rank": second["generator_rank"],
                    **pair_distances(
                        cache[first["synthetic_id"]],
                        cache[second["synthetic_id"]],
                        **metric_kwargs(experiment, group, settings),
                    ),
                }
            )
    return output


def activity_thresholds(
    real_rows: list[dict[str, Any]],
    boundary_rows: list[dict[str, Any]],
    synthetic_rows: list[dict[str, Any]],
    settings: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[tuple[Any, ...], float]]:
    percentile = float(settings["real_real_percentile"])
    minimum = int(settings["minimum_real_real_pairs_per_activity_fold"])
    output: list[dict[str, Any]] = []
    lookup: dict[tuple[Any, ...], float] = {}
    groups = sorted({(row["model_group"], int(row["fold"]), row["activity"]) for row in synthetic_rows})
    for group, fold, activity in groups:
        real_selected = [
            row for row in real_rows
            if row["model_group"] == group and int(row["fold"]) == fold and row["activity"] == activity
        ]
        if len(real_selected) < minimum:
            raise ValueError(
                f"{group} fold {fold} {activity}: only {len(real_selected)} real-real pairs; need {minimum}"
            )
        metrics = list(SHAPE_METRICS) + list(kinematic_distance_metric_names(group))
        for metric in metrics:
            value = percentile_threshold([float(row[metric]) for row in real_selected], percentile)
            lookup[("distance", group, fold, activity, metric)] = value
            output.append(
                {
                    "threshold_type": "real_real",
                    "model_group": group,
                    "fold": fold,
                    "activity": activity,
                    "generator_rank": "all",
                    "metric": metric,
                    "reference_count": len(real_selected),
                    "percentile": percentile,
                    "threshold": value,
                    "used_in_gate": True,
                }
            )
        boundary_selected = [
            row for row in boundary_rows
            if row["model_group"] == group and int(row["fold"]) == fold and row["activity"] == activity
        ]
        for metric in boundary_metric_names(group):
            value = percentile_threshold([float(row[metric]) for row in boundary_selected], percentile)
            lookup[("boundary", group, fold, activity, metric)] = value
            output.append(
                {
                    "threshold_type": "real_boundary",
                    "model_group": group,
                    "fold": fold,
                    "activity": activity,
                    "generator_rank": "all",
                    "metric": metric,
                    "reference_count": len(boundary_selected),
                    "percentile": percentile,
                    "threshold": value,
                    "used_in_gate": True,
                }
            )
        ranks = sorted({int(row["generator_rank"]) for row in synthetic_rows if row["model_group"] == group and int(row["fold"]) == fold and row["activity"] == activity})
        for rank in ranks:
            rank_rows = [
                row for row in synthetic_rows
                if row["model_group"] == group and int(row["fold"]) == fold
                and row["activity"] == activity and int(row["generator_rank"]) == rank
            ]
            for metric in PHYSICS_METRICS[group]:
                source_field = f"real_physics_{metric}"
                value = percentile_threshold(
                    [float(row[source_field]) for row in rank_rows],
                    float(settings["physics_residual_percentile"]),
                )
                lookup[("physics", group, fold, activity, rank, metric)] = value
                output.append(
                    {
                        "threshold_type": "real_physics_residual",
                        "model_group": group,
                        "fold": fold,
                        "activity": activity,
                        "generator_rank": rank,
                        "metric": metric,
                        "reference_count": len(rank_rows),
                        "percentile": float(settings["physics_residual_percentile"]),
                        "threshold": value,
                        "used_in_gate": True,
                    }
                )
    return output, lookup


def apply_gate(
    rows: list[dict[str, Any]], lookup: dict[tuple[Any, ...], float], settings: dict[str, Any]
) -> list[dict[str, Any]]:
    digest_counts = Counter(str(row["trajectory_sha256"]) for row in rows)
    decisions = []
    for row in rows:
        group, fold, activity = row["model_group"], int(row["fold"]), row["activity"]
        rank = int(row["generator_rank"])
        boundary_flags = {
            metric: float(row[metric]) <= lookup[("boundary", group, fold, activity, metric)]
            for metric in boundary_metric_names(group)
        }
        shape_flags = {
            metric: float(row[metric]) <= lookup[("distance", group, fold, activity, metric)]
            for metric in SHAPE_METRICS
        }
        kinematic_metrics = kinematic_distance_metric_names(group)
        kinematic_flags = {
            metric: float(row[metric]) <= lookup[("distance", group, fold, activity, metric)]
            for metric in kinematic_metrics
        }
        physics_flags = {
            metric: float(row[f"synthetic_physics_{metric}"])
            <= lookup[("physics", group, fold, activity, rank, metric)]
            for metric in PHYSICS_METRICS[group]
        }
        kinematic_fraction = sum(kinematic_flags.values()) / len(kinematic_flags)
        duplicate_pass = not (
            bool(settings["reject_exact_duplicates"])
            and digest_counts[str(row["trajectory_sha256"])] > 1
        )
        finite = all(
            np.isfinite(float(row[key]))
            for key in list(SHAPE_METRICS)
            + list(kinematic_metrics)
            + list(boundary_metric_names(group))
            + [f"synthetic_physics_{metric}" for metric in PHYSICS_METRICS[group]]
        )
        continuity_pass = all(boundary_flags.values())
        shape_pass = all(shape_flags.values())
        physics_pass = all(physics_flags.values())
        kinematic_pass = kinematic_fraction >= float(settings["minimum_kinematic_pass_fraction"])
        overall = all(
            (
                finite,
                continuity_pass,
                shape_pass,
                kinematic_pass,
                bool(row["direction_consistent"]),
                physics_pass,
                duplicate_pass,
            )
        )
        decisions.append(
            {
                **row,
                "finite_metrics_pass": finite,
                "continuity_gate_pass": continuity_pass,
                "shape_gate_pass": shape_pass,
                "kinematic_gate_pass": kinematic_pass,
                "kinematic_metrics_passed": sum(kinematic_flags.values()),
                "kinematic_metrics_total": len(kinematic_flags),
                "kinematic_pass_fraction": kinematic_fraction,
                "physics_gate_pass": physics_pass,
                "physics_metrics_passed": sum(physics_flags.values()),
                "physics_metrics_total": len(physics_flags),
                "direction_gate_pass": bool(row["direction_consistent"]),
                "exact_duplicate_count": digest_counts[str(row["trajectory_sha256"])],
                "duplicate_gate_pass": duplicate_pass,
                "overall_quality_pass": overall,
            }
        )
    return decisions


def approved_manifest(
    generation_manifest: dict[str, Any], decisions: list[dict[str, Any]], output_dir: Path
) -> dict[str, Any]:
    decision_map = {row["synthetic_id"]: row for row in decisions}
    approved = []
    for sample in generation_manifest["samples"]:
        decision = decision_map[str(sample["synthetic_id"])]
        if decision["overall_quality_pass"]:
            approved.append(
                {
                    **sample,
                    "continuity_gate_pass": True,
                    "shape_gate_pass": True,
                    "kinematic_gate_pass": True,
                    "physics_gate_pass": True,
                    "direction_gate_pass": True,
                    "duplicate_gate_pass": True,
                    "overall_quality_pass": True,
                }
            )
    write_csv(output_dir / "final_approved_synthetic_manifest.csv", approved)
    payload = {
        "description": "GATE-approved A10-A14 conditional synthetic falls",
        "dataset_root_relative_to_manifest": "../synthetic_trajectories",
        "test_subjects_used": False,
        "validation_subjects_used_for_thresholds": False,
        "candidate_count": len(generation_manifest["samples"]),
        "approved_count": len(approved),
        "samples": approved,
    }
    dump_json(output_dir / "final_approved_synthetic_manifest.json", payload)
    return payload


def generator_summary(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        grouped[(row["model_group"], row["fold"], row["generator_rank"], row["seed_index"])].append(row)
    output = []
    for (group, fold, rank, seed), rows in sorted(grouped.items()):
        passed = sum(bool(row["overall_quality_pass"]) for row in rows)
        output.append(
            {
                "model_group": group,
                "fold": fold,
                "generator_rank": rank,
                "seed_index": seed,
                "trajectory_count": len(rows),
                "quality_pass_count": passed,
                "quality_pass_rate": passed / len(rows),
                "mean_normalized_rmse": float(np.mean([row["normalized_rmse"] for row in rows])),
                "mean_dtw_normalized": float(np.mean([row["dtw_normalized"] for row in rows])),
            }
        )
    return output


def activity_summary(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        grouped[(row["model_group"], row["activity"])].append(row)
    output = []
    for (group, activity), rows in sorted(grouped.items()):
        passed = sum(bool(row["overall_quality_pass"]) for row in rows)
        output.append(
            {
                "model_group": group,
                "activity": activity,
                "candidate_count": len(rows),
                "approved_count": passed,
                "approval_rate": passed / len(rows),
                "continuity_pass_rate": np.mean([row["continuity_gate_pass"] for row in rows]),
                "shape_pass_rate": np.mean([row["shape_gate_pass"] for row in rows]),
                "kinematic_pass_rate": np.mean([row["kinematic_gate_pass"] for row in rows]),
                "physics_pass_rate": np.mean([row["physics_gate_pass"] for row in rows]),
                "direction_pass_rate": np.mean([row["direction_gate_pass"] for row in rows]),
            }
        )
    return output


def plot_distance_comparison(
    real_rows: list[dict[str, Any]], synthetic_rows: list[dict[str, Any]], path: Path
) -> None:
    panels = (("normalized_rmse", "Normalized RMSE"), ("dtw_normalized", "Normalized DTW"))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for axis, (metric, label) in zip(axes, panels):
        boxes = axis.boxplot(
            [[float(row[metric]) for row in real_rows], [float(row[metric]) for row in synthetic_rows]],
            tick_labels=["Real-real", "Synthetic-real"],
            patch_artist=True,
            showfliers=True,
        )
        boxes["boxes"][0].set_facecolor("#7A9E9F")
        boxes["boxes"][1].set_facecolor("#3B78A4")
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Activity-aware training-subject trajectory distances")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_pass_rates(summary: list[dict[str, Any]], path: Path) -> None:
    labels = [f"{row['activity']}" for row in summary]
    rates = [100.0 * float(row["approval_rate"]) for row in summary]
    colors = ["#3B78A4" if row["model_group"] == "planar" else "#A35D29" for row in summary]
    fig, axis = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
    bars = axis.bar(range(len(rates)), rates, color=colors)
    axis.set_xticks(range(len(labels)), labels)
    axis.set_ylim(0.0, 105.0)
    axis.set_ylabel("GATE approval rate (%)")
    axis.set_title("Synthetic trajectory approval by activity")
    axis.grid(axis="y", alpha=0.25)
    for bar, rate in zip(bars, rates):
        axis.text(bar.get_x() + bar.get_width() / 2, min(102.0, rate + 2.0), f"{rate:.1f}%", ha="center", fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(
    path: Path,
    decisions: list[dict[str, Any]],
    activity_rows: list[dict[str, Any]],
    generator_rows: list[dict[str, Any]],
    settings: dict[str, Any],
) -> None:
    total = len(decisions)
    passed = sum(bool(row["overall_quality_pass"]) for row in decisions)
    lines = [
        "# A10-A14 synthetic trajectory GATE report",
        "",
        "## Protocol",
        "",
        "- A10-A13 use the unified activity-specific direct-CartPole model; A14 uses the separate rotation-physics model.",
        "- The two generators in each fold were selected only by validation forecast MSE.",
        "- Contexts and all thresholds use training subjects only.",
        "- Real-real, boundary, and kinematic thresholds are activity- and fold-specific p95 values.",
        "- Physics thresholds are generator-, activity-, and fold-specific p95 values from real training trajectories.",
        "- Complete approval requires continuity, shape, kinematic, direction, physics-residual, and exact-duplicate gates.",
        f"- Kinematic gate requires at least {100 * float(settings['minimum_kinematic_pass_fraction']):.0f}% of metrics.",
        "",
        "## Counts",
        "",
        f"- Candidates: {total}",
        f"- Approved: {passed}/{total} ({100.0 * passed / max(1, total):.1f}%)",
        "",
        "## Activity summary",
        "",
        "| Activity | Candidates | Approved | Approval | Continuity | Shape | Kinematic | Physics | Direction |",
        "|:--|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for row in activity_rows:
        lines.append(
            f"| {row['activity']} | {row['candidate_count']} | {row['approved_count']} | "
            f"{100*row['approval_rate']:.1f}% | {100*row['continuity_pass_rate']:.1f}% | "
            f"{100*row['shape_pass_rate']:.1f}% | {100*row['kinematic_pass_rate']:.1f}% | "
            f"{100*row['physics_pass_rate']:.1f}% | {100*row['direction_pass_rate']:.1f}% |"
        )
    lines.extend(
        [
            "",
            "## Generator summary",
            "",
            "| Group | Fold | Rank | Seed | Candidates | Approved | Rate |",
            "|:--|--:|--:|--:|--:|--:|--:|",
        ]
    )
    for row in generator_rows:
        lines.append(
            f"| {row['model_group']} | {row['fold']} | {row['generator_rank']} | {row['seed_index']} | "
            f"{row['trajectory_count']} | {row['quality_pass_count']} | {100*row['quality_pass_rate']:.1f}% |"
        )
    lines.extend(
        [
            "",
            "Only files listed in `final_approved_synthetic_manifest.json` may enter detector-data preparation.",
            "Passing GATE establishes consistency with training-data quality envelopes; downstream detector utility must still be tested on unseen real subjects.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_quality(
    config_file: Path,
    config: dict[str, Any],
    generation_manifest_file: Path,
    output_dir: Path,
    planar_dir: Path | None,
    rotation_dir: Path | None,
) -> dict[str, Any]:
    settings = dict(config["quality"])
    generation_manifest = read_json(generation_manifest_file)
    if bool(generation_manifest.get("held_out_contexts_used", True)):
        raise ValueError("generation manifest does not certify training-only contexts")
    group_context: dict[str, tuple[Any, dict[str, Any]]] = {}
    real_rows: list[dict[str, Any]] = []
    boundary_rows: list[dict[str, Any]] = []
    for group, override in (("planar", planar_dir), ("rotation", rotation_dir)):
        physics_dir = resolve_physics_dir(config_file, config, group, override)
        core = load_physics_core(physics_dir, group)
        experiment = core.load_config(physics_dir / "experiment.json")
        records = core.load_real_records(str(config["generation"]["prepared_data_mode"]), group)
        group_context[group] = (records, experiment)
        folds = {int(row["fold"]) for row in generation_manifest["samples"] if row["model_group"] == group}
        group_real, group_boundary = build_real_references(group, records, experiment, folds, settings)
        real_rows.extend(group_real)
        boundary_rows.extend(group_boundary)
    synthetic_rows, cache = build_synthetic_rows(
        generation_manifest_file.parent,
        generation_manifest,
        group_context,
        settings,
    )
    diversity_rows = build_diversity_rows(synthetic_rows, cache, group_context, settings)
    threshold_rows, lookup = activity_thresholds(real_rows, boundary_rows, synthetic_rows, settings)
    decisions = apply_gate(synthetic_rows, lookup, settings)
    generators = generator_summary(decisions)
    activities = activity_summary(decisions)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "real_real_distances.csv", real_rows)
    write_csv(output_dir / "real_boundary_reference.csv", boundary_rows)
    write_csv(output_dir / "synthetic_real_distances.csv", synthetic_rows)
    write_csv(output_dir / "selected_generator_diversity.csv", diversity_rows)
    write_csv(output_dir / "quality_thresholds.csv", threshold_rows)
    write_csv(output_dir / "quality_decisions.csv", decisions)
    write_csv(output_dir / "generator_quality_summary.csv", generators)
    write_csv(output_dir / "activity_quality_summary.csv", activities)
    approved = approved_manifest(generation_manifest, decisions, output_dir)
    plot_distance_comparison(real_rows, synthetic_rows, output_dir / "real_real_vs_synthetic_real.png")
    plot_pass_rates(activities, output_dir / "activity_quality_pass_rates.png")
    write_report(output_dir / "QUALITY_REPORT.md", decisions, activities, generators, settings)
    payload = {
        "protocol": {
            "test_subjects_used": False,
            "validation_subjects_used_for_thresholds": False,
            "top_two_selected_by_validation_only": True,
            "activity_and_fold_specific_quality_thresholds": True,
            "physics_residual_gate": True,
            "rotation_yaw_gate": True,
            "threshold_percentile": float(settings["real_real_percentile"]),
        },
        "counts": {
            "real_real_pairs": len(real_rows),
            "real_boundary_trajectories": len(boundary_rows),
            "synthetic_real_pairs": len(synthetic_rows),
            "synthetic_synthetic_pairs": len(diversity_rows),
            "quality_pass": approved["approved_count"],
        },
        "activity_summary": activities,
        "generator_summary": generators,
    }
    dump_json(output_dir / "quality_summary.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "study_config.json")
    parser.add_argument("--generation-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--planar-dir", type=Path)
    parser.add_argument("--rotation-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_file, config = load_study_config(args.config)
    generation_root = resolve_from(config_file, str(config["generation_output_directory"]))
    manifest = (
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
        config_file,
        config,
        manifest,
        output_dir,
        args.planar_dir,
        args.rotation_dir,
    )
    print(
        f"GATE approved {payload['counts']['quality_pass']}/"
        f"{payload['counts']['synthetic_real_pairs']} trajectories."
    )
    print(f"Outputs: {output_dir}")


if __name__ == "__main__":
    main()

