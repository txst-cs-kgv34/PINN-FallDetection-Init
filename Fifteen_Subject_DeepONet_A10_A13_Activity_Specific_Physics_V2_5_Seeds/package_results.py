#!/usr/bin/env python3
"""Package A10-A13 activity-specific physics calibration results."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from operator_core import ROOT, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-seed", type=int)
    args = parser.parse_args()
    config = load_config(ROOT / "experiment.json")
    if args.pilot_seed:
        seed = int(args.pilot_seed)
        base_seed = int(config["optimization_seeds"][seed - 1])
        label = f"seed_{seed:02d}_{base_seed}"
        destination = ROOT / f"Fifteen_Subject_A10_A13_Activity_Specific_Physics_V2_Seed_{seed:02d}_Pilot_Results.zip"
        required = (
            ROOT / "results" / "selected" / "full" / label / "aggregate_summary.json",
            ROOT / "comparison" / f"pilot_seed_{seed:02d}" / "comparison_summary.json",
        )
        result_candidates = [
            ROOT / "results" / "selected" / "full" / label,
            ROOT / "results" / "matched_no_physics" / "full" / label,
            *[
                ROOT / "results" / "candidates" / "full" / (
                    "lambda_0" if float(weight) == 0.0 else
                    "lambda_" + f"{float(weight):.0e}".replace("+", "").replace("e-0", "e-")
                ) / label
                for weight in [config["calibration"]["baseline_weight"], *config["calibration"]["candidate_weights"]]
            ],
            ROOT / "comparison" / f"pilot_seed_{seed:02d}",
        ]
    else:
        destination = ROOT / config["result_archive"]
        required = (
            ROOT / "results" / "selected" / "full" / "multi_seed_summary.json",
            ROOT / "comparison" / "full" / "comparison_summary.json",
        )
        result_candidates = [ROOT / "results", ROOT / "comparison"]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f"requested result package is incomplete: {path}")
    names = (
        "README.md", "FINDINGS.md", "VALIDATION.md", "EXPERIMENT_RECONCILIATION.md",
        "PILOT_SEED_01_AUDIT.md", "experiment.json",
        "requirements.txt", "prepare_data.py", "validate_prepared_data.py",
        "operator_core.py", "calibration_core.py", "train_candidate.py",
        "evaluation.py", "select_fold.py", "aggregate_calibration.py",
        "compare_calibration.py", "validate_setup.py", "package_results.py",
        "run.sh", "run_on_mac.sh", "tests", "audit_adapter",
    )
    candidates = [ROOT / name for name in names]
    candidates.extend(result_candidates)
    candidates.append(ROOT / "outputs" / "real_data_full" / "planar_manifest.json")
    files: set[Path] = set()
    for candidate in candidates:
        if candidate.is_file():
            files.add(candidate)
        elif candidate.is_dir():
            files.update(
                path for path in candidate.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            )
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            if path.resolve() != destination.resolve():
                archive.write(path, path.relative_to(ROOT))
    print(destination)


if __name__ == "__main__":
    main()
