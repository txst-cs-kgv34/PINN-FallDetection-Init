#!/usr/bin/env python3
"""Check that the shortened end-to-end run executed every original stage."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    run = ROOT / "results" / "smoke_run"
    required = [
        "stage1_best.weights.h5",
        "identified_parameters.json",
        "stage3_best.weights.h5",
        "conditional_forward_pinn.weights.h5",
        "configuration.json",
        "training_losses.png",
        "real_vs_pinn_reconstruction.png",
        "generated_samples.png",
    ]
    missing = [name for name in required if not (run / name).is_file()]
    if missing:
        raise AssertionError(f"missing smoke outputs: {missing}")

    parameters = json.loads((run / "identified_parameters.json").read_text())
    for key in ("kp_theta", "kd_theta", "kp_x", "kd_x", "pi_deg", "tau_s"):
        if not np.isfinite(parameters[key]):
            raise AssertionError(f"non-finite controller value: {key}")

    trajectories = []
    for path in sorted((run / "synthetic_subjectB_PINN").glob("*.npy")):
        data = np.load(path)
        if data.shape != (3001, 4):
            raise AssertionError(f"{path.name} has unexpected shape {data.shape}")
        if not np.isfinite(data).all():
            raise AssertionError(f"{path.name} contains non-finite values")
        trajectories.append(
            {
                "file": path.name,
                "shape": list(data.shape),
                "theta_deg_range": [float(data[:, 2].min()), float(data[:, 2].max())],
                "x_m_range": [float(data[:, 3].min()), float(data[:, 3].max())],
            }
        )
    if len(trajectories) != 3:
        raise AssertionError(f"expected three smoke trajectories, found {len(trajectories)}")

    report = {
        "status": "pass",
        "meaning": "All four original stages executed and wrote finite outputs.",
        "scientific_interpretation": "none; two epochs per stage are an execution test only",
        "plausibility_warning": "Smoke trajectories are intentionally undertrained and have extreme ranges.",
        "controller": {key: parameters[key] for key in ("kp_theta", "kd_theta", "kp_x", "kd_x", "pi_deg", "tau_s")},
        "trajectories": trajectories,
    }
    output = ROOT / "results" / "smoke_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS: all four stages completed in smoke mode and outputs are finite")
    print("WARNING: smoke trajectories are undertrained and not scientifically interpretable")
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
