"""Create conservative automatic phase suggestions for manual review.

The suggestions are signal-derived candidates, not ground-truth contact labels.
They use a subject-relative initial vertical axis because floor calibration and
force measurements are unavailable.
"""

from pathlib import Path
import argparse
import csv
import json

import numpy as np

from skeleton_model import com_proxy


PHASES = ("initial_standing", "fall_onset", "descent", "apparent_contact", "post_fall")


def smooth(values, width):
    width = max(1, int(width))
    if width == 1:
        return values.copy()
    kernel = np.ones(width, dtype=float) / width
    pad = width // 2
    padded = np.pad(values, (pad, width - 1 - pad), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


def sustained(mask, start, length):
    length = max(1, int(length))
    for index in range(max(0, start), max(0, len(mask) - length + 1)):
        if np.all(mask[index : index + length]):
            return index
    return None


def robust_scale(values):
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    return median, max(1.4826 * mad, 1e-6)


def suggest(pose, segments, fps):
    count = len(pose)
    baseline_n = max(6, min(int(round(0.5 * fps)), max(6, count // 4)))
    feet = pose[:, [21, 25]].mean(axis=1)
    eyes = pose[:, [28, 30]].mean(axis=1)
    up = np.median(eyes[:baseline_n] - feet[:baseline_n], axis=0)
    up = up / max(np.linalg.norm(up), 1e-9)
    com = com_proxy(pose, segments)[0]
    height = (com - feet) @ up
    body = pose[:, 26] - feet
    body_norm = np.linalg.norm(body, axis=1).clip(1e-9)
    tilt = np.degrees(np.arccos(np.clip((body @ up) / body_norm, -1.0, 1.0)))
    width = max(3, int(round(0.12 * fps)) | 1)
    height_s = smooth(height, width)
    tilt_s = smooth(tilt, width)
    velocity = np.gradient(com, 1.0 / fps, axis=0)
    speed = smooth(np.linalg.norm(velocity, axis=1), width)
    vertical_velocity = smooth(np.gradient(height_s, 1.0 / fps), width)
    tilt_rate = smooth(np.abs(np.gradient(tilt_s, 1.0 / fps)), width)

    speed_med, speed_scale = robust_scale(speed[:baseline_n])
    tilt_med, tilt_scale = robust_scale(tilt_rate[:baseline_n])
    onset_signal = (speed > max(0.12, speed_med + 5 * speed_scale)) | (
        tilt_rate > max(12.0, tilt_med + 5 * tilt_scale)
    )
    onset = sustained(onset_signal, max(1, baseline_n // 2), max(2, int(0.1 * fps)))
    if onset is None:
        onset = int(np.argmax(speed + 0.01 * tilt_rate))
    onset = min(onset, count - 4)

    descent_signal = vertical_velocity < -max(0.10, 3 * robust_scale(vertical_velocity[:baseline_n])[1])
    descent = sustained(descent_signal, onset, max(2, int(0.1 * fps)))
    if descent is None:
        stop = min(count, onset + max(3, int(1.0 * fps)))
        descent = onset + int(np.argmin(vertical_velocity[onset:stop]))
    descent = max(onset + 1, min(descent, count - 3))

    search = height_s[descent:]
    minimum = float(np.min(search))
    tolerance = max(0.01, 0.02 * max(abs(minimum), 1e-6))
    near_minimum = np.flatnonzero(search <= minimum + tolerance)
    contact = descent + int(near_minimum[0] if len(near_minimum) else np.argmin(search))
    contact = max(descent + 1, min(contact, count - 2))

    post_speed_threshold = max(0.08, speed_med + 3 * speed_scale)
    post = sustained(
        speed < post_speed_threshold,
        min(count - 1, contact + max(1, int(0.2 * fps))),
        max(3, int(0.4 * fps)),
    )
    if post is None:
        post = count - 1
    post = max(contact + 1, min(post, count - 1))

    frames = [0, onset, descent, contact, post]
    for index in range(1, len(frames)):
        frames[index] = max(frames[index], frames[index - 1] + 1)
    if frames[-1] >= count:
        frames = np.linspace(0, count - 1, len(PHASES)).round().astype(int).tolist()

    height_drop = float(height_s[onset] - height_s[contact])
    duration_s = (count - 1) / fps
    score = int(height_drop > 0.12) + int(onset < contact) + int(post < count - 1)
    confidence = ["low", "medium", "high"][min(score, 2)]
    if duration_s < 1.5 or height_drop < 0.05:
        confidence = "low"
    diagnostics = {
        "baseline_frames": baseline_n,
        "initial_vertical_axis_camera": up.tolist(),
        "onset_peak_speed_m_s": float(speed[onset]),
        "onset_peak_tilt_rate_deg_s": float(tilt_rate[onset]),
        "onset_to_contact_height_drop_m": height_drop,
        "post_fall_speed_m_s": float(speed[post]),
        "duration_s": float(duration_s),
        "short_clip_warning": bool(duration_s < 1.5),
        "suggestion_confidence": confidence,
    }
    return frames, diagnostics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = json.loads((args.run / "config.json").read_text(encoding="utf-8"))
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    model = json.loads((args.run / "segment_model.json").read_text(encoding="utf-8"))
    if selection["subject_id"] != config["subject_id"]:
        raise ValueError("selection subject does not match audit")
    notes = []
    diagnostics = []
    for trial in selection["remaining_candidate_trials"]:
        raw = np.loadtxt(args.run / "raw" / f"{trial}.csv", delimiter=",", ndmin=2)
        pose = raw.reshape(-1, 32, 3) * {"mm": 0.001, "m": 1.0}[config["coordinate_units"]]
        frames, detail = suggest(pose, model["segments"], float(config["fps"]))
        diagnostics.append({"trial": trial, **detail})
        for phase, frame in zip(PHASES, frames):
            notes.append(
                {
                    "trial": trial,
                    "frame0": int(frame),
                    "nominal_time_s": float(frame / config["fps"]),
                    "view_mode": "raw",
                    "phase": phase,
                    "note": "Automatic candidate; verify visually before use.",
                    "status": "automatic_suggestion_review_required",
                }
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "subject": config["subject_id"],
                "nominal_fps": config["fps"],
                "notes": notes,
                "warning": "Signal-derived candidates only; apparent contact is not force-verified.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    diagnostics_path = args.output.with_name(args.output.stem + "_diagnostics.csv")
    with diagnostics_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(diagnostics[0]))
        writer.writeheader()
        writer.writerows(diagnostics)
    print(f"Wrote {len(notes)} phase candidates for {len(diagnostics)} trials")


if __name__ == "__main__":
    main()
