#!/usr/bin/env python3
"""Validate matched from-scratch A11 calibration inputs and protocol."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from calibration_core import candidate_weights, residual_scales
from operator_core import load_config, optimization_seeds


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
    if calibration.get("initialization") != "same_deterministic_random_state_within_each_seed_and_fold":
        errors.append("all lambda arms must share one deterministic initialization per seed-fold")
    if int(calibration.get("training_epochs", -1)) != int(config["training"]["epochs"]):
        errors.append("calibration and training epoch limits differ")
    if not np.isclose(float(calibration.get("learning_rate", -1)), float(config["training"]["learning_rate"])):
        errors.append("calibration and training learning rates differ")
    if int(calibration.get("minimum_training_epochs", -1)) != int(calibration.get("ramp_epochs", -2)):
        errors.append("all arms must share the same minimum training period as the physics ramp")
    angular_scale, horizontal_scale = residual_scales(config)
    if not np.isclose(angular_scale, 9.81 / .57) or not np.isclose(horizontal_scale, 9.81):
        errors.append("unexpected residual nondimensionalization")
    for subject in subjects:
        audit = (root / config["audit_dir_template"].format(subject=subject)).resolve()
        if not audit.is_dir():
            errors.append(f"missing audit folder: {audit}")
    report = {
        "dataset": str(dataset),
        "a11_trials": len(selected),
        "candidate_weights": candidate_weights(config, include_baseline=True),
        "residual_scales": {"angular_g_over_l": angular_scale, "horizontal_g": horizontal_scale},
        "training_epochs": int(calibration["training_epochs"]),
        "learning_rate": float(calibration["learning_rate"]),
        "same_initialization_enforced": True,
        "test_access_before_selection": False,
    }
    print(json.dumps(report, indent=2))
    if errors:
        print("\nSETUP ERRORS:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("\nSetup validation passed: 64 A11 trials, four matched from-scratch weights, identical schedules, and leakage-free folds.")


if __name__ == "__main__":
    main()
