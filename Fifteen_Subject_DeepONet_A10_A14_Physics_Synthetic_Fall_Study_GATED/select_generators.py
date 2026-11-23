#!/usr/bin/env python3
"""Select the top two direct-physics generators per fold using validation only."""

from __future__ import annotations

import argparse
import math
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from study_core import (
    GROUPS,
    HERE,
    dump_json,
    group_settings,
    load_study_config,
    normalized_validation_subjects,
    read_json,
    resolve_from,
    resolve_physics_dir,
    resolve_results_dir,
    sha256,
    validate_fold_split,
    write_csv,
)


SEED_PATTERN = re.compile(r"seed_(\d+)_(\d+)$")
FOLD_PATTERN = re.compile(r"fold_(\d+)$")


@dataclass(frozen=True)
class Candidate:
    model_group: str
    fold: int
    seed_index: int
    base_optimization_seed: int
    effective_fold_seed: int
    physics_weight: float
    validation_subjects: tuple[str, ...]
    train_subjects: tuple[str, ...]
    test_subjects: tuple[str, ...]
    best_epoch: int
    validation_forecast_mse: float
    selection_metric: str
    checkpoint: Path
    selection_file: Path
    metadata_file: Path
    initialization_sha256: str


def _common_checks(candidate: Candidate) -> None:
    if candidate.physics_weight <= 0.0:
        raise ValueError(f"non-physics candidate entered synthesis pool: {candidate.checkpoint}")
    if not math.isfinite(candidate.validation_forecast_mse) or candidate.validation_forecast_mse < 0.0:
        raise ValueError(f"invalid validation loss in {candidate.selection_file}")
    if candidate.best_epoch < 1:
        raise ValueError(f"invalid best epoch in {candidate.selection_file}")
    if not candidate.checkpoint.is_file() or candidate.checkpoint.stat().st_size == 0:
        raise ValueError(f"missing or empty checkpoint: {candidate.checkpoint}")
    train = set(candidate.train_subjects)
    validation = set(candidate.validation_subjects)
    test = set(candidate.test_subjects)
    if train & validation or train & test or validation & test:
        raise ValueError(f"subject leakage in {candidate.metadata_file}")


def load_planar_candidate(directory: Path, expected_activities: tuple[str, ...]) -> Candidate | None:
    manifest_file = directory / "candidate_manifest.json"
    selection_file = directory / "training_selection.json"
    manifest = read_json(manifest_file)
    selection = read_json(selection_file)
    weight = float(manifest["target_physics_weight"])
    if weight == 0.0:
        return None
    if weight < 0.0:
        raise ValueError(f"negative physics weight in {manifest_file}")
    if not bool(manifest.get("trained_from_scratch", False)):
        raise ValueError(f"candidate was not trained from scratch: {manifest_file}")
    if bool(manifest.get("test_data_accessed", True)):
        raise ValueError(f"test data were accessed during planar training: {manifest_file}")
    if tuple(manifest.get("activity_specific_controller_heads", ())) != expected_activities:
        raise ValueError(f"planar candidate does not contain all activity heads: {manifest_file}")
    if float(selection["target_physics_weight"]) != weight:
        raise ValueError(f"weight mismatch between manifest and selection: {directory}")
    if bool(selection.get("test_data_accessed", True)):
        raise ValueError(f"test data were accessed during selection: {selection_file}")
    if not bool(selection.get("checkpoint_selected_only_on_validation_subjects", False)):
        raise ValueError(f"checkpoint was not selected on validation subjects: {selection_file}")
    fold = dict(manifest["fold"])
    validate_fold_split(fold)
    candidate = Candidate(
        model_group="planar",
        fold=int(fold["id"]),
        seed_index=int(manifest["seed_index"]),
        base_optimization_seed=int(manifest["base_seed"]),
        effective_fold_seed=int(manifest["effective_seed"]),
        physics_weight=weight,
        validation_subjects=normalized_validation_subjects(fold),
        train_subjects=tuple(map(str, fold["train"])),
        test_subjects=tuple(map(str, fold["test"])),
        best_epoch=int(selection["best_epoch"]),
        validation_forecast_mse=float(selection["best_validation_forecast_mse"]),
        selection_metric="validation_subject_activity_balanced_forecast_mse",
        checkpoint=(directory / "final_best_model_state.pt").resolve(),
        selection_file=selection_file.resolve(),
        metadata_file=manifest_file.resolve(),
        initialization_sha256=str(manifest["initialization_sha256"]),
    )
    _common_checks(candidate)
    return candidate


