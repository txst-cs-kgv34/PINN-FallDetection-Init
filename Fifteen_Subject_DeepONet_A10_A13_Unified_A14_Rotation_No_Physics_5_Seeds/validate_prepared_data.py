#!/usr/bin/env python3
"""Validate prepared arrays, masks, activity counts, and conditioning fields."""

from __future__ import annotations
import argparse,json
from collections import Counter
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--mode",choices=("smoke","full"),default="full"); args=parser.parse_args()
    expected={"planar":257,"rotation":49}; expected_activity={"A10":58,"A11":64,"A12":68,"A13":67,"A14":49}; seen={}
    for group in ("planar","rotation"):
        root=ROOT/"outputs"/f"real_data_{args.mode}"; manifest=json.loads((root/f"{group}_manifest.json").read_text()); trials=manifest["included_trials"]
        if len(trials)!=expected[group]: raise ValueError(f"{group}: expected {expected[group]}, found {len(trials)}")
        for item in trials:
            path=root/group/item["data_file"]
            with np.load(path,allow_pickle=False) as data:
                required={"time_s","theta_rad","x_m","yaw_rad","valid_mask","physics_mask","initial_state","demographics","mass_kg","height_m","fall_direction","activity_vector"}
                if not required<=set(data.files): raise ValueError(f"{path}: missing {sorted(required-set(data.files))}")
                n=len(data["time_s"])
                for key in ("theta_rad","x_m","yaw_rad","valid_mask","physics_mask"):
                    if data[key].shape!=(n,) or not np.isfinite(data[key]).all(): raise ValueError(f"{path}: invalid {key}")
                if np.any(data["physics_mask"]>data["valid_mask"]): raise ValueError(f"{path}: physics mask exceeds valid mask")
                if not np.isclose(np.linalg.norm(data["fall_direction"]),1.0,atol=1e-5): raise ValueError(f"{path}: fall direction not unit")
                expected_state=4 if group=="planar" else 6
                if data["initial_state"].shape!=(expected_state,): raise ValueError(f"{path}: wrong initial-state width")
        seen.update(Counter(item["activity"] for item in trials))
    if seen!=expected_activity: raise ValueError(f"activity counts changed: {seen}")
    print(f"PASS: {expected['planar']} planar and {expected['rotation']} rotation trials; arrays, masks, directions, and activities valid")

if __name__=="__main__": main()
