#!/usr/bin/env python3
"""Prepare architecture-neutral 30 Hz CoM trajectories for fall detection."""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from detector_data_core import (
    dump_json,
    load_activity_types,
    load_demographics,
    load_skeleton_csv,
    parse_trial,
    resample_signal,
    sha256,
    skeleton_to_theta_x,
    write_csv,
)


HERE = Path(__file__).resolve().parent
FALL_SUBJECTS = (
    "S30", "S32", "S34", "S43", "S44", "S45", "S46", "S48",
    "S49", "S55", "S56", "S57", "S59", "S62", "S63",
)
ADL_SUBJECTS = tuple(subject for subject in FALL_SUBJECTS if subject != "S59") + ("S31",)
REAL_FALL_ACTIVITY_IDS = set(range(10, 15))
REQUIRED_PHASES = (
    "initial_standing", "fall_onset", "descent", "apparent_contact", "post_fall"
)


def phase_file(audit_dir: Path, subject: str) -> Path:
    candidates = (
        audit_dir / "analysis_inputs" / f"{subject}_phase_notes_manual.json",
        audit_dir / "analysis_inputs" / f"{subject}_phase_notes.json",
        audit_dir / "analysis_inputs" / f"{subject}_A11_phase_notes.json",
        audit_dir / "analysis_inputs" / f"{subject}_phase_notes_model_ready.json",
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(f"{subject}: no manual A11 phase-note file found")


def load_a11_phases(path: Path, subject: str) -> dict[str, dict[str, int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if str(payload.get("subject")) != subject:
        raise ValueError(f"{path}: subject mismatch")
    grouped: dict[str, dict[str, int]] = defaultdict(dict)
    for note in payload.get("notes", []):
        trial = str(note.get("trial", ""))
        phase = str(note.get("phase", ""))
        if trial.startswith(subject + "A11") and phase in REQUIRED_PHASES:
            grouped[trial][phase] = int(note["frame0"])
    result: dict[str, dict[str, int]] = {}
    for trial, marks in grouped.items():
        if set(marks) != set(REQUIRED_PHASES):
            continue
        ordered = [marks[phase] for phase in REQUIRED_PHASES]
        if any(left >= right for left, right in zip(ordered, ordered[1:])):
            raise ValueError(f"{path}: non-increasing phase order for {trial}")
        result[trial] = marks
    return result


def preferred_fall_files(audit_dir: Path, subject: str) -> dict[str, Path]:
    repaired = sorted((audit_dir / "repaired_data" / subject).glob(f"{subject}A1[0-4]T*.csv"))
    candidates = repaired or sorted(audit_dir.glob(f"findings/**/raw/{subject}A1[0-4]T*.csv"))
    result: dict[str, Path] = {}
    for path in candidates:
        prior = result.get(path.stem)
        if prior is not None and sha256(prior) != sha256(path):
            raise ValueError(f"Conflicting duplicate audit files for {path.stem}")
        result[path.stem] = path
    return result


def preferred_a11_files(audit_dir: Path, subject: str) -> dict[str, Path]:
    return {
        trial: path
        for trial, path in preferred_fall_files(audit_dir, subject).items()
        if parse_trial(trial)[1] == 11
    }


def fall_sample_files(fall_root: Path, subject: str) -> dict[str, Path]:
    """Return the raw A10-A14 skeleton recordings for one subject."""
    subject_dir = fall_root / f"{subject}_FallSamples"
    result: dict[str, Path] = {}
    for path in sorted(subject_dir.glob(f"{subject}A1[0-4]T*.csv")):
        trial_subject, activity_id, _ = parse_trial(path.stem)
        if trial_subject != subject or activity_id not in REAL_FALL_ACTIVITY_IDS:
            raise ValueError(f"{path}: unexpected real-fall filename")
        if path.stem in result:
            raise ValueError(f"Duplicate real-fall trial: {path.stem}")
        result[path.stem] = path
    return result


def real_fall_inventory(
    fall_root: Path,
    activities: dict[int, str],
    included_sample_ids: set[str],
    exclusions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    exclusion_lookup = {
        str(row["trial"]): str(row["reason"])
        for row in exclusions
        if row["source_kind"] == "real_fall"
    }
    rows: list[dict[str, Any]] = []
    for subject in FALL_SUBJECTS:
        for trial, path in sorted(fall_sample_files(fall_root, subject).items()):
            _, activity_id, _ = parse_trial(trial)
            sample_id = f"REAL_{trial}"
            included = sample_id in included_sample_ids
            if included:
                disposition = "included in prepared detector dataset"
            else:
                disposition = exclusion_lookup.get(trial, "not included")
            rows.append(
                {
                    "subject": subject,
                    "trial": trial,
                    "activity_id": activity_id,
                    "activity_code": f"A{activity_id:02d}",
                    "activity_name": activities[activity_id],
                    "source_file": str(path.relative_to(fall_root.parent)),
                    "included_in_current_dataset": included,
                    "disposition": disposition,
                }
            )
    return rows


def audited_a11_fall_inventory(
    audit_root: Path,
    activities: dict[int, str],
    included_sample_ids: set[str],
    exclusions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Inventory the audited A11 files used by the current front-fall study."""
    exclusion_lookup = {
        str(row["trial"]): str(row["reason"])
        for row in exclusions
        if row["source_kind"] == "real_fall"
    }
    rows: list[dict[str, Any]] = []
    for subject in FALL_SUBJECTS:
        audit_dir = audit_root / f"{subject}_PINN_audit"
        for trial, path in sorted(preferred_a11_files(audit_dir, subject).items()):
            sample_id = f"REAL_{trial}"
            included = sample_id in included_sample_ids
            rows.append(
                {
                    "subject": subject,
                    "trial": trial,
                    "activity_id": 11,
                    "activity_code": "A11",
                    "activity_name": activities[11],
                    "source_file": str(path.relative_to(audit_root)),
                    "included_in_current_dataset": included,
                    "disposition": (
                        "included in phase-marked A11 detector dataset"
                        if included
                        else exclusion_lookup.get(trial, "not included")
                    ),
                }
            )
    return rows


def validate_audit_demographics(
    audit_dir: Path, subject: str, demographics: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    path = audit_dir / "configs" / f"{subject}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = demographics[subject]
    checks = {
        "sex": (str(payload["sex"]).lower(), expected["sex"]),
        "mass_lb": (float(payload["mass_lb"]), expected["mass_lb"]),
        "height_in": (float(payload["height_in"]), expected["height_in"]),
        "fps": (float(payload["fps"]), 30.0),
        "coordinate_units": (str(payload["coordinate_units"]).lower(), "mm"),
    }
    for name, (actual, wanted) in checks.items():
        if actual != wanted:
            raise ValueError(f"{subject}: audit/demographics {name} mismatch: {actual} != {wanted}")
    return payload


def save_trial(
    output_root: Path,
    sample_id: str,
    source_kind: str,
    time_s: np.ndarray,
    theta_rad: np.ndarray,
    x_m: np.ndarray,
    label: int,
    activity_id: int,
    mass_kg: float,
    height_m: float,
) -> str:
    if not (len(time_s) == len(theta_rad) == len(x_m)) or len(time_s) < 2:
        raise ValueError(f"{sample_id}: invalid trajectory array lengths")
    if not all(np.all(np.isfinite(values)) for values in (time_s, theta_rad, x_m)):
        raise ValueError(f"{sample_id}: trajectory contains non-finite values")
    relative = Path("trials") / source_kind / f"{sample_id}.npz"
    destination = output_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        time_s=np.asarray(time_s, dtype=np.float32),
        theta_rad=np.asarray(theta_rad, dtype=np.float32),
        x_m=np.asarray(x_m, dtype=np.float32),
        valid_mask=np.ones(len(time_s), dtype=np.uint8),
        label=np.int8(label),
        activity_id=np.int16(activity_id),
        sample_rate_hz=np.float32(30.0),
        mass_kg=np.float32(mass_kg),
        height_m=np.float32(height_m),
    )
    return str(relative)


def base_row(
    *,
    sample_id: str,
    label: int,
    source_kind: str,
    subject: str,
    activity_id: int,
    activity_name: str,
    trial: str,
    demographics: dict[str, Any],
    time_s: np.ndarray,
    data_file: str,
) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "label": label,
        "class_name": "adl" if label == 0 else "fall",
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
        "sample_count": len(time_s),
        "duration_s": float(time_s[-1]),
        "sex": demographics["sex"],
        "mass_kg": demographics["mass_kg"],
        "height_m": demographics["height_m"],
        "data_file": data_file,
    }


def prepare_adl(
    adl_root: Path,
    output_root: Path,
    demographics: dict[str, dict[str, Any]],
    activities: dict[int, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    discovered_subjects = {
        path.name.removesuffix("_ADLSamples")
        for path in adl_root.glob("S*_ADLSamples")
        if any(path.glob("*.csv"))
    }
    if discovered_subjects != set(ADL_SUBJECTS):
        raise ValueError(
            f"ADL subject set {sorted(discovered_subjects)} does not match expected {sorted(ADL_SUBJECTS)}"
        )
    missing_s59 = adl_root / "S59_ADLSamples"
    if missing_s59.is_dir() and any(missing_s59.glob("*.csv")):
        raise ValueError("S59_ADLSamples must be absent or contain no CSV files")

    for subject in sorted(ADL_SUBJECTS, key=lambda value: int(value[1:])):
        for path in sorted((adl_root / f"{subject}_ADLSamples").glob("*.csv")):
            trial_subject, activity_id, _ = parse_trial(path.stem)
            if trial_subject != subject:
                raise ValueError(f"{path}: directory/filename subject mismatch")
            if activity_id not in set(range(1, 10)) - {4}:
                raise ValueError(f"{path}: unexpected ADL activity A{activity_id:02d}")
            source_ref = str(path.relative_to(adl_root.parent))
            try:
                skeleton, blank_rows = load_skeleton_csv(path)
                time_s, theta, x_m, coordinates = skeleton_to_theta_x(
                    skeleton,
                    demographics[subject]["sex"],
                    30.0,
                    standing_frame=min(7, len(skeleton) - 1),
                    standing_radius=min(7, max(0, len(skeleton) - 1)),
                    pivot_frame=None,
                    end_frame=None,
                )
            except ValueError as exc:
                excluded.append(
                    {
                        "source_kind": "real_adl",
                        "source_file": source_ref,
                        "trial": path.stem,
                        "reason": str(exc).replace(str(path), source_ref),
                    }
                )
                continue
            sample_id = f"ADL_{path.stem}"
            data_file = save_trial(
                output_root,
                sample_id,
                "real_adl",
                time_s,
                theta,
                x_m,
                0,
                activity_id,
                demographics[subject]["mass_kg"],
                demographics[subject]["height_m"],
            )
            row = base_row(
                sample_id=sample_id,
                label=0,
                source_kind="real_adl",
                subject=subject,
                activity_id=activity_id,
                activity_name=activities[activity_id],
                trial=path.stem,
                demographics=demographics[subject],
                time_s=time_s,
                data_file=data_file,
            )
            row.update(
                {
                    "source_file": source_ref,
                    "source_sha256": sha256(path),
                    "coordinate_method": "adult segment-mass CoM; fixed first-0.5-s body frame and foot pivot",
                    "replacement_for_missing_adl_subject": "S59" if subject == "S31" else "",
                    **coordinates,
                }
            )
            rows.append(row)
            if blank_rows:
                repairs.append(
                    {
                        "source_kind": "real_adl",
                        "trial": path.stem,
                        "source_file": source_ref,
                        "repair": "linear interpolation of wholly blank skeleton row",
                        "repaired_frame0": "|".join(map(str, blank_rows)),
                        "repaired_row_count": len(blank_rows),
                    }
                )
    return rows, excluded, repairs


def prepare_all_real_falls(
    fall_root: Path,
    audit_root: Path,
    output_root: Path,
    demographics: dict[str, dict[str, Any]],
    activities: dict[int, str],
    minimum_duration_s: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert full A10-A14 raw skeleton recordings into canonical CoM trials."""
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    discovered_subjects = {
        path.name.removesuffix("_FallSamples")
        for path in fall_root.glob("S*_FallSamples")
        if any(path.glob("*.csv"))
    }
    if discovered_subjects != set(FALL_SUBJECTS):
        raise ValueError(
            f"Fall subject set {sorted(discovered_subjects)} does not match "
            f"expected {sorted(FALL_SUBJECTS)}"
        )

    for subject in FALL_SUBJECTS:
        audit_dir = audit_root / f"{subject}_PINN_audit"
        audit_cfg = validate_audit_demographics(audit_dir, subject, demographics)
        sample_rate_hz = float(audit_cfg["fps"])
        for trial, path in sorted(fall_sample_files(fall_root, subject).items()):
            _, activity_id, _ = parse_trial(trial)
            source_ref = str(path.relative_to(fall_root.parent))
            try:
                skeleton, blank_rows = load_skeleton_csv(path)
                time_s, theta, x_m, coordinates = skeleton_to_theta_x(
                    skeleton,
                    demographics[subject]["sex"],
                    sample_rate_hz,
                    standing_frame=min(7, len(skeleton) - 1),
                    standing_radius=min(7, max(0, len(skeleton) - 1)),
                    pivot_frame=None,
                    end_frame=None,
                )
            except ValueError as exc:
                excluded.append(
                    {
                        "source_kind": "real_fall",
                        "source_file": source_ref,
                        "trial": trial,
                        "reason": str(exc).replace(str(path), source_ref),
                    }
                )
                continue
            if float(time_s[-1]) < minimum_duration_s:
                excluded.append(
                    {
                        "source_kind": "real_fall",
                        "source_file": source_ref,
                        "trial": trial,
                        "reason": (
                            f"full-recording duration {float(time_s[-1]):.3f} s is below "
                            f"{minimum_duration_s:.3f} s"
                        ),
                    }
                )
                continue
            sample_id = f"REAL_{trial}"
            data_file = save_trial(
                output_root,
                sample_id,
                "real_fall",
                time_s,
                theta,
                x_m,
                1,
                activity_id,
                demographics[subject]["mass_kg"],
                demographics[subject]["height_m"],
            )
            row = base_row(
                sample_id=sample_id,
                label=1,
                source_kind="real_fall",
                subject=subject,
                activity_id=activity_id,
                activity_name=activities[activity_id],
                trial=trial,
                demographics=demographics[subject],
                time_s=time_s,
                data_file=data_file,
            )
            row.update(
                {
                    "source_file": source_ref,
                    "source_sha256": sha256(path),
                    "coordinate_method": (
                        "adult segment-mass CoM; fixed first-0.5-s body frame and foot pivot; "
                        "complete real-fall recording"
                    ),
                    "audit_config": str(
                        (audit_dir / "configs" / f"{subject}.json").relative_to(audit_root)
                    ),
                    **coordinates,
                }
            )
            rows.append(row)
            if blank_rows:
                repairs.append(
                    {
                        "source_kind": "real_fall",
                        "trial": trial,
                        "source_file": source_ref,
                        "repair": "linear interpolation of wholly blank skeleton row",
                        "repaired_frame0": "|".join(map(str, blank_rows)),
                        "repaired_row_count": len(blank_rows),
                    }
                )
    return rows, excluded, repairs


def prepare_a11_real_falls(
    audit_root: Path,
    output_root: Path,
    demographics: dict[str, dict[str, Any]],
    activities: dict[int, str],
    minimum_duration_s: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    for subject in FALL_SUBJECTS:
        audit_dir = audit_root / f"{subject}_PINN_audit"
        audit_cfg = validate_audit_demographics(audit_dir, subject, demographics)
        phases_path = phase_file(audit_dir, subject)
        phases = load_a11_phases(phases_path, subject)
        files = preferred_a11_files(audit_dir, subject)
        for trial, path in sorted(files.items()):
            source_ref = str(path.relative_to(audit_root))
            marks = phases.get(trial)
            if marks is None:
                excluded.append(
                    {
                        "source_kind": "real_fall",
                        "source_file": source_ref,
                        "trial": trial,
                        "reason": "no complete manual A11 phase sequence; not model-ready",
                    }
                )
                continue
            try:
                skeleton, blank_rows = load_skeleton_csv(path)
                time_s, theta, x_m, coordinates = skeleton_to_theta_x(
                    skeleton,
                    demographics[subject]["sex"],
                    float(audit_cfg["fps"]),
                    standing_frame=marks["initial_standing"],
                    standing_radius=2,
                    pivot_frame=marks["fall_onset"],
                    end_frame=marks["apparent_contact"],
                )
            except ValueError as exc:
                excluded.append(
                    {
                        "source_kind": "real_fall",
                        "source_file": source_ref,
                        "trial": trial,
                        "reason": str(exc).replace(str(path), source_ref),
                    }
                )
                continue
            if float(time_s[-1]) < minimum_duration_s:
                excluded.append(
                    {
                        "source_kind": "real_fall",
                        "source_file": source_ref,
                        "trial": trial,
                        "reason": f"contact-clipped duration {float(time_s[-1]):.3f} s is below {minimum_duration_s:.3f} s",
                    }
                )
                continue
            sample_id = f"REAL_{trial}"
            data_file = save_trial(
                output_root,
                sample_id,
                "real_fall",
                time_s,
                theta,
                x_m,
                1,
                11,
                demographics[subject]["mass_kg"],
                demographics[subject]["height_m"],
            )
            row = base_row(
                sample_id=sample_id,
                label=1,
                source_kind="real_fall",
                subject=subject,
                activity_id=11,
                activity_name=activities[11],
                trial=trial,
                demographics=demographics[subject],
                time_s=time_s,
                data_file=data_file,
            )
            row.update(
                {
                    "source_file": source_ref,
                    "source_sha256": sha256(path),
                    "coordinate_method": "manual standing body frame; fixed foot pivot at marked fall onset; clipped through apparent contact",
                    "phase_file": str(phases_path.relative_to(audit_root)),
                    "initial_standing_frame0": marks["initial_standing"],
                    "fall_onset_frame0": marks["fall_onset"],
                    "apparent_contact_frame0": marks["apparent_contact"],
                    **coordinates,
                }
            )
            rows.append(row)
            if blank_rows:
                repairs.append(
                    {
                        "source_kind": "real_fall",
                        "trial": trial,
                        "source_file": source_ref,
                        "repair": "linear interpolation of wholly blank skeleton row",
                        "repaired_frame0": "|".join(map(str, blank_rows)),
                        "repaired_row_count": len(blank_rows),
                    }
                )
    return rows, excluded, repairs


def prepare_synthetic_falls(
    synthetic_root: Path,
    output_root: Path,
    demographics: dict[str, dict[str, Any]],
    activities: dict[int, str],
) -> list[dict[str, Any]]:
    manifest_file = synthetic_root / "outputs" / "trajectory_quality" / "final_approved_synthetic_manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    generation_root = manifest_file.parent / str(manifest["dataset_root_relative_to_manifest"])
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in manifest["samples"]:
        synthetic_id = str(item["synthetic_id"])
        if synthetic_id in seen:
            raise ValueError(f"Duplicate approved synthetic ID: {synthetic_id}")
        seen.add(synthetic_id)
        subject = str(item["source_subject"])
        if subject not in demographics:
            raise ValueError(f"No demographics for synthetic source subject {subject}")
        source_file = (generation_root / str(item["data_file"])).resolve()
        with np.load(source_file, allow_pickle=False) as data:
            valid = np.asarray(data["valid_mask"]) > 0.5
            time_s, theta, x_m = resample_signal(
                np.asarray(data["time_s"])[valid],
                np.asarray(data["synthetic_theta_rad"])[valid],
                np.asarray(data["synthetic_x_m"])[valid],
                30.0,
            )
        sample_id = f"SYN_{synthetic_id}"
        data_file = save_trial(
            output_root,
            sample_id,
            "synthetic_fall",
            time_s,
            theta,
            x_m,
            1,
            11,
            demographics[subject]["mass_kg"],
            demographics[subject]["height_m"],
        )
        row = base_row(
            sample_id=sample_id,
            label=1,
            source_kind="synthetic_fall",
            subject=subject,
            activity_id=11,
            activity_name=activities[11],
            trial=synthetic_id,
            demographics=demographics[subject],
            time_s=time_s,
            data_file=data_file,
        )
        row.update(
            {
                "source_file": str(source_file.relative_to(synthetic_root)),
                "source_sha256": sha256(source_file),
                "coordinate_method": "continuity-corrected Physics generator theta/x resampled from 100 Hz to 30 Hz",
                "source_real_trial": str(item["source_trial"]),
                "generator_fold": int(item["fold"]),
                "generator_rank": int(item["generator_rank"]),
                "generator_seed_index": int(item["seed_index"]),
                "generator_base_seed": int(item["base_optimization_seed"]),
                "quality_approved": True,
            }
        )
        rows.append(row)
    if len(rows) != int(manifest["approved_count"]):
        raise ValueError("Approved synthetic manifest count does not match materialized rows")
    return rows


def membership_rows(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in samples:
        kind = str(row["source_kind"])
        result.append(
            {
                "sample_id": row["sample_id"],
                "label": row["label"],
                "source_kind": kind,
                "split_group": row["split_group"],
                "real_falls_plus_real_adl": kind in {"real_adl", "real_fall"},
                "synthetic_physics_falls_plus_real_adl": kind in {"real_adl", "synthetic_fall"},
                "real_and_synthetic_falls_plus_real_adl": True,
            }
        )
    return result


def summary_rows(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        grouped[(str(row["source_kind"]), int(row["activity_id"]), str(row["activity_name"]))].append(row)
    result = []
    for (kind, activity_id, activity_name), rows in sorted(grouped.items()):
        durations = np.asarray([float(row["duration_s"]) for row in rows])
        result.append(
            {
                "source_kind": kind,
                "label": int(rows[0]["label"]),
                "activity_id": activity_id,
                "activity_name": activity_name,
                "sample_count": len(rows),
                "subject_count": len({str(row["subject"]) for row in rows}),
                "minimum_duration_s": float(np.min(durations)),
                "median_duration_s": float(np.median(durations)),
                "maximum_duration_s": float(np.max(durations)),
            }
        )
    return result


def resolved_path(override: Path | None, project_root: Path, default_name: str) -> Path:
    return (override if override is not None else project_root / default_name).expanduser().resolve()


def require_input(path: Path, label: str, *, directory: bool) -> None:
    exists = path.is_dir() if directory else path.is_file()
    if not exists:
        kind = "directory" if directory else "file"
        raise FileNotFoundError(f"Missing {label} {kind}: {path}")


def initialize_output(output_root: Path, overwrite: bool, project_root: Path) -> None:
    if output_root.exists() and any(output_root.iterdir()):
        if not overwrite:
            raise FileExistsError(f"{output_root} is not empty; pass --overwrite")
        protected = {Path("/").resolve(), HERE.resolve(), HERE.parent.resolve(), project_root.resolve()}
        if output_root.resolve() in protected:
            raise ValueError(f"Refusing to remove protected output path: {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=HERE.parent,
        help="PINN-FallDetection-Init root; sibling input paths are discovered from here",
    )
    parser.add_argument("--adl-root", type=Path, help="default: PROJECT_ROOT/ADLSamples")
    parser.add_argument("--fall-root", type=Path, help="default: PROJECT_ROOT/FallSamples")
    parser.add_argument("--audit-root", type=Path, help="default: PROJECT_ROOT")
    parser.add_argument(
        "--synthetic-results-root",
        type=Path,
        help="default: PROJECT_ROOT/Fifteen_Subject_DeepONet_Synthetic_Fall_Study",
    )
    parser.add_argument(
        "--demographics", type=Path, help="default: PROJECT_ROOT/human_subjects_demographics.csv"
    )
    parser.add_argument(
        "--activity-types", type=Path, help="default: PROJECT_ROOT/Activity_Types.md"
    )
    parser.add_argument("--output-dir", type=Path, default=HERE / "outputs")
    parser.add_argument("--minimum-real-fall-duration-s", type=float, default=0.4)
    parser.add_argument(
        "--real-fall-scope",
        choices=("all", "a11"),
        default="a11",
        help="a11 (default): audited front falls through contact; all: future A10-A14 study",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.expanduser().resolve()
    adl_root = resolved_path(args.adl_root, project_root, "ADLSamples")
    fall_root = resolved_path(args.fall_root, project_root, "FallSamples")
    audit_root = resolved_path(args.audit_root, project_root, ".")
    synthetic_root = resolved_path(
        args.synthetic_results_root,
        project_root,
        "Fifteen_Subject_DeepONet_Synthetic_Fall_Study",
    )
    demographics_path = resolved_path(
        args.demographics, project_root, "human_subjects_demographics.csv"
    )
    activity_types_path = resolved_path(args.activity_types, project_root, "Activity_Types.md")
    output_root = args.output_dir.expanduser().resolve()

    require_input(adl_root, "ADL skeleton", directory=True)
    if args.real_fall_scope == "all":
        require_input(fall_root, "real-fall skeleton", directory=True)
    require_input(audit_root, "audit root", directory=True)
    require_input(synthetic_root, "synthetic-study", directory=True)
    require_input(demographics_path, "demographics", directory=False)
    require_input(activity_types_path, "activity-types", directory=False)
    initialize_output(output_root, args.overwrite, project_root)
    manifest_file = output_root / "dataset_manifest.json"

    demographics = load_demographics(demographics_path)
    activities = load_activity_types(activity_types_path)
    required_demographics = set(FALL_SUBJECTS) | set(ADL_SUBJECTS)
    missing_demographics = required_demographics - set(demographics)
    if missing_demographics:
        raise ValueError(f"Missing demographics for {sorted(missing_demographics)}")

    adl_rows, adl_excluded, adl_repairs = prepare_adl(
        adl_root, output_root, demographics, activities
    )
    if args.real_fall_scope == "all":
        real_rows, real_excluded, real_repairs = prepare_all_real_falls(
            fall_root,
            audit_root,
            output_root,
            demographics,
            activities,
            args.minimum_real_fall_duration_s,
        )
    else:
        real_rows, real_excluded, real_repairs = prepare_a11_real_falls(
            audit_root,
            output_root,
            demographics,
            activities,
            args.minimum_real_fall_duration_s,
        )
    synthetic_rows = prepare_synthetic_falls(
        synthetic_root, output_root, demographics, activities
    )
    samples = adl_rows + real_rows + synthetic_rows
    sample_ids = [str(row["sample_id"]) for row in samples]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("Prepared sample IDs are not unique")

    memberships = membership_rows(samples)
    summaries = summary_rows(samples)
    exclusions = adl_excluded + real_excluded
    repairs = adl_repairs + real_repairs
    if args.real_fall_scope == "all":
        fall_inventory = real_fall_inventory(
            fall_root, activities, set(sample_ids), exclusions
        )
    else:
        fall_inventory = audited_a11_fall_inventory(
            audit_root, activities, set(sample_ids), exclusions
        )
    counts = Counter(str(row["source_kind"]) for row in samples)
    labels = Counter(int(row["label"]) for row in samples)
    study_counts = {
        name: sum(bool(row[name]) for row in memberships)
        for name in (
            "real_falls_plus_real_adl",
            "synthetic_physics_falls_plus_real_adl",
            "real_and_synthetic_falls_plus_real_adl",
        )
    }

    write_csv(output_root / "dataset_manifest.csv", samples)
    write_csv(output_root / "study_membership.csv", memberships)
    write_csv(output_root / "dataset_summary.csv", summaries)
    write_csv(output_root / "available_real_fall_inventory.csv", fall_inventory)
    if exclusions:
        write_csv(output_root / "excluded_samples.csv", exclusions)
    if repairs:
        write_csv(output_root / "repaired_rows.csv", repairs)
    payload = {
        "description": "Architecture-neutral 30 Hz theta/x CoM trajectories for binary fall detection",
        "created_for": "PINN Fall Detection downstream study",
        "sample_rate_hz": 30.0,
        "labels": {"0": "ADL", "1": "fall"},
        "canonical_features": ["theta_rad", "x_m"],
        "windowing_applied": False,
        "split_assignment_applied": False,
        "split_rule": "split by split_group/source subject before windowing or augmentation; all synthetic variants remain with their real source subject",
        "real_fall_scope": (
            "A10-A14 full raw recordings from FallSamples, minimum 0.40 s"
            if args.real_fall_scope == "all"
            else "A11 Frontfall only, complete manual phases, through apparent contact, minimum 0.40 s"
        ),
        "adl_scope": "A01-A03 and A05-A09; A04 absent; A08 treated as walking",
        "adl_subject_substitution": "S59 has no ADL; S31 is included as its replacement source but is never relabeled as S59",
        "counts": {
            "total": len(samples),
            "by_source_kind": dict(sorted(counts.items())),
            "by_label": {str(key): value for key, value in sorted(labels.items())},
            "excluded": len(exclusions),
            "repaired_source_trials": len(repairs),
            "available_real_fall_files_in_selected_scope": len(fall_inventory),
            "study_membership": study_counts,
        },
        "samples": samples,
    }
    dump_json(manifest_file, payload)
    dump_json(
        output_root / "integrity_report.json",
        {
            "finite_arrays": True,
            "unique_sample_ids": True,
            "sample_rate_hz": 30.0,
            "adl_subjects": sorted({row["subject"] for row in adl_rows}),
            "real_fall_subjects": sorted({row["subject"] for row in real_rows}),
            "synthetic_source_subjects": sorted({row["subject"] for row in synthetic_rows}),
            "empty_adl_files_excluded": sum("empty skeleton file" in row["reason"] for row in adl_excluded),
            "isolated_blank_rows_repaired": sum(int(row["repaired_row_count"]) for row in repairs),
            "exclusion_count": len(exclusions),
        },
    )
    print(f"Prepared {len(samples)} trials: {dict(sorted(counts.items()))}")
    print(f"Labels: {dict(sorted(labels.items()))}")
    print(f"Excluded: {len(exclusions)}; source trials with repairs: {len(repairs)}")
    print(f"Outputs: {output_root}")


if __name__ == "__main__":
    main()
