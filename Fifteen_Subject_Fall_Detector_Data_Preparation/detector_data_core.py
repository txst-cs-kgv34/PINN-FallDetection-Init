"""Shared parsing and CoM utilities for the detector-data preparation stage."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np


TRIAL_PATTERN = re.compile(r"^(S\d+)A(\d{2})T(\d{2})$")
FOOT_LEFT = 21
FOOT_RIGHT = 25
HEAD = 26
NOSE = 27
HIP_LEFT = 18
HIP_RIGHT = 22
SHOULDER_LEFT = 5
SHOULDER_RIGHT = 12


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_trial(stem: str) -> tuple[str, int, int]:
    match = TRIAL_PATTERN.fullmatch(stem)
    if not match:
        raise ValueError(f"Unrecognized trial identifier: {stem}")
    subject, activity, trial = match.groups()
    return subject, int(activity), int(trial)


def load_activity_types(path: Path) -> dict[int, str]:
    activities: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("*") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[1].isdigit():
            continue
        activities[int(cells[1])] = cells[0]
    expected = set(range(1, 15))
    if set(activities) != expected:
        raise ValueError(f"Activity table contains {sorted(activities)}, expected 1 through 14")
    return activities


def load_demographics(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            subject = str(row["Participant#"]).strip()
            if subject in result:
                raise ValueError(f"Duplicate demographics row for {subject}")
            height_in = 12.0 * float(row["Height(ft)"]) + float(row["(inch)"])
            result[subject] = {
                "subject": subject,
                "sex": str(row["Gender"]).strip().lower(),
                "mass_lb": float(row["Weight(lb)"]),
                "mass_kg": float(row["Weight(lb)"]) * 0.45359237,
                "height_in": height_in,
                "height_m": height_in * 0.0254,
            }
    return result


def load_skeleton_csv(
    path: Path, maximum_blank_run: int = 3
) -> tuple[np.ndarray, list[int]]:
    """Load 96-column skeleton rows and repair only short blank-row gaps."""
    rows: list[np.ndarray] = []
    blank_rows: list[int] = []
    for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines()):
        cells = line.split(",")
        if len(cells) != 96:
            raise ValueError(f"{path}: row {index + 1} has {len(cells)} columns, expected 96")
        stripped = [cell.strip() for cell in cells]
        if all(not cell for cell in stripped):
            rows.append(np.full(96, np.nan, dtype=np.float64))
            blank_rows.append(index)
            continue
        if any(not cell for cell in stripped):
            raise ValueError(f"{path}: row {index + 1} is partially blank")
        row = np.asarray([float(cell) for cell in stripped], dtype=np.float64)
        if not np.all(np.isfinite(row)):
            raise ValueError(f"{path}: row {index + 1} contains non-finite values")
        rows.append(row)
    if not rows:
        raise ValueError(f"{path}: empty skeleton file")
    data = np.vstack(rows)
    if blank_rows:
        longest_run = 1
        current_run = 1
        for previous, current in zip(blank_rows, blank_rows[1:]):
            current_run = current_run + 1 if current == previous + 1 else 1
            longest_run = max(longest_run, current_run)
        if longest_run > maximum_blank_run:
            raise ValueError(
                f"{path}: longest blank-row run is {longest_run} frames; "
                f"maximum repairable run is {maximum_blank_run}"
            )
        valid = np.flatnonzero(np.all(np.isfinite(data), axis=1))
        if len(valid) < 2:
            raise ValueError(f"{path}: fewer than two valid skeleton rows")
        indices = np.arange(len(data), dtype=np.float64)
        for column in range(data.shape[1]):
            data[:, column] = np.interp(indices, valid, data[valid, column])
    if not np.all(np.isfinite(data)):
        raise AssertionError(f"{path}: blank-row repair did not produce finite data")
    return data, blank_rows


def segment_model(sex: str) -> list[dict[str, Any]]:
    if sex not in ("male", "female"):
        raise ValueError(f"Unsupported adult segment model sex: {sex}")
    segments: list[dict[str, Any]] = [
        {"name": "head", "mass_fraction": 0.0694, "a": [26], "b": [26], "fraction": 0.0},
        {"name": "trunk", "mass_fraction": 0.4346, "a": [3], "b": [18, 22], "fraction": 0.5138},
    ]
    for side, upper, forearm, hand, thigh, shank, foot in [
        ("left", (5, 6), (6, 7), 8, (18, 19), (19, 20), (20, 21)),
        ("right", (12, 13), (13, 14), 15, (22, 23), (23, 24), (24, 25)),
    ]:
        for name, pair, mass, fraction in [
            ("upper_arm", upper, 0.0271, 0.5772),
            ("forearm", forearm, 0.0162, 0.4574),
            ("thigh", thigh, 0.1416, 0.4095),
            ("shank", shank, 0.0433, 0.4395),
        ]:
            segments.append(
                {"name": f"{name}_{side}", "mass_fraction": mass, "a": [pair[0]], "b": [pair[1]], "fraction": fraction}
            )
        segments.append(
            {"name": f"hand_{side}", "mass_fraction": 0.0061, "a": [hand], "b": [hand], "fraction": 0.0}
        )
        segments.append(
            {"name": f"foot_{side}", "mass_fraction": 0.0137, "a": [foot[0]], "b": [foot[1]], "fraction": 0.5}
        )
    if sex == "female":
        female = {
            "head": (0.0668, 0.0),
            "trunk": (0.4257, 0.4964),
            "upper_arm": (0.0255, 0.5754),
            "forearm": (0.0138, 0.4559),
            "hand": (0.0056, 0.0),
            "thigh": (0.1478, 0.3612),
            "shank": (0.0481, 0.4352),
            "foot": (0.0129, 0.5),
        }
        for segment in segments:
            base = segment["name"].removesuffix("_left").removesuffix("_right")
            segment["mass_fraction"], segment["fraction"] = female[base]
        total = sum(float(segment["mass_fraction"]) for segment in segments)
        for segment in segments:
            segment["mass_fraction"] = float(segment["mass_fraction"]) / total
    return segments


def com_proxy(pose_m: np.ndarray, segments: list[dict[str, Any]]) -> np.ndarray:
    positions = np.stack(
        [
            (1.0 - float(segment["fraction"])) * pose_m[:, segment["a"]].mean(axis=1)
            + float(segment["fraction"]) * pose_m[:, segment["b"]].mean(axis=1)
            for segment in segments
        ],
        axis=1,
    )
    weights = np.asarray([segment["mass_fraction"] for segment in segments])
    return np.sum(positions * weights[None, :, None], axis=1)


def _normalize(vector: np.ndarray, label: str) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm < 1e-8:
        raise ValueError(f"Cannot define {label}; vector norm={norm}")
    return vector / norm


def body_frame(pose_m: np.ndarray, center_frame: int, radius: int) -> dict[str, Any]:
    if not 0 <= center_frame < len(pose_m):
        raise ValueError(f"Body-frame center {center_frame} is outside {len(pose_m)} frames")
    start = max(0, center_frame - radius)
    stop = min(len(pose_m), center_frame + radius + 1)
    standing = np.median(pose_m[start:stop], axis=0)
    origin = 0.5 * (standing[FOOT_LEFT] + standing[FOOT_RIGHT])
    vertical = _normalize(standing[HEAD] - origin, "standing vertical")
    lateral_raw = standing[HIP_RIGHT] - standing[HIP_LEFT]
    lateral_raw -= np.dot(lateral_raw, vertical) * vertical
    if np.linalg.norm(lateral_raw) < 1e-8:
        lateral_raw = standing[SHOULDER_RIGHT] - standing[SHOULDER_LEFT]
        lateral_raw -= np.dot(lateral_raw, vertical) * vertical
    lateral = _normalize(lateral_raw, "standing lateral")
    forward = _normalize(np.cross(lateral, vertical), "standing forward")
    nose = standing[NOSE] - standing[HEAD]
    nose -= np.dot(nose, vertical) * vertical + np.dot(nose, lateral) * lateral
    if np.linalg.norm(nose) >= 1e-8 and np.dot(forward, nose) < 0.0:
        forward = -forward
    basis = np.column_stack([lateral, vertical, forward])
    if not np.allclose(basis.T @ basis, np.eye(3), atol=1e-8):
        raise ValueError("Body-frame basis is not orthonormal")
    return {"origin": origin, "basis": basis, "start": start, "stop": stop}


def skeleton_to_theta_x(
    skeleton_mm: np.ndarray,
    sex: str,
    sample_rate_hz: float,
    standing_frame: int,
    standing_radius: int,
    pivot_frame: int | None,
    end_frame: int | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    pose_m = skeleton_mm.reshape(-1, 32, 3) * 0.001
    if end_frame is not None:
        if not 0 <= end_frame < len(pose_m):
            raise ValueError(f"End frame {end_frame} is outside {len(pose_m)} frames")
        pose_m = pose_m[: end_frame + 1]
    frame = body_frame(pose_m, min(standing_frame, len(pose_m) - 1), standing_radius)
    origin = frame["origin"]
    basis = frame["basis"]
    com_body = (com_proxy(pose_m, segment_model(sex)) - origin) @ basis
    left_foot = (pose_m[:, FOOT_LEFT] - origin) @ basis
    right_foot = (pose_m[:, FOOT_RIGHT] - origin) @ basis
    foot_midpoint = 0.5 * (left_foot + right_foot)
    baseline_samples = min(len(pose_m), max(1, int(round(0.5 * sample_rate_hz))))
    if pivot_frame is None:
        pivot = np.median(foot_midpoint[:baseline_samples], axis=0)
        pivot_semantics = "median foot midpoint during first 0.5 s"
    else:
        if not 0 <= pivot_frame < len(pose_m):
            raise ValueError(f"Pivot frame {pivot_frame} is outside {len(pose_m)} frames")
        pivot = foot_midpoint[pivot_frame]
        pivot_semantics = f"foot midpoint at manually marked onset frame {pivot_frame}"
    relative = com_body - pivot
    x_m = relative[:, 2]
    vertical_m = relative[:, 1]
    theta_rad = np.unwrap(np.arctan2(x_m, vertical_m))
    x_m = x_m - np.median(x_m[:baseline_samples])
    time_s = np.arange(len(theta_rad), dtype=np.float64) / float(sample_rate_hz)
    metadata = {
        "body_frame_start_frame0": int(frame["start"]),
        "body_frame_end_frame0": int(frame["stop"] - 1),
        "pivot_semantics": pivot_semantics,
    }
    return (
        time_s.astype(np.float32),
        theta_rad.astype(np.float32),
        x_m.astype(np.float32),
        metadata,
    )


def resample_signal(
    time_s: np.ndarray,
    theta_rad: np.ndarray,
    x_m: np.ndarray,
    target_rate_hz: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    time = np.asarray(time_s, dtype=np.float64)
    theta = np.asarray(theta_rad, dtype=np.float64)
    x_position = np.asarray(x_m, dtype=np.float64)
    if len(time) < 2 or not (len(time) == len(theta) == len(x_position)):
        raise ValueError("Resampling requires matching arrays with at least two samples")
    if not np.all(np.diff(time) > 0.0):
        raise ValueError("Resampling time must be strictly increasing")
    duration = float(time[-1] - time[0])
    count = int(np.floor(duration * target_rate_hz + 1e-8)) + 1
    target = np.arange(count, dtype=np.float64) / target_rate_hz + time[0]
    return (
        (target - target[0]).astype(np.float32),
        np.interp(target, time, theta).astype(np.float32),
        np.interp(target, time, x_position).astype(np.float32),
    )
