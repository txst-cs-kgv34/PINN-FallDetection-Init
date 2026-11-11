#!/usr/bin/env python3
"""Generate conditional synthetic falls with validation-selected Physics models."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from study_core import (
    HERE,
    dump_json,
    load_physics_core,
    load_study_config,
    read_json,
    resolve_from,
    resolve_physics_dir,
    write_csv,
)


def load_state(path: Path, device):
    import torch

    try:
        return torch.load(path, map_location=device, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=device)


def selected_generator_rows(selection_file: Path) -> list[dict[str, Any]]:
    payload = read_json(selection_file)
    materialized = payload.get("materialized_generators", [])
    rows: list[dict[str, Any]] = []
    if materialized:
        for raw in materialized:
            row = dict(raw)
            expected = (
                selection_file.parent
                / "selected_generators"
                / f"fold_{int(row['fold']):02d}"
                / (
                    f"rank_{int(row['rank_within_fold']):02d}_"
                    f"seed_{int(row['seed_index']):02d}_{int(row['base_optimization_seed'])}"
                )
                / "final_best_model_state.pt"
            )
            row["checkpoint"] = str(
                expected.resolve()
                if expected.is_file()
                else Path(row["materialized_checkpoint"]).expanduser().resolve()
            )
            rows.append(row)
    else:
        for raw in payload.get("rankings", []):
            if bool(raw.get("selected")):
                row = dict(raw)
                row["checkpoint"] = str(Path(row["source_checkpoint"]).expanduser().resolve())
                rows.append(row)
    if not rows:
        raise ValueError(
            f"No selected generators found in {selection_file}; run ./run.sh select first"
        )
    keys = {(int(row["fold"]), int(row["seed_index"])) for row in rows}
    if len(keys) != len(rows):
        raise ValueError("Duplicate fold/seed generator entries in the selection manifest")
    for row in rows:
        checkpoint = Path(row["checkpoint"])
        if not checkpoint.is_file() or checkpoint.stat().st_size == 0:
            raise ValueError(f"Missing or empty selected checkpoint: {checkpoint}")
    return sorted(
        rows,
        key=lambda row: (
            int(row["fold"]),
            int(row["rank_within_fold"]),
        ),
    )


def verify_generator_split(row: dict[str, Any], fold: dict[str, Any]) -> None:
    expected_train = tuple(map(str, fold["train"]))
    expected_validation = str(fold["validation"])
    expected_test = tuple(map(str, fold["test"]))
    if tuple(row["train_subjects"]) != expected_train:
        raise ValueError(f"Training split mismatch for fold {row['fold']}")
    if str(row["validation_subject"]) != expected_validation:
        raise ValueError(f"Validation-subject mismatch for fold {row['fold']}")
    if tuple(row["test_subjects"]) != expected_test:
        raise ValueError(f"Test split mismatch for fold {row['fold']}")
    if set(expected_train) & ({expected_validation} | set(expected_test)):
        raise ValueError(f"Subject leakage in fold {row['fold']}")


def combine_context_and_forecast(
    real_theta: np.ndarray,
    real_x: np.ndarray,
    model_prediction: np.ndarray,
    time_s: np.ndarray,
    valid_mask: np.ndarray,
    context_region_s: float,
    correction_decay_s: float = 0.15,
    slope_window_samples: int = 11,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    dict[str, float],
]:
    """Join observed context to a C1-corrected model forecast.

    The sample at the boundary belongs to the observed context.  A decaying
    correction is applied to the model from that sample onward so that its
    position and analytical first derivative match the observed trajectory at
    the boundary.  The correction tends to zero, returning the trajectory to
    the unmodified model forecast away from the join.
    """
    if correction_decay_s <= 0.0:
        raise ValueError("correction_decay_s must be positive")
    if slope_window_samples < 2:
        raise ValueError("slope_window_samples must be at least two")
    valid = valid_mask > 0.5
    context = valid & (time_s <= context_region_s)
    forecast = valid & (time_s > context_region_s)
    if not np.any(context) or not np.any(forecast):
        raise ValueError("Trajectory does not contain both context and forecast samples")
    boundary_index = int(np.flatnonzero(context)[-1])
    boundary_time_s = float(time_s[boundary_index])
    model_region = valid & (time_s >= boundary_time_s)
    context_indices = np.flatnonzero(context)[-slope_window_samples:]
    model_indices = np.flatnonzero(model_region)[:slope_window_samples]
    if len(context_indices) < 2 or len(model_indices) < 2:
        raise ValueError("Too few samples to estimate boundary velocity")

    def boundary_slope(values: np.ndarray, indices: np.ndarray) -> float:
        centered_time = np.asarray(time_s[indices], dtype=np.float64) - boundary_time_s
        degree = min(2, len(indices) - 1)
        coefficients = np.polyfit(
            centered_time,
            np.asarray(values[indices], dtype=np.float64),
            degree,
        )
        derivative = np.polyder(coefficients)
        return float(np.polyval(derivative, 0.0))

    raw_model = np.asarray(model_prediction, dtype=np.float64)
    corrected_model = raw_model.copy()
    correction_metadata: dict[str, float] = {
        "boundary_time_s": boundary_time_s,
        "correction_decay_s": float(correction_decay_s),
        "slope_window_samples": float(slope_window_samples),
    }
    channels = (
        ("theta", np.asarray(real_theta, dtype=np.float64), 0),
        ("x", np.asarray(real_x, dtype=np.float64), 1),
    )
    elapsed = np.asarray(time_s[model_region], dtype=np.float64) - boundary_time_s
    for name, observed, channel in channels:
        observed_slope = boundary_slope(observed, context_indices)
        model_slope = boundary_slope(raw_model[:, channel], model_indices)
        position_offset = float(
            observed[boundary_index] - raw_model[boundary_index, channel]
        )
        velocity_offset = observed_slope - model_slope
        correction = (
            position_offset
            + (velocity_offset + position_offset / correction_decay_s) * elapsed
        ) * np.exp(-elapsed / correction_decay_s)
        corrected_model[model_region, channel] += correction
        correction_metadata[f"{name}_position_offset"] = position_offset
        correction_metadata[f"{name}_observed_boundary_velocity"] = observed_slope
        correction_metadata[f"{name}_raw_model_boundary_velocity"] = model_slope
        correction_metadata[f"{name}_velocity_offset"] = velocity_offset

    theta = np.asarray(real_theta, dtype=np.float32).copy()
    x_m = np.asarray(real_x, dtype=np.float32).copy()
    theta[forecast] = corrected_model[forecast, 0]
    x_m[forecast] = corrected_model[forecast, 1]
    return (
        theta,
        x_m,
        context,
        forecast,
        corrected_model.astype(np.float32),
        correction_metadata,
    )


def transition_jump(
    synthetic_theta: np.ndarray,
    synthetic_x: np.ndarray,
    context_mask: np.ndarray,
    forecast_mask: np.ndarray,
) -> tuple[float, float]:
    last_context = int(np.flatnonzero(context_mask)[-1])
    first_forecast = int(np.flatnonzero(forecast_mask)[0])
    return (
        float(np.degrees(abs(synthetic_theta[first_forecast] - synthetic_theta[last_context]))),
        float(100.0 * abs(synthetic_x[first_forecast] - synthetic_x[last_context])),
    )


def generate(
    physics_dir: Path,
    selection_file: Path,
    output_dir: Path,
    device_name: str,
    batch_size: int,
    limit_per_subject: int | None,
    maximum_generators: int | None,
    correction_decay_s: float,
    slope_window_samples: int,
) -> dict[str, Any]:
    import torch

    core = load_physics_core(physics_dir)
    experiment = core.load_config(physics_dir / "experiment.json")
    device = core.choose_torch_device(device_name)
    records = core.load_real_records("full")
    record_keys = {(record.subject, record.trial) for record in records}
    if len(record_keys) != len(records):
        raise ValueError("Prepared real data contains duplicate subject/trial keys")
    selected = selected_generator_rows(selection_file)
    if maximum_generators is not None:
        selected = selected[:maximum_generators]
    output_dir.mkdir(parents=True, exist_ok=True)
    context_region_s = float(experiment["model"]["context_region_s"])
    manifest_rows: list[dict[str, Any]] = []

    for generator in selected:
        fold = core.fold_by_id(experiment, int(generator["fold"]))
        verify_generator_split(generator, fold)
        model = core.create_model(experiment).to(device)
        model.load_state_dict(load_state(Path(generator["checkpoint"]), device))
        model.eval()
        dataset = core.build_real_dataset(
            records,
            list(fold["train"]),
            experiment,
            limit_per_subject=limit_per_subject,
        )
        generator_dir = output_dir / f"fold_{int(generator['fold']):02d}" / (
            f"rank_{int(generator['rank_within_fold']):02d}_"
            f"seed_{int(generator['seed_index']):02d}_{int(generator['base_optimization_seed'])}"
        )
        generator_dir.mkdir(parents=True, exist_ok=True)
        with torch.no_grad():
            for raw_batch in core.iter_batches(dataset, batch_size, False, 0):
                device_batch = core.batch_to_device(raw_batch, device)
                _, prediction, controller, _ = core.infer_real(
                    model, device_batch, experiment
                )
                predicted = prediction.detach().cpu().numpy()
                controller_normalized = controller.detach().cpu().numpy()
                gain_scale = model.gain_scale.detach().cpu().numpy()
                for index in range(predicted.shape[0]):
                    subject = str(raw_batch["subject"][index])
                    trial = str(raw_batch["trial"][index])
                    if subject not in set(fold["train"]):
                        raise AssertionError(
                            f"Attempted to generate from non-training subject {subject}"
                        )
                    if subject == str(fold["validation"]) or subject in set(fold["test"]):
                        raise AssertionError(f"Held-out subject leaked into generation: {subject}")
                    time_s = raw_batch["time_s"][index].numpy()
                    real_theta = raw_batch["theta_rad"][index].numpy()
                    real_x = raw_batch["x_m"][index].numpy()
                    valid_mask = raw_batch["valid_mask"][index].numpy()
                    (
                        synthetic_theta,
                        synthetic_x,
                        context_mask,
                        forecast_mask,
                        corrected_model,
                        correction,
                    ) = (
                        combine_context_and_forecast(
                            real_theta,
                            real_x,
                            predicted[index],
                            time_s,
                            valid_mask,
                            context_region_s,
                            correction_decay_s,
                            slope_window_samples,
                        )
                    )
                    jump_theta_deg, jump_x_cm = transition_jump(
                        synthetic_theta,
                        synthetic_x,
                        context_mask,
                        forecast_mask,
                    )
                    file_name = f"{subject}_{trial}.npz"
                    destination = generator_dir / file_name
                    np.savez_compressed(
                        destination,
                        time_s=time_s.astype(np.float32),
                        synthetic_theta_rad=synthetic_theta.astype(np.float32),
                        synthetic_x_m=synthetic_x.astype(np.float32),
                        raw_model_theta_rad=predicted[index, :, 0].astype(np.float32),
                        raw_model_x_m=predicted[index, :, 1].astype(np.float32),
                        corrected_model_theta_rad=corrected_model[:, 0],
                        corrected_model_x_m=corrected_model[:, 1],
                        valid_mask=valid_mask.astype(np.float32),
                        context_mask=context_mask.astype(np.uint8),
                        forecast_mask=forecast_mask.astype(np.uint8),
                        inferred_controller_normalized=controller_normalized[index].astype(
                            np.float32
                        ),
                        inferred_physical_gains=(
                            controller_normalized[index] * gain_scale
                        ).astype(np.float32),
                        continuity_boundary_time_s=np.float32(
                            correction["boundary_time_s"]
                        ),
                        continuity_decay_s=np.float32(
                            correction["correction_decay_s"]
                        ),
                        continuity_theta_position_offset_rad=np.float32(
                            correction["theta_position_offset"]
                        ),
                        continuity_x_position_offset_m=np.float32(
                            correction["x_position_offset"]
                        ),
                        continuity_theta_velocity_offset_rad_s=np.float32(
                            correction["theta_velocity_offset"]
                        ),
                        continuity_x_velocity_offset_m_s=np.float32(
                            correction["x_velocity_offset"]
                        ),
                    )
                    manifest_rows.append(
                        {
                            "synthetic_id": (
                                f"F{int(generator['fold']):02d}_"
                                f"R{int(generator['rank_within_fold']):02d}_"
                                f"S{int(generator['seed_index']):02d}_{trial}"
                            ),
                            "fold": int(generator["fold"]),
                            "generator_rank": int(generator["rank_within_fold"]),
                            "seed_index": int(generator["seed_index"]),
                            "base_optimization_seed": int(
                                generator["base_optimization_seed"]
                            ),
                            "best_epoch": int(generator["best_epoch"]),
                            "best_validation_normalized_mse": float(
                                generator["best_validation_normalized_mse"]
                            ),
                            "validation_subject": str(fold["validation"]),
                            "source_subject": subject,
                            "source_trial": trial,
                            "source_is_training_subject": True,
                            "validation_or_test_context_used": False,
                            "context_region_s": context_region_s,
                            "continuity_correction": "C1_decaying_exponential",
                            "continuity_decay_s": correction_decay_s,
                            "continuity_slope_window_samples": slope_window_samples,
                            "continuity_boundary_time_s": correction["boundary_time_s"],
                            "raw_boundary_theta_offset_deg": float(
                                np.degrees(correction["theta_position_offset"])
                            ),
                            "raw_boundary_x_offset_cm": float(
                                100.0 * correction["x_position_offset"]
                            ),
                            "raw_boundary_theta_velocity_offset_deg_s": float(
                                np.degrees(correction["theta_velocity_offset"])
                            ),
                            "raw_boundary_x_velocity_offset_cm_s": float(
                                100.0 * correction["x_velocity_offset"]
                            ),
                            "endpoint_semantics": "source_conditioned_apparent_contact",
                            "valid_samples": int(np.sum(valid_mask > 0.5)),
                            "forecast_samples": int(np.sum(forecast_mask)),
                            "transition_jump_theta_deg": jump_theta_deg,
                            "transition_jump_x_cm": jump_x_cm,
                            "data_file": str(destination.relative_to(output_dir)),
                            "checkpoint": str(Path(generator["checkpoint"]).resolve()),
                        }
                    )
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    if not manifest_rows:
        raise ValueError("No synthetic trajectories were generated")
    write_csv(output_dir / "synthetic_manifest.csv", manifest_rows)
    payload = {
        "description": "Conditional full-fall trajectories from observed training-subject context and model-predicted forecast",
        "physics_directory": str(physics_dir.resolve()),
        "selection_file": str(selection_file.resolve()),
        "device": str(device),
        "context_policy": "real samples for t <= 0.40 s; continuity-corrected model forecast for t > 0.40 s",
        "continuity_correction": {
            "method": "C1 decaying exponential bridge",
            "decay_s": correction_decay_s,
            "slope_window_samples": slope_window_samples,
            "position_and_velocity_matched_at_boundary": True,
        },
        "duration_semantics": "apparent-contact endpoint and valid length inherited from the source context trial; contact time is not predicted",
        "held_out_contexts_used": False,
        "generator_count": len(selected),
        "synthetic_trajectory_count": len(manifest_rows),
        "samples": manifest_rows,
    }
    dump_json(output_dir / "synthetic_manifest.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "study_config.json")
    parser.add_argument("--physics-dir", type=Path)
    parser.add_argument("--selection-file", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda", "mps"))
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--limit-per-subject", type=int)
    parser.add_argument("--maximum-generators", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_file, config = load_study_config(args.config)
    physics_dir = resolve_physics_dir(config_file, config, args.physics_dir)
    selection_file = (
        args.selection_file.expanduser().resolve()
        if args.selection_file
        else resolve_from(config_file, str(config["output_directory"]))
        / "generator_selection.json"
    )
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else resolve_from(config_file, str(config["generation_output_directory"]))
    )
    batch_size = (
        args.batch_size
        if args.batch_size is not None
        else int(config["generation"]["batch_size"])
    )
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    payload = generate(
        physics_dir,
        selection_file,
        output_dir,
        args.device,
        batch_size,
        args.limit_per_subject,
        args.maximum_generators,
        float(config["generation"]["continuity_decay_s"]),
        int(config["generation"]["continuity_slope_window_samples"]),
    )
    print(
        f"Generated {payload['synthetic_trajectory_count']} conditional trajectories "
        f"from {payload['generator_count']} validation-selected checkpoints."
    )
    print(f"Outputs: {output_dir}")


if __name__ == "__main__":
    main()
