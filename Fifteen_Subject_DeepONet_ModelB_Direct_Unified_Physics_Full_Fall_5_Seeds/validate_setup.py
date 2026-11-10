#!/usr/bin/env python3
"""Validate data availability and the leakage-free 15-subject, five-fold protocol."""

from __future__ import annotations

import argparse
import json
from collections import Counter

import numpy as np

from operator_core import load_config, optimization_seeds, resolve_glob, resolve_path


def validate_protocol(config: dict) -> list[str]:
    errors: list[str] = []
    subject_ids = [str(item["id"]) for item in config["subjects"]]
    expected = set(subject_ids)
    protocol = config["protocol"]
    fold_count = int(protocol["fold_count"])
    test_per_fold = int(protocol["test_subjects_per_fold"])
    validation_per_fold = int(protocol["validation_subjects_per_fold"])
    train_per_fold = int(protocol["training_subjects_per_fold"])

    if len(subject_ids) != 15 or len(expected) != 15:
        errors.append("The protocol requires 15 unique subjects")
    if len(config["folds"]) != fold_count or fold_count != 5:
        errors.append("The protocol requires exactly five folds")
    if validation_per_fold != 1:
        errors.append("The protocol requires one validation subject per fold")
    if train_per_fold + test_per_fold + validation_per_fold != len(expected):
        errors.append("Configured train/validation/test counts do not cover 15 subjects")

    randomized_order = [str(value) for value in config.get("randomized_subject_order", [])]
    if len(randomized_order) != len(expected) or set(randomized_order) != expected:
        errors.append("randomized_subject_order must contain every subject exactly once")
    else:
        reproduced = np.random.default_rng(int(config["split_seed"])).permutation(subject_ids).tolist()
        if reproduced != randomized_order:
            errors.append("split_seed does not reproduce randomized_subject_order")

    validation_counts: Counter[str] = Counter()
    test_counts: Counter[str] = Counter()
    train_counts: Counter[str] = Counter()
    flattened_tests: list[str] = []
    for fold in config["folds"]:
        fold_id = fold["id"]
        train = [str(value) for value in fold["train"]]
        validation = str(fold["validation"])
        test = [str(value) for value in fold["test"]]
        if len(train) != train_per_fold or len(set(train)) != train_per_fold:
            errors.append(f"fold {fold_id}: expected {train_per_fold} unique training subjects")
        if len(test) != test_per_fold or len(set(test)) != test_per_fold:
            errors.append(f"fold {fold_id}: expected {test_per_fold} unique test subjects")
        roles = set(train) | {validation} | set(test)
        if roles != expected:
            errors.append(f"fold {fold_id}: roles do not cover exactly the configured subjects")
        if set(train) & set(test) or validation in set(train) or validation in set(test):
            errors.append(f"fold {fold_id}: subject leakage between roles")
        train_counts.update(train)
        validation_counts[validation] += 1
        test_counts.update(test)
        flattened_tests.extend(test)

    if flattened_tests != randomized_order:
        errors.append("Fold test groups must follow randomized_subject_order")
    for subject in expected:
        if test_counts[subject] != 1:
            errors.append(f"{subject}: expected exactly one test appearance")
        if train_counts[subject] != fold_count - 1 - validation_counts[subject]:
            errors.append(f"{subject}: unexpected number of training appearances")
    validation_subjects = [str(fold["validation"]) for fold in config["folds"]]
    if len(set(validation_subjects)) != fold_count:
        errors.append("Validation subjects must be unique across the five folds")

    model = config["model"]
    training = config["training"]
    physics = config["physics"]
    real_data = config["real_data"]
    fixed_values = {
        "context_windows": (int(model["context_windows"]), 4),
        "context_region_s": (float(model["context_region_s"]), 0.40),
        "context_window_s": (float(model["context_window_s"]), 0.10),
        "latent_width": (int(model["latent_width"]), 96),
        "fourier_modes": (int(model["fourier_modes"]), 12),
        "physics_weight": (float(training["physics_weight"]), 0.01),
        "fixed_pi_rad": (float(physics["fixed_pi_rad"]), 0.0635),
        "fixed_tau_s": (float(physics["fixed_tau_s"]), 0.23),
    }
    for name, (actual, expected_value) in fixed_values.items():
        if not np.isclose(actual, expected_value):
            errors.append(f"Model B condition changed: {name}={actual}, expected {expected_value}")
    if config["model"]["controller_semantics"] != "physical_gains":
        errors.append("Model B requires the physical-gain controller head")
    if config["training_regime"] != "direct_physics":
        errors.append("Model B requires training_regime=direct_physics")
    if not bool(training["use_physics"]) or bool(config["requires_teachers"]):
        errors.append("Model B requires direct physics and no teacher data")
    if list(config["training_sources"]) != ["real"]:
        errors.append("Model B must train only on real trajectories")
    if float(training["gain_weight"]) != 0.0 or float(training["synthetic_source_weight"]) != 0.0:
        errors.append("Model B must not use gain supervision or synthetic training data")
    if real_data.get("endpoint_semantics") != "source_end_is_apparent_contact":
        errors.append("Full-fall runs require source_end_is_apparent_contact")
    if "fall_angle_deg" in real_data or "prefall_margin_s" in real_data:
        errors.append("Full-fall runs must not configure the legacy pre-20-degree cutoff")
    contact_exclusion = float(physics.get("contact_exclusion_s", -1.0))
    if contact_exclusion < 0.0 or contact_exclusion >= float(model["context_region_s"]):
        errors.append("physics.contact_exclusion_s must be nonnegative and shorter than context")
    try:
        seeds = optimization_seeds(config)
        if len(seeds) != 5:
            errors.append(f"The repeated experiment requires five optimization seeds, found {len(seeds)}")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"Invalid optimization_seeds: {exc}")
    return errors


