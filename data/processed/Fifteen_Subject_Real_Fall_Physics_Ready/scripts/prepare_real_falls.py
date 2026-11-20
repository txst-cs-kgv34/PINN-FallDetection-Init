#!/usr/bin/env python3
"""Build a compact, subject-wise real-fall dataset from the 15 audit folders.

The output keeps the original camera-frame CoM proxy, adds a trial-aligned
horizontal progression coordinate, carries repair masks, and never fabricates
missing or incomplete phase labels.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path


SUBJECTS = ["S30", "S32", "S34", "S43", "S44", "S45", "S46", "S48", "S49", "S55", "S56", "S57", "S59", "S62", "S63"]
ACTIVITIES = {
    "A10": "backfall",
    "A11": "frontfall",
    "A12": "leftfall",
    "A13": "rightfall",
    "A14": "rotatefall",
}
PHASES = ["initial_standing", "fall_onset", "descent", "apparent_contact", "post_fall"]
DEMOGRAPHICS = {
    "S30": ("female", 190, 5, 6),
    "S32": ("male", 160, 5, 10),
    "S34": ("female", 125, 5, 6),
    "S43": ("female", 130, 5, 4),
    "S44": ("male", 180, 6, 1),
    "S45": ("male", 170, 5, 11),
    "S46": ("male", 160, 5, 8),
    "S48": ("male", 188, 5, 8),
    "S49": ("female", 165, 4, 11),
    "S55": ("male", 145, 5, 5),
    "S56": ("male", 165, 5, 10),
    "S57": ("male", 180, 5, 8),
    "S59": ("male", 220, 6, 0),
    "S62": ("male", 155, 5, 4),
    "S63": ("male", 180, 5, 6),
}
A11_FILES = {
    "S30": "S30_phase_notes_manual.json",
    "S32": "S32_phase_notes_manual.json",
    "S34": "S34_phase_notes_manual.json",
    "S43": "S43_A11_phase_notes.json",
    "S44": "S44_phase_notes_manual.json",
    "S45": "S45_phase_notes_manual.json",
    "S46": "S46_phase_notes_manual.json",
    "S48": "S48_phase_notes_manual.json",
    "S49": "S49_phase_notes_manual.json",
    "S55": "S55_phase_notes.json",
    "S56": "S56_phase_notes_manual.json",
    "S57": "S57_phase_notes.json",
    "S59": "S59_phase_notes_manual.json",
    "S62": "S62_phase_notes_model_ready.json",
    "S63": "S63_A11_phase_notes.json",
}

# Numeric recordings deliberately withheld from modeling. Unavailable recordings
# are discovered from the audit inventory and get a separate source-unavailable status.
EXCLUSIONS = {
    "S34A14T04": "Only available A14 trial; manually confirmed incomplete fall.",
    "S43A10T01": "Existing audit exclusion: nearly the whole clip is a constant pose and is not a usable fall trajectory.",
    "S43A11T01": "User-confirmed invalid front fall in the existing A11 annotation scope.",
    "S43A13T04": "Manually confirmed incomplete fall; recording ends during descent.",
    "S45A10T03": "Manually confirmed incomplete fall.",
    "S45A13T02": "Manually confirmed incomplete fall.",
    "S45A14T04": "Manually confirmed incomplete fall.",
    "S46A12T04": "Manually confirmed incomplete fall.",
    "S46A14T01": "Manually confirmed incomplete fall.",
    "S46A14T02": "Manually confirmed incomplete fall.",
    "S46A14T05": "Manually confirmed incomplete fall.",
    "S48A10T01": "Only T04 was manually confirmed as a valid A10 trial.",
    "S48A10T02": "Only T04 was manually confirmed as a valid A10 trial.",
    "S48A10T03": "Only T04 was manually confirmed as a valid A10 trial.",
    "S48A10T05": "Only T04 was manually confirmed as a valid A10 trial.",
    "S48A12T01": "Manually confirmed incomplete fall.",
    "S48A13T02": "Manually confirmed incomplete fall.",
    "S48A13T03": "Manually confirmed incomplete fall.",
    "S48A13T05": "Manually confirmed incomplete fall.",
    "S49A10T01": "Manually confirmed incomplete fall.",
    "S49A11T01": "Manually confirmed incomplete fall.",
    "S49A12T02": "Only T03 was manually confirmed as a valid A12 trial.",
    "S49A12T04": "Only T03 was manually confirmed as a valid A12 trial.",
    "S49A12T05": "Only T03 was manually confirmed as a valid A12 trial.",
    "S49A13T03": "Manually confirmed incomplete fall.",
    "S49A14T01": "Manually confirmed incomplete fall.",
    "S55A10T01": "Manually confirmed incomplete fall.",
    "S56A10T01": "Manually confirmed incomplete fall.",
    "S56A10T03": "Manually confirmed incomplete fall.",
    "S56A14T05": "Manually confirmed incomplete fall.",
    "S57A10T01": "Manually confirmed incomplete fall.",
    "S57A10T04": "Manually confirmed incomplete fall.",
    "S57A11T01": "Manually confirmed incomplete fall in the existing A11 review.",
    "S57A11T02": "Manually confirmed incomplete fall in the existing A11 review.",
    "S63A10T01": "Manually confirmed incomplete fall.",
    "S63A10T02": "Manually confirmed incomplete fall; audit also notes that T02 starts near a fallen pose.",
}

CAMERA_AXIS_NOTES = {
    ("S30", "A10"): "manual_Z_minusY_projection",
    ("S32", "A10"): "manual_Z_minusY_projection",
    ("S34", "A10"): "manual_Z_minusY_projection",
    ("S62", "A10"): "manual_Z_minusY_projection",
    ("S62", "A14"): "manual_Z_minusY_projection",
}


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def choose_com_paths(audits_root: Path) -> dict[str, Path]:
    found: dict[str, list[Path]] = defaultdict(list)
    for path in audits_root.rglob("S*A*T*_com_proxy.csv"):
        found[path.name.split("_com_proxy.csv")[0]].append(path)
    chosen = {}
    for trial, paths in found.items():
        # Prefer the repair-aware audit if both original and repaired outputs exist.
        chosen[trial] = sorted(paths, key=lambda p: ("audit_repaired" not in str(p), len(str(p))))[0]
    return chosen


def read_phase_file(path: Path, source_kind: str, registry: dict[str, dict]) -> None:
    payload = read_json(path)
    by_trial: dict[str, dict[str, dict]] = defaultdict(dict)
    for note in payload.get("notes", []):
        trial = note.get("trial", "")
        phase = note.get("phase", "")
        if phase in by_trial[trial]:
            raise ValueError(f"duplicate {phase} note for {trial} in {path}")
        by_trial[trial][phase] = note
    for trial, marks in by_trial.items():
        if trial in registry:
            raise ValueError(f"duplicate phase source for {trial}: {path} and {registry[trial]['source_file']}")
        registry[trial] = {
            "source_file": str(path),
            "source_kind": source_kind,
            "marks": marks,
            "fps": payload.get("nominal_fps", 30),
        }


def repair_info(audit_dir: Path, subject: str, trial: str, frame_count: int) -> dict:
    path = audit_dir / "repaired_data" / subject / f"{trial}.repair.json"
    if not path.exists():
        return {"repaired_frames": set(), "repaired_rows": 0, "repair_fraction": 0.0, "boundary_carry": False}
    payload = read_json(path)
    frames = set()
    boundary = False
    for gap in payload.get("gaps", []):
        frames.update(range(int(gap["start_row1"]) - 1, int(gap["end_row1"])))
        boundary = boundary or gap.get("previous_valid_row1") is None or gap.get("next_valid_row1") is None
    repaired_rows = int(payload.get("repaired_rows", len(frames)))
    return {
        "repaired_frames": frames,
        "repaired_rows": repaired_rows,
        "repair_fraction": repaired_rows / frame_count if frame_count else 0.0,
        "boundary_carry": boundary,
    }


def repair_tier(info: dict) -> str:
    fraction = info["repair_fraction"]
    if fraction >= 0.20:
        return "exclude_primary_modeling"
    if fraction >= 0.05:
        return "sensitivity_check_required"
    if info["boundary_carry"] and fraction > 0:
        return "manual_review_boundary_repair"
    if fraction > 0:
        return "minor_repair_review"
    return "no_repair"


def phase_segment(frame: int, marks: dict[str, int]) -> str:
    if frame < marks["initial_standing"]:
        return "pre_standing"
    if frame < marks["fall_onset"]:
        return "standing"
    if frame < marks["descent"]:
        return "onset_to_descent"
    if frame < marks["apparent_contact"]:
        return "descent"
    if frame < marks["post_fall"]:
        return "post_contact"
    return "post_fall"


def dominant_direction(dx: float, dz: float) -> str:
    if abs(dx) >= abs(dz):
        return "+X" if dx >= 0 else "-X"
    return "+Z" if dz >= 0 else "-Z"


def build(args: argparse.Namespace) -> None:
    audits_root = args.audits_root.resolve()
    notes_root = args.notes_root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)

    phase_registry: dict[str, dict] = {}
    for path in sorted(notes_root.rglob("S*_A*_phase_notes.json")):
        read_phase_file(path, "new_manual_A10_A12_A13_A14", phase_registry)
    for subject in SUBJECTS:
        path = audits_root / f"{subject}_PINN_audit" / "analysis_inputs" / A11_FILES[subject]
        read_phase_file(path, "existing_manual_A11", phase_registry)

    com_paths = choose_com_paths(audits_root)
    manifest: list[dict] = []
    validation_errors: list[str] = []
    validation_warnings: list[str] = []
    phase_annotations: dict[str, dict] = {}
    feature_files = []

    for subject in SUBJECTS:
        audit_dir = audits_root / f"{subject}_PINN_audit"
        for activity, activity_name in ACTIVITIES.items():
            for trial_number in range(1, 6):
                trial = f"{subject}{activity}T{trial_number:02d}"
                com_path = com_paths.get(trial)
                source_available = com_path is not None
                source_rows = load_csv(com_path) if com_path else []
                frame_count = len(source_rows)
                phase_entry = phase_registry.get(trial)
                marks = {}
                phase_complete = False
                phase_order_valid = False
                phase_in_bounds = False
                time_consistent = False
                if phase_entry:
                    marks = {p: int(phase_entry["marks"][p]["frame0"]) for p in PHASES if p in phase_entry["marks"]}
                    phase_complete = set(marks) == set(PHASES)
                    phase_order_valid = phase_complete and all(marks[a] < marks[b] for a, b in zip(PHASES, PHASES[1:]))
                    phase_in_bounds = phase_complete and source_available and all(0 <= v < frame_count for v in marks.values())
                    fps = float(phase_entry["fps"])
                    time_consistent = phase_complete and all(
                        abs(float(phase_entry["marks"][p].get("nominal_time_s", marks[p] / fps)) - marks[p] / fps) < 1e-8
                        for p in PHASES
                    )
                explicit_exclusion = EXCLUSIONS.get(trial)
                manual_valid = bool(phase_complete and not explicit_exclusion)
                if source_available and not phase_complete and not explicit_exclusion:
                    validation_warnings.append(f"{trial}: numeric source exists but no complete manual phase set or exclusion reason")
                if phase_complete and not (phase_order_valid and phase_in_bounds and time_consistent):
                    validation_errors.append(
                        f"{trial}: complete phase set failed validation order={phase_order_valid} bounds={phase_in_bounds} time={time_consistent}"
                    )

                rinfo = repair_info(audit_dir, subject, trial, frame_count)
                rtier = repair_tier(rinfo)
                repaired_onset_contact = 0
                direction_x = direction_z = horizontal_norm = None
                direction_class = ""
                feature_relpath = ""
                if manual_valid and source_available and phase_order_valid and phase_in_bounds:
                    onset = marks["fall_onset"]
                    contact = marks["apparent_contact"]
                    repaired_onset_contact = sum(onset <= f <= contact for f in rinfo["repaired_frames"])
                    x0 = float(source_rows[onset]["com_proxy_camera_x_m"])
                    y0 = float(source_rows[onset]["com_proxy_camera_y_m"])
                    z0 = float(source_rows[onset]["com_proxy_camera_z_m"])
                    xc = float(source_rows[contact]["com_proxy_camera_x_m"])
                    zc = float(source_rows[contact]["com_proxy_camera_z_m"])
                    dx, dz = xc - x0, zc - z0
                    horizontal_norm = math.hypot(dx, dz)
                    if horizontal_norm < 1e-6:
                        validation_errors.append(f"{trial}: onset-to-contact horizontal CoM displacement is too small")
                        direction_x, direction_z = 1.0, 0.0
                    else:
                        direction_x, direction_z = dx / horizontal_norm, dz / horizontal_norm
                    direction_class = dominant_direction(dx, dz)
                    feature_relpath = f"features/{subject}/{trial}.csv"
                    out_rows = []
                    boundary_by_frame = {value: key for key, value in marks.items()}
                    for frame, row in enumerate(source_rows):
                        x = float(row["com_proxy_camera_x_m"])
                        y = float(row["com_proxy_camera_y_m"])
                        z = float(row["com_proxy_camera_z_m"])
                        relx, relz = x - x0, z - z0
                        out_rows.append({
                            "trial": trial,
                            "subject": subject,
                            "activity": activity,
                            "activity_name": activity_name,
                            "frame0": frame,
                            "time_from_clip_start_s": f"{frame / 30.0:.10f}",
                            "time_from_fall_onset_s": f"{(frame - onset) / 30.0:.10f}",
                            "phase_segment": phase_segment(frame, marks),
                            "phase_boundary": boundary_by_frame.get(frame, ""),
                            "com_camera_x_m": f"{x:.10f}",
                            "com_camera_y_down_m": f"{y:.10f}",
                            "com_camera_z_m": f"{z:.10f}",
                            "com_vertical_up_m": f"{-y:.10f}",
                            "aligned_progression_m": f"{relx * direction_x + relz * direction_z:.10f}",
                            "aligned_lateral_m": f"{-relx * direction_z + relz * direction_x:.10f}",
                            "vertical_from_onset_m": f"{-(y - y0):.10f}",
                            "fall_direction_x": f"{direction_x:.10f}",
                            "fall_direction_z": f"{direction_z:.10f}",
                            "repaired_frame": int(frame in rinfo["repaired_frames"]),
                            "source_review_flag": row.get("review_flag", ""),
                        })
                    feature_path = output / feature_relpath
                    write_csv(feature_path, out_rows)
                    feature_files.append(feature_path)

                rotate_ambiguous = subject == "S44" and activity == "A14"
                strict_repair = rtier not in {"exclude_primary_modeling", "manual_review_boundary_repair"}
                include_detection = manual_valid and source_available and phase_order_valid and phase_in_bounds
                include_planar_primary = include_detection and activity != "A14" and strict_repair
                include_planar_sensitivity = include_detection and activity != "A14"
                include_rotation_primary = include_detection and activity == "A14" and strict_repair and not rotate_ambiguous
                include_rotation_sensitivity = include_detection and activity == "A14"
                if not source_available:
                    status = "source_unavailable"
                    reason = "Expected trial has no numeric CoM output in the audit (missing or empty source)."
                elif explicit_exclusion:
                    status = "manual_exclusion"
                    reason = explicit_exclusion
                elif not phase_complete:
                    status = "phase_unresolved"
                    reason = "Numeric trial exists but has no complete five-phase manual annotation."
                elif rotate_ambiguous:
                    status = "manual_valid_activity_ambiguous"
                    reason = "Manual observation: rotate-fall trials resemble front falls and appear to miss the turn-around; withhold from primary A14 physics fitting."
                elif rtier == "exclude_primary_modeling":
                    status = "manual_valid_repair_sensitivity_only"
                    reason = "Manual fall is valid, but at least 20% of the full clip was repaired; retain with repair mask for sensitivity analysis."
                else:
                    status = "manual_valid"
                    reason = "Complete ordered manual phases and numeric audit source are available."

                row = {
                    "subject": subject,
                    "sex": DEMOGRAPHICS[subject][0],
                    "mass_lb": DEMOGRAPHICS[subject][1],
                    "mass_kg": round(DEMOGRAPHICS[subject][1] * 0.45359237, 6),
                    "height_ft": DEMOGRAPHICS[subject][2],
                    "height_in": DEMOGRAPHICS[subject][3],
                    "height_m": round((DEMOGRAPHICS[subject][2] * 12 + DEMOGRAPHICS[subject][3]) * 0.0254, 6),
                    "trial": trial,
                    "activity": activity,
                    "activity_name": activity_name,
                    "trial_number": trial_number,
                    "source_available": source_available,
                    "frame_count": frame_count,
                    "phase_source_kind": phase_entry["source_kind"] if phase_entry else "",
                    "phase_complete": phase_complete,
                    "phase_order_valid": phase_order_valid,
                    "phase_in_bounds": phase_in_bounds,
                    **{f"{p}_frame0": marks.get(p, "") for p in PHASES},
                    "manual_fall_valid": manual_valid,
                    "dataset_status": status,
                    "decision_reason": reason,
                    "repaired_rows": rinfo["repaired_rows"],
                    "repair_fraction": round(rinfo["repair_fraction"], 8),
                    "repair_tier": rtier,
                    "repaired_onset_to_contact_frames": repaired_onset_contact,
                    "camera_axis_manual_note": CAMERA_AXIS_NOTES.get((subject, activity), ""),
                    "fall_direction_camera": direction_class,
                    "fall_direction_x": "" if direction_x is None else round(direction_x, 8),
                    "fall_direction_z": "" if direction_z is None else round(direction_z, 8),
                    "onset_contact_horizontal_displacement_m": "" if horizontal_norm is None else round(horizontal_norm, 8),
                    "rotate_direction_varies_by_trial": activity == "A14",
                    "activity_identity_review": "frontfall_like_missing_turn" if rotate_ambiguous else "",
                    "include_detection_training": include_detection,
                    "include_planar_physics_primary": include_planar_primary,
                    "include_planar_physics_sensitivity": include_planar_sensitivity,
                    "include_rotation_physics_primary": include_rotation_primary,
                    "include_rotation_physics_sensitivity": include_rotation_sensitivity,
                    "feature_file": feature_relpath,
                }
                manifest.append(row)
                if phase_entry:
                    phase_annotations[trial] = {
                        "trial": trial,
                        "subject": subject,
                        "activity": activity,
                        "source_kind": phase_entry["source_kind"],
                        "phase_frames0": marks,
                        "manual_fall_valid": manual_valid,
                        "dataset_status": status,
                        "decision_reason": reason,
                    }

    if validation_errors:
        raise RuntimeError("dataset validation failed:\n" + "\n".join(validation_errors))

    # Machine-readable tables.
    write_csv(output / "manifests" / "trial_manifest.csv", manifest)
    write_json(output / "manifests" / "trial_manifest.json", manifest)
    write_json(output / "annotations" / "phase_annotations.json", phase_annotations)
    demographics = []
    for subject in SUBJECTS:
        sex, mass, feet, inches = DEMOGRAPHICS[subject]
        demographics.append({
            "subject": subject,
            "sex": sex,
            "mass_lb": mass,
            "mass_kg": round(mass * 0.45359237, 6),
            "height_ft": feet,
            "height_in": inches,
            "height_m": round((feet * 12 + inches) * 0.0254, 6),
        })
    write_csv(output / "manifests" / "subject_demographics.csv", demographics)

    # Preserve exact manual note sources used to build the manifest.
    source_notes = output / "annotations" / "source_notes"
    source_notes.mkdir(parents=True)
    copied = set()
    for entry in phase_registry.values():
        src = Path(entry["source_file"])
        if src not in copied:
            shutil.copy2(src, source_notes / src.name)
            copied.add(src)

    # Subject-focused indexes.
    for subject in SUBJECTS:
        subject_rows = [r for r in manifest if r["subject"] == subject]
        write_csv(output / "subjects" / subject / "trial_manifest.csv", subject_rows)
        write_json(
            output / "subjects" / subject / "phase_annotations.json",
            {k: v for k, v in phase_annotations.items() if v["subject"] == subject},
        )
        counts = Counter(r["dataset_status"] for r in subject_rows)
        excluded = [r for r in subject_rows if not r["include_detection_training"]]
        lines = [
            f"# {subject} real-fall preparation",
            "",
            f"- Detection-ready manual falls: **{sum(bool(r['include_detection_training']) for r in subject_rows)}**",
            f"- Planar-physics primary trials: **{sum(bool(r['include_planar_physics_primary']) for r in subject_rows)}**",
            f"- Rotation-physics primary trials: **{sum(bool(r['include_rotation_physics_primary']) for r in subject_rows)}**",
            f"- Source-unavailable slots: **{counts['source_unavailable']}**",
            f"- Manual exclusions: **{counts['manual_exclusion']}**",
            "",
            "The per-trial manifest is authoritative. Repaired frames are retained only with an explicit frame mask.",
        ]
        if excluded:
            lines += ["", "## Not used for detection training", ""]
            lines += [f"- `{r['trial']}` — {r['decision_reason']}" for r in excluded]
        (output / "subjects" / subject / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # LOSO folds prevent subject leakage.
    loso = []
    for test_subject in SUBJECTS:
        loso.append({
            "fold": f"test_{test_subject}",
            "train_subjects": [s for s in SUBJECTS if s != test_subject],
            "test_subjects": [test_subject],
            "grouping_key": "subject",
        })
    write_json(output / "splits" / "loso_folds.json", loso)

    # Aggregate findings.
    detection_rows = [r for r in manifest if r["include_detection_training"]]
    planar_primary = [r for r in manifest if r["include_planar_physics_primary"]]
    rotation_primary = [r for r in manifest if r["include_rotation_physics_primary"]]
    activity_counts = []
    for activity, name in ACTIVITIES.items():
        rows = [r for r in manifest if r["activity"] == activity]
        activity_counts.append({
            "activity": activity,
            "activity_name": name,
            "expected_slots": len(rows),
            "numeric_sources": sum(bool(r["source_available"]) for r in rows),
            "detection_ready": sum(bool(r["include_detection_training"]) for r in rows),
            "planar_physics_primary": sum(bool(r["include_planar_physics_primary"]) for r in rows),
            "rotation_physics_primary": sum(bool(r["include_rotation_physics_primary"]) for r in rows),
            "manual_exclusions": sum(r["dataset_status"] == "manual_exclusion" for r in rows),
            "source_unavailable": sum(r["dataset_status"] == "source_unavailable" for r in rows),
        })
    write_csv(output / "manifests" / "activity_summary.csv", activity_counts)

    findings = [
        "# Findings",
        "",
        f"The consolidated inventory contains **{len(manifest)} expected subject/activity/trial slots**: "
        f"**{sum(bool(r['source_available']) for r in manifest)} numeric sources** and "
        f"**{len(detection_rows)} manually validated detection-ready falls**.",
        "",
        f"The strict physics subsets contain **{len(planar_primary)} planar trials** (A10–A13) and "
        f"**{len(rotation_primary)} rotate-fall trials** (A14). Repair-sensitive but manually valid trials remain in the manifest and features with masks.",
        "",
        "## Activity summary",
        "",
        "| Activity | Numeric | Detection-ready | Planar primary | Rotation primary | Manual exclusions | Unavailable |",
        "|:--|--:|--:|--:|--:|--:|--:|",
    ]
    for r in activity_counts:
        findings.append(
            f"| {r['activity']} {r['activity_name']} | {r['numeric_sources']} | {r['detection_ready']} | "
            f"{r['planar_physics_primary']} | {r['rotation_physics_primary']} | {r['manual_exclusions']} | {r['source_unavailable']} |"
        )
    findings += [
        "",
        "## Scientific cautions",
        "",
        "- A10 for S30, S32, S34, and S62, plus A14 for S62, was manually reviewed in the camera Z/−Y projection. Trial-aligned X–Z progression is supplied so a fixed camera-X assumption is unnecessary.",
        "- A14 direction varies by trial after rotation. The manifest records the camera-frame onset-to-contact direction; it is not an anatomical left/right label.",
        "- S44 A14 is retained for detection/sensitivity work but withheld from primary rotate-physics fitting because the trials appear front-fall-like and may omit the turn-around.",
        "- Apparent contact is skeleton-observed, not force-plate verified. Repair masks must be used in losses and evaluation.",
    ]
    (output / "FINDINGS.md").write_text("\n".join(findings) + "\n", encoding="utf-8")

    readme = f"""# Fifteen-subject real-fall phase dataset

