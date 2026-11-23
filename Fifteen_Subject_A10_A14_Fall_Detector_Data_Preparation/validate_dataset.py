#!/usr/bin/env python3
"""Validate every prepared trajectory and leakage/provenance invariant."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from detector_data_core import as_bool, write_json


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE / "outputs")
    args = parser.parse_args()
    root = args.output_dir.expanduser().resolve()
    with (root / "dataset_manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["sample_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate sample IDs")
    counts = Counter(row["source_kind"] for row in rows)
    families: Counter[str] = Counter()
    activity_counts: Counter[str] = Counter()
    for row in rows:
        path = root / row["data_file"]
        if not path.is_file():
            raise FileNotFoundError(path)
        with np.load(path, allow_pickle=False) as data:
            required = {"time_s", "theta_rad", "x_m", "yaw_rad", "valid_mask", "observed_mask", "yaw_available_mask", "label", "activity_id", "sample_rate_hz", "mass_kg", "height_m"}
            if missing := required - set(data.files):
                raise ValueError(f"{path}: missing {sorted(missing)}")
            arrays = [np.asarray(data[name]) for name in ("time_s", "theta_rad", "x_m", "yaw_rad", "valid_mask", "observed_mask", "yaw_available_mask")]
            if len({len(values) for values in arrays}) != 1 or len(arrays[0]) < 2:
                raise ValueError(f"{path}: inconsistent arrays")
            if not np.all(np.diff(arrays[0]) > 0.0) or not all(np.all(np.isfinite(values)) for values in arrays[:4]):
                raise ValueError(f"{path}: invalid time or non-finite signals")
            if not np.isclose(float(data["sample_rate_hz"]), 30.0):
                raise ValueError(f"{path}: sample rate is not 30 Hz")
            if int(data["label"]) != int(row["label"]) or int(data["activity_id"]) != int(row["activity_id"]):
                raise ValueError(f"{path}: scalar metadata mismatch")
        if row["split_group"] != row["source_subject"]:
            raise ValueError(f"{row['sample_id']}: split/source mismatch")
        if row["source_kind"] == "synthetic_fall":
            if not as_bool(row["quality_approved"]):
                raise ValueError(f"{row['sample_id']}: non-approved synthetic row")
            if not row["synthetic_family_id"] or row["synthetic_family_id"] != row["source_real_trial"]:
                raise ValueError(f"{row['sample_id']}: invalid synthetic family")
            families[row["synthetic_family_id"]] += 1
            activity_counts[row["activity_code"]] += 1
    if families and max(families.values()) > 8:
        raise ValueError("A synthetic family has more than the expected eight fold/rank variants")
    report = {
        "status": "PASS",
        "trajectory_count": len(rows),
        "by_source_kind": dict(sorted(counts.items())),
        "synthetic_family_count": len(families),
        "maximum_approved_variants_per_family": max(families.values(), default=0),
        "synthetic_by_activity": dict(sorted(activity_counts.items())),
        "finite_arrays": True,
        "unique_sample_ids": True,
        "split_group_equals_source_subject": True,
        "synthetic_manifest_is_approved_only": True,
    }
    write_json(root / "integrity_report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
