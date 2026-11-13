#!/usr/bin/env python3
"""Validate prepared detector arrays, labels, timing, and leakage groups."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE / "outputs")
    args = parser.parse_args()
    root = args.output_dir.expanduser().resolve()
    manifest = json.loads((root / "dataset_manifest.json").read_text(encoding="utf-8"))
    samples = manifest["samples"]
    seen: set[str] = set()
    counts = {"real_adl": 0, "real_fall": 0, "synthetic_fall": 0}
    for row in samples:
        sample_id = str(row["sample_id"])
        if sample_id in seen:
            raise ValueError(f"Duplicate sample ID: {sample_id}")
        seen.add(sample_id)
        kind = str(row["source_kind"])
        counts[kind] += 1
        if str(row["split_group"]) != str(row["source_subject"]):
            raise ValueError(f"{sample_id}: split group differs from source subject")
        path = root / str(row["data_file"])
        with np.load(path, allow_pickle=False) as data:
            required = {
                "time_s", "theta_rad", "x_m", "valid_mask", "label",
                "activity_id", "sample_rate_hz", "mass_kg", "height_m",
            }
            if not required.issubset(data.files):
                raise ValueError(f"{sample_id}: missing arrays {sorted(required - set(data.files))}")
            time = np.asarray(data["time_s"], dtype=np.float64)
            theta = np.asarray(data["theta_rad"], dtype=np.float64)
            x_m = np.asarray(data["x_m"], dtype=np.float64)
            if not (len(time) == len(theta) == len(x_m) == int(row["sample_count"])):
                raise ValueError(f"{sample_id}: manifest/array length mismatch")
            if not all(np.all(np.isfinite(values)) for values in (time, theta, x_m)):
                raise ValueError(f"{sample_id}: non-finite trajectory value")
            if len(time) > 1 and not np.allclose(np.diff(time), 1.0 / 30.0, atol=2e-6):
                raise ValueError(f"{sample_id}: time grid is not 30 Hz")
            if int(data["label"]) != int(row["label"]):
                raise ValueError(f"{sample_id}: label mismatch")
            if int(data["activity_id"]) != int(row["activity_id"]):
                raise ValueError(f"{sample_id}: activity mismatch")
            if not np.all(np.asarray(data["valid_mask"]) == 1):
                raise ValueError(f"{sample_id}: variable-length canonical file should be fully valid")
    adl_subjects = {row["subject"] for row in samples if row["source_kind"] == "real_adl"}
    if "S59" in adl_subjects or "S31" not in adl_subjects:
        raise ValueError("S59/S31 ADL substitution is not represented correctly")
    if counts != {"real_adl": 545, "real_fall": 70, "synthetic_fall": 226}:
        raise ValueError(f"Unexpected source counts: {counts}")
    print(f"Validated {len(samples)} canonical 30 Hz trials: {counts}")
    print("Labels, timing, finite values, file keys, and split groups are consistent.")


if __name__ == "__main__":
    main()
