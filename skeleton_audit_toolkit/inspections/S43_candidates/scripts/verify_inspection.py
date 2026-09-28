"""Verify geometry, filtering, candidate exclusions and exported inspection data."""

from pathlib import Path
import json
import tempfile

import numpy as np

from foot_geometry import compute_foot_geometry
from filter_motion import filter_motion
from inspect_trials import prepare_inspection


def main():
    root = Path(__file__).resolve().parents[1]
    # Independent, simple geometry with a known midpoint and 3-4-5 separation.
    pose = np.zeros((40, 32, 3))
    pose[:, 21] = [0, 2, 0]
    pose[:, 25] = [3, 2, 4]
    com = np.tile([2, 1, 3], (40, 1))
    geometry = compute_foot_geometry(pose, com)
    np.testing.assert_allclose(geometry["foot_separation_camera_xz"], 5)
    np.testing.assert_allclose(geometry["foot_midpoint"], np.tile([1.5, 2, 2], (40, 1)))
    np.testing.assert_allclose(
        geometry["com_relative_to_foot_midpoint"], np.tile([0.5, -1, 1], (40, 1))
    )
    shifted = compute_foot_geometry(pose + 100, com + 100)
    np.testing.assert_allclose(
        shifted["com_relative_to_foot_midpoint"],
        geometry["com_relative_to_foot_midpoint"],
    )
    original = pose.copy()
    filtered, status = filter_motion(pose, 30, 1.5)
    assert status["status"] == "available" and filtered.shape == pose.shape
    np.testing.assert_allclose(filtered, pose, atol=1e-12)
    np.testing.assert_array_equal(pose, original)
    skipped, status = filter_motion(pose[:10], 30, 1.5)
    assert skipped is None and status["status"] == "skipped_short_clip"
    for cutoff in [0, -1, 15, float("nan")]:
        try:
            filter_motion(pose, 30, cutoff)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid cutoff accepted")

    # Verify delivered raw coordinates, unchanged frame counts and raw review flags.
    output = root / "inspections/S43_candidates"
    payload = json.loads((output / "inspection_data.json").read_text())
    assert len(payload["trials"]) == 24
    assert sum(t["frames"] for t in payload["trials"]) == 5898
    assert "S43A10T01" not in [t["trial"] for t in payload["trials"]]
    assert payload["fps"] == 30
    assert sum(sum(t["raw_review_flags"]) for t in payload["trials"]) == 800
    assert sum(sum(t["raw_repeated_previous"]) for t in payload["trials"]) == 1211
    for trial in payload["trials"]:
        original = (
            np.loadtxt(
                root / "findings/S43_audit/raw" / (trial["trial"] + ".csv"),
                delimiter=",",
            ).reshape(-1, 32, 3)
            * 0.001
        )
        np.testing.assert_array_equal(trial["modes"]["raw"]["pose"], original)
        assert len(trial["modes"]["filtered"]["pose"]) == trial["frames"]
        for mode in trial["modes"].values():
            assert np.isfinite(np.asarray(mode["pose"])).all()
        rows = np.genfromtxt(
            output / "geometry" / (trial["trial"] + ".csv"),
            delimiter=",",
            names=True,
            dtype=None,
            encoding="utf-8",
        )
        assert len(rows) == 2 * trial["frames"]
        for mode in ["raw", "filtered"]:
            np.testing.assert_allclose(
                rows["nominal_time_s"][rows["mode"] == mode],
                np.arange(trial["frames"]) / 30,
            )

    # Raw-only workflow is also supported; invalid selection must fail before writing.
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        selected = {
            "subject_id": "S43",
            "remaining_candidate_trials": ["S43A10T02"],
            "excluded_trials": {},
        }
        path = temp / "selection.json"
        path.write_text(json.dumps(selected))
        prepare_inspection(root / "findings/S43_audit", path, temp / "raw_only")
        raw_only = json.loads((temp / "raw_only/inspection_data.json").read_text())
        assert list(raw_only["trials"][0]["modes"]) == ["raw"]
        selected["excluded_trials"] = {"S43A10T02": "test exclusion"}
        path.write_text(json.dumps(selected))
        try:
            prepare_inspection(root / "findings/S43_audit", path, temp / "rejected")
        except ValueError:
            assert not (temp / "rejected").exists()
        else:
            raise AssertionError("Excluded trial accepted")
    print(
        "PASS: geometry, filter guards, source preservation, 24 candidates/5898 frames, flags, timing and selection enforcement"
    )


if __name__ == "__main__":
    main()
