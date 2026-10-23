#!/usr/bin/env python3
"""Validate the files needed by the S63 Stage-3 gain sweep without training."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source" / "pinn_pole_synthetic_data_generation.py"
LOCK = ROOT / "CORE_PIPELINE_LOCK.json"
INPUTS = ROOT / "data" / "pole_compatible" / "A11"
STAGE1_WEIGHTS = ROOT / "results" / "full_run" / "stage1_best.weights.h5"
IDENTIFIED = ROOT / "results" / "full_run" / "identified_parameters.json"
RUNTIME_OVERRIDES = ROOT / "config" / "S63_runtime_overrides.json"
EXPECTED_TRIALS = [f"SubjectB_S63A11T{i:02d}.tsv" for i in range(1, 6)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Missing required file: {path.relative_to(ROOT)}")


def main() -> None:
    for path in (SOURCE, LOCK, STAGE1_WEIGHTS, IDENTIFIED, RUNTIME_OVERRIDES):
        require(path)

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    actual_hash = sha256(SOURCE)
    if actual_hash != lock["sha256"]:
        raise SystemExit(
            "Core pipeline hash mismatch. Restore the unchanged S63 pole source before running."
        )

    missing_trials = [name for name in EXPECTED_TRIALS if not (INPUTS / name).is_file()]
    if missing_trials:
        raise SystemExit("Missing S63 pole-compatible trials: " + ", ".join(missing_trials))

    identified = json.loads(IDENTIFIED.read_text(encoding="utf-8"))
    runtime_override = json.loads(RUNTIME_OVERRIDES.read_text(encoding="utf-8"))
    if float(runtime_override["minimum_trial_seconds"]) != 0.25:
        raise SystemExit("S63 minimum_trial_seconds must remain 0.25 for this experiment.")
    expected = {
        "kp_theta": 145.109024,
        "kd_theta": 15.048624,
        "kp_x": 14.932888,
        "kd_x": 15.048451,
        "pi_deg": 3.628571,
        "tau_s": 0.23,
    }
    for name, value in expected.items():
        if abs(float(identified[name]) - value) > 1e-5:
            raise SystemExit(
                f"Unexpected {name} in identified_parameters.json: "
                f"{identified[name]} (expected approximately {value})"
            )

    print("S63 gain-sweep setup: PASS")
    print("  unchanged core SHA-256:", actual_hash)
    print("  S63 A11 pole-compatible trials: 5")
    print("  documented minimum-trial gate: 0.25 s")
    print("  common Stage-1 checkpoint:", STAGE1_WEIGHTS.relative_to(ROOT))
    print("  experiment: 11 independent Stage-3 fixed-gain chunks")


if __name__ == "__main__":
    main()
