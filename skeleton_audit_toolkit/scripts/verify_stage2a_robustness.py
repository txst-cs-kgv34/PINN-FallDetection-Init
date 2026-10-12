"""Verify the retained Stage-2A robustness checkpoint."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from run_stage2a_parameter_recovery import trial_bank
from run_stage2a_robustness import condition_values, scaled_trials


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_bool(value):
    return value == "True"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("analyses/S43_stage2a_robustness"),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/S43_stage2a_robustness.json"),
    )
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    assert len(config["conditions"]) == 20
    reference = condition_values(config["conditions"][0])
    assert reference["angle_noise_sd_deg"] == 0.12
    assert reference["estimated_length_scale"] == 1.0
    assert reference["reported_perturbation_scale"] == 1.0
    trials = trial_bank()
    halved = scaled_trials(trials, 0.5)
    assert halved[0].pulse_amplitude_ratio == trials[0].pulse_amplitude_ratio * 0.5
    assert halved[7].pulse2_amplitude_ratio == trials[7].pulse2_amplitude_ratio * 0.5

    required = [
        "SUMMARY.md",
        "experiment_config.json",
        "robustness_metrics.csv",
        "condition_summary.csv",
        "optimization_profiles.csv",
        "combined_example_trajectories.csv",
        "plots/condition_pass_fraction.png",
        "plots/condition_median_errors.png",
        "plots/combined_parameter_identity.png",
        "plots/combined_held_out_trajectory.png",
    ]
    for relative in required:
        path = args.results / relative
        assert path.is_file() and path.stat().st_size > 0, path

    rows = read_rows(args.results / "robustness_metrics.csv")
    summaries = read_rows(args.results / "condition_summary.csv")
    profiles = read_rows(args.results / "optimization_profiles.csv")
    examples = read_rows(args.results / "combined_example_trajectories.csv")
    assert len(rows) == 88
    assert len({row["case_id"] for row in rows}) == 88
    assert len(summaries) == 20
    assert len(examples) == 4 * 37
    expected_profiles = sum(
        15 if as_bool(row["adaptive_multistart_used"]) else 5 for row in rows
    )
    assert len(profiles) == expected_profiles

    by_condition = {
        condition: [row for row in rows if row["condition_id"] == condition]
        for condition in {row["condition_id"] for row in rows}
    }
    assert len(by_condition["reference"]) == 4
    assert all(as_bool(row["case_pass"]) for row in by_condition["reference"])
    assert all(
        not as_bool(row["case_pass"]) for row in by_condition["perturb_unmeasured"]
    )
    assert all(
        not as_bool(row["all_parameter_gates_pass"])
        for row in by_condition["combined_moderate"]
    )
    assert all(
        as_bool(row["held_out_gate_pass"])
        for row in by_condition["combined_moderate"]
    )
    assert all(
        as_bool(row["adaptive_multistart_used"])
        for row in by_condition["combined_moderate"]
    )
    summary_by_id = {row["condition_id"]: row for row in summaries}
    moderate_passes = sum(
        as_bool(summary_by_id[item]["condition_gate_pass"])
        for item in config["moderate_gate_conditions"]
    )
    assert moderate_passes == 5
    print("Stage-2A robustness verification passed.")


if __name__ == "__main__":
    main()
