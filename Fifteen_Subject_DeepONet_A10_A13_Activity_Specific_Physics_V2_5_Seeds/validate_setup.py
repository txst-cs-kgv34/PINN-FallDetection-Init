#!/usr/bin/env python3
"""Validate A10-A13 V2 data, axes, folds, heads, and matched protocol."""

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
        errors.append(f"expected 257 strict-primary A10-A13 trials, found {len(selected)}")
    observed_counts = dict(sorted(Counter(row["activity"] for row in selected).items()))
    if observed_counts != config["data"]["expected_by_activity"]:
        errors.append(f"activity counts changed: {observed_counts}")
    subjects = set(config["subjects"])
    tested: list[str] = []
    for fold in config["folds"]:
        train = set(fold["train"])
        validation = set(fold["validation"])
        test = set(fold["test"])
        if train & validation or train & test or validation & test:
            errors.append(f"fold {fold['id']}: subject leakage")
        if train | validation | test != subjects:
            errors.append(f"fold {fold['id']}: roles do not cover subjects")
        if (len(train), len(validation), len(test)) != (10, 2, 3):
            errors.append(f"fold {fold['id']}: expected 10/2/3 train/validation/test")
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
    if calibration.get("selection_metric") != "validation_subject_activity_balanced_forecast_mse":
        errors.append("weights must use subject-activity-balanced validation forecast MSE")
    if calibration.get("selection_tie_break") != "smaller_physics_weight":
        errors.append("selection ties must prefer the smaller physics weight")
    if calibration.get("initialization") != "same_deterministic_random_state_within_each_seed_and_fold":
        errors.append("all lambda arms must share one deterministic initialization per seed-fold")
    if int(calibration.get("training_epochs", -1)) != 800:
        errors.append("calibration must use 800 maximum epochs")
    if not np.isclose(float(calibration.get("learning_rate", -1)), 5e-4):
        errors.append("calibration must use learning rate 5e-4")
    if int(calibration.get("minimum_training_epochs", -1)) != int(calibration.get("ramp_epochs", -2)):
        errors.append("all arms must share the same minimum training period as the physics ramp")
    angular_scale, horizontal_scale = residual_scales(config)
    if not np.isclose(angular_scale, 9.81 / .57) or not np.isclose(horizontal_scale, 9.81):
        errors.append("unexpected residual nondimensionalization")
    axes = config["data"]["activity_axes_subject_frame_lateral_forward"]
    expected_axes = {"A10": [0.0, -1.0], "A11": [0.0, 1.0], "A12": [-1.0, 0.0], "A13": [1.0, 0.0]}
    if axes != expected_axes:
        errors.append(f"activity axes changed: {axes}")
    if config["model"].get("controller_semantics") != "four_activity_specific_cartpole_gain_heads":
        errors.append("model must use four activity-specific CartPole controller heads")
    for subject in subjects:
        audit = (root / config["audit_dir_template"].format(subject=subject)).resolve()
        if not audit.is_dir():
            errors.append(f"missing audit folder: {audit}")
    report = {
        "dataset": str(dataset),
        "a10_a13_trials": len(selected),
        "trials_by_activity": observed_counts,
        "activity_axes": axes,
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
    print("\nSetup validation passed: 257 A10-A13 trials, four activity heads, 10/2/3 folds, and four matched weights.")


if __name__ == "__main__":
    main()
