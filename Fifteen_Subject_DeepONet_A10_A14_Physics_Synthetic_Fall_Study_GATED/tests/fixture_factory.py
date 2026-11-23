from __future__ import annotations

import json
from pathlib import Path


SUBJECTS = [f"S{i:02d}" for i in range(1, 16)]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def fold(fold_id: int, validation_count: int) -> dict:
    start = (fold_id - 1) * 3
    test = SUBJECTS[start : start + 3]
    remaining = [subject for subject in SUBJECTS if subject not in test]
    validation = remaining[-validation_count:]
    train = remaining[:-validation_count]
    return {
        "id": fold_id,
        "train": train,
        "validation": validation if validation_count == 2 else validation[0],
        "test": test,
    }


def create_fixture(root: Path) -> tuple[Path, dict]:
    planar = root / "planar"
    rotation = root / "rotation"
    for directory in (planar, rotation):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "operator_core.py").write_text("# fixture\n", encoding="utf-8")
    planar_folds = [fold(index, 2) for index in range(1, 6)]
    rotation_folds = [fold(index, 1) for index in range(1, 6)]
    write_json(planar / "experiment.json", {"folds": planar_folds})
    write_json(
        rotation / "experiment.json",
        {"folds": rotation_folds, "training": {"rotation_physics_weight": 0.01}},
    )
    weights = (0.0001, 0.001, 0.01)
    for fold_row in planar_folds:
        for index, weight in enumerate(weights, start=1):
            directory = (
                planar
                / "results/candidates/full"
                / f"lambda_{weight:g}"
                / f"seed_{index:02d}_{1000+index}"
                / f"fold_{fold_row['id']:02d}"
            )
            directory.mkdir(parents=True)
            (directory / "final_best_model_state.pt").write_bytes(f"p-{weight}".encode())
            write_json(
                directory / "candidate_manifest.json",
                {
                    "target_physics_weight": weight,
                    "trained_from_scratch": True,
                    "test_data_accessed": False,
                    "activity_specific_controller_heads": ["A10", "A11", "A12", "A13"],
                    "fold": fold_row,
                    "seed_index": index,
                    "base_seed": 1000 + index,
                    "effective_seed": 2000 + index,
                    "initialization_sha256": f"hash-{fold_row['id']}",
                },
            )
            write_json(
                directory / "training_selection.json",
                {
                    "target_physics_weight": weight,
                    "test_data_accessed": False,
                    "checkpoint_selected_only_on_validation_subjects": True,
                    "best_epoch": 20 + index,
                    "best_validation_forecast_mse": float(4 - index),
                },
            )
    for fold_row in rotation_folds:
        for index in (1, 2):
            directory = rotation / "results/rotation/full" / f"seed_{index:02d}_{3000+index}" / f"fold_{fold_row['id']:02d}"
            directory.mkdir(parents=True)
            (directory / "final_best_model_state.pt").write_bytes(f"r-{index}".encode())
            write_json(
                directory / "fold_manifest.json",
                {
                    "model_group": "rotation",
                    "physics_enabled": True,
                    "fold": fold_row,
                    "seed_index": index,
                    "base_seed": 3000 + index,
                    "effective_seed": 4000 + index,
                },
            )
            write_json(
                directory / "training_selection.json",
                {
                    "selection_subject_only": True,
                    "best_epoch": 30 + index,
                    "best_validation_forecast_mse": float(3 - index),
                },
            )
            write_json(
                directory / "summary.json",
                {
                    "fold": fold_row["id"],
                    "seed_index": index,
                    "base_optimization_seed": 3000 + index,
                    "physics_loss_enabled": True,
                    "checkpoint_selected_only_on_validation_subject": True,
                },
            )
    config_file = root / "study_config.json"
    config = {
        "planar": {
            "physics_directory": str(planar),
            "results_subdirectory": "results/candidates/full",
            "activities": ["A10", "A11", "A12", "A13"],
            "expected_folds": 5,
            "expected_candidates_per_fold": 3,
            "top_k_per_fold": 2,
        },
        "rotation": {
            "physics_directory": str(rotation),
            "results_subdirectory": "results/rotation/full",
            "activities": ["A14"],
            "expected_folds": 5,
            "expected_candidates_per_fold": 2,
            "top_k_per_fold": 2,
        },
        "selection_output_directory": "outputs/selection",
    }
    write_json(config_file, config)
    return config_file, config

