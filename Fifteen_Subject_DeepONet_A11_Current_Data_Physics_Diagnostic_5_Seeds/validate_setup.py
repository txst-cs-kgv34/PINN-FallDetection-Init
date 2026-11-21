#!/usr/bin/env python3
"""Validate A11 data placement, paired conditions, constants, and folds."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from operator_core import load_config, optimization_seeds


def as_bool(value: str) -> bool:
    return value.lower() in {"true", "1", "yes"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--config", default="experiment.json"); args = parser.parse_args()
    config = load_config(args.config); root = Path(config["_root"]); errors = []
    dataset = (root / config["dataset_root"]).resolve(); manifest_path = dataset / "manifests" / "trial_manifest.csv"
    if not manifest_path.is_file(): errors.append(f"missing dataset manifest: {manifest_path}"); rows = []
    else:
        with manifest_path.open(newline="", encoding="utf-8") as handle: rows = list(csv.DictReader(handle))
    if rows:
        selected = [
            row for row in rows
            if row["activity"] in config["data"]["activities"]
            and as_bool(row[config["data"]["selection_flag"]])
        ]
        expected_count = int(config["data"]["expected_trial_count"])
        if len(selected) != expected_count:
            errors.append(f"expected {expected_count} A11 trials, found {len(selected)}")
        counts = Counter(row["activity"] for row in selected)
        if dict(counts) != {"A11": expected_count}:
            errors.append(f"diagnostic activity counts changed: {dict(counts)}")
    subjects = set(config["subjects"]); tests = []
    for fold in config["folds"]:
        train, validation, test = set(fold["train"]), {fold["validation"]}, set(fold["test"])
        if train & validation or train & test or validation & test: errors.append(f"fold {fold['id']}: subject leakage")
        if train | validation | test != subjects: errors.append(f"fold {fold['id']}: roles do not cover subjects")
        tests.extend(fold["test"])
    if set(tests) != subjects or len(tests) != len(subjects): errors.append("every subject must appear exactly once as test")
    constants = {
        "latent_width": (config["model"]["latent_width"], 96), "fourier_modes": (config["model"]["fourier_modes"], 12),
        "context_windows": (config["model"]["context_windows"], 4), "context_window_s": (config["model"]["context_window_s"], .10),
        "context_region_s": (config["model"]["context_region_s"], .40), "cartpole_physics_weight": (config["training"]["cartpole_physics_weight"], .01),
        "stick_mass_kg": (config["physics"]["stick_mass_kg"], .0138), "effective_cart_mass_kg": (config["physics"]["effective_cart_mass_kg"], 1.0),
        "stick_length_m": (config["physics"]["stick_length_m"], .57), "fixed_tau_s": (config["physics"]["fixed_tau_s"], .23), "fixed_pi_rad": (config["physics"]["fixed_pi_rad"], .0635),
    }
    for name, (actual, expected) in constants.items():
        if not np.isclose(actual, expected): errors.append(f"Model B constant changed: {name}={actual}, expected {expected}")
    if optimization_seeds(config) != [20261101, 20261102, 20261103, 20261104, 20261105]: errors.append("optimization seeds changed")
    conditions = config.get("conditions", {})
    if set(conditions) != {"physics", "no_physics"}:
        errors.append("conditions must be exactly physics and no_physics")
    elif not bool(conditions["physics"]["use_physics"]):
        errors.append("physics condition must enable physics")
    elif bool(conditions["no_physics"]["use_physics"]):
        errors.append("no_physics condition must disable physics")
    elif not np.isclose(conditions["physics"]["cartpole_physics_weight"], .01):
        errors.append("physics diagnostic must use the preserved 0.01 weight")
    elif not np.isclose(conditions["no_physics"]["cartpole_physics_weight"], 0.0):
        errors.append("no_physics weight must be zero")
    for subject in subjects:
        audit = (root / config["audit_dir_template"].format(subject=subject)).resolve()
        if not audit.is_dir(): errors.append(f"missing audit folder: {audit}")
    print(json.dumps({"dataset": str(dataset), "a11_trials": len(selected) if rows else 0, "folds": config["folds"], "conditions": conditions}, indent=2))
    if errors:
        print("\nSETUP ERRORS:"); [print(f"- {error}") for error in errors]; raise SystemExit(1)
    print("\nSetup validation passed: 64 A11 trials, two paired conditions, five seeds, and leakage-free folds.")


if __name__ == "__main__":
    main()
