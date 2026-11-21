#!/usr/bin/env python3
"""Select an A11 physics weight on validation only, then evaluate held-out tests once."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from calibration_core import (
    candidate_weights,
    load_torch_state,
    read_json,
    require_baseline_fold,
    weight_label,
)
from evaluation import evaluate
from operator_core import (
    ROOT,
    build_dataset,
    choose_torch_device,
    create_model,
    dump_json,
    fold_by_id,
    load_config,
    load_real_records,
    seed_everything,
    seed_spec,
)


def candidate_directory(mode: str, weight: float, seed_label: str, fold_id: int) -> Path:
    return ROOT / "results" / "candidates" / mode / weight_label(weight) / seed_label / f"fold_{fold_id:02d}"


def selection_options(config: dict, mode: str, seed_label: str, fold_id: int) -> list[dict]:
    baseline = require_baseline_fold(config, seed_label, fold_id)
    baseline_selection = read_json(baseline["selection"])
    physics_options = []
    warm_start_values = []
    for weight in candidate_weights(config):
        directory = candidate_directory(mode, weight, seed_label, fold_id)
        selection_path = directory / "training_selection.json"
        checkpoint = directory / "final_best_model_state.pt"
        if not selection_path.is_file() or not checkpoint.is_file():
            raise FileNotFoundError(f"candidate is incomplete: {directory}")
        selection = read_json(selection_path)
        warm_start_values.append(float(selection["warm_start_validation_forecast_mse"]))
        physics_options.append({
            "weight": weight,
            "source": "warm_started_physics_candidate",
            "validation_forecast_mse": float(selection["best_validation_forecast_mse"]),
            "best_epoch_after_warm_start": int(selection["best_epoch_after_warm_start"]),
            "checkpoint": checkpoint,
        })
    if max(warm_start_values) - min(warm_start_values) > 1e-7:
        raise ValueError(f"candidate warm-start validation values disagree: {warm_start_values}")
    comparable_baseline = float(np.mean(warm_start_values))
    options = [{
        "weight": 0.0,
        "source": "existing_no_physics",
        "validation_forecast_mse": comparable_baseline,
        "stored_original_validation_forecast_mse": float(baseline_selection["best_validation_forecast_mse"]),
        "best_epoch_after_warm_start": 0,
        "checkpoint": baseline["checkpoint"],
    }]
    return options + physics_options


def verify_test_targets(output_dir: Path, baseline_predictions: Path, trials: list[str]) -> dict:
    maximum = {"time_s": 0.0, "target_theta_rad": 0.0, "target_x_m": 0.0}
    for trial in trials:
        current_path = output_dir / "test_predictions" / f"{trial}.npz"
        baseline_path = baseline_predictions / f"{trial}.npz"
        if not baseline_path.is_file():
            raise FileNotFoundError(baseline_path)
        with np.load(current_path, allow_pickle=False) as current, np.load(baseline_path, allow_pickle=False) as baseline:
            for key in maximum:
                if current[key].shape != baseline[key].shape:
                    raise ValueError(f"{trial}: target shape differs for {key}")
                difference = float(np.max(np.abs(current[key] - baseline[key]))) if current[key].size else 0.0
                maximum[key] = max(maximum[key], difference)
    if any(value != 0.0 for value in maximum.values()):
        raise ValueError(f"selected V2 and baseline targets differ: {maximum}")
    return {
        "verified_trials": len(trials),
        "targets_exactly_identical": True,
        "maximum_absolute_difference": maximum,
    }


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
    baseline = require_baseline_fold(config, seed_label, fold_id)
    options = selection_options(config, args.mode, seed_label, fold_id)
    selected = min(options, key=lambda row: (row["validation_forecast_mse"], row["weight"]))
    if not math.isfinite(selected["validation_forecast_mse"]):
        raise ValueError("no finite validation candidate")
    records = load_real_records(args.mode, "planar")
    test_set = build_dataset(records, list(fold["test"]))
    model = create_model(config, "planar").to(device)
    model.load_state_dict(load_torch_state(Path(selected["checkpoint"]), device))
    output_dir = ROOT / "results" / "selected" / args.mode / seed_label / f"fold_{fold_id:02d}"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows, subject_metrics, activity_metrics = evaluate(model, test_set, config, device, output_dir)
    target_verification = verify_test_targets(
        output_dir,
        baseline["predictions"],
        [str(row["trial"]) for row in rows],
    )
    import torch
    torch.save(model.state_dict(), output_dir / "final_selected_model_state.pt")
    serializable_options = [
        {key: (str(value) if key == "checkpoint" else value) for key, value in option.items()}
        for option in options
    ]
    dump_json(output_dir / "weight_selection.json", {
        "selection_metric": config["calibration"]["selection_metric"],
        "tie_break": config["calibration"]["selection_tie_break"],
        "validation_subject": fold["validation"],
        "test_subjects_not_used_for_selection": fold["test"],
        "options": serializable_options,
        "selected_weight": selected["weight"],
        "selected_source": selected["source"],
        "selected_validation_forecast_mse": selected["validation_forecast_mse"],
        "selected_best_epoch_after_warm_start": selected["best_epoch_after_warm_start"],
    })
    summary = {
        "experiment": config["experiment_name"],
        "display_name": config["display_name"],
        "condition": "validation_selected_calibration_v2",
        "model_group": "planar",
        "fold": fold_id,
        "seed_index": args.seed_index,
        "base_optimization_seed": base_seed,
        "effective_fold_seed": run_seed,
        "selected_physics_weight": selected["weight"],
        "selected_source": selected["source"],
        "selected_validation_forecast_mse": selected["validation_forecast_mse"],
        "test_trial_count": len(rows),
        "test_forecast_sample_count": sum(int(row["forecast_samples"]) for row in rows),
        "test_subject_mean_metrics": subject_metrics,
        "test_activity_mean_metrics": activity_metrics,
        "target_verification_against_existing_no_physics": target_verification,
        "checkpoint_and_weight_selected_only_on_validation_subject": True,
        "test_access_before_selection": False,
    }
    dump_json(output_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
