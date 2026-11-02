#!/usr/bin/env python3
"""Validate external files, selected chunks, and the five-fold subject protocol."""

from __future__ import annotations

import argparse
import json
from collections import Counter

import numpy as np

from operator_core import GAIN_NAMES, load_config, resolve_glob, resolve_path


def validate_protocol(config: dict) -> list[str]:
    errors: list[str] = []
    subject_ids = [str(item["id"]) for item in config["subjects"]]
    expected = set(subject_ids)
    if len(subject_ids) != 5 or len(expected) != 5:
        errors.append("Experiment 1 requires five unique subjects")
    validation_counts: Counter[str] = Counter()
    test_counts: Counter[str] = Counter()
    train_counts: Counter[str] = Counter()
    if len(config["folds"]) != 5:
        errors.append("Experiment 1 requires five balanced folds")
    randomized_order = list(config.get("randomized_subject_order", []))
    if len(randomized_order) != 5 or set(randomized_order) != expected:
        errors.append("randomized_subject_order must contain every subject exactly once")
    else:
        reproduced = np.random.default_rng(int(config["split_seed"])).permutation(subject_ids).tolist()
        if reproduced != randomized_order:
            errors.append("split_seed does not reproduce randomized_subject_order")
    for fold in config["folds"]:
        train = list(fold["train"])
        validation = str(fold["validation"])
        test = str(fold["test"])
        if len(train) != 3 or len(set(train)) != 3:
            errors.append(f"fold {fold['id']}: expected three unique training subjects")
        if set(train) | {validation, test} != expected:
            errors.append(f"fold {fold['id']}: roles do not cover exactly the five subjects")
        if set(train) & {validation, test} or validation == test:
            errors.append(f"fold {fold['id']}: subject leakage between roles")
        train_counts.update(train)
        validation_counts[validation] += 1
        test_counts[test] += 1
    for subject in expected:
        if train_counts[subject] != 3:
            errors.append(f"{subject}: expected three training appearances")
        if validation_counts[subject] != 1:
            errors.append(f"{subject}: expected one validation appearance")
        if test_counts[subject] != 1:
            errors.append(f"{subject}: expected one test appearance")
    if len(randomized_order) == 5:
        for index, fold in enumerate(config["folds"]):
            if fold["test"] != randomized_order[index]:
                errors.append(f"fold {fold['id']}: test role does not follow randomized order")
            if fold["validation"] != randomized_order[(index + 1) % 5]:
                errors.append(f"fold {fold['id']}: validation role does not follow rotation")
    model = config["model"]
    if int(model["context_windows"]) != 4:
        errors.append("This protocol is fixed to the selected four-window context")
    if float(model["context_region_s"]) + 1e-9 < float(model["context_window_s"]):
        errors.append("context_region_s must be at least context_window_s")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    args = parser.parse_args()
    config = load_config(args.config)
    errors = validate_protocol(config)
    rows = []
    reference_endpoints = {
        (240.0, 30.0, 13.0, 30.0): "Subject-B pole reference",
        (120.0, 28.0, 14.0, 19.0): "Subject-A pole reference",
    }
    for subject in config["subjects"]:
        paths = {
            name: resolve_path(config, subject[name])
            for name in ("pipeline_source", "checkpoint", "gain_result")
        }
        for name, path in paths.items():
            if not path.is_file():
                errors.append(f"{subject['id']}: missing {name}: {path}")
        real_files = resolve_glob(config, subject["real_data_glob"])
        if not real_files:
            errors.append(f"{subject['id']}: no real TSVs match {subject['real_data_glob']}")
        gains = None
        if paths["gain_result"].is_file():
            result = json.loads(paths["gain_result"].read_text(encoding="utf-8"))
            if int(result.get("chunk", -1)) != int(subject["selected_chunk"]):
                errors.append(f"{subject['id']}: selected chunk and result.json disagree")
            missing = [name for name in GAIN_NAMES if name not in result]
            if missing:
                errors.append(f"{subject['id']}: gain result is missing {missing}")
            else:
                gains = tuple(float(result[name]) for name in GAIN_NAMES)
                rounded = tuple(round(value, 6) for value in gains)
                for endpoint, label in reference_endpoints.items():
                    if all(abs(a - b) < 1e-6 for a, b in zip(rounded, endpoint)):
                        errors.append(f"{subject['id']}: selected exact {label}, which is excluded")
        rows.append(
            {
                "subject": subject["id"],
                "teacher": subject["teacher_id"],
                "chunk": subject["selected_chunk"],
                "checkpoint": str(paths["checkpoint"]),
                "real_trial_count": len(real_files),
                "gains": gains,
            }
        )
    print(json.dumps(rows, indent=2))
    print("\nBalanced folds:")
    print(
        f"  split_seed={config.get('split_seed')} "
        f"randomized_order={','.join(config.get('randomized_subject_order', []))}"
    )
    for fold in config["folds"]:
        print(
            f"  fold {fold['id']}: train={','.join(fold['train'])} "
            f"validation={fold['validation']} test={fold['test']}"
        )
    if errors:
        print("\nSETUP ERRORS:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("\nSetup validation passed: five external teachers, five real-data sources, and no fold leakage.")


if __name__ == "__main__":
    main()
