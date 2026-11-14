from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Package detector results for sharing.")
    parser.add_argument("--include-models", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name(
            "Fifteen_Subject_CoM_Transformer_Fall_Detector_Results.zip"
        ),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    outputs = root / "outputs"
    if not outputs.is_dir():
        raise FileNotFoundError("No outputs directory exists. Run experiments first.")
    include_root_files = ["README.md", "config.json", "requirements.txt"]
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in include_root_files:
            archive.write(root / name, Path(root.name) / name)
        for path in sorted(outputs.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix == ".pt" and not args.include_models:
                continue
            archive.write(path, Path(root.name) / path.relative_to(root))
    print(f"Packaged results: {args.output}")


if __name__ == "__main__":
    main()

