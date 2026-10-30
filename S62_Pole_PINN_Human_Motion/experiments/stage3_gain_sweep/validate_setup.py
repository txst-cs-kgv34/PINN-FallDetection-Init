#!/usr/bin/env python3
"""Fail fast unless the gain sweep has a clean subject-only full-run baseline."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATCH = re.match(r"^(S\d+)_Pole_PINN_Human_Motion$", ROOT.name)
if MATCH is None:
    raise RuntimeError(f"Cannot infer subject ID from {ROOT.name}")
SUBJECT_ID = MATCH.group(1)
INPUTS = ROOT / "data" / "pole_compatible" / "A11"
SCOPE = ROOT / "config" / f"{SUBJECT_ID}_A11_experiment_scope.json"
FULL_RUN = ROOT / "results" / "full_run"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    expected = sorted(f"SubjectB_{trial}.tsv" for trial in scope["included_trials"])
    actual = sorted(path.name for path in INPUTS.glob("SubjectB_*.tsv"))
    if actual != expected:
        raise RuntimeError(
            f"Input inventory mismatch. Expected={expected}; actual={actual}. "
            "Use a freshly extracted corrected package and rerun build."
        )

    required = [
        FULL_RUN / "stage1_best.weights.h5",
        FULL_RUN / "identified_parameters.json",
        FULL_RUN / "run_mode.json",
        FULL_RUN / "conditional_forward_pinn.weights.h5",
        FULL_RUN / "configuration.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Clean full-run baseline is incomplete: " + ", ".join(missing)
        )

    generated = list((FULL_RUN / "synthetic_subjectB_PINN").glob("synth_B_*.npy"))
    if len(generated) != 100:
        raise RuntimeError(
            f"Clean full-run baseline is incomplete: expected 100 generated trajectories, found {len(generated)}"
        )

    mode = json.loads((FULL_RUN / "run_mode.json").read_text(encoding="utf-8"))
    if mode.get("mode") != "full":
        raise RuntimeError("The baseline run_mode.json is not a full run")
    if not mode.get("input_inventory_validated") or mode.get("input_files") != expected:
        raise RuntimeError(
            "The saved full run does not prove subject-only inputs. Rerun the corrected full pipeline; "
            "the earlier mixed-subject checkpoint must not be used."
        )

    parameters = json.loads(
        (FULL_RUN / "identified_parameters.json").read_text(encoding="utf-8")
    )
    names = ("kp_theta", "kd_theta", "kp_x", "kd_x", "pi_deg", "tau_s")
    values = {name: float(parameters[name]) for name in names}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("Identified parameters contain non-finite values")

    print(f"PASS: {SUBJECT_ID} gain-sweep baseline is subject-only")
    print(f"  inputs ({len(actual)}): {', '.join(actual)}")
    print(f"  Stage-1 SHA-256: {sha256(FULL_RUN / 'stage1_best.weights.h5')}")
    print(
        "  gains: "
        + ", ".join(f"{name}={values[name]:.8g}" for name in names)
    )


if __name__ == "__main__":
    main()
