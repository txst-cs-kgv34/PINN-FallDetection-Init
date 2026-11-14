from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Sequence

import numpy as np

from detector_core import load_config, logical_group, read_manifest, split_scenario_rows


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate detector inputs and split policy.")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    args = parser.parse_args(argv)
    config = load_config(args.config)
    data_root = Path(config["data_root"])
    rows = read_manifest(data_root)
    identifiers = [row["sample_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate sample_id values were found")
    counts = Counter(row["source_kind"] for row in rows)
    expected_sources = {"real_adl", "real_fall", "synthetic_fall"}
    if set(counts) != expected_sources:
        raise ValueError(f"Expected {expected_sources}, found {set(counts)}")
    for row in rows:
        if abs(float(row["sample_rate_hz"]) - float(config["sample_rate_hz"])) > 1e-5:
            raise ValueError(f"Unexpected sample rate for {row['sample_id']}")
        path = data_root / row["data_file"]
        if not path.is_file():
            raise FileNotFoundError(path)
        with np.load(path, allow_pickle=False) as archive:
            required = {"theta_rad", "x_m", "valid_mask", "label"}
            if not required.issubset(archive.files):
                raise ValueError(f"{path} is missing {sorted(required - set(archive.files))}")
            if int(archive["label"]) != int(row["label"]):
                raise ValueError(f"Label mismatch in {path}")
            if len(archive["theta_rad"]) != int(row["sample_count"]):
                raise ValueError(f"Length mismatch in {path}")
    groups = {logical_group(row, config) for row in rows}
    configured = {
        group for fold in config["folds"] for group in fold["test_groups"]
    }
    if groups != configured:
        raise ValueError(
            f"Fold groups do not match manifest. Missing={sorted(groups-configured)}, "
            f"extra={sorted(configured-groups)}"
        )
    for fold_index in range(len(config["folds"])):
        for scenario in (
            "real_fall_real_adl",
            "synthetic_fall_real_adl",
            "real_synthetic_fall_real_adl",
        ):
            selected, partitions = split_scenario_rows(rows, config, scenario, fold_index)
            if any(row["source_kind"] == "synthetic_fall" for row in selected["test"]):
                raise AssertionError("Synthetic test leakage")
    print("Detector setup validation passed.")
    print(f"Data root: {data_root}")
    print(f"Trajectories: {len(rows)}")
    print(f"Source counts: {dict(counts)}")
    print(f"Logical subject groups: {len(groups)}")
    print(f"Cross-validation folds: {len(config['folds'])}")


if __name__ == "__main__":
    main()

