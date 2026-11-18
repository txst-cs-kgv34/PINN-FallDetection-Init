from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Package fall-source ratio results.")
    parser.add_argument("--include-models", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name(
            "Fifteen_Subject_CoM_Transformer_Fall_Source_Ratio_Ablation_Results.zip"
        ),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    outputs = root / "outputs"
    if not outputs.is_dir():
        raise FileNotFoundError("No outputs directory exists. Run the experiment first.")
    root_files = [
        "README.md",
        "FINDINGS.md",
        "config.json",
        "requirements.txt",
        "run.sh",
        "base_detector_imports.py",
        "source_ratio_sampler.py",
        "train_ratio_ablation.py",
        "compare_ratios.py",
        "validate_setup.py",
        "smoke_test.py",
        "package_results.py",
    ]
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in root_files:
            path = root / name
            if path.is_file():
                archive.write(path, Path(root.name) / name)
        for path in sorted(outputs.rglob("*")):
            if path.is_file() and (args.include_models or path.suffix != ".pt"):
                archive.write(path, Path(root.name) / path.relative_to(root))
        for path in sorted((root / "tests").glob("*.py")):
            archive.write(path, Path(root.name) / path.relative_to(root))
    print(f"Packaged results: {args.output}")


if __name__ == "__main__":
    main()
