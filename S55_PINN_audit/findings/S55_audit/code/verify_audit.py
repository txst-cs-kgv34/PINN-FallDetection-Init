"""Verify a completed subject audit without relying on subject-specific counts."""

from pathlib import Path
import argparse
import hashlib
import json

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()

    run = args.run
    config = json.loads((run / "config.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "results/manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run / "results/study_summary.json").read_text(encoding="utf-8"))
    trials = json.loads((run / "results/trial_summary.json").read_text(encoding="utf-8"))

    expected = sum(len(v) for v in config.get("expected_trials", {}).values())
    assert len(manifest) == expected, (len(manifest), expected)
    assert summary["expected_files"] == expected
    assert summary["nonempty_files"] + summary["empty_files"] + summary["invalid_files"] + summary["missing_files"] == expected
    assert len(trials) == expected

    numeric = [row for row in manifest if row["status"] == "numeric"]
    total_frames = 0
    for row in numeric:
        raw = run / "raw" / f"{row['trial']}.csv"
        assert raw.exists()
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == row["sha256"]
        array = np.loadtxt(raw, delimiter=",", ndmin=2)
        assert array.shape[1] == 96
        assert np.isfinite(array).all()
        total_frames += len(array)
    assert total_frames == summary["total_frames"]

    required = [
        run / "FINDINGS.md",
        run / "REPORT.html",
        run / "results/trial_summary.csv",
        run / "results/temporal_summary.csv",
        run / "results/plots/tracking_diagnostics.png",
    ]
    assert all(path.exists() and path.stat().st_size for path in required)
    if args.source:
        assert hashlib.sha256(args.source.read_bytes()).hexdigest() == summary["archive_sha256"]

    print(
        f"PASS: {config['subject_id']} audit; {expected} expected, "
        f"{len(numeric)} numeric, {total_frames} analyzed frames"
    )


if __name__ == "__main__":
    main()
