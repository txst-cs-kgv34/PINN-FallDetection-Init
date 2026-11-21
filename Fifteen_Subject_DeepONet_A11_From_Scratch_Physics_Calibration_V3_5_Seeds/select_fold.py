#!/usr/bin/env python3
"""Select lambda on validation, then test selected V3 and its matched lambda=0 arm."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from calibration_core import candidate_weights, load_torch_state, read_json, weight_label
from evaluation import evaluate
from operator_core import (
    ROOT, build_dataset, choose_torch_device, create_model, dump_json, fold_by_id,
    load_config, load_real_records, seed_everything, seed_spec,
)


def candidate_directory(mode: str, weight: float, seed_label: str, fold_id: int) -> Path:
    return ROOT / "results" / "candidates" / mode / weight_label(weight) / seed_label / f"fold_{fold_id:02d}"


def selection_options(config: dict, mode: str, seed_label: str, fold_id: int) -> list[dict]:
    options = []
    hashes = set()
    initial_values = []
    for weight in candidate_weights(config, include_baseline=True):
        directory = candidate_directory(mode, weight, seed_label, fold_id)
        selection_path = directory / "training_selection.json"
        manifest_path = directory / "candidate_manifest.json"
        checkpoint = directory / "final_best_model_state.pt"
        if not selection_path.is_file() or not manifest_path.is_file() or not checkpoint.is_file():
            raise FileNotFoundError(f"candidate is incomplete: {directory}")
        selection = read_json(selection_path)
        manifest = read_json(manifest_path)
        hashes.add(str(manifest["initialization_sha256"]))
        initial_values.append(float(selection["random_initialization_validation_forecast_mse"]))
        options.append({
            "weight": weight,
            "source": "matched_from_scratch_candidate",
            "validation_forecast_mse": float(selection["best_validation_forecast_mse"]),
            "best_epoch": int(selection["best_epoch"]),
            "initialization_sha256": str(manifest["initialization_sha256"]),
            "checkpoint": checkpoint,
        })
    if len(hashes) != 1:
        raise ValueError(f"lambda arms did not share initialization: {sorted(hashes)}")
    if max(initial_values) - min(initial_values) > 1e-7:
        raise ValueError(f"lambda arms disagree before training: {initial_values}")
    return options


def verify_test_targets(selected_dir: Path, baseline_dir: Path, trials: list[str]) -> dict:
    maximum = {"time_s": 0.0, "target_theta_rad": 0.0, "target_x_m": 0.0}
    for trial in trials:
        with np.load(selected_dir / "test_predictions" / f"{trial}.npz", allow_pickle=False) as left, \
             np.load(baseline_dir / "test_predictions" / f"{trial}.npz", allow_pickle=False) as right:
            for key in maximum:
                if left[key].shape != right[key].shape:
                    raise ValueError(f"{trial}: target shape differs for {key}")
                difference = float(np.max(np.abs(left[key] - right[key]))) if left[key].size else 0.0
                maximum[key] = max(maximum[key], difference)
    if any(value != 0.0 for value in maximum.values()):
        raise ValueError(f"selected and matched lambda=0 targets differ: {maximum}")
    return {"verified_trials": len(trials), "targets_exactly_identical": True, "maximum_absolute_difference": maximum}


def evaluate_arm(config, fold, seed_index, base_seed, run_seed, device, test_set, option, condition: str, output_dir: Path) -> tuple[list[dict], dict]:
    model = create_model(config, "planar").to(device)
    model.load_state_dict(load_torch_state(Path(option["checkpoint"]), device))
    rows, subject_metrics, activity_metrics = evaluate(model, test_set, config, device, output_dir)
    import torch
    torch.save(model.state_dict(), output_dir / "final_selected_model_state.pt")
    summary = {
        "experiment": config["experiment_name"],
        "display_name": config["display_name"],
        "condition": condition,
        "model_group": "planar",
        "fold": int(fold["id"]),
        "seed_index": seed_index,
        "base_optimization_seed": base_seed,
        "effective_fold_seed": run_seed,
        "physics_weight": float(option["weight"]),
        "validation_forecast_mse": float(option["validation_forecast_mse"]),
        "best_epoch": int(option["best_epoch"]),
        "initialization_sha256": option["initialization_sha256"],
        "test_trial_count": len(rows),
        "test_forecast_sample_count": sum(int(row["forecast_samples"]) for row in rows),
        "test_subject_mean_metrics": subject_metrics,
        "test_activity_mean_metrics": activity_metrics,
        "checkpoint_and_weight_selected_only_on_validation_subject": True,
        "test_access_before_selection": False,
    }
    dump_json(output_dir / "summary.json", summary)
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--seed-index", type=int, default=1)
    parser.add_argument("--device", choices=("auto", "mps", "cuda", "cpu"), default="auto")
    args = parser.parse_args()
    config = load_config(args.config)
    fold = fold_by_id(config, args.fold)
    fold_id = int(fold["id"])
    base_seed, seed_label = seed_spec(config, args.seed_index)
    run_seed = base_seed + fold_id
    seed_everything(run_seed)
    device = choose_torch_device(args.device)
    options = selection_options(config, args.mode, seed_label, fold_id)
    selected = min(options, key=lambda row: (row["validation_forecast_mse"], row["weight"]))
    baseline = next(option for option in options if math.isclose(option["weight"], 0.0, abs_tol=1e-15))
    if not math.isfinite(selected["validation_forecast_mse"]):
        raise ValueError("no finite validation candidate")

    records = load_real_records(args.mode, "planar")
    test_set = build_dataset(records, list(fold["test"]))
    selected_dir = ROOT / "results" / "selected" / args.mode / seed_label / f"fold_{fold_id:02d}"
    baseline_dir = ROOT / "results" / "matched_no_physics" / args.mode / seed_label / f"fold_{fold_id:02d}"
    selected_dir.mkdir(parents=True, exist_ok=True)
    baseline_dir.mkdir(parents=True, exist_ok=True)

    serializable = [{key: (str(value) if key == "checkpoint" else value) for key, value in option.items()} for option in options]
    dump_json(selected_dir / "weight_selection.json", {
        "selection_metric": config["calibration"]["selection_metric"],
        "tie_break": config["calibration"]["selection_tie_break"],
        "validation_subject": fold["validation"],
        "test_subjects_not_used_for_selection": fold["test"],
        "all_arms_share_initialization": True,
        "options": serializable,
        "selected_weight": selected["weight"],
        "selected_validation_forecast_mse": selected["validation_forecast_mse"],
        "selected_best_epoch": selected["best_epoch"],
    })
    selected_rows, selected_summary = evaluate_arm(
        config, fold, args.seed_index, base_seed, run_seed, device, test_set,
        selected, "validation_selected_v3", selected_dir,
    )
    _, baseline_summary = evaluate_arm(
        config, fold, args.seed_index, base_seed, run_seed, device, test_set,
        baseline, "matched_from_scratch_lambda_0", baseline_dir,
    )
    verification = verify_test_targets(selected_dir, baseline_dir, [str(row["trial"]) for row in selected_rows])
    selected_summary["target_verification_against_matched_lambda_0"] = verification
    baseline_summary["target_verification_against_selected_v3"] = verification
    dump_json(selected_dir / "summary.json", selected_summary)
    dump_json(baseline_dir / "summary.json", baseline_summary)
    print(json.dumps({"selected": selected_summary, "matched_no_physics": baseline_summary}, indent=2))


if __name__ == "__main__":
    main()