def discover_planar(results_dir: Path, activities: tuple[str, ...]) -> list[Candidate]:
    rows: list[Candidate] = []
    for directory in sorted(results_dir.glob("lambda_*/seed_*_*/fold_*")):
        if not directory.is_dir():
            continue
        candidate = load_planar_candidate(directory, activities)
        if candidate is not None:
            rows.append(candidate)
    return rows


def load_rotation_candidate(directory: Path, experiment: dict[str, Any]) -> Candidate:
    manifest_file = directory / "fold_manifest.json"
    selection_file = directory / "training_selection.json"
    summary_file = directory / "summary.json"
    manifest = read_json(manifest_file)
    selection = read_json(selection_file)
    summary = read_json(summary_file)
    if str(manifest.get("model_group")) != "rotation":
        raise ValueError(f"expected rotation model in {manifest_file}")
    if not bool(manifest.get("physics_enabled", False)) or not bool(summary.get("physics_loss_enabled", False)):
        raise ValueError(f"rotation physics is not enabled in {directory}")
    if not bool(selection.get("selection_subject_only", False)):
        raise ValueError(f"rotation checkpoint was not validation-selected: {selection_file}")
    if not bool(summary.get("checkpoint_selected_only_on_validation_subject", False)):
        raise ValueError(f"rotation summary is not validation-only: {summary_file}")
    fold = dict(manifest["fold"])
    validate_fold_split(fold)
    candidate = Candidate(
        model_group="rotation",
        fold=int(fold["id"]),
        seed_index=int(manifest["seed_index"]),
        base_optimization_seed=int(manifest["base_seed"]),
        effective_fold_seed=int(manifest["effective_seed"]),
        physics_weight=float(experiment["training"]["rotation_physics_weight"]),
        validation_subjects=normalized_validation_subjects(fold),
        train_subjects=tuple(map(str, fold["train"])),
        test_subjects=tuple(map(str, fold["test"])),
        best_epoch=int(selection["best_epoch"]),
        validation_forecast_mse=float(selection["best_validation_forecast_mse"]),
        selection_metric="validation_forecast_mse",
        checkpoint=(directory / "final_best_model_state.pt").resolve(),
        selection_file=selection_file.resolve(),
        metadata_file=manifest_file.resolve(),
        initialization_sha256="not_recorded_in_original_a14_run",
    )
    if (
        candidate.fold != int(summary["fold"])
        or candidate.seed_index != int(summary["seed_index"])
        or candidate.base_optimization_seed != int(summary["base_optimization_seed"])
    ):
        raise ValueError(f"rotation path/summary mismatch in {directory}")
    _common_checks(candidate)
    return candidate


def discover_rotation(results_dir: Path, experiment: dict[str, Any]) -> list[Candidate]:
    rows: list[Candidate] = []
    for directory in sorted(results_dir.glob("seed_*_*/fold_*")):
        if directory.is_dir():
            rows.append(load_rotation_candidate(directory, experiment))
    return rows


