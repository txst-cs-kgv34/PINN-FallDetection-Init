#!/usr/bin/env python3
"""Validate the delivered subject-wise real-fall package."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FEATURE_COLUMNS = {
    "trial", "subject", "activity", "frame0", "time_from_fall_onset_s",
    "phase_segment", "phase_boundary", "com_camera_x_m", "com_camera_y_down_m",
    "com_camera_z_m", "com_vertical_up_m", "aligned_progression_m",
    "aligned_lateral_m", "vertical_from_onset_m", "fall_direction_x",
    "fall_direction_z", "repaired_frame",
}
PHASES = {"initial_standing", "fall_onset", "descent", "apparent_contact", "post_fall"}


def main() -> None:
    with (ROOT / "manifests" / "trial_manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    assert len(manifest) == 375, f"expected 375 slots, found {len(manifest)}"
    assert len({r["trial"] for r in manifest}) == 375, "duplicate trial IDs"
    included = [r for r in manifest if r["include_detection_training"] == "True"]
    assert len(included) == 322, f"expected 322 detection-ready trials, found {len(included)}"
    for row in included:
        path = ROOT / row["feature_file"]
        assert path.exists(), f"missing feature: {path}"
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            assert REQUIRED_FEATURE_COLUMNS <= set(reader.fieldnames or []), f"feature schema mismatch: {path}"
            frames = list(reader)
        assert len(frames) == int(row["frame_count"]), f"frame count mismatch: {row['trial']}"
        assert [int(r["frame0"]) for r in frames] == list(range(len(frames))), f"non-contiguous frames: {row['trial']}"
        boundaries = {r["phase_boundary"] for r in frames if r["phase_boundary"]}
        assert boundaries == PHASES, f"phase boundary mismatch: {row['trial']}"
        assert all(r["repaired_frame"] in {"0", "1"} for r in frames), f"bad repair mask: {row['trial']}"
    report = json.loads((ROOT / "VALIDATION_REPORT.json").read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert all(report["checks"].values())
    print(f"PASS: {len(manifest)} slots, {len(included)} detection-ready features, all schemas and phase boundaries valid")


if __name__ == "__main__":
    main()
