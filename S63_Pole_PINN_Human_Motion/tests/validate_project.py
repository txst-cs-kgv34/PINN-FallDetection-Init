#!/usr/bin/env python3
"""Static and byte-level preflight checks that do not import TensorFlow."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "source" / "pinn_pole_synthetic_data_generation.py"
EXPECTED_CORE_SHA256 = "604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9"
REQUIRED_PHASES = [
    "initial_standing",
    "fall_onset",
    "descent",
    "apparent_contact",
    "post_fall",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_default(name: str) -> object:
    tree = ast.parse(CORE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Config":
            for statement in node.body:
                if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                    if statement.target.id == name:
                        return ast.literal_eval(statement.value)
    raise KeyError(name)


def main() -> None:
    lock = json.loads((ROOT / "CORE_PIPELINE_LOCK.json").read_text())
    assert sha256(CORE) == EXPECTED_CORE_SHA256 == lock["sha256"]
    assert config_default("number_generated_trajectories") == 100
    assert config_default("stage1_epochs") == 7000
    assert config_default("stage2_epochs") == 5000
    assert config_default("stage3_epochs") == 5000

    subject = json.loads((ROOT / "config" / "S63.json").read_text())
    phases = json.loads((ROOT / "config" / "S63_A11_phase_notes.json").read_text())
    scope = json.loads((ROOT / "config" / "S63_A11_experiment_scope.json").read_text())
    override = json.loads((ROOT / "config" / "S63_runtime_overrides.json").read_text())
    assert subject["subject_id"] == phases["subject"] == scope["subject"] == "S63"
    assert subject["sex"] == "male"
    assert subject["mass_lb"] == 180 and subject["height_in"] == 66
    assert scope["included_trials"] == [f"S63A11T{i:02d}" for i in range(1, 6)]
    assert float(override["minimum_trial_seconds"]) == 0.25

    for trial in scope["included_trials"]:
        notes = [note for note in phases["notes"] if note["trial"] == trial]
        assert [note["phase"] for note in notes] == REQUIRED_PHASES
        raw = np.loadtxt(ROOT / "data" / "raw" / f"{trial}.csv", delimiter=",", ndmin=2)
        assert raw.shape[1] == 96 and np.isfinite(raw).all()
        assert max(note["frame0"] for note in notes) < len(raw)
        assert all(abs(note["nominal_time_s"] - note["frame0"] / 30.0) < 1e-12 for note in notes)

    print("PASS: S63 project preflight checks succeeded")
    print("  unchanged core; original epochs; 100 generated trajectories")
    print("  five valid A11 inputs with complete manual phase observations")


if __name__ == "__main__":
    main()