This package consolidates the manually reviewed A10–A14 fall phases for all 15 subjects and prepares compact CoM trajectories for detection and physics-informed experiments. It does not fabricate unavailable trials or complete an incomplete fall.

## Ready-to-use contents

- `manifests/trial_manifest.csv`: authoritative 375-slot inventory, validity decisions, repair quality, phase frames, camera direction, and experiment inclusion flags.
- `features/S##/S##A##T##.csv`: one compact aligned CoM sequence per manually valid fall, including phase segments and repaired-frame masks.
- `annotations/phase_annotations.json`: normalized phase boundaries and decisions.
- `annotations/source_notes/`: exact manual JSON sources used in this build, including existing A11 annotations.
- `subjects/S##/`: subject-wise manifests and notes.
- `splits/loso_folds.json`: subject-grouped leave-one-subject-out folds.
- `manifests/activity_summary.csv`: aggregate counts by activity.

## Inclusion flags

- `include_detection_training`: manually valid fall with complete, ordered, in-bounds phases and a numeric audit source. Repaired rows remain explicitly masked.
- `include_planar_physics_primary`: strict-quality A10–A13 subset.
- `include_planar_physics_sensitivity`: all manually valid A10–A13 trials, including repair-sensitive cases.
- `include_rotation_physics_primary`: strict-quality A14 subset, excluding S44's activity-identity ambiguity.
- `include_rotation_physics_sensitivity`: all manually valid A14 trials.

