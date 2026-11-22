#!/usr/bin/env python3
"""Validate A10-A13 arrays, activity axes, masks, and one-hot fields."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
ACTIVITY_INDEX = {"A10": 0, "A11": 1, "A12": 2, "A13": 3}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    args = parser.parse_args()
    config = json.loads((ROOT / "experiment.json").read_text(encoding="utf-8"))
    root = ROOT / "outputs" / f"real_data_{args.mode}"
    manifest = json.loads((root / "planar_manifest.json").read_text(encoding="utf-8"))
    trials = manifest["included_trials"]
    expected = int(config["data"]["expected_trial_count"])
    if len(trials) != expected:
        raise ValueError(f"expected {expected} A10-A13 trials, found {len(trials)}")
    axes = config["data"]["activity_axes_subject_frame_lateral_forward"]
    for item in trials:
        activity = item["activity"]
        if activity not in ACTIVITY_INDEX:
            raise ValueError(f"{item['trial']}: unexpected activity {activity}")
        if item.get("axis_source") != "activity_identity_only_no_future_target_motion":
            raise ValueError(f"{item['trial']}: future-free axis provenance missing")
        path = root / "planar" / item["data_file"]
        with np.load(path, allow_pickle=False) as data:
            required = {
                "time_s", "theta_rad", "x_m", "yaw_rad", "valid_mask",
                "physics_mask", "initial_state", "demographics", "mass_kg",
                "height_m", "fall_direction", "activity_vector",
            }
            if not required <= set(data.files):
                raise ValueError(f"{path}: missing {sorted(required - set(data.files))}")
            n = len(data["time_s"])
            for key in ("theta_rad", "x_m", "yaw_rad", "valid_mask", "physics_mask"):
                if data[key].shape != (n,) or not np.isfinite(data[key]).all():
                    raise ValueError(f"{path}: invalid {key}")
            if np.any(data["physics_mask"] > data["valid_mask"]):
                raise ValueError(f"{path}: physics mask exceeds valid mask")
            expected_axis = np.asarray(axes[activity], dtype=np.float32)
            if not np.array_equal(data["fall_direction"], expected_axis):
                raise ValueError(f"{path}: activity axis differs from configuration")
            if data["initial_state"].shape != (4,):
                raise ValueError(f"{path}: wrong initial-state width")
            one_hot = data["activity_vector"]
            if one_hot.shape != (4,) or not np.isclose(one_hot.sum(), 1.0):
                raise ValueError(f"{path}: invalid activity one-hot")
            if int(one_hot.argmax()) != ACTIVITY_INDEX[activity]:
                raise ValueError(f"{path}: activity head does not match {activity}")
    seen = dict(sorted(Counter(item["activity"] for item in trials).items()))
    if seen != config["data"]["expected_by_activity"]:
        raise ValueError(f"activity counts changed: {seen}")
    print(f"PASS: {expected} A10-A13 trials; activity axes are fixed and future-free")


if __name__ == "__main__":
    main()
