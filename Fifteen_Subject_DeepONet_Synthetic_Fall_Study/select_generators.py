#!/usr/bin/env python3
"""Select full-fall Physics DeepONet generators without using test performance.

The only ranking value is ``best_validation_value`` from each run's
``training_selection.json``. Test error fields in ``summary.json`` are never
read or used for ranking, qualification, or tie-breaking.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
EXPECTED_SELECTION_METRIC = "real validation-subject forecast normalized MSE"
SEED_PATTERN = re.compile(r"seed_(\d+)_(\d+)$")
FOLD_PATTERN = re.compile(r"fold_(\d+)$")


@dataclass(frozen=True)
class Candidate:
    fold: int
    seed_index: int
    base_optimization_seed: int
    effective_fold_seed: int
    validation_subject: str
    train_subjects: tuple[str, ...]
    test_subjects: tuple[str, ...]
    best_epoch: int
    best_validation_normalized_mse: float
    selection_metric: str
    checkpoint: Path
    training_selection_file: Path
    summary_file: Path


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Missing required file: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def resolve_config_path(config_file: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = config_file.parent / path
    return path.resolve()


def load_candidate(seed_dir: Path, fold_dir: Path) -> Candidate:
    seed_match = SEED_PATTERN.fullmatch(seed_dir.name)
    fold_match = FOLD_PATTERN.fullmatch(fold_dir.name)
    if seed_match is None or fold_match is None:
        raise ValueError(f"Unexpected result directory layout: {fold_dir}")

    path_seed_index = int(seed_match.group(1))
    path_base_seed = int(seed_match.group(2))
    path_fold = int(fold_match.group(1))
    selection_file = fold_dir / "training_selection.json"
    summary_file = fold_dir / "summary.json"
    checkpoint = fold_dir / "final_best_model_state.pt"
    selection = read_json(selection_file)
    summary = read_json(summary_file)

    # Explicit allow-list: no test error or test performance field is accessed.
    fold = int(summary["fold"])
    seed_index = int(summary["seed_index"])
    base_seed = int(summary["base_optimization_seed"])
    effective_seed = int(summary["effective_fold_seed"])
    validation_subject = str(summary["validation_subject"])
    train_subjects = tuple(map(str, summary["train_subjects"]))
    test_subjects = tuple(map(str, summary["test_subjects"]))
    best_epoch = int(selection["best_epoch"])
    best_value = float(selection["best_validation_value"])
    selection_metric = str(selection["selection_metric"])

    if (fold, seed_index, base_seed) != (path_fold, path_seed_index, path_base_seed):
        raise ValueError(
            f"Path/metadata mismatch in {fold_dir}: path says fold={path_fold}, "
            f"seed_index={path_seed_index}, base_seed={path_base_seed}; summary says "
            f"fold={fold}, seed_index={seed_index}, base_seed={base_seed}"
        )
    if selection_metric != EXPECTED_SELECTION_METRIC:
        raise ValueError(
            f"Unexpected selection metric in {selection_file}: {selection_metric!r}"
        )
    if bool(selection.get("test_subject_used_for_selection", True)):
        raise ValueError(f"Test-subject leakage flag is true in {selection_file}")
    if not bool(summary.get("checkpoint_selected_only_on_real_validation_subject", False)):
        raise ValueError(f"Checkpoint selection is not validation-only in {summary_file}")
    if not bool(summary.get("physics_loss_enabled", False)):
        raise ValueError(f"Expected a Physics model in {summary_file}")
    if str(selection.get("training_regime")) != "direct_physics":
        raise ValueError(f"Unexpected training regime in {selection_file}")
    if not math.isfinite(best_value) or best_value < 0.0:
        raise ValueError(f"Invalid validation loss {best_value!r} in {selection_file}")
    if best_epoch < 1:
        raise ValueError(f"Invalid best epoch {best_epoch} in {selection_file}")
    if not checkpoint.is_file() or checkpoint.stat().st_size == 0:
        raise ValueError(f"Missing or empty selected checkpoint: {checkpoint}")

    train_set = set(train_subjects)
    test_set = set(test_subjects)
    if validation_subject in train_set or validation_subject in test_set:
        raise ValueError(f"Validation subject overlaps train/test in {summary_file}")
    if train_set & test_set:
        raise ValueError(f"Train/test overlap in {summary_file}")
    if len(train_subjects) != 11 or len(test_subjects) != 3:
        raise ValueError(
            f"Expected 11 train and 3 test subjects in {summary_file}; "
            f"found {len(train_subjects)} and {len(test_subjects)}"
        )

    return Candidate(
        fold=fold,
        seed_index=seed_index,
        base_optimization_seed=base_seed,
        effective_fold_seed=effective_seed,
        validation_subject=validation_subject,
        train_subjects=train_subjects,
        test_subjects=test_subjects,
        best_epoch=best_epoch,
        best_validation_normalized_mse=best_value,
        selection_metric=selection_metric,
        checkpoint=checkpoint.resolve(),
        training_selection_file=selection_file.resolve(),
        summary_file=summary_file.resolve(),
    )


def discover_candidates(results_dir: Path) -> list[Candidate]:
    if not results_dir.is_dir():
        raise ValueError(
            f"Full-results directory does not exist: {results_dir}\n"
            "Run the full five-seed Physics experiment first or pass --results-dir."
        )
    candidates: list[Candidate] = []
    for seed_dir in sorted(results_dir.glob("seed_*_*")):
        if not seed_dir.is_dir() or SEED_PATTERN.fullmatch(seed_dir.name) is None:
            continue
        for fold_dir in sorted(seed_dir.glob("fold_*")):
            if fold_dir.is_dir() and FOLD_PATTERN.fullmatch(fold_dir.name):
                candidates.append(load_candidate(seed_dir, fold_dir))
    if not candidates:
        raise ValueError(f"No fold/seed model runs found beneath {results_dir}")
    return candidates


def validate_protocol(
    candidates: list[Candidate], expected_folds: int, expected_seeds: int
) -> None:
    by_fold: dict[int, list[Candidate]] = {}
    for candidate in candidates:
        by_fold.setdefault(candidate.fold, []).append(candidate)

    expected_fold_ids = set(range(1, expected_folds + 1))
    if set(by_fold) != expected_fold_ids:
        raise ValueError(
            f"Expected folds {sorted(expected_fold_ids)}, found {sorted(by_fold)}"
        )
    expected_seed_indices = set(range(1, expected_seeds + 1))
    all_test_subjects: list[str] = []
    reference_seed_set: set[int] | None = None

    for fold, rows in sorted(by_fold.items()):
        seed_indices = {row.seed_index for row in rows}
        if len(rows) != expected_seeds or seed_indices != expected_seed_indices:
            raise ValueError(
                f"Fold {fold} must contain seed indices {sorted(expected_seed_indices)}; "
                f"found {sorted(seed_indices)} across {len(rows)} runs"
            )
        if reference_seed_set is None:
            reference_seed_set = seed_indices
        elif seed_indices != reference_seed_set:
            raise ValueError(f"Seed-index mismatch in fold {fold}")

        reference = rows[0]
        for row in rows[1:]:
            if (
                row.validation_subject != reference.validation_subject
                or row.train_subjects != reference.train_subjects
                or row.test_subjects != reference.test_subjects
            ):
                raise ValueError(f"Subject split changes across seeds in fold {fold}")
        all_test_subjects.extend(reference.test_subjects)

    if len(all_test_subjects) != len(set(all_test_subjects)):
        raise ValueError("A subject appears as a test subject in more than one fold")
    if len(set(all_test_subjects)) != expected_folds * 3:
        raise ValueError(
            f"Expected {expected_folds * 3} unique test subjects, "
            f"found {len(set(all_test_subjects))}"
        )


def rank_candidates(
    candidates: list[Candidate], top_k: int
) -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    rows: list[dict[str, Any]] = []
    by_fold: dict[int, list[Candidate]] = {}
    for candidate in candidates:
        by_fold.setdefault(candidate.fold, []).append(candidate)
    for fold, fold_candidates in sorted(by_fold.items()):
        if top_k > len(fold_candidates):
            raise ValueError(
                f"top_k={top_k} exceeds the {len(fold_candidates)} candidates in fold {fold}"
            )
        ordered = sorted(
            fold_candidates,
            key=lambda item: (
                item.best_validation_normalized_mse,
                item.seed_index,
            ),
        )
        for rank, candidate in enumerate(ordered, start=1):
            rows.append(
                {
                    "fold": candidate.fold,
                    "validation_subject": candidate.validation_subject,
                    "rank_within_fold": rank,
                    "selected": rank <= top_k,
                    "seed_index": candidate.seed_index,
                    "base_optimization_seed": candidate.base_optimization_seed,
                    "effective_fold_seed": candidate.effective_fold_seed,
                    "best_epoch": candidate.best_epoch,
                    "best_validation_normalized_mse": candidate.best_validation_normalized_mse,
                    "selection_metric": candidate.selection_metric,
                    "train_subjects": list(candidate.train_subjects),
                    "test_subjects": list(candidate.test_subjects),
                    "source_checkpoint": str(candidate.checkpoint),
                    "source_training_selection": str(candidate.training_selection_file),
                    "source_summary": str(candidate.summary_file),
                }
            )
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            flat["train_subjects"] = ";".join(row["train_subjects"])
            flat["test_subjects"] = ";".join(row["test_subjects"])
            writer.writerow(flat)


def materialize_selected(
    selected_rows: list[dict[str, Any]], output_dir: Path, overwrite: bool
) -> list[dict[str, Any]]:
    destination_root = output_dir / "selected_generators"
    if destination_root.exists():
        if not overwrite:
            raise ValueError(
                f"{destination_root} already exists; pass --overwrite to replace it"
            )
        if destination_root.parent.resolve() != output_dir.resolve():
            raise ValueError("Refusing to remove an unexpected selected-generator path")
        shutil.rmtree(destination_root)
    destination_root.mkdir(parents=True)

    manifests: list[dict[str, Any]] = []
    for row in selected_rows:
        folder = destination_root / f"fold_{row['fold']:02d}" / (
            f"rank_{row['rank_within_fold']:02d}_seed_{row['seed_index']:02d}_"
            f"{row['base_optimization_seed']}"
        )
        folder.mkdir(parents=True)
        source_checkpoint = Path(row["source_checkpoint"])
        copied_checkpoint = folder / "final_best_model_state.pt"
        shutil.copy2(source_checkpoint, copied_checkpoint)
        shutil.copy2(row["source_training_selection"], folder / "training_selection.json")

        checkpoint_hash = sha256(copied_checkpoint)
        if checkpoint_hash != sha256(source_checkpoint):
            raise IOError(f"Checkpoint hash mismatch after copying {source_checkpoint}")
        manifest = {
            **row,
            "materialized_checkpoint": str(copied_checkpoint.resolve()),
            "checkpoint_sha256": checkpoint_hash,
            "test_metrics_used_for_selection": False,
        }
        (folder / "generator_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        manifests.append(manifest)
    return manifests


def write_summary(path: Path, ranked: list[dict[str, Any]], top_k: int) -> None:
    selected = [row for row in ranked if row["selected"]]
    lines = [
        "# Validation-only generator selection",
        "",
        f"Selected the top {top_k} seed-specific checkpoints within each fold.",
        "Ranking used only `best_validation_value` from `training_selection.json`.",
        "No test error, test RMSE, or test-subject performance was used.",
        "",
        "| Fold | Validation subject | Rank | Seed index | Base seed | Best epoch | Validation normalized MSE |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in selected:
        lines.append(
            f"| {row['fold']} | {row['validation_subject']} | "
            f"{row['rank_within_fold']} | {row['seed_index']} | "
            f"{row['base_optimization_seed']} | {row['best_epoch']} | "
            f"{row['best_validation_normalized_mse']:.8f} |"
        )
    lines.extend(
        [
            "",
            "These checkpoints are candidate generators. Their generated trajectories must pass the predefined synthetic-data quality checks before downstream fall-detector training.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_selection(
    results_dir: Path,
    output_dir: Path,
    expected_folds: int,
    expected_seeds: int,
    top_k: int,
    copy_checkpoints: bool,
    overwrite: bool,
) -> dict[str, Any]:
    candidates = discover_candidates(results_dir.resolve())
    validate_protocol(candidates, expected_folds, expected_seeds)
    ranked = rank_candidates(candidates, top_k)
    selected = [row for row in ranked if row["selected"]]

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "all_generator_rankings.csv", ranked)
    write_csv(output_dir / "selected_generators.csv", selected)
    write_summary(output_dir / "SELECTION_SUMMARY.md", ranked, top_k)
    materialized = (
        materialize_selected(selected, output_dir, overwrite) if copy_checkpoints else []
    )
    payload = {
        "protocol": {
            "ranking_unit": "seed-specific checkpoint within each fold",
            "ranking_metric": EXPECTED_SELECTION_METRIC,
            "test_metrics_used_for_selection": False,
            "expected_folds": expected_folds,
            "expected_seeds_per_fold": expected_seeds,
            "top_k_per_fold": top_k,
        },
        "results_directory": str(results_dir.resolve()),
        "candidate_count": len(ranked),
        "selected_count": len(selected),
        "rankings": ranked,
        "materialized_generators": materialized,
    }
    (output_dir / "generator_selection.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "study_config.json")
    parser.add_argument("--physics-dir", type=Path)
    parser.add_argument("--results-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--expected-folds", type=int)
    parser.add_argument("--expected-seeds", type=int)
    parser.add_argument("--copy-checkpoints", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_file = args.config.expanduser().resolve()
    config = read_json(config_file)
    physics_dir = (
        args.physics_dir.expanduser().resolve()
        if args.physics_dir
        else resolve_config_path(config_file, str(config["physics_directory"]))
    )
    results_dir = (
        args.results_dir.expanduser().resolve()
        if args.results_dir
        else physics_dir / str(config["results_subdirectory"])
    )
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else resolve_config_path(config_file, str(config["output_directory"]))
    )
    payload = run_selection(
        results_dir=results_dir,
        output_dir=output_dir,
        expected_folds=(
            args.expected_folds
            if args.expected_folds is not None
            else int(config["expected_folds"])
        ),
        expected_seeds=(
            args.expected_seeds
            if args.expected_seeds is not None
            else int(config["expected_seeds_per_fold"])
        ),
        top_k=args.top_k if args.top_k is not None else int(config["top_k_per_fold"]),
        copy_checkpoints=args.copy_checkpoints,
        overwrite=args.overwrite,
    )
    print(
        f"Validated {payload['candidate_count']} fold/seed checkpoints and selected "
        f"{payload['selected_count']} validation-ranked generators."
    )
    print(f"Outputs: {output_dir}")


if __name__ == "__main__":
    main()
