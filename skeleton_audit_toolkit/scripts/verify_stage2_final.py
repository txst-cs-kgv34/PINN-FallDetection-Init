"""Verify the retained final Stage-2 real-data sensitivity checkpoint."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def finite_rows(rows, fields):
    for row in rows:
        for field in fields:
            require(math.isfinite(float(row[field])), f"nonfinite {field}")


def verify(output):
    metrics = read_csv(output / "assumption_grid_metrics.csv")
    selected = read_csv(output / "selected_fold_metrics.csv")
    profiles = read_csv(output / "optimization_profiles.csv")
    predictions = read_csv(output / "held_out_com_predictions.csv")
    ranges = read_csv(output / "parameter_sensitivity_ranges.csv")
    frozen = json.loads((output / "experiment_config.json").read_text(encoding="utf-8"))

    require(len(metrics) == 96, "expected 96 fold/assumption fits")
    require(len(selected) == 8, "expected eight leave-one-trial-out folds")
    require(len(profiles) == 960, "expected 960 delay/start optimizer profiles")
    require(len(predictions) == 244, "expected 244 held-out CoM samples")
    require(len(ranges) == 2, "expected A11 and A13 sensitivity ranges")
    require({row["activity"] for row in selected} == {"A11", "A13"}, "activity set")
    require(all(row["valid_profile"].lower() == "true" for row in profiles), "invalid optimizer profile retained")

    finite_rows(
        metrics,
        [
            "alpha_kp",
            "beta_kd",
            "delay_frames",
            "gamma_torque_limit",
            "training_objective_rmse",
            "training_aic",
            "xy_rmse_m",
        ],
    )
    finite_rows(
        predictions,
        [
            "actual_horizontal_m",
            "actual_vertical_m",
            "selected_horizontal_m",
            "selected_vertical_m",
        ],
    )

    for row in metrics:
        require(
            row["held_out_trial"] not in row["training_trials"].split(";"),
            f"held-out leakage in {row['held_out_trial']}",
        )

    central = {}
    for row in metrics:
        if float(row["length_scale"]) == 1.0 and float(row["damping_ratio"]) == 0.0:
            central[(row["activity"], row["held_out_trial"], row["perturbation_model"])] = row
    for row in selected:
        key = (row["activity"], row["held_out_trial"])
        expected = min(
            ("zero", "shared_pulse"),
            key=lambda name: float(central[key + (name,)]["training_aic"]),
        )
        require(row["selected_model"] == expected, f"training-only selection mismatch for {key}")

    plot_count = len(list((output / "plots").glob("*_held_out_com_path.png")))
    require(plot_count == 8, "expected eight held-out CoM plots")
    require(frozen["stage2_real_config"]["simulation"]["observation_hz"] == 30, "observation rate")
    require(frozen["stage2_real_config"]["simulation"]["internal_hz"] == 150, "integration rate")

    summary = (output / "SUMMARY.md").read_text(encoding="utf-8").lower()
    require("not recovered physiological controllers" in summary, "interpretation guard")
    require("no held-out com sample is used" in summary, "held-out policy guard")
    require("option 3 cannot be performed retrospectively" in summary, "measurement limitation guard")

    print("Stage-2 final checkpoint verification passed.")
    print("96 fits; 8 held-out folds; 244 CoM samples; no held-out leakage; 8 plots.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analyses/S43_stage2_final_real_effective_sensitivity"),
    )
    args = parser.parse_args()
    verify(args.output)


if __name__ == "__main__":
    main()
