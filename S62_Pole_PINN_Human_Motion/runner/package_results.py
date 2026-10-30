#!/usr/bin/env python3
"""Package the files needed for remote review of an S62 full run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "S62_Pole_PINN_full_run_results.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    full_run = ROOT / "results" / "full_run"
    scope = json.loads((ROOT / "config" / "S62_A11_experiment_scope.json").read_text())
    expected_inputs = sorted(f"SubjectB_{trial}.tsv" for trial in scope["included_trials"])
    required = [
        full_run / "identified_parameters.json",
        full_run / "configuration.json",
        full_run / "stage1_best.weights.h5",
        full_run / "stage3_best.weights.h5",
        full_run / "conditional_forward_pinn.weights.h5",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    run_mode_path = full_run / "run_mode.json"
    if not run_mode_path.is_file():
        missing.append("results/full_run/run_mode.json")
    else:
        run_mode = json.loads(run_mode_path.read_text(encoding="utf-8"))
        if not run_mode.get("input_inventory_validated"):
            missing.append("full run lacks validated subject-only input provenance")
        if run_mode.get("input_files") != expected_inputs:
            missing.append(
                f"full run input inventory mismatch: expected {expected_inputs}; "
                f"found {run_mode.get('input_files')}"
            )
    synthetic = sorted((full_run / "synthetic_subjectB_PINN").glob("synth_B_*.npy"))
    if len(synthetic) != 100:
        missing.append(f"expected 100 synthetic trajectories; found {len(synthetic)}")
    if missing:
        raise FileNotFoundError("Full-run handoff is incomplete: " + "; ".join(missing))

    include_roots = [
        ROOT / "results",
        ROOT / "config",
    ]
    fixed_files = [
        ROOT / "CORE_PIPELINE_LOCK.json",
        ROOT / "README.md",
        ROOT / "FINDINGS.md",
        ROOT / "RETURN_FILES.md",
    ]
    files = sorted(
        {path for base in include_roots for path in base.rglob("*") if path.is_file()}
        | set(fixed_files)
    )
    manifest = {
        "project": "S62_Pole_PINN_Human_Motion",
        "synthetic_trajectory_count": len(synthetic),
        "files": [
            {
                "path": str(path.relative_to(ROOT)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    manifest_path = ROOT / "results" / "HANDOFF_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    files.append(manifest_path)

    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(set(files)):
            archive.write(path, arcname=str(Path(ROOT.name) / path.relative_to(ROOT)))
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
