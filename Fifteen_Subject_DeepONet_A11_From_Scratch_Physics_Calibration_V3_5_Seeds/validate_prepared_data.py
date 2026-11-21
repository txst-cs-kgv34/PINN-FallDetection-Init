#!/usr/bin/env python3
"""Validate the prepared A11 arrays, masks, and conditioning fields."""

from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--mode",choices=("smoke","full"),default="full"); args=parser.parse_args()
    expected=64; root=ROOT/"outputs"/f"real_data_{args.mode}"
    manifest=json.loads((root/"planar_manifest.json").read_text()); trials=manifest["included_trials"]
    if len(trials)!=expected: raise ValueError(f"expected {expected} A11 trials, found {len(trials)}")
    for item in trials:
        if item["activity"]!="A11": raise ValueError(f"{item['trial']}: non-A11 trial")
        path=root/"planar"/item["data_file"]
        with np.load(path,allow_pickle=False) as data:
            required={"time_s","theta_rad","x_m","yaw_rad","valid_mask","physics_mask","initial_state","demographics","mass_kg","height_m","fall_direction","activity_vector"}
            if not required<=set(data.files): raise ValueError(f"{path}: missing {sorted(required-set(data.files))}")
            n=len(data["time_s"])
            for key in ("theta_rad","x_m","yaw_rad","valid_mask","physics_mask"):
                if data[key].shape!=(n,) or not np.isfinite(data[key]).all(): raise ValueError(f"{path}: invalid {key}")
            if np.any(data["physics_mask"]>data["valid_mask"]): raise ValueError(f"{path}: physics mask exceeds valid mask")
            if not np.isclose(np.linalg.norm(data["fall_direction"]),1.0,atol=1e-5): raise ValueError(f"{path}: fall direction not unit")
            if data["initial_state"].shape!=(4,): raise ValueError(f"{path}: wrong initial-state width")
            if data["activity_vector"].shape!=(4,) or not np.isclose(data["activity_vector"][1],1.0): raise ValueError(f"{path}: wrong A11 activity vector")
    seen=Counter(item["activity"] for item in trials)
    if seen!={"A11":expected}: raise ValueError(f"activity counts changed: {seen}")
    print(f"PASS: {expected} A11 trials; arrays, masks, directions, and conditioning fields valid")

if __name__ == "__main__":
    main()
