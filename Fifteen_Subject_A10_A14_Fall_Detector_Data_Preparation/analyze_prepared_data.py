#!/usr/bin/env python3
"""Summarize activity, subject, family, and planned fall-mixture coverage."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from detector_data_core import write_csv, write_json


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE / "outputs")
    args = parser.parse_args()
    root = args.output_dir.expanduser().resolve()
    with (root / "dataset_manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    table = []
    for subject in sorted({row["source_subject"] for row in rows}, key=lambda value: int(value[1:])):
        for activity in [f"A{value:02d}" for value in range(10, 15)]:
            real = [row for row in rows if row["source_kind"] == "real_fall" and row["source_subject"] == subject and row["activity_code"] == activity]
            synthetic = [row for row in rows if row["source_kind"] == "synthetic_fall" and row["source_subject"] == subject and row["activity_code"] == activity]
            if real or synthetic:
                table.append({"subject": subject, "activity": activity, "real_falls": len(real), "synthetic_variants": len(synthetic), "synthetic_source_families": len({row["synthetic_family_id"] for row in synthetic})})
    write_csv(root / "subject_activity_coverage.csv", table)
    summary = {
        "counts_by_source": dict(Counter(row["source_kind"] for row in rows)),
        "real_falls_by_activity": dict(sorted(Counter(row["activity_code"] for row in rows if row["source_kind"] == "real_fall").items())),
        "synthetic_variants_by_activity": dict(sorted(Counter(row["activity_code"] for row in rows if row["source_kind"] == "synthetic_fall").items())),
        "synthetic_source_families": len({row["synthetic_family_id"] for row in rows if row["source_kind"] == "synthetic_fall"}),
        "subjects_with_synthetic": len({row["source_subject"] for row in rows if row["source_kind"] == "synthetic_fall"}),
        "zero_synthetic_subject_activity_cells_with_real_falls": [f"{row['subject']}-{row['activity']}" for row in table if int(row["real_falls"]) and not int(row["synthetic_variants"])],
    }
    write_json(root / "analysis_summary.json", summary)
    print(summary)


if __name__ == "__main__":
    main()
