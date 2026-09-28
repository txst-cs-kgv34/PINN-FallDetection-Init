"""Validate manual phase notes and convert them to per-trial windows."""

import json
import re
from collections import defaultdict
from pathlib import Path

PHASE_ORDER = (
    "initial_standing",
    "fall_onset",
    "descent",
    "apparent_contact",
    "post_fall",
)
DYNAMICS_PHASE_ORDER = PHASE_ORDER[:-1]
TRIAL_PATTERN = re.compile(r"^(?P<subject>S\d+)(?P<activity>A\d+)(?P<trial>T\d+)$")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_phase_notes(notes_path, run_dir, config, selection):
    """Return ordered, validated phase windows.

    Phase notes remain provisional skeleton observations. Validation checks file
    structure, candidate membership, frame bounds, nominal time and phase order;
    it does not confirm physical ground contact.
    """
    payload = read_json(notes_path)
    subject = config["subject_id"]
    fps = float(config["fps"])
    errors = []

    if payload.get("subject") != subject:
        errors.append(
            f"phase-note subject {payload.get('subject')!r} does not match {subject!r}"
        )
    if abs(float(payload.get("nominal_fps", -1)) - fps) > 1e-9:
        errors.append("phase-note nominal_fps does not match the subject configuration")

    candidates = set(selection["remaining_candidate_trials"])
    excluded = set(selection.get("excluded_trials", {}))
    grouped = defaultdict(dict)
    notes = payload.get("notes")
    if not isinstance(notes, list):
        errors.append("notes must be a list")
        notes = []

    raw_dir = Path(run_dir) / "raw"
    frame_counts = {}
    for raw_path in raw_dir.glob("*.csv"):
        with raw_path.open("rb") as handle:
            frame_counts[raw_path.stem] = sum(1 for line in handle if line.strip())

    for index, note in enumerate(notes):
        if not isinstance(note, dict):
            errors.append(f"note {index} is not an object")
            continue
        trial = note.get("trial")
        phase = note.get("phase")
        match = TRIAL_PATTERN.fullmatch(str(trial))
        if not match or match.group("subject") != subject:
            errors.append(f"note {index} has invalid trial {trial!r}")
            continue
        if trial in excluded:
            errors.append(f"note {index} references excluded trial {trial}")
        if trial not in candidates:
            errors.append(
                f"note {index} references a trial outside the candidate list: {trial}"
            )
        if phase not in PHASE_ORDER:
            errors.append(f"note {index} has unsupported phase {phase!r}")
            continue
        if phase in grouped[trial]:
            errors.append(f"trial {trial} has duplicate {phase} notes")
            continue
        try:
            frame = int(note["frame0"])
            nominal_time = float(note["nominal_time_s"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"note {index} has invalid frame0 or nominal_time_s")
            continue
        if frame < 0 or frame >= frame_counts.get(trial, 0):
            errors.append(f"note {index} frame {frame} is outside trial {trial}")
        if abs(nominal_time - frame / fps) > 1e-8:
            errors.append(f"note {index} nominal time does not equal frame0/fps")
        grouped[trial][phase] = {**note, "frame0": frame}

    windows = []
    for trial in sorted(grouped):
        missing = [
            phase for phase in DYNAMICS_PHASE_ORDER if phase not in grouped[trial]
        ]
        if missing:
            errors.append(
                f"trial {trial} is missing required dynamics phases: {', '.join(missing)}"
            )
            continue
        present_phases = [phase for phase in PHASE_ORDER if phase in grouped[trial]]
        frames = [grouped[trial][phase]["frame0"] for phase in present_phases]
        if any(right <= left for left, right in zip(frames, frames[1:])):
            errors.append(f"trial {trial} phase frames are not strictly increasing")
            continue
        match = TRIAL_PATTERN.fullmatch(trial)
        window = {
            "trial": trial,
            "activity": match.group("activity"),
            "frame_count": frame_counts[trial],
            "annotation_status": grouped[trial]["fall_onset"].get("status", ""),
        }
        for phase, frame in zip(present_phases, frames):
            window[f"{phase}_frame0"] = frame
            window[f"{phase}_time_s"] = frame / fps
        if "post_fall" not in grouped[trial]:
            window["post_fall_frame0"] = None
            window["post_fall_time_s"] = None
        window["onset_to_apparent_contact_s"] = (
            window["apparent_contact_frame0"] - window["fall_onset_frame0"]
        ) / fps
        window["initial_to_post_fall_s"] = (
            (window["post_fall_frame0"] - window["initial_standing_frame0"]) / fps
            if window["post_fall_frame0"] is not None
            else None
        )
        windows.append(window)

    if errors:
        raise ValueError("Invalid phase notes:\n- " + "\n- ".join(errors))
    if not windows:
        raise ValueError("No complete annotated trials were found")
    return payload, windows