def validate_protocol(
    candidates: list[Candidate], model_group: str, expected_folds: int, expected_per_fold: int
) -> None:
    by_fold: dict[int, list[Candidate]] = {}
    for candidate in candidates:
        by_fold.setdefault(candidate.fold, []).append(candidate)
    expected_ids = set(range(1, expected_folds + 1))
    if set(by_fold) != expected_ids:
        raise ValueError(f"{model_group}: expected folds {sorted(expected_ids)}, found {sorted(by_fold)}")
    all_tests: list[str] = []
    for fold_id, rows in sorted(by_fold.items()):
        if len(rows) != expected_per_fold:
            raise ValueError(
                f"{model_group} fold {fold_id}: expected {expected_per_fold} eligible candidates, found {len(rows)}"
            )
        reference = rows[0]
        for row in rows[1:]:
            if (
                row.train_subjects != reference.train_subjects
                or row.validation_subjects != reference.validation_subjects
                or row.test_subjects != reference.test_subjects
            ):
                raise ValueError(f"{model_group}: subject split changes across candidates in fold {fold_id}")
        all_tests.extend(reference.test_subjects)
    if len(all_tests) != len(set(all_tests)):
        raise ValueError(f"{model_group}: a test subject appears in more than one fold")


def rank_candidates(candidates: list[Candidate], top_k: int) -> list[dict[str, Any]]:
    by_fold: dict[int, list[Candidate]] = {}
    for candidate in candidates:
        by_fold.setdefault(candidate.fold, []).append(candidate)
    rows: list[dict[str, Any]] = []
    for fold_id, candidates_in_fold in sorted(by_fold.items()):
        ordered = sorted(
            candidates_in_fold,
            key=lambda item: (
                item.validation_forecast_mse,
                item.physics_weight,
                item.seed_index,
            ),
        )
        if top_k < 1 or top_k > len(ordered):
            raise ValueError(f"invalid top_k={top_k} for fold {fold_id}")
        for rank, candidate in enumerate(ordered, start=1):
            raw = asdict(candidate)
            raw.update(
                {
                    "rank_within_fold": rank,
                    "selected": rank <= top_k,
                    "checkpoint": str(candidate.checkpoint),
                    "selection_file": str(candidate.selection_file),
                    "metadata_file": str(candidate.metadata_file),
                    "validation_subjects": list(candidate.validation_subjects),
                    "train_subjects": list(candidate.train_subjects),
                    "test_subjects": list(candidate.test_subjects),
                    "test_metrics_used_for_selection": False,
                }
            )
            rows.append(raw)
    return rows


def _csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        flat = dict(row)
        for key in ("validation_subjects", "train_subjects", "test_subjects"):
            flat[key] = ";".join(map(str, row[key]))
        output.append(flat)
    return output


def materialize(rows: list[dict[str, Any]], output_dir: Path, overwrite: bool) -> list[dict[str, Any]]:
    destination_root = output_dir / "selected_generators"
    if destination_root.exists():
        if not overwrite:
            raise ValueError(f"{destination_root} exists; pass --overwrite")
        shutil.rmtree(destination_root)
    manifests = []
    for row in rows:
        folder = destination_root / str(row["model_group"]) / f"fold_{int(row['fold']):02d}" / (
            f"rank_{int(row['rank_within_fold']):02d}_seed_{int(row['seed_index']):02d}_"
            f"lambda_{float(row['physics_weight']):g}"
        )
        folder.mkdir(parents=True, exist_ok=True)
        source = Path(str(row["checkpoint"]))
        copied = folder / "final_best_model_state.pt"
        shutil.copy2(source, copied)
        shutil.copy2(str(row["selection_file"]), folder / "training_selection.json")
        shutil.copy2(str(row["metadata_file"]), folder / Path(str(row["metadata_file"])).name)
        digest = sha256(copied)
        if digest != sha256(source):
            raise IOError(f"checkpoint hash mismatch after copying {source}")
        manifest = {
            **row,
            "materialized_checkpoint": str(copied.resolve()),
            "checkpoint_sha256": digest,
        }
        dump_json(folder / "generator_manifest.json", manifest)
        manifests.append(manifest)
    return manifests


