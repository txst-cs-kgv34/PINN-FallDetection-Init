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

    subject = json.loads((ROOT / "config" / "S57.json").read_text())
    phases = json.loads((ROOT / "config" / "S57_A11_phase_notes.json").read_text())
    scope = json.loads((ROOT / "config" / "S57_A11_experiment_scope.json").read_text())
    override = json.loads((ROOT / "config" / "S57_runtime_overrides.json").read_text())
    assert subject["subject_id"] == phases["subject"] == scope["subject"] == "S57"
    assert subject["sex"] == "male"
    assert subject["mass_lb"] == 180 and subject["height_in"] == 68
    assert scope["included_trials"] == [f"S57A11T{i:02d}" for i in range(3, 6)]
    assert set(scope["excluded_trials"]) == {"S57A11T01", "S57A11T02"}
    assert float(override["minimum_trial_seconds"]) == 0.25

    expected_tsv = sorted(f"SubjectB_{trial}.tsv" for trial in scope["included_trials"])
    actual_tsv = sorted(
        path.name for path in (ROOT / "data" / "pole_compatible" / "A11").glob("SubjectB_*.tsv")
    )
    # This preflight runs before the adapter, so missing generated TSVs are
    # allowed.  Foreign/stale TSVs are not; the post-build input validator
    # later requires the inventory to match exactly.
    assert set(actual_tsv).issubset(set(expected_tsv)), (expected_tsv, actual_tsv)

    for trial in scope["included_trials"]:
        notes = [note for note in phases["notes"] if note["trial"] == trial]
        assert [note["phase"] for note in notes] == REQUIRED_PHASES
        raw = np.loadtxt(ROOT / "data" / "raw" / f"{trial}.csv", delimiter=",", ndmin=2)
        assert raw.shape[1] == 96 and np.isfinite(raw).all()
        assert max(note["frame0"] for note in notes) < len(raw)
        assert all(abs(note["nominal_time_s"] - note["frame0"] / 30.0) < 1e-12 for note in notes)

    print("PASS: S57 project preflight checks succeeded")
    print("  unchanged core; original epochs; 100 generated trajectories")
    print("  three valid A11 inputs (T03-T05); incomplete T01-T02 excluded")


if __name__ == "__main__":
    main()
