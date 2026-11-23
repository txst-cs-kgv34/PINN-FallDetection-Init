#!/usr/bin/env python3
"""Generate A10-A13 planar and A14 rotation trajectories from top-two physics models."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from study_core import (
    GROUPS,
    HERE,
    dump_json,
    load_physics_core,
    load_study_config,
    normalized_validation_subjects,
    read_json,
    resolve_from,
    resolve_physics_dir,
    write_csv,
)


CHANNELS = {"planar": ("theta", "x"), "rotation": ("theta", "x", "yaw")}


def load_state(path: Path, device):
    import torch

    try:
        return torch.load(path, map_location=device, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=device)


def selected_generator_rows(selection_file: Path) -> list[dict[str, Any]]:
    payload = read_json(selection_file)
    materialized = list(payload.get("materialized_generators", []))
    if materialized:
        rows = [dict(row) for row in materialized]
        for row in rows:
            row["checkpoint"] = str(Path(row["materialized_checkpoint"]).expanduser().resolve())
    else:
        rows = []
        for group in GROUPS:
            rows.extend(dict(row) for row in payload["groups"][group]["selected"])
    if not rows:
        raise ValueError(f"No selected generators in {selection_file}; run select first")
    keys = {
        (str(row["model_group"]), int(row["fold"]), int(row["rank_within_fold"]))
        for row in rows
    }
    if len(keys) != len(rows):
        raise ValueError("duplicate group/fold/rank entries in generator selection")
    for row in rows:
        checkpoint = Path(str(row["checkpoint"]))
        if not checkpoint.is_file() or checkpoint.stat().st_size == 0:
            raise ValueError(f"missing or empty checkpoint: {checkpoint}")
        if float(row["physics_weight"]) <= 0.0:
            raise ValueError("lambda=0 is not eligible for synthetic generation")
    return sorted(
        rows,
        key=lambda row: (
            GROUPS.index(str(row["model_group"])),
            int(row["fold"]),
            int(row["rank_within_fold"]),
        ),
    )


def verify_generator_split(row: dict[str, Any], fold: dict[str, Any]) -> None:
    if tuple(map(str, row["train_subjects"])) != tuple(map(str, fold["train"])):
        raise ValueError(f"training split mismatch for {row['model_group']} fold {row['fold']}")
    if tuple(map(str, row["validation_subjects"])) != normalized_validation_subjects(fold):
        raise ValueError(f"validation split mismatch for {row['model_group']} fold {row['fold']}")
    if tuple(map(str, row["test_subjects"])) != tuple(map(str, fold["test"])):
        raise ValueError(f"test split mismatch for {row['model_group']} fold {row['fold']}")


def combine_context_and_forecast(
    real_channels: np.ndarray,
    model_prediction: np.ndarray,
    time_s: np.ndarray,
    valid_mask: np.ndarray,
    context_region_s: float,
    correction_decay_s: float,
    slope_window_samples: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, float]]:
    """Join observed context to a per-channel C1-corrected model forecast."""
    if real_channels.shape != model_prediction.shape:
        raise ValueError("real and predicted channels must have identical shape")
    if correction_decay_s <= 0.0 or slope_window_samples < 2:
        raise ValueError("invalid continuity correction settings")
    valid = np.asarray(valid_mask) > 0.5
    context = valid & (np.asarray(time_s) <= float(context_region_s))
    forecast = valid & (np.asarray(time_s) > float(context_region_s))
    if not np.any(context) or not np.any(forecast):
        raise ValueError("trajectory lacks context or forecast samples")
    boundary_index = int(np.flatnonzero(context)[-1])
    boundary_time = float(time_s[boundary_index])
    model_region = valid & (np.asarray(time_s) >= boundary_time)
    context_indices = np.flatnonzero(context)[-slope_window_samples:]
    model_indices = np.flatnonzero(model_region)[:slope_window_samples]
    if len(context_indices) < 2 or len(model_indices) < 2:
        raise ValueError("too few samples for boundary velocity estimation")

    def slope(values: np.ndarray, indices: np.ndarray) -> float:
        local_time = np.asarray(time_s[indices], dtype=np.float64) - boundary_time
        degree = min(2, len(indices) - 1)
        return float(np.polyval(np.polyder(np.polyfit(local_time, values[indices], degree)), 0.0))

    corrected = np.asarray(model_prediction, dtype=np.float64).copy()
    metadata: dict[str, float] = {
        "boundary_time_s": boundary_time,
        "correction_decay_s": float(correction_decay_s),
        "slope_window_samples": float(slope_window_samples),
    }
    elapsed = np.asarray(time_s[model_region], dtype=np.float64) - boundary_time
    for index in range(real_channels.shape[1]):
        observed = np.asarray(real_channels[:, index], dtype=np.float64)
        raw = np.asarray(model_prediction[:, index], dtype=np.float64)
        observed_slope = slope(observed, context_indices)
        model_slope = slope(raw, model_indices)
        position_offset = float(observed[boundary_index] - raw[boundary_index])
        velocity_offset = float(observed_slope - model_slope)
        correction = (
            position_offset
            + (velocity_offset + position_offset / correction_decay_s) * elapsed
        ) * np.exp(-elapsed / correction_decay_s)
        corrected[model_region, index] += correction
        metadata[f"channel_{index}_position_offset"] = position_offset
        metadata[f"channel_{index}_velocity_offset"] = velocity_offset
    synthetic = np.asarray(real_channels, dtype=np.float32).copy()
    synthetic[forecast] = corrected[forecast]
    return synthetic, context, forecast, corrected.astype(np.float32), metadata


def residual_metrics(core, trajectory, gains, batch, config, group: str) -> dict[str, float]:
    import torch

    r1, r2, ryaw, mask = core.physics_residual_components(
        trajectory,
        gains,
        batch["time_s"],
        batch["mass_kg"],
        batch["height_m"],
        config["physics"],
        batch["physics_mask"],
        group,
    )
    if not bool(mask.any()):
        raise ValueError("physics residual contains no valid samples")
    gravity = float(config["physics"]["gravity_m_s2"])
    length = float(config["physics"]["stick_length_m"])

    def rmse(values, scale: float) -> float:
        selected = values[mask] / float(scale)
        return float(torch.sqrt(torch.mean(selected.square())).detach().cpu())

    result = {
        "angular_scaled_rmse": rmse(r1, gravity / length),
        "horizontal_scaled_rmse": rmse(r2, gravity),
    }
    if group == "rotation":
        result["yaw_residual_rmse"] = rmse(ryaw, 1.0)
    return result


def trajectory_digest(values: np.ndarray, valid_mask: np.ndarray) -> str:
    valid = np.asarray(valid_mask) > 0.5
    rounded = np.round(np.asarray(values, dtype=np.float64)[valid], decimals=7)
    return hashlib.sha256(rounded.tobytes()).hexdigest()


def generate_group(
    group: str,
    physics_dir: Path,
    generators: list[dict[str, Any]],
    output_dir: Path,
    device_name: str,
    batch_size: int,
    data_mode: str,
    limit_per_subject: int | None,
    correction_decay_s: float,
    slope_window_samples: int,
) -> tuple[list[dict[str, Any]], str]:
    import torch

    core = load_physics_core(physics_dir, group)
    experiment = core.load_config(physics_dir / "experiment.json")
    device = core.choose_torch_device(device_name)
    records = core.load_real_records(data_mode, group)
    context_region_s = float(experiment["model"]["context_region_s"])
    rows: list[dict[str, Any]] = []
    channel_names = CHANNELS[group]

    for generator in generators:
        fold = core.fold_by_id(experiment, int(generator["fold"]))
        verify_generator_split(generator, fold)
        model = core.create_model(experiment, group).to(device)
        model.load_state_dict(load_state(Path(str(generator["checkpoint"])), device))
        model.eval()
        dataset = core.build_dataset(records, list(map(str, fold["train"])), limit_per_subject)
        generator_dir = output_dir / group / f"fold_{int(generator['fold']):02d}" / (
            f"rank_{int(generator['rank_within_fold']):02d}_seed_{int(generator['seed_index']):02d}"
        )
        generator_dir.mkdir(parents=True, exist_ok=True)
        with torch.no_grad():
            for raw_batch in core.iter_batches(dataset, batch_size, False, 0):
                batch = core.batch_to_device(raw_batch, device)
                prediction, controller, _ = core.infer(model, batch, experiment, group)
                gains = controller * model.gain_scale
                prediction_np = prediction.detach().cpu().numpy()
                gains_np = gains.detach().cpu().numpy()
                controller_np = controller.detach().cpu().numpy()
                for index in range(prediction.shape[0]):
                    subject = str(raw_batch["subject"][index])
                    trial = str(raw_batch["trial"][index])
                    activity = str(raw_batch["activity"][index])
                    train_subjects = set(map(str, fold["train"]))
                    held_out = set(normalized_validation_subjects(fold)) | set(map(str, fold["test"]))
                    if subject not in train_subjects or subject in held_out:
                        raise AssertionError(f"held-out context reached generation: {group}/{subject}")
                    time_s = raw_batch["time_s"][index].numpy()
                    valid_mask = raw_batch["valid_mask"][index].numpy()
                    physics_mask = raw_batch["physics_mask"][index].numpy()
                    channels = [
                        raw_batch["theta_rad"][index].numpy(),
                        raw_batch["x_m"][index].numpy(),
                    ]
                    if group == "rotation":
                        channels.append(raw_batch["yaw_rad"][index].numpy())
                    real = np.stack(channels, axis=1)
                    synthetic, context_mask, forecast_mask, corrected, correction = (
                        combine_context_and_forecast(
                            real,
                            prediction_np[index],
                            time_s,
                            valid_mask,
                            context_region_s,
                            correction_decay_s,
                            slope_window_samples,
                        )
                    )
                    one_batch = {
                        key: value[index : index + 1] if hasattr(value, "shape") and getattr(value, "shape", [0])[0] == prediction.shape[0] else value
                        for key, value in batch.items()
                    }
                    real_tensor = torch.as_tensor(real[None], dtype=prediction.dtype, device=device)
                    synthetic_tensor = torch.as_tensor(synthetic[None], dtype=prediction.dtype, device=device)
                    one_gains = gains[index : index + 1]
                    real_residual = residual_metrics(core, real_tensor, one_gains, one_batch, experiment, group)
                    synthetic_residual = residual_metrics(core, synthetic_tensor, one_gains, one_batch, experiment, group)
                    data_file = generator_dir / f"{trial}.npz"
                    payload = {
                        "time_s": time_s.astype(np.float32),
                        "synthetic_theta_rad": synthetic[:, 0].astype(np.float32),
                        "synthetic_x_m": synthetic[:, 1].astype(np.float32),
                        "raw_model_theta_rad": prediction_np[index, :, 0].astype(np.float32),
                        "raw_model_x_m": prediction_np[index, :, 1].astype(np.float32),
                        "corrected_model_theta_rad": corrected[:, 0],
                        "corrected_model_x_m": corrected[:, 1],
                        "valid_mask": valid_mask.astype(np.float32),
                        "physics_mask": physics_mask.astype(np.float32),
                        "context_mask": context_mask.astype(np.uint8),
                        "forecast_mask": forecast_mask.astype(np.uint8),
                        "inferred_controller_normalized": controller_np[index].astype(np.float32),
                        "inferred_physical_gains": gains_np[index].astype(np.float32),
                    }
                    if group == "rotation":
                        payload.update(
                            {
                                "synthetic_yaw_rad": synthetic[:, 2].astype(np.float32),
                                "raw_model_yaw_rad": prediction_np[index, :, 2].astype(np.float32),
                                "corrected_model_yaw_rad": corrected[:, 2],
                            }
                        )
                    np.savez_compressed(data_file, **payload)
                    residual_columns = {}
                    for metric, value in real_residual.items():
                        residual_columns[f"real_physics_{metric}"] = value
                    for metric, value in synthetic_residual.items():
                        residual_columns[f"synthetic_physics_{metric}"] = value
                    offsets = {}
                    for channel_index, name in enumerate(channel_names):
                        scale = 180.0 / np.pi if name in {"theta", "yaw"} else 100.0
                        unit = "deg" if name in {"theta", "yaw"} else "cm"
                        velocity_unit = "deg_s" if name in {"theta", "yaw"} else "cm_s"
                        offsets[f"raw_boundary_{name}_offset_{unit}"] = scale * correction[f"channel_{channel_index}_position_offset"]
                        offsets[f"raw_boundary_{name}_velocity_offset_{velocity_unit}"] = scale * correction[f"channel_{channel_index}_velocity_offset"]
                    synthetic_id = (
                        f"{group[0].upper()}F{int(generator['fold']):02d}_"
                        f"R{int(generator['rank_within_fold']):02d}_"
                        f"S{int(generator['seed_index']):02d}_{trial}"
                    )
                    rows.append(
                        {
                            "synthetic_id": synthetic_id,
                            "model_group": group,
                            "activity": activity,
                            "fold": int(generator["fold"]),
                            "generator_rank": int(generator["rank_within_fold"]),
                            "seed_index": int(generator["seed_index"]),
                            "base_optimization_seed": int(generator["base_optimization_seed"]),
                            "physics_weight": float(generator["physics_weight"]),
                            "best_epoch": int(generator["best_epoch"]),
                            "validation_forecast_mse": float(generator["validation_forecast_mse"]),
                            "validation_subjects": ";".join(normalized_validation_subjects(fold)),
                            "source_subject": subject,
                            "source_trial": trial,
                            "source_is_training_subject": True,
                            "validation_or_test_context_used": False,
                            "context_region_s": context_region_s,
                            "continuity_correction": "C1_decaying_exponential",
                            "continuity_boundary_time_s": correction["boundary_time_s"],
                            "continuity_decay_s": correction_decay_s,
                            "continuity_slope_window_samples": slope_window_samples,
                            "endpoint_semantics": "source_conditioned_apparent_contact",
                            "valid_samples": int(np.sum(valid_mask > 0.5)),
                            "forecast_samples": int(np.sum(forecast_mask)),
                            "trajectory_sha256": trajectory_digest(synthetic, valid_mask),
                            "data_file": str(data_file.relative_to(output_dir)),
                            "checkpoint": str(Path(str(generator["checkpoint"])).resolve()),
                            **offsets,
                            **residual_columns,
                        }
                    )
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
    return rows, str(device)


def run_generation(
    config_file: Path,
    config: dict[str, Any],
    selection_file: Path,
    output_dir: Path,
    device_name: str,
    batch_size: int,
    limit_per_subject: int | None,
    maximum_generators_per_group: int | None,
    planar_dir: Path | None,
    rotation_dir: Path | None,
) -> dict[str, Any]:
    selected = selected_generator_rows(selection_file)
    settings = dict(config["generation"])
    all_rows: list[dict[str, Any]] = []
    devices: dict[str, str] = {}
    physics_directories: dict[str, str] = {}
    for group, override in (("planar", planar_dir), ("rotation", rotation_dir)):
        generators = [row for row in selected if str(row["model_group"]) == group]
        if maximum_generators_per_group is not None:
            generators = generators[:maximum_generators_per_group]
        physics_dir = resolve_physics_dir(config_file, config, group, override)
        rows, device = generate_group(
            group,
            physics_dir,
            generators,
            output_dir,
            device_name,
            batch_size,
            str(settings["prepared_data_mode"]),
            limit_per_subject,
            float(settings["continuity_decay_s"]),
            int(settings["continuity_slope_window_samples"]),
        )
        all_rows.extend(rows)
        devices[group] = device
        physics_directories[group] = str(physics_dir)
    if not all_rows:
        raise ValueError("no synthetic trajectories were generated")
    write_csv(output_dir / "synthetic_manifest.csv", all_rows)
    payload = {
        "description": "Conditional A10-A13 direct-CartPole and A14 rotation-physics trajectories from top-two validation models",
        "selection_file": str(selection_file),
        "physics_directories": physics_directories,
        "devices": devices,
        "context_policy": str(settings["context_policy"]),
        "duration_semantics": "apparent-contact endpoint and valid length inherited from the source trial",
        "held_out_contexts_used": False,
        "generator_count": len(selected),
        "synthetic_trajectory_count": len(all_rows),
        "counts_by_group": {group: sum(row["model_group"] == group for row in all_rows) for group in GROUPS},
        "samples": all_rows,
    }
    dump_json(output_dir / "synthetic_manifest.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "study_config.json")
    parser.add_argument("--selection-file", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--planar-dir", type=Path)
    parser.add_argument("--rotation-dir", type=Path)
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda", "mps"))
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--limit-per-subject", type=int)
    parser.add_argument("--maximum-generators-per-group", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_file, config = load_study_config(args.config)
    selection_file = (
        args.selection_file.expanduser().resolve()
        if args.selection_file
        else resolve_from(config_file, str(config["selection_output_directory"])) / "generator_selection.json"
    )
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else resolve_from(config_file, str(config["generation_output_directory"]))
    )
    batch_size = args.batch_size or int(config["generation"]["batch_size"])
    payload = run_generation(
        config_file,
        config,
        selection_file,
        output_dir,
        args.device,
        batch_size,
        args.limit_per_subject,
        args.maximum_generators_per_group,
        args.planar_dir,
        args.rotation_dir,
    )
    print(
        f"Generated {payload['synthetic_trajectory_count']} trajectories from "
        f"{payload['generator_count']} validation-selected direct-physics checkpoints."
    )
    print(f"Outputs: {output_dir}")


if __name__ == "__main__":
    main()

