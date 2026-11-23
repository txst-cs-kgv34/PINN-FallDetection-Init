#!/usr/bin/env python3
"""Package manifests and prepared arrays after the local preparation run."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "Fifteen_Subject_A10_A14_Fall_Detector_Data_Preparation_Results.zip")
    args = parser.parse_args()
    output_root = HERE / "outputs"
    if not (output_root / "integrity_report.json").is_file():
        raise FileNotFoundError("Run validate before package")
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in ("README.md", "FINDINGS.md", "sampling_policy.json"):
            archive.write(HERE / name, name)
        for path in sorted(output_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(HERE))
    print(args.output)


if __name__ == "__main__":
    main()
