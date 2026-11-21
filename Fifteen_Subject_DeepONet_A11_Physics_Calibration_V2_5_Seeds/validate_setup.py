#!/usr/bin/env python3
"""Validate A11 calibration inputs and the completed no-physics reference."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from calibration_core import baseline_root, candidate_weights, residual_scales
from operator_core import load_config, optimization_seeds, seed_spec


def as_bool(value: str) -> bool:
    return value.lower() in {"true", "1", "yes"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    args = parser.parse_args()
    config = load_config(args.config)
    root = Path(config["_root"])
    errors: list[str] = []
    dataset = (root / config["dataset_root"]).resolve()
    manifest_path = dataset / "manifests" / "trial_manifest.csv"
    rows: list[dict[str, str]] = []
    if not manifest_path.is_file():
        errors.append(f"missing dataset manifest: {manifest_path}")
    else:
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    selected = [
        row for row in rows
        if row["activity"] in config["data"]["activities"]
        and as_bool(row[config["data"]["selection_flag"]])
    ]
    if len(selected) != int(config["data"]["expected_trial_count"]):
        errors.append(f"expected 64 strict-primary A11 trials, found {len(selected)}")
    if Counter(row["activity"] for row in selected) != Counter({"A11": 64}):
        errors.append("calibration must contain only 64 A11 trials")
    subjects = set(config["subjects"])
    tested: list[str] = []
    for fold in config["folds"]:
        train = set(fold["train"])
        validation = {fold["validation"]}
        test = set(fold["test"])
        if train & validation or train & test or validation & test:
            errors.append(f"fold {fold['id']}: subject leakage")
        if train | validation | test != subjects:
            errors.append(f"fold {fold['id']}: roles do not cover subjects")
        tested.extend(fold["test"])
    if set(tested) != subjects or len(tested) != len(subjects):
        errors.append("every subject must appear exactly once as test")
    if optimization_seeds(config) != [20261101, 20261102, 20261103, 20261104, 20261105]:
        errors.append("optimization seeds changed")
    if candidate_weights(config, include_baseline=True) != [0.0, 0.0001, 0.001, 0.01]:
        errors.append("weight grid must be [0, 1e-4, 1e-3, 1e-2]")
    calibration = config["calibration"]
    if bool(calibration.get("test_access_before_selection", True)):
        errors.append("test access must be disabled before weight selection")
    if calibration.get("selection_metric") != "validation_forecast_mse":
        errors.append("weights must be selected by validation forecast MSE")
    if calibration.get("selection_tie_break") != "smaller_physics_weight":
        errors.append("selection ties must prefer the smaller physics weight")
    angular_scale, horizontal_scale = residual_scales(config)
    if not np.isclose(angular_scale, 9.81 / .57) or not np.isclose(horizontal_scale, 9.81):
        errors.append("unexpected residual nondimensionalization")
    baseline = baseline_root(config)
    baseline_config_path = baseline / "experiment.json"
    if not baseline_config_path.is_file():
        errors.append(f"missing baseline experiment: {baseline_config_path}")
        baseline_config = None
    else:
        baseline_config = json.loads(baseline_config_path.read_text(encoding="utf-8"))
        for key in ("subjects", "folds", "optimization_seeds", "data", "model", "physics"):
            if baseline_config.get(key) != config.get(key):
                errors.append(f"calibration and baseline differ in {key}")
    completed = 0
    if baseline_config is not None:
        for seed_index in range(1, 6):
            _, label = seed_spec(config, seed_index)
            for fold_id in range(1, 6):
                directory = baseline / "results" / "no_physics" / "full" / label / f"fold_{fold_id:02d}"
                required = (
                    directory / "final_best_model_state.pt",
                    directory / "training_selection.json",
                    directory / "summary.json",
                    directory / "test_metrics_by_trial.csv",
                )
                if all(path.is_file() for path in required):
                    completed += 1
                else:
                    errors.append(f"incomplete no-physics baseline fold: {directory}")
        for name in ("multi_seed_subject_metrics.csv", "multi_seed_trial_metrics.csv", "multi_seed_summary.json"):
            path = baseline / "results" / "no_physics" / "full" / name
            if not path.is_file():
                errors.append(f"missing baseline aggregate: {path}")
    for subject in subjects:
        audit = (root / config["audit_dir_template"].format(subject=subject)).resolve()
        if not audit.is_dir():
            errors.append(f"missing audit folder: {audit}")
    report = {
        "dataset": str(dataset),
        "a11_trials": len(selected),
        "candidate_weights": candidate_weights(config, include_baseline=True),
        "residual_scales": {"angular_g_over_l": angular_scale, "horizontal_g": horizontal_scale},
        "completed_no_physics_baseline_folds": completed,
        "baseline_root": str(baseline),
        "test_access_before_selection": False,
    }
    print(json.dumps(report, indent=2))
    if errors:
        print("\nSETUP ERRORS:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("\nSetup validation passed: 64 A11 trials, 25 reusable no-physics checkpoints, four validation-only weights, and leakage-free folds.")


if __name__ == "__main__":
    main()
