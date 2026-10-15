"""Integrity checks for the retained S43 audit dataset and results."""

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "findings" / "S43_audit"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    config = json.loads((ROOT / "configs" / "S43.json").read_text())
    run_config = json.loads((RUN / "config.json").read_text())
    manifest = read_csv(RUN / "results" / "manifest.csv")
    trial_summary = read_csv(RUN / "results" / "trial_summary.csv")
    class_summary = read_csv(RUN / "results" / "class_summary.csv")
    segment_model = json.loads((RUN / "segment_model.json").read_text())

    assert config["subject_id"] == run_config["subject_id"] == "S43"
    assert config["sex"] == run_config["sex"] == "female"
    assert len(manifest) == len(trial_summary) == 25
    assert len(class_summary) == 5
    assert {row["activity"] for row in manifest} == {
        "A10", "A11", "A12", "A13", "A14"
    }
    assert all(row["status"] == "numeric" for row in manifest)
    assert all(int(row["columns"]) == 96 for row in trial_summary)
    assert sum(int(row["frames"]) for row in trial_summary) == 6080
    assert len(segment_model["segments"]) == 14

    for row in manifest:
        raw = RUN / "raw" / f"{row['trial']}.csv"
        assert raw.is_file()
        assert raw.stat().st_size == int(row["bytes"])
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == row["sha256"]

    print("PASS S43 audit manifest, raw-file hashes, dimensions and segment model")


if __name__ == "__main__":
    main()
