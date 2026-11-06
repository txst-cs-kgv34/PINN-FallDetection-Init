#!/usr/bin/env python3
"""Convert phase-marked S##_PINN_audit A11 skeleton trials to pole-compatible TSVs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from audit_adapter.skeleton_model import com_proxy, segment_model
from audit_adapter.subject_frame import standing_body_frame, to_subject_frame
from operator_core import ROOT, dump_json, load_config, resolve_path, sha256


PHASES = ("initial_standing", "fall_onset", "descent", "apparent_contact", "post_fall")


def interpolate_to_rate(signal: np.ndarray, source_rate: float, target_rate: float) -> np.ndarray:
    duration = (len(signal) - 1) / source_rate
    count = int(round(duration * target_rate)) + 1
    source_time = np.arange(len(signal), dtype=np.float64) / source_rate
    target_time = np.arange(count, dtype=np.float64) / target_rate
    target_time[-1] = min(target_time[-1], source_time[-1])
    return np.interp(target_time, source_time, signal)


def encode_as_two_markers(theta_rad: np.ndarray, x_m: np.ndarray, length_mm: float) -> np.ndarray:
    x2_mm = 1000.0 * x_m
    zeros = np.zeros_like(x2_mm)
    x1_mm = x2_mm + length_mm * np.sin(theta_rad)
    y1_mm = length_mm * np.cos(theta_rad)
    return np.column_stack([x1_mm, y1_mm, zeros, x2_mm, zeros, zeros])


def find_phase_notes(audit_dir: Path, subject: str) -> Path:
    candidates = [
        audit_dir / "analysis_inputs" / f"{subject}_phase_notes_manual.json",
        audit_dir / "analysis_inputs" / f"{subject}_phase_notes.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"{subject}: missing manual phase notes; expected one of "
        + ", ".join(str(path) for path in candidates)
    )


def grouped_phases(path: Path, subject: str) -> dict[str, dict[str, int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("subject") != subject:
        raise ValueError(f"{path}: subject mismatch")
    grouped: dict[str, dict[str, int]] = {}
    for note in payload.get("notes", []):
        trial = str(note["trial"])
        if trial.startswith(subject + "A11"):
            grouped.setdefault(trial, {})[str(note["phase"])] = int(note["frame0"])
    for trial, marks in grouped.items():
        missing = set(PHASES).difference(marks)
        if missing:
            raise ValueError(f"{trial}: missing phase marks {sorted(missing)}")
        frames = [marks[phase] for phase in PHASES]
        if any(left >= right for left, right in zip(frames, frames[1:])):
            raise ValueError(f"{trial}: phase frames are not strictly increasing")
    if not grouped:
        raise ValueError(f"{subject}: no complete A11 manual phase notes")
    return grouped


def repaired_frames(audit_dir: Path, subject: str) -> dict[str, set[int]]:
    path = audit_dir / "repaired_data" / subject / "repaired_frames.csv"
    result: dict[str, set[int]] = {}
    if not path.is_file():
        return result
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            result.setdefault(row["trial"], set()).add(int(row["frame0"]))
    return result


def validate_demographics(subject_cfg: dict, audit_cfg: dict, subject: str) -> None:
    checks = (
        ("sex", str(subject_cfg["sex"]).lower(), str(audit_cfg["sex"]).lower()),
        ("mass_lb", float(subject_cfg["mass_lb"]), float(audit_cfg["mass_lb"])),
        ("height_in", float(subject_cfg["height_in"]), float(audit_cfg["height_in"])),
    )
    for name, expected, actual in checks:
        if expected != actual:
            raise ValueError(f"{subject}: {name} mismatch, experiment={expected}, audit={actual}")


def build_subject(subject_cfg: dict, config: dict, overwrite: bool) -> dict:
    subject = str(subject_cfg["id"])
    audit_dir = resolve_path(config, subject_cfg["audit_dir"])
    audit_cfg_path = audit_dir / "configs" / f"{subject}.json"
    if not audit_cfg_path.is_file():
        raise FileNotFoundError(f"{subject}: missing {audit_cfg_path}")
    audit_cfg = json.loads(audit_cfg_path.read_text(encoding="utf-8"))
    validate_demographics(subject_cfg, audit_cfg, subject)
    phase_path = find_phase_notes(audit_dir, subject)
    phases = grouped_phases(phase_path, subject)
    repairs = repaired_frames(audit_dir, subject)
    segments = segment_model(str(subject_cfg["sex"]).lower())
    settings = config["audit_adapter"]
    target_rate = float(settings["target_rate_hz"])
    warmup = int(settings["pole_loader_warmup_rows"])
    length_mm = float(settings["encoding_length_mm"])
    standing_radius = int(settings["standing_radius_frames"])
    source_rate = float(audit_cfg["fps"])
    scale = {"mm": 0.001, "m": 1.0}[str(audit_cfg["coordinate_units"])]
    output_dir = ROOT / "outputs" / "audit_pole_inputs" / subject
    derived_dir = ROOT / "outputs" / "audit_derived" / subject
    output_dir.mkdir(parents=True, exist_ok=True)
    derived_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        for path in output_dir.glob("SubjectB_*.tsv"):
            path.unlink()
    trials = []
    for trial, marks in sorted(phases.items()):
        raw_path = audit_dir / "repaired_data" / subject / f"{trial}.csv"
        if not raw_path.is_file():
            raise FileNotFoundError(f"{trial}: missing {raw_path}")
        raw = np.loadtxt(raw_path, delimiter=",", ndmin=2)
        if raw.shape[1] != 96:
            raise ValueError(f"{raw_path} has shape {raw.shape}; expected 96 columns")
        pose_m = raw.reshape(-1, 32, 3) * scale
        standing = marks["initial_standing"]
        onset = marks["fall_onset"]
        contact = marks["apparent_contact"]
        if not 0 <= standing < onset < contact < len(pose_m):
            raise ValueError(f"{trial}: invalid or out-of-range phase order")

        frame = standing_body_frame(pose_m, standing, radius=standing_radius)
        com_body_m = to_subject_frame(com_proxy(pose_m, segments)[0], frame)
        left_foot = to_subject_frame(pose_m[:, 21], frame)
        right_foot = to_subject_frame(pose_m[:, 25], frame)
        foot_midpoint = 0.5 * (left_foot + right_foot)
        pivot = foot_midpoint[onset]
        relative = com_body_m[:, [2, 1]] - pivot[[2, 1]]
        relative = relative[: contact + 1]
        x_m = relative[:, 0]
        vertical_m = relative[:, 1]
        theta_rad = np.unwrap(np.arctan2(x_m, vertical_m))

        threshold_20 = math.radians(float(config["real_data"]["fall_angle_deg"]))
        crossing_20 = np.flatnonzero(np.abs(theta_rad) >= threshold_20)
        crossing_89 = np.flatnonzero(np.abs(theta_rad) >= math.radians(89.0))
        compatibility_trim = None
        if len(crossing_89):
            first_89 = int(crossing_89[0])
            first_20 = int(crossing_20[0]) if len(crossing_20) else None
            if first_20 is None or first_89 <= first_20:
                raise ValueError(f"{trial}: exceeds the arcsin range before the training cutoff")
            compatibility_trim = first_89
            theta_rad = theta_rad[:first_89]
            x_m = x_m[:first_89]
            vertical_m = vertical_m[:first_89]

        theta_target = interpolate_to_rate(theta_rad, source_rate, target_rate)
        x_target = interpolate_to_rate(x_m, source_rate, target_rate)
        encoded = encode_as_two_markers(theta_target, x_target, length_mm)
        pole_input = np.vstack([np.repeat(encoded[:1], warmup, axis=0), encoded])
        destination = output_dir / f"SubjectB_{trial}.tsv"
        if destination.exists() and not overwrite:
            raise FileExistsError(f"{destination} exists; pass --overwrite")
        np.savetxt(destination, pole_input, delimiter="\t", fmt="%.10f")

        time_s = np.arange(len(theta_rad), dtype=np.float64) / source_rate
        derived = derived_dir / f"{trial}_human_theta_x.csv"
        np.savetxt(
            derived,
            np.column_stack([time_s, theta_rad, np.degrees(theta_rad), x_m, vertical_m]),
            delimiter=",",
            header="time_s,theta_rad,theta_deg,x_forward_m,com_vertical_m",
            comments="",
            fmt="%.10f",
        )
        repaired_used = sorted(frame0 for frame0 in repairs.get(trial, set()) if frame0 <= contact)
        trials.append(
            {
                "trial": trial,
                "raw_file": str(raw_path),
                "raw_sha256": sha256(raw_path),
                "phase_file": str(phase_path),
                "initial_standing_frame0": standing,
                "fall_onset_frame0": onset,
                "apparent_contact_frame0": contact,
                "post_fall_frame0": marks["post_fall"],
                "source_rate_hz": source_rate,
                "encoded_rate_hz": target_rate,
                "pole_input_file": str(destination.relative_to(ROOT)),
                "derived_signal_file": str(derived.relative_to(ROOT)),
                "raw_frames_used": int(len(theta_rad)),
                "repaired_frames_used": repaired_used,
                "repaired_fraction_used": len(repaired_used) / max(contact + 1, 1),
                "arcsin_compatibility_trim_frame0": compatibility_trim,
                "first_abs_theta_20deg_s_from_clip_start": (
                    float(crossing_20[0] / source_rate) if len(crossing_20) else None
                ),
                "fixed_pivot_subject_frame_m": pivot.tolist(),
                "tsv_sha256": sha256(destination),
            }
        )
    return {
        "subject": subject,
        "audit_dir": str(audit_dir),
        "sex": subject_cfg["sex"],
        "mass_lb": subject_cfg["mass_lb"],
        "height_in": subject_cfg["height_in"],
        "phase_notes_sha256": sha256(phase_path),
        "coordinate_definition": {
            "theta": "atan2(subject-forward CoM, subject-vertical CoM) relative to the fixed foot midpoint at marked onset",
            "x": "subject-forward CoM relative to the same fixed onset foot midpoint",
            "axis_alignment": "standing anatomical frame; camera X/Z orientation is removed before modeling",
            "filter": "none; linear interpolation only",
        },
        "trials": trials,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--subject",
        action="append",
        help="Prepare only this audit subject (repeatable); default prepares all audit subjects",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    selected = set(args.subject or [])
    manifests = []
    for subject in config["subjects"]:
        if subject.get("input_kind") == "audit_skeleton" and (
            not selected or str(subject["id"]) in selected
        ):
            manifest = build_subject(subject, config, args.overwrite)
            manifests.append(manifest)
            print(f"Prepared {manifest['subject']}: {len(manifest['trials'])} A11 trials")
    if selected and selected != {manifest["subject"] for manifest in manifests}:
        missing = sorted(selected.difference(manifest["subject"] for manifest in manifests))
        raise ValueError(f"Requested subjects are not configured audit inputs: {missing}")
    dump_json(
        ROOT / "outputs" / "audit_pole_inputs" / "audit_adapter_manifest.json",
        {
            "experiment": config["experiment_name"],
            "subjects": manifests,
            "note": "This deterministic adapter supplies real trajectories only. It does not train Pole-PINN or run gain sweeps.",
        },
    )


if __name__ == "__main__":
    main()
