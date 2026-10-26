#!/usr/bin/env python3
"""Package operator metrics, plots, model checkpoints, and provenance for review."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from operator_core import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="S43_S63_DeepONet_FewShot_Results.zip")
    parser.add_argument("--include-teacher-data", action="store_true")
    args = parser.parse_args()
    destination = (ROOT / args.output).resolve()
    candidates = [
        ROOT / "experiment.json",
        ROOT / "README.md",
        ROOT / "requirements.txt",
        ROOT / "operator_core.py",
        ROOT / "export_teacher_data.py",
        ROOT / "train_operator.py",
        ROOT / "validate_setup.py",
        ROOT / "results",
        ROOT / "outputs" / "teacher_data_full" / "teacher_manifest.json",
    ]
    if args.include_teacher_data:
        candidates.append(ROOT / "outputs" / "teacher_data_full")
    files: set[Path] = set()
    for candidate in candidates:
        if candidate.is_file():
            files.add(candidate)
        elif candidate.is_dir():
            files.update(path for path in candidate.rglob("*") if path.is_file())
    if not files:
        raise FileNotFoundError("No results found. Run the experiment first.")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(ROOT))
    print(destination)


if __name__ == "__main__":
    main()
