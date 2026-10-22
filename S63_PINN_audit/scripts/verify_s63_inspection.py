"""Verify the delivered all-trial and A11 S63 inspection packages."""

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "findings" / "S63_audit"


def verify_package(relative, expected_trials, expected_frames):
    output = ROOT / relative
    payload = json.loads((output / "inspection_data.json").read_text())
    assert payload["subject"]["subject_id"] == "S63"
    assert payload["subject"]["sex"] == "male"
    assert payload["fps"] == 30
    assert len(payload["trials"]) == expected_trials
    assert sum(trial["frames"] for trial in payload["trials"]) == expected_frames
    assert (output / "INSPECT.html").stat().st_size > 100_000
    for trial in payload["trials"]:
        raw = np.loadtxt(
            RUN / "raw" / f"{trial['trial']}.csv", delimiter=",", ndmin=2
        ).reshape(-1, 32, 3) * 0.001
        np.testing.assert_array_equal(np.asarray(trial["modes"]["raw"]["pose"]), raw)
        assert len(trial["modes"]["filtered"]["pose"]) == trial["frames"]
        assert len(trial["raw_review_flags"]) == trial["frames"]
        assert len(trial["raw_repeated_previous"]) == trial["frames"]
        assert (output / "geometry" / f"{trial['trial']}.csv").is_file()


def main():
    verify_package(Path("inspections/S63_candidates"), 25, 3897)
    verify_package(Path("inspections/S63_A11_frontfall"), 5, 776)
    print("PASS: S63 all-trial and A11 inspection packages preserve raw data and timing")


if __name__ == "__main__":
    main()
