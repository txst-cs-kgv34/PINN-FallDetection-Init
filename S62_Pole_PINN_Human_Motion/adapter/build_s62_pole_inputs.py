#!/usr/bin/env python3
"""Convert S62 A11 skeleton trials into the unchanged pole loader format.

This file is an upstream adapter. It does not import or modify the PINN.
The output TSVs contain two synthetic marker points whose geometry encodes the
human-derived theta(t) and x(t) signals expected by read_tsv() in the supplied
pole script.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from skeleton_model import com_proxy, segment_model
from subject_frame import standing_body_frame, to_subject_frame


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "S62.json"
PHASE_PATH = ROOT / "config" / "S62_A11_phase_notes.json"
SCOPE_PATH = ROOT / "config" / "S62_A11_experiment_scope.json"
RAW_DIR = ROOT / "data" / "raw"
TSV_DIR = ROOT / "data" / "pole_compatible" / "A11"
DERIVED_DIR = ROOT / "data" / "derived" / "A11"
MANIFEST_PATH = ROOT / "results" / "adapter_manifest.json"

TARGET_RATE_HZ = 250
POLE_LOADER_WARMUP_ROWS = 1024
ENCODING_LENGTH_MM = 570.0
FORWARD_AXIS_INDEX = 2
VERTICAL_AXIS_INDEX = 1
STANDING_RADIUS_FRAMES = 2


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def phase_windows(payload: dict, scope: dict) -> list[dict]:
    grouped: dict[str, dict[str, int]] = {}
    for note in payload["notes"]:
        grouped.setdefault(note["trial"], {})[note["phase"]] = int(note["frame0"])
    included = scope["included_trials"]
    windows = []
    for trial in included:
        marks = grouped[trial]
        required = {"initial_standing", "fall_onset", "apparent_contact"}
        missing = required.difference(marks)
        if missing:
            raise ValueError(f"{trial} is missing phase marks: {sorted(missing)}")
        windows.append(
            {
                "trial": trial,
                "initial_standing_frame0": marks["initial_standing"],
                "fall_onset_frame0": marks["fall_onset"],
                "apparent_contact_frame0": marks["apparent_contact"],
            }
        )
    return windows


def interpolate_to_rate(signal: np.ndarray, source_rate: float, target_rate: float) -> np.ndarray:
    """Linearly interpolate without adding a separate smoothing operation."""
    duration = (len(signal) - 1) / source_rate
    count = int(round(duration * target_rate)) + 1
    source_time = np.arange(len(signal), dtype=np.float64) / source_rate
    target_time = np.arange(count, dtype=np.float64) / target_rate
    target_time[-1] = min(target_time[-1], source_time[-1])
    return np.interp(target_time, source_time, signal)


def encode_as_two_markers(theta_rad: np.ndarray, x_m: np.ndarray) -> np.ndarray:
    """Create six marker columns decoded by the original pole read_tsv()."""
    x2_mm = 1000.0 * x_m
    y2_mm = np.zeros_like(x2_mm)
    z2_mm = np.zeros_like(x2_mm)
    x1_mm = x2_mm + ENCODING_LENGTH_MM * np.sin(theta_rad)
    y1_mm = y2_mm + ENCODING_LENGTH_MM * np.cos(theta_rad)
    z1_mm = np.zeros_like(x2_mm)
    return np.column_stack([x1_mm, y1_mm, z1_mm, x2_mm, y2_mm, z2_mm])


def build_trial(window: dict, subject: dict, segments: list[dict]) -> dict:
    trial = window["trial"]
    raw_path = RAW_DIR / f"{trial}.csv"
    raw = np.loadtxt(raw_path, delimiter=",", ndmin=2)
    if raw.shape[1] != 96:
        raise ValueError(f"{raw_path} has shape {raw.shape}; expected 96 columns")
    scale = {"mm": 0.001, "m": 1.0}[subject["coordinate_units"]]
    pose_m = raw.reshape(-1, 32, 3) * scale

    standing = window["initial_standing_frame0"]
    onset = window["fall_onset_frame0"]
    contact = window["apparent_contact_frame0"]
    if not 0 <= standing < onset < contact < len(pose_m):
        raise ValueError(f"invalid phase order for {trial}")

    # No Butterworth filter or learned/smoothed nuisance torque is used here.
    frame = standing_body_frame(pose_m, standing, radius=STANDING_RADIUS_FRAMES)
    com_camera_m = com_proxy(pose_m, segments)[0]
    com_body_m = to_subject_frame(com_camera_m, frame)
    left_foot_body_m = to_subject_frame(pose_m[:, 21], frame)
    right_foot_body_m = to_subject_frame(pose_m[:, 25], frame)
    foot_midpoint_m = 0.5 * (left_foot_body_m + right_foot_body_m)

    # Fixed foot midpoint at marked onset supplies the origin needed to define
    # a human CoM angle. This is input construction, not a PINN equation change.
    pivot_m = foot_midpoint_m[onset]
    relative = com_body_m[:, [FORWARD_AXIS_INDEX, VERTICAL_AXIS_INDEX]] - pivot_m[
        [FORWARD_AXIS_INDEX, VERTICAL_AXIS_INDEX]
    ]
    relative = relative[: contact + 1]
    x_m = relative[:, 0]
    vertical_m = relative[:, 1]
    theta_rad = np.unwrap(np.arctan2(x_m, vertical_m))

    # The preserved loader recovers theta with arcsin and therefore cannot
    # represent |theta| >= 89 degrees without folding the signal. If a clip
    # reaches that range only after the loader's 20-degree training cutoff,
    # truncate the unused tail. This cannot change the samples seen in
    # training; an earlier 89-degree crossing remains a hard error.
    threshold = math.radians(20.0)
    crossings_20 = np.flatnonzero(np.abs(theta_rad) >= threshold)
    crossings_89 = np.flatnonzero(np.abs(theta_rad) >= math.radians(89.0))
    compatibility_trim_frame0 = None
    if len(crossings_89):
        first_89 = int(crossings_89[0])
        first_20 = int(crossings_20[0]) if len(crossings_20) else None
        if first_20 is None or first_89 <= first_20:
            raise ValueError(f"{trial} exceeds the arcsin-compatible range before the training cutoff")
        compatibility_trim_frame0 = first_89
        theta_rad = theta_rad[:first_89]
        x_m = x_m[:first_89]
        vertical_m = vertical_m[:first_89]

    fps = float(subject["fps"])
    theta_250 = interpolate_to_rate(theta_rad, fps, TARGET_RATE_HZ)
    x_250 = interpolate_to_rate(x_m, fps, TARGET_RATE_HZ)
    encoded = encode_as_two_markers(theta_250, x_250)

    decoded_length = np.linalg.norm(encoded[:, :3] - encoded[:, 3:], axis=1)
    decoded_theta = np.arcsin(
        np.clip((encoded[:, 0] - encoded[:, 3]) / decoded_length, -1.0, 1.0)
    )
    decoded_x = encoded[:, 3] * 0.001
    if not np.allclose(decoded_theta, theta_250, atol=1e-10, rtol=0.0):
        raise AssertionError(f"theta encoding check failed for {trial}")
    if not np.allclose(decoded_x, x_250, atol=1e-12, rtol=0.0):
        raise AssertionError(f"x encoding check failed for {trial}")

    # The original loader discards the first 1024 rows. Padding is removed
    # before resampling/training and therefore never becomes a model sample.
    padding = np.repeat(encoded[:1], POLE_LOADER_WARMUP_ROWS, axis=0)
    pole_input = np.vstack([padding, encoded])
    tsv_path = TSV_DIR / f"SubjectB_{trial}.tsv"
    np.savetxt(tsv_path, pole_input, delimiter="\t", fmt="%.10f")

    time_s = np.arange(len(theta_rad), dtype=np.float64) / fps
    derived_path = DERIVED_DIR / f"{trial}_human_theta_x.csv"
    derived = np.column_stack(
        [time_s, theta_rad, np.degrees(theta_rad), x_m, vertical_m]
    )
    np.savetxt(
        derived_path,
        derived,
        delimiter=",",
        header="time_s,theta_rad,theta_deg,x_forward_m,com_vertical_m",
        comments="",
        fmt="%.10f",
    )

    crossings = np.flatnonzero(np.abs(theta_rad) >= threshold)
    first_crossing_s = float(crossings[0] / fps) if len(crossings) else None
    return {
        "trial": trial,
        "raw_file": str(raw_path.relative_to(ROOT)),
        "raw_sha256": sha256(raw_path),
        "pole_input_file": str(tsv_path.relative_to(ROOT)),
        "derived_signal_file": str(derived_path.relative_to(ROOT)),
        "raw_frames_used": int(len(theta_rad)),
        "requested_contact_frame0": contact,
        "arcsin_compatibility_trim_frame0": compatibility_trim_frame0,
        "training_samples_changed_by_compatibility_trim": False,
        "source_rate_hz": fps,
        "encoded_rate_hz": TARGET_RATE_HZ,
        "encoded_signal_rows": int(len(encoded)),
        "total_tsv_rows": int(len(pole_input)),
        "theta_min_deg": float(np.degrees(theta_rad).min()),
        "theta_max_deg": float(np.degrees(theta_rad).max()),
        "x_min_m": float(x_m.min()),
        "x_max_m": float(x_m.max()),
        "first_abs_theta_20deg_s_from_clip_start": first_crossing_s,
        "initial_standing_frame0": standing,
        "fall_onset_frame0": onset,
        "apparent_contact_frame0": contact,
        "fixed_pivot_subject_frame_m": pivot_m.tolist(),
        "tsv_sha256": sha256(tsv_path),
    }


def main() -> None:
    subject = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    phases = json.loads(PHASE_PATH.read_text(encoding="utf-8"))
    scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    if subject["subject_id"] != "S62" or subject["sex"] != "male":
        raise ValueError("this experiment is locked to male subject S62")
    if phases["subject"] != "S62" or scope["subject"] != "S62":
        raise ValueError("phase notes and experiment scope must both target S62")

    TSV_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    segments = segment_model(subject["sex"])
    trials = [build_trial(w, subject, segments) for w in phase_windows(phases, scope)]

    expected_files = sorted(Path(item["pole_input_file"]).name for item in trials)
    actual_files = sorted(path.name for path in TSV_DIR.glob("SubjectB_*.tsv"))
    if actual_files != expected_files:
        missing = sorted(set(expected_files) - set(actual_files))
        unexpected = sorted(set(actual_files) - set(expected_files))
        raise RuntimeError(
            f"subject input inventory mismatch after adapter build: missing={missing}; "
            f"unexpected={unexpected}. Extract the corrected project into a clean directory."
        )

    manifest = {
        "experiment": "S62 A11 human motion through unchanged pole PINN pipeline",
        "subject": {
            "id": subject["subject_id"],
            "sex": subject["sex"],
            "mass_lb": subject["mass_lb"],
            "mass_kg": subject["mass_lb"] * 0.45359237,
            "height_in": subject["height_in"],
            "height_m": subject["height_in"] * 0.0254,
            "skeleton_rate_hz": subject["fps"],
        },
        "input_definition": {
            "theta": "atan2(forward CoM, vertical CoM) relative to fixed foot midpoint at marked fall onset",
            "x": "subject-forward whole-body CoM coordinate relative to the same fixed onset foot midpoint; original pole loader subsequently centers its first 0.5 s",
            "com": "male segment-mass-weighted CoM from 32 Azure Kinect joints",
            "signal_filter": "none; only linear interpolation from 30 Hz to the pole loader's required 250 Hz input rate",
            "activity": "A11 Frontfall only",
        },
        "pole_compatibility": {
            "columns": ["x1_mm", "y1_mm", "z1_mm", "x2_mm", "y2_mm", "z2_mm"],
            "encoding_length_mm": ENCODING_LENGTH_MM,
            "warmup_rows_removed_by_original_loader": POLE_LOADER_WARMUP_ROWS,
            "file_pattern": "SubjectB_*.tsv",
            "filename_note": "SubjectB_ is the unchanged source loader's filename contract; these files contain S62 data.",
        },
        "core_pipeline": {
            "file": "source/pinn_pole_synthetic_data_generation.py",
            "sha256": sha256(ROOT / "source" / "pinn_pole_synthetic_data_generation.py"),
            "modified": False,
        },
        "trials": trials,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(trials)} pole-compatible A11 inputs")
    print(f"Manifest: {MANIFEST_PATH}")
    for item in trials:
        print(
            f"  {item['trial']}: {item['total_tsv_rows']} rows, "
            f"first |theta|>=20 deg at {item['first_abs_theta_20deg_s_from_clip_start']:.3f} s"
        )


if __name__ == "__main__":
    main()