def audit_status(config: dict, subject: dict) -> tuple[dict, list[str]]:
    subject_id = str(subject["id"])
    audit_dir = resolve_path(config, subject["audit_dir"])
    errors: list[str] = []
    required = {
        "demographics": audit_dir / "configs" / f"{subject_id}.json",
        "repaired_data": audit_dir / "repaired_data" / subject_id,
    }
    phase_candidates = [
        audit_dir / "analysis_inputs" / f"{subject_id}_phase_notes_manual.json",
        audit_dir / "analysis_inputs" / f"{subject_id}_phase_notes.json",
    ]
    for name, path in required.items():
        if not path.exists():
            errors.append(f"{subject_id}: missing {name}: {path}")
    phase_path = next((path for path in phase_candidates if path.is_file()), None)
    if phase_path is None:
        errors.append(f"{subject_id}: missing phase notes in {audit_dir / 'analysis_inputs'}")
    phase_trial_count = 0
    if phase_path is not None:
        payload = json.loads(phase_path.read_text(encoding="utf-8"))
        phase_trial_count = len(
            {
                note["trial"]
                for note in payload.get("notes", [])
                if str(note["trial"]).startswith(subject_id + "A11")
            }
        )
        if phase_trial_count == 0:
            errors.append(f"{subject_id}: phase notes contain no A11 trials")
    return {
        "subject": subject_id,
        "input_kind": "audit_skeleton",
        "audit_dir": str(audit_dir),
        "phase_marked_trial_count": phase_trial_count,
        "prepared_tsv_count": len(resolve_glob(config, subject["real_data_glob"])),
    }, errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    args = parser.parse_args()
    config = load_config(args.config)
    errors = validate_protocol(config)
    rows = []
    for subject in config["subjects"]:
        subject_id = str(subject["id"])
        if subject.get("input_kind") == "audit_skeleton":
            row, subject_errors = audit_status(config, subject)
            errors.extend(subject_errors)
            rows.append(row)
        else:
            real_files = resolve_glob(config, subject["real_data_glob"])
            if not real_files:
                errors.append(
                    f"{subject_id}: no legacy pole TSVs match {subject['real_data_glob']}; "
                    "run only the existing deterministic pole-compatible adapter, not Pole-PINN training or a gain sweep"
                )
            rows.append(
                {
                    "subject": subject_id,
                    "input_kind": "legacy_pole_tsv",
                    "real_trial_count": len(real_files),
                }
            )

    print(json.dumps(rows, indent=2))
    print("\nFive grouped held-out folds:")
    for fold in config["folds"]:
        print(
            f"  fold {fold['id']}: train={','.join(fold['train'])} "
            f"validation={fold['validation']} test={','.join(fold['test'])}"
        )
    if errors:
        print("\nSETUP ERRORS:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(
        "\nSetup validation passed for Model B: 15 subjects, five folds, "
        "five optimization seeds, one real validation subject per fold, "
        "and no held-out leakage."
    )


if __name__ == "__main__":
    main()
