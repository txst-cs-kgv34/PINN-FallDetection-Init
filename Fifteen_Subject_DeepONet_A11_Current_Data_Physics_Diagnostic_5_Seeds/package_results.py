#!/usr/bin/env python3
"""Package both A11 conditions, comparison, code, and prepared manifest."""

from __future__ import annotations
import zipfile
from pathlib import Path
from operator_core import ROOT, load_config

def main() -> None:
    config = load_config(ROOT / "experiment.json"); destination = ROOT / config["result_archive"]
    if not all((ROOT / "results" / condition / "full" / "multi_seed_summary.json").is_file() for condition in ("physics", "no_physics")):
        raise FileNotFoundError("both five-seed condition summaries are required")
    if not (ROOT / "comparison" / "comparison_summary.json").is_file():
        raise FileNotFoundError("run compare_results.py before packaging")
    candidates = [ROOT / name for name in ("README.md", "FINDINGS.md", "experiment.json", "requirements.txt", "prepare_data.py", "validate_prepared_data.py", "operator_core.py", "train_fold.py", "aggregate_results.py", "compare_results.py", "validate_setup.py", "package_results.py", "run.sh", "run_on_mac.sh", "tests", "audit_adapter", "results", "comparison")]
    candidates += [ROOT / "outputs" / "real_data_full" / "planar_manifest.json"]
    files = set()
    for candidate in candidates:
        if candidate.is_file(): files.add(candidate)
        elif candidate.is_dir(): files.update(path for path in candidate.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            if path.resolve() != destination.resolve(): archive.write(path, path.relative_to(ROOT))
    print(destination)

if __name__ == "__main__":
    main()
