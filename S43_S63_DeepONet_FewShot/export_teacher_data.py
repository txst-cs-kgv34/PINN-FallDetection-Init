#!/usr/bin/env python3
"""Generate matched trajectories from the three exact PINN teacher checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from operator_core import GAIN_NAMES, ROOT, dump_json, load_config, resolve_from_config


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def import_pipeline(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import pipeline source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def shared_initial_conditions(settings: dict, count: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    theta0_deg = rng.uniform(settings["theta0_min_deg"], settings["theta0_max_deg"], count)
    if count >= 3:
        theta0_deg[:3] = [settings["theta0_min_deg"], 0.0, settings["theta0_max_deg"]]
    initial = np.column_stack(
        [
            np.radians(theta0_deg),
            rng.uniform(settings["x0_min_m"], settings["x0_max_m"], count),
            rng.normal(0.0, settings["theta_dot0_std_rad_s"], count),
            rng.normal(0.0, settings["x_dot0_std_m_s"], count),
        ]
    )
    return initial.astype(np.float32)


def predict(model, time_s: np.ndarray, initial_states: np.ndarray, batch_size: int) -> tuple[np.ndarray, np.ndarray]:
    rows = []
    owners = []
    for index, initial in enumerate(initial_states):
        n = time_s.size
        rows.append(
            np.column_stack(
                [
                    time_s,
                    np.full(n, initial[0], dtype=np.float32),
                    np.full(n, initial[1], dtype=np.float32),
                    np.full(n, initial[2], dtype=np.float32),
                    np.full(n, initial[3], dtype=np.float32),
                ]
            )
        )
        owners.append(index)
    inputs = np.concatenate(rows, axis=0).astype(np.float32)
    predictions = []
    for start in range(0, len(inputs), batch_size):
        predictions.append(model(inputs[start : start + batch_size], training=False).numpy())
    prediction = np.concatenate(predictions, axis=0)
    prediction = prediction.reshape(len(initial_states), len(time_s), 2)
    return prediction[:, :, 0].astype(np.float32), prediction[:, :, 1].astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    generation = dict(config["teacher_generation"])
    if args.mode == "smoke":
        generation["trajectory_count"] = 6
        generation["horizon_s"] = 0.6
    count = int(generation["trajectory_count"])
    rate = int(generation["sample_rate_hz"])
    time_s = np.linspace(
        0.0, generation["horizon_s"], int(round(generation["horizon_s"] * rate)) + 1
    ).astype(np.float32)
    initial_states = shared_initial_conditions(generation, count, int(config["seed"]))
    output_dir = ROOT / "outputs" / f"teacher_data_{args.mode}"
    output_dir.mkdir(parents=True, exist_ok=True)

    import tensorflow as tf

    tf.keras.backend.set_floatx("float32")
    manifest_teachers = []
    for teacher_index, teacher in enumerate(config["teachers"]):
        source = resolve_from_config(config, teacher["pipeline_source"])
        checkpoint = resolve_from_config(config, teacher["checkpoint"])
        gain_result_path = resolve_from_config(config, teacher["gain_result"])
        for path in (source, checkpoint, gain_result_path):
            if not path.is_file():
                raise FileNotFoundError(f"Required teacher file not found: {path}")
        destination = output_dir / f"{teacher['id']}.npz"
        if destination.exists() and not args.overwrite:
            raise FileExistsError(f"{destination} exists; pass --overwrite to regenerate it.")

        pipeline = import_pipeline(source, f"teacher_pipeline_{teacher_index}_{args.mode}")
        # The model must retain the 30 s normalization used while training its checkpoint.
        if abs(float(pipeline.CFG.generation_horizon_s) - 30.0) > 1e-6:
            raise ValueError(
                f"{teacher['id']}: pipeline time scale is {pipeline.CFG.generation_horizon_s}, expected 30 s."
            )
        tf.random.set_seed(int(config["seed"]) + teacher_index)
        model = pipeline.ConditionalPolePINN()
        _ = model(tf.zeros((1, 5), dtype=tf.float32))
        model.load_weights(checkpoint)
        theta_rad, x_m = predict(
            model, time_s, initial_states, int(generation["prediction_batch_size"])
        )
        if not np.isfinite(theta_rad).all() or not np.isfinite(x_m).all():
            raise ValueError(f"{teacher['id']}: non-finite predictions generated")
        np.savez_compressed(
            destination,
            time_s=time_s,
            theta_rad=theta_rad,
            x_m=x_m,
            initial_states=initial_states,
        )

        gain_result = json.loads(gain_result_path.read_text(encoding="utf-8"))
        gains = [float(gain_result[name]) for name in GAIN_NAMES]
        manifest_teachers.append(
            {
                "id": teacher["id"],
                "subject": teacher["subject"],
                "mass_kg": float(teacher["mass_lb"]) * 0.45359237,
                "height_m": float(teacher["height_in"]) * 0.0254,
                "gains": gains,
                "gain_names": list(GAIN_NAMES),
                "pi_rad": float(np.radians(gain_result["fixed_pi_deg"])),
                "pi_deg": float(gain_result["fixed_pi_deg"]),
                "tau_s": float(gain_result["fixed_tau_s"]),
                "checkpoint": str(checkpoint),
                "checkpoint_sha256": sha256(checkpoint),
                "pipeline_source": str(source),
                "pipeline_source_sha256": sha256(source),
                "gain_result": str(gain_result_path),
                "data_file": destination.name,
                "trajectory_count": count,
                "sample_count": int(time_s.size),
            }
        )
        print(f"Generated {count} matched trajectories from {teacher['id']}")

    manifest = {
        "experiment": config["experiment_name"],
        "mode": args.mode,
        "seed": int(config["seed"]),
        "horizon_s": float(generation["horizon_s"]),
        "sample_rate_hz": rate,
        "shared_initial_conditions": True,
        "teacher_count": len(manifest_teachers),
        "distinct_subject_count": len({item["subject"] for item in manifest_teachers}),
        "teachers": manifest_teachers,
        "limitations": [
            "There are three teacher gain anchors but only two human subjects.",
            "These trajectories are teacher-PINN outputs, not additional measured falls.",
            "The 3 s full horizon is a synthetic pilot horizon and is not evidence of 3 s real-data validity for every subject.",
        ],
    }
    dump_json(output_dir / "teacher_manifest.json", manifest)
    print(f"Saved teacher dataset manifest: {output_dir / 'teacher_manifest.json'}")


if __name__ == "__main__":
    main()