def write_summary(path: Path, groups: dict[str, dict[str, Any]]) -> None:
    lines = [
        "# Validation-only top-two generator selection",
        "",
        "Only direct-physics checkpoints are eligible. No held-out test metric is read or used.",
        "",
        "| Group | Fold | Validation subjects | Rank | Seed | Physics weight | Validation MSE |",
        "|:--|--:|:--|--:|--:|--:|--:|",
    ]
    for group in GROUPS:
        for row in groups[group]["selected"]:
            lines.append(
                f"| {group} | {row['fold']} | {', '.join(row['validation_subjects'])} | "
                f"{row['rank_within_fold']} | {row['seed_index']} | {row['physics_weight']:.4g} | "
                f"{row['validation_forecast_mse']:.8f} |"
            )
    lines.extend(
        [
            "",
            "Planar candidates are ranked among the 15 nonzero-lambda A10-A13 V2 candidates in each fold.",
            "Rotation candidates are ranked among the five direct-physics A14 seeds in each fold.",
            "Generated trajectories must pass the GATE quality pipeline before detector use.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_selection(
    config_file: Path,
    config: dict[str, Any],
    output_dir: Path,
    planar_dir: Path | None,
    rotation_dir: Path | None,
    copy_checkpoints: bool,
    overwrite: bool,
) -> dict[str, Any]:
    overrides = {"planar": planar_dir, "rotation": rotation_dir}
    group_payloads: dict[str, dict[str, Any]] = {}
    all_selected: list[dict[str, Any]] = []
    for group in GROUPS:
        settings = group_settings(config, group)
        physics_dir = resolve_physics_dir(config_file, config, group, overrides[group])
        results_dir = resolve_results_dir(physics_dir, config, group)
        experiment = read_json(physics_dir / "experiment.json")
        if group == "planar":
            candidates = discover_planar(results_dir, tuple(settings["activities"]))
        else:
            candidates = discover_rotation(results_dir, experiment)
        validate_protocol(
            candidates,
            group,
            int(settings["expected_folds"]),
            int(settings["expected_candidates_per_fold"]),
        )
        ranked = rank_candidates(candidates, int(settings["top_k_per_fold"]))
        selected = [row for row in ranked if bool(row["selected"])]
        write_csv(output_dir / group / "all_generator_rankings.csv", _csv_rows(ranked))
        write_csv(output_dir / group / "selected_generators.csv", _csv_rows(selected))
        group_payloads[group] = {
            "physics_directory": str(physics_dir),
            "results_directory": str(results_dir),
            "candidate_count": len(ranked),
            "selected_count": len(selected),
            "rankings": ranked,
            "selected": selected,
        }
        all_selected.extend(selected)
    materialized = materialize(all_selected, output_dir, overwrite) if copy_checkpoints else []
    payload = {
        "protocol": {
            "ranking_metric": "validation forecast MSE within the same fold",
            "test_metrics_used_for_selection": False,
            "planar_eligible_pool": "all-head nonzero-physics V2 candidates",
            "rotation_eligible_pool": "direct-physics A14 seed models",
            "top_k_per_group_fold": 2,
        },
        "groups": group_payloads,
        "materialized_generators": materialized,
        "selected_count": len(all_selected),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_json(output_dir / "generator_selection.json", payload)
    write_summary(output_dir / "SELECTION_SUMMARY.md", group_payloads)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "study_config.json")
    parser.add_argument("--planar-dir", type=Path)
    parser.add_argument("--rotation-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--copy-checkpoints", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_file, config = load_study_config(args.config)
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else resolve_from(config_file, str(config["selection_output_directory"]))
    )
    payload = run_selection(
        config_file,
        config,
        output_dir,
        args.planar_dir,
        args.rotation_dir,
        args.copy_checkpoints,
        args.overwrite,
    )
    print(f"Selected {payload['selected_count']} validation-ranked direct-physics generators.")
    print(f"Outputs: {output_dir}")


if __name__ == "__main__":
    main()

