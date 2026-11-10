#!/usr/bin/env python3
"""Validate that prepared real arrays retain the complete source-to-contact interval."""

from __future__ import annotations

import argparse
import json
from collections import Counter

import numpy as np

from operator_core import ROOT, load_config


def is_prefix_mask(mask: np.ndarray) -> bool:
    values = mask.astype(bool)
    count = int(values.sum())
    return bool(np.all(values[:count]) and not np.any(values[count:]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="full")
    args = parser.parse_args()
    config = load_config(args.config)
    data_dir = ROOT / "outputs" / f"real_data_{args.mode}"
    manifest_path = data_dir / "real_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []
    expected_exclusion = int(
        round(
            float(config["physics"]["contact_exclusion_s"])
            * int(config["real_data"]["target_rate_hz"])
        )
    )
    if manifest.get("experiment") != config["experiment_name"]:
        errors.append("Prepared-data experiment name does not match experiment.json")
    if manifest.get("trajectory_scope") != "complete source clip through apparent contact":
        errors.append("Prepared manifest does not declare the full apparent-contact scope")

    counts: Counter[str] = Counter()
    for item in manifest["included_trials"]:
        trial = str(item["trial"])
        counts[str(item["subject"])] += 1
        with np.load(data_dir / item["data_file"], allow_pickle=False) as data:
            valid = data["valid_mask"] > 0.5
            physics = data["physics_mask"] > 0.5
            theta = data["theta_rad"]
        if not is_prefix_mask(valid):
            errors.append(f"{trial}: valid_mask is not a contiguous prefix")
        if not is_prefix_mask(physics):
            errors.append(f"{trial}: physics_mask is not a contiguous prefix")
        if np.any(physics & ~valid):
            errors.append(f"{trial}: physics_mask includes data-invalid samples")
        valid_count = int(valid.sum())
        physics_count = int(physics.sum())
        if valid_count != int(item["usable_samples"]):
            errors.append(f"{trial}: full source interval was truncated or miscounted")
        if valid_count - physics_count != min(expected_exclusion, valid_count):
            errors.append(f"{trial}: unexpected contact-exclusion mask length")
        if not np.isfinite(theta[valid]).all():
            errors.append(f"{trial}: non-finite angle inside the full-fall interval")
        if float(item["maximum_abs_theta_deg"]) < 20.0:
            warnings.append(
                f"{trial}: maximum |theta| is below 20 degrees; verify the source endpoint"
            )

    expected_subjects = {str(subject["id"]) for subject in config["subjects"]}
    if set(counts) != expected_subjects:
        errors.append("Prepared trials do not cover all configured subjects")
    print(json.dumps({"included_trials_by_subject": dict(sorted(counts.items()))}, indent=2))
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(
        f"Full-fall validation passed: {sum(counts.values())} trials retain their complete "
        f"source interval; physics excludes only the final {expected_exclusion} samples."
    )


if __name__ == "__main__":
    main()
