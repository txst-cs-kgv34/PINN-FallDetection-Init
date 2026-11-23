#!/usr/bin/env python3
"""Create leakage-safe 30 Hz A10-A14 detector trajectories and manifests."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from detector_data_core import (
    adl_signals,
    as_bool,
    fall_signals,
    load_activity_types,
    load_demographics,
    load_skeleton_csv,
    parse_trial,
    ratio_policies,
    resample_valid,
    sha256,
    write_csv,
    write_json,
)


HERE = Path(__file__).resolve().parent
FALL_SUBJECTS = ("S30", "S32", "S34", "S43", "S44", "S45", "S46", "S48", "S49", "S55", "S56", "S57", "S59", "S62", "S63")
ADL_SUBJECTS = tuple(subject for subject in FALL_SUBJECTS if subject != "S59") + ("S31",)
EXPECTED_REAL_FALLS = 322
EXPECTED_SYNTHETIC_FALLS = 1380
EXPECTED_ADL = 545


def locate_raw_trial(project_root: Path, subject: str, trial: str) -> Path:
    audit = project_root / f"{subject}_PINN_audit"
    candidates = [
        audit / "repaired_data" / subject / f"{trial}.csv",
        audit / "findings" / f"{subject}_audit_repaired" / "raw" / f"{trial}.csv",
        audit / "findings" / f"{subject}_audit" / "raw" / f"{trial}.csv",
    ]
    candidates.extend(sorted(audit.glob(f"findings/*/raw/{trial}.csv")))
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise FileNotFoundError(f"{trial}: no audited skeleton CSV found under {audit}")


def repaired_frames(feature_file: Path, frame_count: int) -> set[int]:
    result: set[int] = set()
    with feature_file.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if int(row["repaired_frame"]):
                result.add(int(row["frame0"]))
    if any(index < 0 or index >= frame_count for index in result):
        raise ValueError(f"{feature_file}: repaired frame outside source bounds")
    return result


def save_trial(
    output: Path,
    sample_id: str,
    source_kind: str,
    signals: dict[str, np.ndarray],
    *,
    label: int,
    activity_id: int,
    demographics: dict[str, Any],
    observed_mask: np.ndarray | None = None,
    yaw_available: bool = True,
) -> str:
    time_s = np.asarray(signals["time_s"], dtype=np.float32)
    theta = np.asarray(signals["theta_rad"], dtype=np.float32)
    x_m = np.asarray(signals["x_m"], dtype=np.float32)
    yaw = np.asarray(signals.get("yaw_rad", np.zeros_like(theta)), dtype=np.float32)
    if not (len(time_s) == len(theta) == len(x_m) == len(yaw)) or len(time_s) < 2:
        raise ValueError(f"{sample_id}: inconsistent trajectory lengths")
    if not np.all(np.diff(time_s) > 0.0) or not all(np.all(np.isfinite(values)) for values in (time_s, theta, x_m, yaw)):
        raise ValueError(f"{sample_id}: invalid time or non-finite signal")
    observed = np.ones(len(time_s), dtype=np.uint8) if observed_mask is None else np.asarray(observed_mask, dtype=np.uint8)
    if len(observed) != len(time_s):
        raise ValueError(f"{sample_id}: observed-mask length mismatch")
    relative = Path("trials") / source_kind / f"{sample_id}.npz"
    destination = output / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        time_s=time_s,
        theta_rad=theta,
        x_m=x_m,
        yaw_rad=yaw,
        valid_mask=np.ones(len(time_s), dtype=np.uint8),
        observed_mask=observed,
        yaw_available_mask=np.full(len(time_s), int(yaw_available), dtype=np.uint8),
        label=np.int8(label),
        activity_id=np.int16(activity_id),
        sample_rate_hz=np.float32(30.0),
        mass_kg=np.float32(demographics["mass_kg"]),
        height_m=np.float32(demographics["height_m"]),
    )
    return str(relative)


def base_row(sample_id: str, source_kind: str, subject: str, activity_id: int, activity_name: str, trial: str, demographics: dict[str, Any], signals: dict[str, np.ndarray], data_file: str) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "label": 0 if source_kind == "real_adl" else 1,
        "class_name": "adl" if source_kind == "real_adl" else "fall",
        "source_kind": source_kind,
        "is_synthetic": source_kind == "synthetic_fall",
        "subject": subject,
        "source_subject": subject,
        "split_group": subject,
        "activity_id": activity_id,
        "activity_code": f"A{activity_id:02d}",
        "activity_name": activity_name,
        "trial": trial,
        "sample_rate_hz": 30.0,
        "sample_count": len(signals["time_s"]),
        "duration_s": float(signals["time_s"][-1]),
        "sex": demographics["sex"],
        "mass_kg": demographics["mass_kg"],
        "height_m": demographics["height_m"],
        "data_file": data_file,
    }


def prepare_adl(adl_root: Path, output: Path, demographics: dict[str, dict[str, Any]], activities: dict[int, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    discovered = {path.name.removesuffix("_ADLSamples") for path in adl_root.glob("S*_ADLSamples") if any(path.glob("*.csv"))}
    if discovered != set(ADL_SUBJECTS):
        raise ValueError(f"ADL subjects {sorted(discovered)} do not match expected {sorted(ADL_SUBJECTS)}")
    for subject in sorted(ADL_SUBJECTS, key=lambda value: int(value[1:])):
        for source in sorted((adl_root / f"{subject}_ADLSamples").glob("*.csv")):
            file_subject, activity_id, _ = parse_trial(source.stem)
            if file_subject != subject or activity_id not in set(range(1, 10)) - {4}:
                raise ValueError(f"Unexpected ADL path: {source}")
            try:
                raw, blank_rows = load_skeleton_csv(source)
                signals = adl_signals(raw, demographics[subject]["sex"])
            except ValueError as exc:
                exclusions.append({"source_kind": "real_adl", "trial": source.stem, "source_file": str(source), "reason": str(exc)})
                continue
            sample_id = f"ADL_{source.stem}"
            observed = np.ones(len(signals["time_s"]), dtype=np.uint8)
            observed[blank_rows] = 0
            data_file = save_trial(output, sample_id, "real_adl", signals, label=0, activity_id=activity_id, demographics=demographics[subject], observed_mask=observed)
            row = base_row(sample_id, "real_adl", subject, activity_id, activities[activity_id], source.stem, demographics[subject], signals, data_file)
            row.update({"source_file": str(source), "source_sha256": sha256(source), "coordinate_method": "fixed standing body frame; forward CoM relative to first-0.5-s foot pivot", "repaired_frame_count": len(blank_rows), "replacement_for_missing_adl_subject": "S59" if subject == "S31" else ""})
            rows.append(row)
    return rows, exclusions


def prepare_real_falls(dataset_root: Path, project_root: Path, output: Path, demographics: dict[str, dict[str, Any]], activities: dict[int, str]) -> list[dict[str, Any]]:
    manifest = dataset_root / "manifests" / "trial_manifest.csv"
    with manifest.open(newline="", encoding="utf-8") as handle:
        selected = [row for row in csv.DictReader(handle) if as_bool(row["include_detection_training"])]
    rows: list[dict[str, Any]] = []
    for item in selected:
        subject, activity_id, _ = parse_trial(item["trial"])
        source = locate_raw_trial(project_root, subject, item["trial"])
        raw, unexpected_blanks = load_skeleton_csv(source)
        if unexpected_blanks:
            raise ValueError(f"{source}: audited source still contains blank rows")
        signals_any = fall_signals(raw, item)
        signals = {key: value for key, value in signals_any.items() if isinstance(value, np.ndarray)}
        feature_file = dataset_root / item["feature_file"]
        repaired = repaired_frames(feature_file, len(raw))
        observed = np.ones(len(signals["time_s"]), dtype=np.uint8)
        for index in repaired:
            if index < len(observed):
                observed[index] = 0
        sample_id = f"REAL_{item['trial']}"
        data_file = save_trial(output, sample_id, "real_fall", signals, label=1, activity_id=activity_id, demographics=demographics[subject], observed_mask=observed)
        row = base_row(sample_id, "real_fall", subject, activity_id, activities[activity_id], item["trial"], demographics[subject], signals, data_file)
        row.update({
            "source_file": str(source), "source_sha256": sha256(source),
            "physics_ready_feature_file": item["feature_file"],
            "coordinate_method": "DeepONet-aligned standing body frame; A10-A13 activity axis; A14 onset-to-contact axis; through apparent contact",
            "fall_direction_lateral": signals_any["direction_lateral"],
            "fall_direction_forward": signals_any["direction_forward"],
            "fall_direction_source": signals_any["direction_source"],
            "initial_standing_frame0": int(item["initial_standing_frame0"]),
            "fall_onset_frame0": int(item["fall_onset_frame0"]),
            "apparent_contact_frame0": int(item["apparent_contact_frame0"]),
            "repaired_frame_count": len(repaired), "synthetic_family_id": item["trial"],
        })
        rows.append(row)
    return rows


def prepare_synthetic(synthetic_root: Path, output: Path, demographics: dict[str, dict[str, Any]], activities: dict[int, str]) -> list[dict[str, Any]]:
    manifest_file = synthetic_root / "outputs" / "trajectory_quality" / "final_approved_synthetic_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("test_subjects_used") or manifest.get("validation_subjects_used_for_thresholds"):
        raise ValueError("Approved manifest reports forbidden validation/test use")
    generation_root = (manifest_file.parent / manifest["dataset_root_relative_to_manifest"]).resolve()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in manifest["samples"]:
        synthetic_id = str(item["synthetic_id"])
        if synthetic_id in seen:
            raise ValueError(f"Duplicate synthetic ID: {synthetic_id}")
        seen.add(synthetic_id)
        required = ("overall_quality_pass", "continuity_gate_pass", "shape_gate_pass", "kinematic_gate_pass", "physics_gate_pass", "direction_gate_pass", "duplicate_gate_pass", "source_is_training_subject")
        if not all(as_bool(item[name]) for name in required) or as_bool(item["validation_or_test_context_used"]):
            raise ValueError(f"{synthetic_id}: non-approved or leakage-bearing manifest row")
        activity = str(item["activity"])
        activity_id = int(activity[1:])
        subject = str(item["source_subject"])
        source = generation_root / item["data_file"]
        with np.load(source, allow_pickle=False) as data:
            valid = np.asarray(data["valid_mask"]) > 0.5
            source_time = np.asarray(data["time_s"])[valid]
            source_theta = np.asarray(data["synthetic_theta_rad"])[valid]
            source_x = np.asarray(data["synthetic_x_m"])[valid]
            if activity == "A14":
                time_s, theta, x_m, yaw = resample_valid(source_time, source_theta, source_x, np.asarray(data["synthetic_yaw_rad"])[valid])
                yaw_available = True
            else:
                time_s, theta, x_m = resample_valid(source_time, source_theta, source_x)
                yaw = np.zeros_like(theta)
                yaw_available = False
        signals = {"time_s": time_s, "theta_rad": theta, "x_m": x_m, "yaw_rad": yaw}
        sample_id = f"SYN_{synthetic_id}"
        data_file = save_trial(output, sample_id, "synthetic_fall", signals, label=1, activity_id=activity_id, demographics=demographics[subject], yaw_available=yaw_available)
        row = base_row(sample_id, "synthetic_fall", subject, activity_id, activities[activity_id], synthetic_id, demographics[subject], signals, data_file)
        row.update({
            "source_file": str(source), "source_sha256": sha256(source),
            "coordinate_method": "GATE-approved C1-corrected direct-physics DeepONet trajectory resampled from 100 Hz to 30 Hz",
            "source_real_trial": item["source_trial"], "synthetic_family_id": item["source_trial"],
            "model_group": item["model_group"], "generator_fold": int(item["fold"]),
            "generator_rank": int(item["generator_rank"]), "generator_seed_index": int(item["seed_index"]),
            "physics_weight": float(item["physics_weight"]), "quality_approved": True,
            "yaw_available": yaw_available, "trajectory_sha256": item["trajectory_sha256"],
        })
        rows.append(row)
    if len(rows) != int(manifest["approved_count"]):
        raise ValueError("Approved-count mismatch after synthetic materialization")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=HERE.parent)
    parser.add_argument("--adl-root", type=Path)
    parser.add_argument("--physics-ready-root", type=Path)
    parser.add_argument("--synthetic-results-root", type=Path)
    parser.add_argument("--demographics", type=Path)
    parser.add_argument("--activity-types", type=Path)
    parser.add_argument("--output-dir", type=Path, default=HERE / "outputs")
    parser.add_argument("--fall-batch-size", type=int, default=10)
    parser.add_argument("--allow-count-drift", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    project = args.project_root.expanduser().resolve()
    adl_root = (args.adl_root or project / "ADLSamples").expanduser().resolve()
    dataset_root = (args.physics_ready_root or project / "data/processed/Fifteen_Subject_Real_Fall_Physics_Ready").expanduser().resolve()
    synthetic_root = (args.synthetic_results_root or project / "Fifteen_Subject_DeepONet_A10_A14_Physics_Synthetic_Fall_Study_GATED").expanduser().resolve()
    demographics_path = (args.demographics or project / "human_subjects_demographics.csv").expanduser().resolve()
    activity_path = (args.activity_types or project / "Activity_Types.md").expanduser().resolve()
    output = args.output_dir.expanduser().resolve()
    for path, directory in ((adl_root, True), (dataset_root, True), (synthetic_root, True), (demographics_path, False), (activity_path, False)):
        if not (path.is_dir() if directory else path.is_file()):
            raise FileNotFoundError(path)
    if output.exists() and any(output.iterdir()):
        if not args.overwrite:
            raise FileExistsError(f"{output} is not empty; pass --overwrite")
        if output in {Path("/").resolve(), HERE.resolve(), project}:
            raise ValueError(f"Refusing to clear protected path: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    demographics = load_demographics(demographics_path)
    activities = load_activity_types(activity_path)
    required_subjects = set(FALL_SUBJECTS) | set(ADL_SUBJECTS)
    if missing := required_subjects - set(demographics):
        raise ValueError(f"Missing demographics: {sorted(missing)}")
    adl_rows, exclusions = prepare_adl(adl_root, output, demographics, activities)
    real_rows = prepare_real_falls(dataset_root, project, output, demographics, activities)
    synthetic_rows = prepare_synthetic(synthetic_root, output, demographics, activities)
    expected = {"real_adl": EXPECTED_ADL, "real_fall": EXPECTED_REAL_FALLS, "synthetic_fall": EXPECTED_SYNTHETIC_FALLS}
    actual = {"real_adl": len(adl_rows), "real_fall": len(real_rows), "synthetic_fall": len(synthetic_rows)}
    if not args.allow_count_drift and actual != expected:
        raise ValueError(f"Prepared counts {actual} do not match reviewed counts {expected}; inspect inputs or pass --allow-count-drift")
    samples = adl_rows + real_rows + synthetic_rows
    if len({row["sample_id"] for row in samples}) != len(samples):
        raise ValueError("Prepared sample IDs are not unique")
    write_csv(output / "dataset_manifest.csv", samples)
    if exclusions:
        write_csv(output / "excluded_samples.csv", exclusions)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        grouped[(row["source_kind"], row["activity_code"])].append(row)
    summary = [{"source_kind": key[0], "activity_code": key[1], "sample_count": len(values), "subject_count": len({row["subject"] for row in values}), "minimum_duration_s": min(float(row["duration_s"]) for row in values), "median_duration_s": float(np.median([float(row["duration_s"]) for row in values])), "maximum_duration_s": max(float(row["duration_s"]) for row in values)} for key, values in sorted(grouped.items())]
    write_csv(output / "dataset_summary.csv", summary)
    policies = ratio_policies(args.fall_batch_size)
    write_json(output / "fall_mixture_policies.json", {
        "scope": "training fall samples only; ADL/fall class balance is separate",
        "split_rule": "split by source subject before sampling; synthetic is training-only",
        "sampling_rule": "stratify by activity where possible; choose synthetic_family_id before generator variant",
        "policies": policies,
    })
    write_json(output / "dataset_manifest.json", {
        "description": "Architecture-neutral 30 Hz A10-A14 real/synthetic fall and real ADL trajectories",
        "canonical_detector_features": ["theta_rad", "x_m"],
        "optional_feature": "yaw_rad with yaw_available_mask; planar synthetic yaw is intentionally unavailable",
        "counts": {"total": len(samples), "by_source_kind": actual, "excluded_adl": len(exclusions)},
        "real_fall_scope": "all include_detection_training trials in the reviewed physics-ready dataset, clipped through marked apparent contact",
        "synthetic_scope": "only GATE-approved direct-physics A10-A14 trajectories",
        "leakage_rule": "all variants use source_subject as split_group; synthetic is forbidden in validation/test",
        "windowing_applied": False,
        "normalization_applied": False,
        "samples": samples,
    })
    print(f"Prepared {len(samples)} trajectories: {actual}; excluded ADL files: {len(exclusions)}")
    print(f"Outputs: {output}")


if __name__ == "__main__":
    main()
