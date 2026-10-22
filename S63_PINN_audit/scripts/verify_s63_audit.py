"""Verify the delivered S63 audit manifest, raw bytes, dimensions, and outputs."""

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "findings" / "S63_audit"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    config = json.loads((ROOT / "configs" / "S63.json").read_text())
    run_config = json.loads((RUN / "config.json").read_text())
    study = json.loads((RUN / "results" / "study_summary.json").read_text())
    manifest = read_csv(RUN / "results" / "manifest.csv")
    trials = read_csv(RUN / "results" / "trial_summary.csv")
    classes = read_csv(RUN / "results" / "class_summary.csv")
    segment_model = json.loads((RUN / "segment_model.json").read_text())

    assert config == run_config
    assert config["subject_id"] == "S63"
    assert config["sex"] == "male"
    assert config["mass_lb"] == 180 and config["height_in"] == 66
    assert len(manifest) == len(trials) == 25
    assert len(classes) == 5
    assert {row["activity"] for row in manifest} == {"A10", "A11", "A12", "A13", "A14"}
    assert all(row["status"] == "numeric" for row in manifest)
    assert all(int(row["columns"]) == 96 for row in trials)
    assert sum(int(row["frames"]) for row in trials) == 3897
    assert study["nonempty_files"] == 25 and study["total_frames"] == 3897
    assert study["empty_files"] == study["missing_files"] == study["invalid_files"] == 0
    assert len(segment_model["segments"]) == 14

    for row in manifest:
        raw = RUN / "raw" / f"{row['trial']}.csv"
        assert raw.is_file()
        assert raw.stat().st_size == int(row["bytes"])
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == row["sha256"]

    print("PASS: S63 audit manifest, raw hashes, dimensions, demographics, and segment model")


if __name__ == "__main__":
    main()
