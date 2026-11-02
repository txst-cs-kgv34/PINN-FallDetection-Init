#!/usr/bin/env python3
"""Package code, manifests, logs, metrics, plots, and trained DeepONet states."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from operator_core import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="Five_Subject_DeepONet_Experiment1_Results.zip")
    parser.add_argument("--include-teacher-data", action="store_true")
    args = parser.parse_args()
    destination = (ROOT / args.output).resolve()
    candidates = [
        ROOT / "README.md",
        ROOT / "experiment.json",
        ROOT / "requirements.txt",
        ROOT / "operator_core.py",
        ROOT / "validate_setup.py",
        ROOT / "export_teacher_data.py",
        ROOT / "prepare_real_data.py",
        ROOT / "train_fold.py",
        ROOT / "aggregate_results.py",
        ROOT / "package_results.py",
        ROOT / "run_on_mac.sh",
        ROOT / "tests",
        ROOT / "results",
        ROOT / "outputs" / "teacher_data_full" / "teacher_manifest.json",
        ROOT / "outputs" / "real_data_full" / "real_manifest.json",
    ]
    if args.include_teacher_data:
        candidates.append(ROOT / "outputs" / "teacher_data_full")
        candidates.append(ROOT / "outputs" / "real_data_full")
    files: set[Path] = set()
    for candidate in candidates:
        if candidate.is_file():
            files.add(candidate)
        elif candidate.is_dir():
            files.update(
                path
                for path in candidate.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            )
    if not any(path.name == "aggregate_summary.json" for path in files):
        raise FileNotFoundError("Aggregate full results are missing; run all five folds first")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            if path.resolve() != destination:
                archive.write(path, path.relative_to(ROOT))
    print(destination)


if __name__ == "__main__":
    main()

