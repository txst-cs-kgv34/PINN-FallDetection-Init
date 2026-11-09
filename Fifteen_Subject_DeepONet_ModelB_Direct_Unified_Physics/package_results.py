#!/usr/bin/env python3
"""Package code, manifests, logs, metrics, plots, and trained model states."""

from __future__ import annotations

import argparse
import zipfile

from operator_core import ROOT, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--output")
    parser.add_argument("--include-arrays", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    output_name = args.output or str(config["result_archive"])
    destination = (ROOT / output_name).resolve()
    candidates = [
        ROOT / "README.md",
        ROOT / "FINDINGS.md",
        ROOT / "experiment.json",
        ROOT / "requirements.txt",
        ROOT / "operator_core.py",
        ROOT / "validate_setup.py",
        ROOT / "prepare_audit_inputs.py",
        ROOT / "audit_adapter",
        ROOT / "prepare_real_data.py",
        ROOT / "train_fold.py",
        ROOT / "aggregate_results.py",
        ROOT / "package_results.py",
        ROOT / "run_on_mac.sh",
        ROOT / "run.sh",
        ROOT / "tests",
        ROOT / "results",
        ROOT / "outputs" / "real_data_full" / "real_manifest.json",
        ROOT / "outputs" / "audit_pole_inputs" / "audit_adapter_manifest.json",
    ]
    if bool(config["requires_teachers"]):
        candidates.extend(
            [
                ROOT / "export_teacher_data.py",
                ROOT / "outputs" / "teacher_data_full" / "teacher_manifest.json",
            ]
        )
    if args.include_arrays:
        candidates.append(ROOT / "outputs" / "real_data_full")
        if bool(config["requires_teachers"]):
            candidates.append(ROOT / "outputs" / "teacher_data_full")
    files = set()
    for candidate in candidates:
        if candidate.is_file():
            files.add(candidate)
        elif candidate.is_dir():
            files.update(
                path
                for path in candidate.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            )
    if not any(path.name == "multi_seed_summary.json" for path in files):
        raise FileNotFoundError(
            "Five-seed aggregate results are missing; run all 25 fold models first"
        )
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            if path.resolve() != destination:
                archive.write(path, path.relative_to(ROOT))
    print(destination)


if __name__ == "__main__":
    main()
