#!/usr/bin/env python3
"""Prepare strict-primary A10-A13 trials in activity-defined body axes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from audit_adapter.skeleton_model import com_proxy, segment_model
from audit_adapter.subject_frame import standing_body_frame, to_subject_frame


ROOT = Path(__file__).resolve().parent
ACTIVITY_INDEX = {"A10": 0, "A11": 1, "A12": 2, "A13": 3}


def load_config(path: str | Path) -> dict:
    source = Path(path).expanduser().resolve()
    value = json.loads(source.read_text(encoding="utf-8"))
    value["_root"] = str(source.parent)
    return value


def resolve(config: dict, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(config["_root"]) / path
    return path.resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def bool_field(row: dict[str, str], name: str) -> bool:
    return str(row.get(name, "")).strip().lower() in {"1", "true", "yes"}


def locate_raw_trial(audit_dir: Path, subject: str, trial: str) -> Path:
    candidates = [
        audit_dir / "repaired_data" / subject / f"{trial}.csv",
        audit_dir / "findings" / f"{subject}_audit_repaired" / "raw" / f"{trial}.csv",
        audit_dir / "findings" / f"{subject}_audit" / "raw" / f"{trial}.csv",
    ]
    candidates.extend(sorted(audit_dir.glob(f"findings/*/raw/{trial}.csv")))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"{trial}: no skeleton CSV found under {audit_dir}")


def repaired_raw_frames(dataset_root: Path, row: dict[str, str], frame_count: int) -> set[int]:
    relative = row.get("feature_file", "")
    if not relative:
        return set()
    path = dataset_root / relative
    if not path.is_file():
        raise FileNotFoundError(f"{row['trial']}: missing feature repair mask {path}")
    repaired = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            if int(item["repaired_frame"]):
                repaired.add(int(item["frame0"]))
    if any(frame < 0 or frame >= frame_count for frame in repaired):
        raise ValueError(f"{row['trial']}: repaired-frame mask is outside skeleton bounds")
    return repaired


def target_grid(source_count: int, source_rate: float, target_rate: float) -> tuple[np.ndarray, np.ndarray]:
    duration = (source_count - 1) / source_rate
    target_count = int(round(duration * target_rate)) + 1
    source_time = np.arange(source_count, dtype=np.float64) / source_rate
    target_time = np.arange(target_count, dtype=np.float64) / target_rate
    target_time[-1] = min(target_time[-1], source_time[-1])
    return source_time, target_time


def interpolate(signal: np.ndarray, source_time: np.ndarray, target_time: np.ndarray) -> np.ndarray:
    return np.interp(target_time, source_time, signal).astype(np.float32)


def pad(values: np.ndarray, samples: int) -> tuple[np.ndarray, np.ndarray]:
    if len(values) > samples:
        raise ValueError(f"trajectory has {len(values)} samples; configured grid has {samples}")
    output = np.full(samples, values[-1], dtype=np.float32)
    output[: len(values)] = values
    mask = np.zeros(samples, dtype=np.float32)
    mask[: len(values)] = 1.0
    return output, mask


def initial_state(signals: list[np.ndarray], rate: int, fit_samples: int) -> np.ndarray:
    values = []
    derivatives = []
    for signal in signals:
        values.append(float(signal[0]))
        count = min(len(signal), fit_samples)
        if count < 3:
            derivatives.append(0.0)
        else:
            time = np.arange(count, dtype=np.float64) / rate
            derivatives.append(float(np.polyfit(time, signal[:count], 1)[0]))
    return np.asarray(values + derivatives, dtype=np.float32)


def prepare_trial(row: dict[str, str], config: dict, dataset_root: Path) -> tuple[dict, dict[str, np.ndarray]]:
    subject = row["subject"]
    trial = row["trial"]
    activity = row["activity"]
    audit_dir = resolve(config, config["audit_dir_template"].format(subject=subject))
    raw_path = locate_raw_trial(audit_dir, subject, trial)
    raw = np.loadtxt(raw_path, delimiter=",", ndmin=2)
    if raw.shape[1] != 96:
        raise ValueError(f"{raw_path}: expected 96 columns, found {raw.shape}")
    pose_m = raw.reshape(-1, 32, 3) * 0.001
    standing = int(row["initial_standing_frame0"])
    onset = int(row["fall_onset_frame0"])
    contact = int(row["apparent_contact_frame0"])
    if not 0 <= standing < onset < contact < len(pose_m):
        raise ValueError(f"{trial}: invalid phase bounds")

    frame = standing_body_frame(
        pose_m, standing, radius=int(config["data"]["standing_radius_frames"])
    )
    pose_body = to_subject_frame(pose_m, frame)
    com_body = to_subject_frame(
        com_proxy(pose_m, segment_model(row["sex"].lower()))[0], frame
    )
    foot_midpoint = 0.5 * (pose_body[:, 21] + pose_body[:, 25])
    pivot = foot_midpoint[onset]
    direction = np.asarray(
        config["data"]["activity_axes_subject_frame_lateral_forward"][activity],
        dtype=np.float64,
    )
    norm = float(np.linalg.norm(direction))
    if not np.isfinite(norm) or not np.isclose(norm, 1.0, atol=1e-8):
        raise ValueError(f"{activity}: configured activity axis is not a unit vector")
    relative_horizontal = com_body[:, [0, 2]] - pivot[[0, 2]]
    x_m = relative_horizontal @ direction
    vertical_m = com_body[:, 1] - pivot[1]
    theta = np.unwrap(np.arctan2(x_m, vertical_m))

    # Match Model B full-fall scope: source clip start through apparent contact.
    source_count = contact + 1
    theta = theta[:source_count]
    x_m = x_m[:source_count]
    source_rate = float(config["data"]["source_rate_hz"])
    target_rate = int(config["data"]["target_rate_hz"])
    source_time, target_time = target_grid(source_count, source_rate, target_rate)
    theta_target = interpolate(theta, source_time, target_time)
    x_target = interpolate(x_m, source_time, target_time)
    baseline_samples = min(len(x_target), int(round(0.5 * target_rate)))
    x_target -= float(np.median(x_target[:baseline_samples]))

    horizon_samples = int(round(float(config["data"]["horizon_s"]) * target_rate)) + 1
    theta_padded, valid = pad(theta_target, horizon_samples)
    x_padded, x_valid = pad(x_target, horizon_samples)
    if not np.array_equal(valid, x_valid):
        raise AssertionError("signal masks differ")
    context_samples = int(round(float(config["model"]["context_region_s"]) * target_rate)) + 1
    if int(valid.sum()) < context_samples:
        raise ValueError(f"{trial}: shorter than the fixed 0.40-s context")

    repaired = repaired_raw_frames(dataset_root, row, len(pose_m))
    physics_mask = valid.copy()
    raw_index = np.rint(target_time * source_rate).astype(int)
    repaired_target = np.asarray([index in repaired for index in raw_index], dtype=bool)
    physics_mask[: len(target_time)][repaired_target] = 0.0
    excluded = int(round(float(config["data"]["contact_exclusion_s"]) * target_rate))
    if excluded:
        physics_mask[max(0, int(valid.sum()) - excluded) :] = 0.0

    state = initial_state(
        [theta_target, x_target], target_rate,
        int(config["data"]["derivative_fit_samples"]),
    )
    time_s = np.linspace(
        0.0, float(config["data"]["horizon_s"]), horizon_samples, dtype=np.float32
    )
    activity_vector = np.zeros(int(config["model"]["activity_count"]), dtype=np.float32)
    if activity in ACTIVITY_INDEX:
        activity_vector[ACTIVITY_INDEX[activity]] = 1.0
    payload = {
        "time_s": time_s,
        "theta_rad": theta_padded,
        "x_m": x_padded,
        "yaw_rad": np.zeros_like(theta_padded),
        "valid_mask": valid,
        "physics_mask": physics_mask,
        "initial_state": state,
        "demographics": np.asarray(
            [float(row["mass_kg"]) / 80.0, float(row["height_m"]) / 1.70],
            dtype=np.float32,
        ),
        "mass_kg": np.asarray(float(row["mass_kg"]), dtype=np.float32),
        "height_m": np.asarray(float(row["height_m"]), dtype=np.float32),
        "fall_direction": direction.astype(np.float32),
        "activity_vector": activity_vector,
    }
    metadata = {
        "subject": subject,
        "trial": trial,
        "activity": activity,
        "model_group": "planar",
        "mass_kg": float(row["mass_kg"]),
        "height_m": float(row["height_m"]),
        "raw_source": str(raw_path),
        "raw_sha256": sha256(raw_path),
        "raw_frames_through_contact": source_count,
        "usable_samples": int(valid.sum()),
        "usable_duration_s": float((valid.sum() - 1) / target_rate),
        "physics_samples_before_delay_filter": int(physics_mask.sum()),
        "repaired_raw_frames_through_contact": len([f for f in repaired if f <= contact]),
        "activity_axis_lateral": float(direction[0]),
        "activity_axis_forward": float(direction[1]),
        "axis_source": "activity_identity_only_no_future_target_motion",
        "initial_standing_frame0": standing,
        "fall_onset_frame0": onset,
        "apparent_contact_frame0": contact,
        "maximum_abs_theta_deg": float(np.degrees(np.max(np.abs(theta_target)))),
    }
    return metadata, payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    dataset_root = resolve(config, config["dataset_root"])
    manifest_path = dataset_root / "manifests" / "trial_manifest.csv"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    output_root = ROOT / "outputs" / f"real_data_{args.mode}"
    output_root.mkdir(parents=True, exist_ok=True)
    model_group = "planar"
    activities = set(config["data"]["activities"])
    flag = str(config["data"]["selection_flag"])
    selected = [
        row for row in rows
        if row["activity"] in activities and bool_field(row, flag)
    ]
    destination_dir = output_root / model_group
    destination_dir.mkdir(parents=True, exist_ok=True)
    included = []
    for row in selected:
        metadata, payload = prepare_trial(row, config, dataset_root)
        destination = destination_dir / f"{row['trial']}.npz"
        if destination.exists() and not args.overwrite:
            raise FileExistsError(f"{destination} exists; pass --overwrite")
        np.savez_compressed(destination, **payload)
        metadata["data_file"] = destination.name
        included.append(metadata)
        print(f"Prepared A10-A13 V2: {row['trial']}")
    report = {
        "experiment": config["experiment_name"],
        "mode": args.mode,
        "model_group": model_group,
        "diagnostic_question": "Do activity-specific CartPole heads improve unified A10-A13 forecasting?",
        "selection_flag": flag,
        "activities": sorted(activities),
        "included_trials": included,
        "included_trial_count": len(included),
        "included_by_activity": dict(sorted(Counter(item["activity"] for item in included).items())),
        "included_by_subject": dict(sorted(Counter(item["subject"] for item in included).items())),
        "coordinate_definition": {
            "subject_frame": "fixed standing frame [lateral-right, vertical-headward, forward-nose-proxy]",
            "signed_activity_axes_lateral_forward": config["data"]["activity_axes_subject_frame_lateral_forward"],
            "theta": "atan2(activity-axis CoM displacement, subject-vertical CoM) relative to onset foot pivot",
            "x": "CoM displacement along the configured signed activity axis",
            "leakage_guard": "axis never uses onset-to-contact or other future target motion",
        },
        "physics_scope": "clip start through apparent contact, repaired samples masked, final 0.03 s excluded",
    }
    write_json(output_root / "planar_manifest.json", report)
    expected = int(config["data"]["expected_trial_count"])
    expected_by_activity = config["data"]["expected_by_activity"]
    if len(included) != expected or report["included_by_activity"] != expected_by_activity:
        raise ValueError(
            f"strict-primary counts changed: total={len(included)}, "
            f"by_activity={report['included_by_activity']}"
        )
    print(f"Prepared {len(included)} strict-primary A10-A13 trials")


if __name__ == "__main__":
    main()
