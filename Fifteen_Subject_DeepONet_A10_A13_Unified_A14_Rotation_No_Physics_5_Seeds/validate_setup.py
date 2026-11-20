#!/usr/bin/env python3
"""Validate data placement, Model B constants, trial counts, and subject folds."""

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
        planar = [row for row in rows if row["activity"] in config["data"]["planar_activities"] and as_bool(row[config["data"]["planar_selection_flag"]])]
        rotation = [row for row in rows if row["activity"] == "A14" and as_bool(row[config["data"]["rotation_selection_flag"]])]
        if len(planar) != 257: errors.append(f"expected 257 planar trials, found {len(planar)}")
        if len(rotation) != 49: errors.append(f"expected 49 rotation trials, found {len(rotation)}")
        counts = Counter(row["activity"] for row in planar)
        expected = {"A10": 58, "A11": 64, "A12": 68, "A13": 67}
        if dict(counts) != expected: errors.append(f"planar activity counts changed: {dict(counts)}")
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
        "context_region_s": (config["model"]["context_region_s"], .40), "cartpole_physics_weight": (config["training"]["cartpole_physics_weight"], 0.0),
        "stick_mass_kg": (config["physics"]["stick_mass_kg"], .0138), "effective_cart_mass_kg": (config["physics"]["effective_cart_mass_kg"], 1.0),
        "stick_length_m": (config["physics"]["stick_length_m"], .57), "fixed_tau_s": (config["physics"]["fixed_tau_s"], .23), "fixed_pi_rad": (config["physics"]["fixed_pi_rad"], .0635),
    }
    for name, (actual, expected) in constants.items():
        if not np.isclose(actual, expected): errors.append(f"Model B constant changed: {name}={actual}, expected {expected}")
    if optimization_seeds(config) != [20261101, 20261102, 20261103, 20261104, 20261105]: errors.append("optimization seeds changed")
    physics_expected = config["training_regime"] == "direct_physics"
    if bool(config["training"]["use_physics"]) != physics_expected: errors.append("training_regime/use_physics mismatch")
    for subject in subjects:
        audit = (root / config["audit_dir_template"].format(subject=subject)).resolve()
        if not audit.is_dir(): errors.append(f"missing audit folder: {audit}")
    print(json.dumps({"dataset": str(dataset), "planar_trials": len(planar) if rows else 0, "rotation_trials": len(rotation) if rows else 0, "folds": config["folds"], "physics_enabled": bool(config["training"]["use_physics"])}, indent=2))
    if errors:
        print("\nSETUP ERRORS:"); [print(f"- {error}") for error in errors]; raise SystemExit(1)
    print("\nSetup validation passed: 257 planar trials including A11, 49 A14 trials, five paired seeds, and leakage-free folds.")


if __name__ == "__main__": main()
