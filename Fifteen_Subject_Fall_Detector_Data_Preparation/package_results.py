#!/usr/bin/env python3
"""Package code, reports, manifests, and prepared trajectories."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


HERE = Path(__file__).resolve().parent
DESTINATION = HERE.parent / "Fifteen_Subject_Fall_Detector_Data_Preparation.zip"


def main() -> None:
    required = (
        HERE / "README.md",
        HERE / "FINDINGS.md",
        HERE / "outputs" / "dataset_manifest.json",
        HERE / "outputs" / "study_membership.csv",
        HERE / "outputs" / "integrity_report.json",
    )
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required outputs: " + ", ".join(map(str, missing)))
    with ZipFile(DESTINATION, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(HERE.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            archive.write(path, Path(HERE.name) / path.relative_to(HERE))
    print(f"Saved {DESTINATION}")


if __name__ == "__main__":
    main()
