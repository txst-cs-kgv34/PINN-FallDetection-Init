"""Verify the retained S43 fixed-delay profile diagnostic."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analyses" / "S43_stage2_fixed_delay_profile"


def _read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    config = json.loads((OUTPUT / "experiment_config.json").read_text())
    decision = json.loads((OUTPUT / "DECISION.json").read_text())
    selected = _read_csv(OUTPUT / "fixed_delay_profiles.csv")
    starts = _read_csv(OUTPUT / "fixed_delay_start_profiles.csv")
    minima = _read_csv(OUTPUT / "fold_seed_minima.csv")
    synthetic = _read_csv(OUTPUT / "synthetic_fixed_delay_profile.csv")
    delays = config["diagnostic"]["fixed_delay_s"]

    assert config["source_stage2"]["use_effective_torque_matching"] is False
    assert config["source_stage2"]["use_nuisance_torque"] is False
    assert config["source_stage2"]["use_torque_saturation"] is False
    assert config["diagnostic"]["gain_optimizer"]["trainable_parameters"] == [
        "Kp", "Kd", "Ki"
    ]
    assert delays == [0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.25, 0.275, 0.3]
    assert len(selected) == 16 * len(delays)
    assert len(starts) == 16 * len(delays) * 3
    assert len(minima) == 16
    assert len(synthetic) == len(delays)
    assert len(list((OUTPUT / "plots").glob("*.png"))) == 11

    numeric = [
        "training_physics_loss", "projected_gradient_norm", "alpha_kp",
        "beta_kd", "kappa_ki", "delay_s",
    ]
    assert all(
        np.isfinite(float(row[column]))
        for row in selected for column in numeric
    )
    assert max(float(row["projected_gradient_norm"]) for row in selected) < 1e-5
    assert all(row["held_out_trial"] not in row["training_trials"].split(";") for row in selected)

    keys = {(row["activity"], row["held_out_trial"], row["seed"]) for row in selected}
    assert len(keys) == 16
    for key in keys:
        local = [row for row in selected if (row["activity"], row["held_out_trial"], row["seed"]) == key]
        assert sorted(float(row["delay_s"]) for row in local) == delays

    true_delay = decision["synthetic"]["true_delay_s"]
    best_delay = decision["synthetic"]["best_profile_delay_s"]
    assert abs(best_delay - true_delay) <= 0.025 + 1e-12
    assert decision["real_data"]["fold_seed_profiles"] == 16
    assert (
        decision["real_data"]["interior_minima"]
        + decision["real_data"]["lower_boundary_minima"]
        + decision["real_data"]["upper_boundary_minima"]
        == 16
    )

    report = {
        "software_verification": "pass",
        "synthetic_known_delay_profile": "pass",
        "counts": {
            "fold_seed_profiles": 16,
            "fixed_delay_selected_rows": len(selected),
            "fixed_delay_start_rows": len(starts),
            "plots": 11,
        },
        "real_data": decision["real_data"],
    }
    (OUTPUT / "VERIFICATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
