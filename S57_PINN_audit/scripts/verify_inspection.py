"""Verify a generated inspection package against its immutable audit run."""

from pathlib import Path
import argparse
import hashlib
import json

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--inspection", type=Path, required=True)
    args = parser.parse_args()

    run = args.run
    inspection = args.inspection
    data = json.loads((inspection / "inspection_data.json").read_text(encoding="utf-8"))
    selection = json.loads((inspection / "selection.json").read_text(encoding="utf-8"))
    manifest = {
        row["trial"]: row
        for row in json.loads((run / "results/manifest.json").read_text(encoding="utf-8"))
    }
    candidates = selection["remaining_candidate_trials"]
    assert data["subject"]["subject_id"] == selection["subject_id"]
    assert sorted(item["trial"] for item in data["trials"]) == sorted(candidates)
    assert (inspection / "INSPECT.html").stat().st_size > 0

    for item in data["trials"]:
        trial = item["trial"]
        raw_path = run / "raw" / f"{trial}.csv"
        assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == manifest[trial]["sha256"]
        raw = np.loadtxt(raw_path, delimiter=",", ndmin=2).reshape(-1, 32, 3)
        raw = raw * {"mm": 0.001, "m": 1.0}[data["subject"]["coordinate_units"]]
        np.testing.assert_array_equal(np.asarray(item["modes"]["raw"]["pose"]), raw)
        assert item["frames"] == len(raw)
        assert len(item["raw_review_flags"]) == len(raw)
        assert len(item.get("repair_methods", [])) in (0, len(raw))
        geometry = np.genfromtxt(
            inspection / "geometry" / f"{trial}.csv",
            delimiter=",",
            names=True,
            dtype=None,
            encoding="utf-8",
        )
        assert len(geometry) >= len(raw)

    if data.get("repair_mask_supplied"):
        expected_repairs = sum(
            method is not None
            for item in data["trials"]
            for method in item["repair_methods"]
        )
        summaries = json.loads(
            (inspection / "inspection_summary.json").read_text(encoding="utf-8")
        )
        assert expected_repairs == sum(row["repaired_frames"] for row in summaries)

    print(
        f"PASS: {selection['subject_id']} inspection; "
        f"{len(data['trials'])} trials, {sum(t['frames'] for t in data['trials'])} frames"
    )


if __name__ == "__main__":
    main()
