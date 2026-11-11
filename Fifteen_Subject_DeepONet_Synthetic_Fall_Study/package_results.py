#!/usr/bin/env python3
"""Package synthetic trajectories and quality outputs without duplicate model weights."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


HERE = Path(__file__).resolve().parent
OUTPUTS = HERE / "outputs"
DESTINATION = HERE / "Fifteen_Subject_DeepONet_Synthetic_Fall_Study_Results.zip"


def main() -> None:
    required = (
        OUTPUTS / "generator_selection" / "generator_selection.json",
        OUTPUTS / "synthetic_trajectories" / "synthetic_manifest.json",
        OUTPUTS / "trajectory_quality" / "quality_summary.json",
        OUTPUTS / "trajectory_quality" / "QUALITY_REPORT.md",
    )
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Complete the select, generate, and quality stages first. Missing: "
            + ", ".join(map(str, missing))
        )
    with ZipFile(DESTINATION, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(OUTPUTS.rglob("*")):
            if path.is_file() and path.suffix != ".pt":
                archive.write(path, path.relative_to(HERE))
        for path in (HERE / "README.md", HERE / "study_config.json"):
            archive.write(path, path.name)
    print(f"Saved {DESTINATION}")


if __name__ == "__main__":
    main()
