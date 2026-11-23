#!/usr/bin/env python3
"""Shared data and coordinate utilities for A10-A14 detector preparation."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import numpy as np


TRIAL_RE = re.compile(r"^(S\d+)A(\d{2})T(\d{2})$")
FOOT_LEFT, FOOT_RIGHT, HEAD, NOSE = 21, 25, 26, 27
HIP_LEFT, HIP_RIGHT, SHOULDER_LEFT, SHOULDER_RIGHT = 18, 22, 5, 12
PLANAR_AXES = {
    "A10": np.asarray([0.0, -1.0]),
    "A11": np.asarray([0.0, 1.0]),
    "A12": np.asarray([-1.0, 0.0]),
    "A13": np.asarray([1.0, 0.0]),
}


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def parse_trial(value: str) -> tuple[str, int, int]:
    match = TRIAL_RE.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid trial identifier: {value}")
    subject, activity, trial = match.groups()
    return subject, int(activity), int(trial)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty table: {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_demographics(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            subject = row["Participant#"].strip()
            height_in = 12.0 * float(row["Height(ft)"]) + float(row["(inch)"])
            result[subject] = {
                "sex": row["Gender"].strip().lower(),
                "mass_kg": float(row["Weight(lb)"]) * 0.45359237,
                "height_m": height_in * 0.0254,
            }
    return result


def load_activity_types(path: Path) -> dict[int, str]:
    result: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("*") for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[1].isdigit():
            result[int(cells[1])] = cells[0]
    if set(result) != set(range(1, 15)):
        raise ValueError("Activity_Types.md must define activities 1 through 14")
    return result


def load_skeleton_csv(path: Path, maximum_blank_run: int = 3) -> tuple[np.ndarray, list[int]]:
    rows: list[np.ndarray] = []
    blanks: list[int] = []
    for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines()):
        cells = [cell.strip() for cell in line.split(",")]
        if len(cells) != 96:
            raise ValueError(f"{path}: row {index + 1} has {len(cells)} columns, expected 96")
        if all(not cell for cell in cells):
            rows.append(np.full(96, np.nan))
            blanks.append(index)
        elif any(not cell for cell in cells):
            raise ValueError(f"{path}: row {index + 1} is partially blank")
        else:
            values = np.asarray([float(cell) for cell in cells], dtype=np.float64)
            if not np.all(np.isfinite(values)):
                raise ValueError(f"{path}: row {index + 1} contains non-finite values")
            rows.append(values)
    if not rows:
        raise ValueError(f"{path}: empty skeleton file")
    data = np.vstack(rows)
    if blanks:
        longest = run = 1
        for previous, current in zip(blanks, blanks[1:]):
            run = run + 1 if current == previous + 1 else 1
            longest = max(longest, run)
        if longest > maximum_blank_run:
            raise ValueError(f"{path}: blank-row run {longest} exceeds {maximum_blank_run}")
        valid = np.flatnonzero(np.all(np.isfinite(data), axis=1))
        if len(valid) < 2:
            raise ValueError(f"{path}: fewer than two numeric skeleton rows")
        indices = np.arange(len(data), dtype=np.float64)
        for column in range(96):
            data[:, column] = np.interp(indices, valid, data[valid, column])
    return data, blanks


def segment_model(sex: str) -> list[dict[str, Any]]:
    if sex not in {"male", "female"}:
        raise ValueError(f"Unsupported segment-model sex: {sex}")
    segments: list[dict[str, Any]] = [
        {"name": "head", "mass": 0.0694, "a": [26], "b": [26], "fraction": 0.0},
        {"name": "trunk", "mass": 0.4346, "a": [3], "b": [18, 22], "fraction": 0.5138},
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
            segments.append({"name": f"{name}_{side}", "mass": mass, "a": [pair[0]], "b": [pair[1]], "fraction": fraction})
        segments.append({"name": f"hand_{side}", "mass": 0.0061, "a": [hand], "b": [hand], "fraction": 0.0})
        segments.append({"name": f"foot_{side}", "mass": 0.0137, "a": [foot[0]], "b": [foot[1]], "fraction": 0.5})
    if sex == "female":
        female = {
            "head": (0.0668, 0.0), "trunk": (0.4257, 0.4964),
            "upper_arm": (0.0255, 0.5754), "forearm": (0.0138, 0.4559),
            "hand": (0.0056, 0.0), "thigh": (0.1478, 0.3612),
            "shank": (0.0481, 0.4352), "foot": (0.0129, 0.5),
        }
        for segment in segments:
            base = segment["name"].removesuffix("_left").removesuffix("_right")
            segment["mass"], segment["fraction"] = female[base]
        total = sum(float(segment["mass"]) for segment in segments)
        for segment in segments:
            segment["mass"] = float(segment["mass"]) / total
    return segments


def com_proxy(pose_m: np.ndarray, sex: str) -> np.ndarray:
    segments = segment_model(sex)
    positions = np.stack([
        (1.0 - float(item["fraction"])) * pose_m[:, item["a"]].mean(axis=1)
        + float(item["fraction"]) * pose_m[:, item["b"]].mean(axis=1)
        for item in segments
    ], axis=1)
    weights = np.asarray([item["mass"] for item in segments])
    return np.sum(positions * weights[None, :, None], axis=1)


def _normalize(vector: np.ndarray, name: str) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm < 1e-8:
        raise ValueError(f"Cannot define {name}; norm={norm}")
    return vector / norm


def standing_frame(pose_m: np.ndarray, center: int, radius: int) -> dict[str, np.ndarray | int]:
    start, stop = max(0, center - radius), min(len(pose_m), center + radius + 1)
    standing = np.median(pose_m[start:stop], axis=0)
    origin = 0.5 * (standing[FOOT_LEFT] + standing[FOOT_RIGHT])
    vertical = _normalize(standing[HEAD] - origin, "standing vertical")
    lateral = standing[HIP_RIGHT] - standing[HIP_LEFT]
    lateral -= np.dot(lateral, vertical) * vertical
    if np.linalg.norm(lateral) < 1e-8:
        lateral = standing[SHOULDER_RIGHT] - standing[SHOULDER_LEFT]
        lateral -= np.dot(lateral, vertical) * vertical
    lateral = _normalize(lateral, "standing lateral")
    forward = _normalize(np.cross(lateral, vertical), "standing forward")
    nose = standing[NOSE] - standing[HEAD]
    nose -= np.dot(nose, vertical) * vertical + np.dot(nose, lateral) * lateral
    if np.linalg.norm(nose) >= 1e-8 and np.dot(forward, nose) < 0.0:
        forward = -forward
    return {"origin": origin, "basis": np.column_stack([lateral, vertical, forward]), "start": start, "stop": stop}


def to_body(points: np.ndarray, frame: dict[str, Any]) -> np.ndarray:
    return (points - frame["origin"]) @ frame["basis"]


def yaw_from_pose(pose_body: np.ndarray, center: int, radius: int) -> np.ndarray:
    lateral = 0.5 * ((pose_body[:, 12] - pose_body[:, 5]) + (pose_body[:, 22] - pose_body[:, 18]))
    yaw = np.unwrap(np.arctan2(lateral[:, 2], lateral[:, 0]))
    start, stop = max(0, center - radius), min(len(yaw), center + radius + 1)
    return yaw - float(np.median(yaw[start:stop]))


def fall_signals(skeleton_mm: np.ndarray, row: dict[str, str]) -> dict[str, np.ndarray | float | str]:
    pose_m = skeleton_mm.reshape(-1, 32, 3) * 0.001
    standing = int(row["initial_standing_frame0"])
    onset = int(row["fall_onset_frame0"])
    contact = int(row["apparent_contact_frame0"])
    if not 0 <= standing < onset < contact < len(pose_m):
        raise ValueError(f"{row['trial']}: invalid phase bounds")
    frame = standing_frame(pose_m, standing, 2)
    pose_body = to_body(pose_m, frame)
    com_body = to_body(com_proxy(pose_m, row["sex"].lower()), frame)
    feet = 0.5 * (pose_body[:, FOOT_LEFT] + pose_body[:, FOOT_RIGHT])
    pivot = feet[onset]
    activity = row["activity"]
    if activity in PLANAR_AXES:
        direction = PLANAR_AXES[activity]
        direction_source = "activity_identity"
    elif activity == "A14":
        direction = com_body[contact, [0, 2]] - com_body[onset, [0, 2]]
        direction = _normalize(direction, f"{row['trial']} onset-to-contact direction")
        direction_source = "onset_to_contact"
    else:
        raise ValueError(f"Unsupported fall activity: {activity}")
    relative = com_body[:, [0, 2]] - pivot[[0, 2]]
    x_raw = relative @ direction
    vertical = com_body[:, 1] - pivot[1]
    theta = np.unwrap(np.arctan2(x_raw, vertical))
    yaw = yaw_from_pose(pose_body, standing, 2)
    count = contact + 1
    theta, x_m, yaw = theta[:count], x_raw[:count], yaw[:count]
    baseline = min(count, 15)
    x_m = x_m - float(np.median(x_m[:baseline]))
    yaw = yaw - float(np.median(yaw[:baseline]))
    return {
        "time_s": np.arange(count, dtype=np.float32) / 30.0,
        "theta_rad": theta.astype(np.float32),
        "x_m": x_m.astype(np.float32),
        "yaw_rad": yaw.astype(np.float32),
        "direction_lateral": float(direction[0]),
        "direction_forward": float(direction[1]),
        "direction_source": direction_source,
    }


def adl_signals(skeleton_mm: np.ndarray, sex: str) -> dict[str, np.ndarray]:
    pose_m = skeleton_mm.reshape(-1, 32, 3) * 0.001
    center, radius = min(7, len(pose_m) - 1), min(7, max(0, len(pose_m) - 1))
    frame = standing_frame(pose_m, center, radius)
    pose_body = to_body(pose_m, frame)
    com_body = to_body(com_proxy(pose_m, sex), frame)
    feet = 0.5 * (pose_body[:, FOOT_LEFT] + pose_body[:, FOOT_RIGHT])
    baseline = min(len(pose_m), 15)
    pivot = np.median(feet[:baseline], axis=0)
    x_raw = com_body[:, 2] - pivot[2]
    vertical = com_body[:, 1] - pivot[1]
    theta = np.unwrap(np.arctan2(x_raw, vertical))
    x_m = x_raw - float(np.median(x_raw[:baseline]))
    yaw = yaw_from_pose(pose_body, center, radius)
    return {
        "time_s": np.arange(len(pose_m), dtype=np.float32) / 30.0,
        "theta_rad": theta.astype(np.float32),
        "x_m": x_m.astype(np.float32),
        "yaw_rad": yaw.astype(np.float32),
    }


def resample_valid(time_s: np.ndarray, *signals: np.ndarray, target_hz: float = 30.0) -> tuple[np.ndarray, ...]:
    time = np.asarray(time_s, dtype=np.float64)
    if len(time) < 2 or not np.all(np.diff(time) > 0.0):
        raise ValueError("Resampling requires a strictly increasing time vector")
    count = int(np.floor((time[-1] - time[0]) * target_hz + 1e-8)) + 1
    target = np.arange(count, dtype=np.float64) / target_hz + time[0]
    output: list[np.ndarray] = [(target - target[0]).astype(np.float32)]
    for signal in signals:
        values = np.asarray(signal, dtype=np.float64)
        if len(values) != len(time):
            raise ValueError("Signal/time length mismatch")
        output.append(np.interp(target, time, values).astype(np.float32))
    return tuple(output)


def ratio_policies(fall_batch_size: int = 10) -> dict[str, dict[str, int | float]]:
    if fall_batch_size <= 0 or fall_batch_size % 10:
        raise ValueError("fall_batch_size must be a positive multiple of 10")
    return {
        "real_only": {"real_fraction": 1.0, "synthetic_fraction": 0.0, "real_per_fall_batch": fall_batch_size, "synthetic_per_fall_batch": 0},
        "real60_synthetic40": {"real_fraction": 0.6, "synthetic_fraction": 0.4, "real_per_fall_batch": 6 * fall_batch_size // 10, "synthetic_per_fall_batch": 4 * fall_batch_size // 10},
        "real40_synthetic60": {"real_fraction": 0.4, "synthetic_fraction": 0.6, "real_per_fall_batch": 4 * fall_batch_size // 10, "synthetic_per_fall_batch": 6 * fall_batch_size // 10},
    }