## Coordinate convention

Azure Kinect camera coordinates are preserved as X, Y-down, and Z. Each valid trial additionally receives an X–Z unit direction from CoM at fall onset to apparent contact. `aligned_progression_m` projects horizontal motion along this direction, `aligned_lateral_m` is the orthogonal horizontal component, and `vertical_from_onset_m` is positive upward. This removes the unsafe assumption that camera X is always the fall axis.

## Recommended experimental use

Use subject-grouped splits only. Start planar physics work with `include_planar_physics_primary == true`, run the sensitivity flag as a separate ablation, and model A14 with a rotational extension rather than pooling it into a single-plane inverted-pendulum residual. For fall detection, filter `include_detection_training == true` and keep the repair mask as an input or loss mask.

See `FINDINGS.md` for reviewed exceptions and counts.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")

    # Validation report and checksums.
    validation = {
        "status": "pass",
        "expected_slots": len(manifest),
        "numeric_sources": sum(bool(r["source_available"]) for r in manifest),
        "complete_phase_sets": sum(bool(r["phase_complete"]) for r in manifest),
        "detection_ready_trials": len(detection_rows),
        "feature_files": len(feature_files),
        "phase_files_new_remaining_activities": len(list(notes_root.rglob("S*_A*_phase_notes.json"))),
        "warnings": validation_warnings,
        "checks": {
            "all_manifest_trials_unique": len({r["trial"] for r in manifest}) == len(manifest),
            "all_detection_trials_have_features": all(r["feature_file"] for r in detection_rows),
            "all_features_exist": all(path.exists() for path in feature_files),
            "all_phase_orders_strict": all(not r["phase_complete"] or r["phase_order_valid"] for r in manifest),
            "all_phase_frames_in_bounds": all(not r["phase_complete"] or r["phase_in_bounds"] for r in manifest),
        },
    }
    write_json(output / "VALIDATION_REPORT.json", validation)
    checksum_rows = []
    for path in sorted(p for p in output.rglob("*") if p.is_file() and p.name != "SHA256SUMS.csv"):
        checksum_rows.append({"path": str(path.relative_to(output)), "sha256": sha256(path), "bytes": path.stat().st_size})
    write_csv(output / "SHA256SUMS.csv", checksum_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audits-root", type=Path, required=True)
    parser.add_argument("--notes-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
