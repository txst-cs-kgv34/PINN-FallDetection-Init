#!/usr/bin/env python3
"""Prepare real trajectories for training, real validation, and real testing."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import resampy

from operator_core import ROOT, dump_json, load_config, resolve_glob, sha256


def load_trial(path: Path, settings: dict) -> tuple[np.ndarray, np.ndarray]:
    data = np.genfromtxt(path, delimiter="\t")
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] < 6:
        raise ValueError(f"{path} has fewer than six columns")
    data = data[int(settings["raw_warmup_rows"]) :, :6]
    x1, y1, z1, x2, y2, z2 = np.hsplit(data, 6)
    length = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2) + 1e-10
    theta = np.arcsin(np.clip((x1 - x2) / length, -1.0, 1.0)).reshape(-1)
    x_mm = x2.reshape(-1)
    theta = resampy.resample(
        theta,
        sr_orig=int(settings["source_rate_hz"]),
        sr_new=int(settings["target_rate_hz"]),
    )
    x_mm = resampy.resample(
        x_mm,
        sr_orig=int(settings["source_rate_hz"]),
        sr_new=int(settings["target_rate_hz"]),
    )
    x_m = x_mm * 0.001
    baseline_count = min(len(x_m), int(round(0.5 * int(settings["target_rate_hz"]))))
    x_m = x_m - np.median(x_m[:baseline_count])

    threshold = np.radians(float(settings["fall_angle_deg"]))
    crossings = np.flatnonzero(np.abs(theta) >= threshold)
    if len(crossings):
        margin = int(round(float(settings["prefall_margin_s"]) * int(settings["target_rate_hz"])))
        usable_end = max(1, int(crossings[0]) - margin)
        theta = theta[:usable_end]
        x_m = x_m[:usable_end]
    return theta.astype(np.float32), x_m.astype(np.float32)


def initial_state(theta: np.ndarray, x_m: np.ndarray, rate: int, fit_samples: int) -> np.ndarray:
    count = min(len(theta), int(fit_samples))
    if count < 3:
        theta_dot0 = 0.0
        x_dot0 = 0.0
    else:
        time = np.arange(count, dtype=np.float64) / rate
        theta_dot0 = float(np.polyfit(time, theta[:count], 1)[0])
        x_dot0 = float(np.polyfit(time, x_m[:count], 1)[0])
    return np.asarray([theta[0], x_m[0], theta_dot0, x_dot0], dtype=np.float32)


def pad_to_grid(values: np.ndarray, samples: int) -> tuple[np.ndarray, np.ndarray]:
    valid = min(len(values), samples)
    padded = np.full(samples, values[valid - 1], dtype=np.float32)
    padded[:valid] = values[:valid]
    mask = np.zeros(samples, dtype=np.float32)
    mask[:valid] = 1.0
    return padded, mask


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    settings = config["real_data"]
    horizon = 0.8 if args.mode == "smoke" else float(config["data"]["horizon_s"])
    rate = int(settings["target_rate_hz"])
    grid_samples = int(round(horizon * rate)) + 1
    time_s = np.linspace(0.0, horizon, grid_samples, dtype=np.float32)
    context_samples = int(round(float(config["model"]["context_region_s"]) * rate)) + 1
    output_dir = ROOT / "outputs" / f"real_data_{args.mode}"
    output_dir.mkdir(parents=True, exist_ok=True)
    included, excluded = [], []

    for subject in config["subjects"]:
        files = resolve_glob(config, subject["real_data_glob"])
        if not files:
            raise FileNotFoundError(f"No real TSVs match {subject['real_data_glob']}")
        subject_included = 0
        for path in files:
            theta, x_m = load_trial(path, settings)
            trial = path.stem.removeprefix("SubjectB_")
            usable_samples = len(theta)
            usable_duration = (usable_samples - 1) / rate if usable_samples else 0.0
            if usable_samples < context_samples:
                excluded.append(
                    {
                        "subject": subject["id"],
                        "trial": trial,
                        "source_file": str(path),
                        "usable_samples": usable_samples,
                        "usable_duration_s": usable_duration,
                        "reason": (
                            f"requires at least {context_samples} samples for the fixed "
                            f"{config['model']['context_windows']}-window context"
                        ),
                    }
                )
                print(f"Excluded {trial}: {usable_duration:.2f}s is shorter than the context")
                continue
            destination = output_dir / f"{trial}.npz"
            if destination.exists() and not args.overwrite:
                raise FileExistsError(f"{destination} exists; pass --overwrite")
            theta_padded, valid_mask = pad_to_grid(theta, grid_samples)
            x_padded, x_valid_mask = pad_to_grid(x_m, grid_samples)
            if not np.array_equal(valid_mask, x_valid_mask):
                raise AssertionError("theta/x masks differ")
            state = initial_state(
                theta, x_m, rate, int(settings["derivative_fit_samples"])
            )
            np.savez_compressed(
                destination,
                time_s=time_s,
                theta_rad=theta_padded,
                x_m=x_padded,
                valid_mask=valid_mask,
                initial_state=state,
            )
            valid_stored = int(valid_mask.sum())
            included.append(
                {
                    "subject": subject["id"],
                    "trial": trial,
                    "mass_kg": float(subject["mass_lb"]) * 0.45359237,
                    "height_m": float(subject["height_in"]) * 0.0254,
                    "source_file": str(path),
                    "source_sha256": sha256(path),
                    "data_file": destination.name,
                    "usable_samples": usable_samples,
                    "usable_duration_s": usable_duration,
                    "stored_valid_samples": valid_stored,
                    "stored_valid_duration_s": (valid_stored - 1) / rate,
                }
            )
            subject_included += 1
            print(f"Included {trial}: {usable_duration:.2f}s ({valid_stored} stored samples)")
        if subject_included == 0:
            raise ValueError(f"No {subject['id']} trials can supply the configured context")

    dump_json(
        output_dir / "real_manifest.json",
        {
            "experiment": config["experiment_name"],
            "mode": args.mode,
            "sample_rate_hz": rate,
            "stored_horizon_s": horizon,
            "context_windows": int(config["model"]["context_windows"]),
            "context_window_s": float(config["model"]["context_window_s"]),
            "context_region_s": float(config["model"]["context_region_s"]),
            "preprocessing": "Audit skeletons are first converted in a fixed standing anatomical frame; all inputs then use the exact warmup removal, 250-to-100 Hz resampling, x centering, and pre-20-degree cutoff from the earlier Model B pole pipeline.",
            "included_trials": included,
            "excluded_trials": excluded,
            "included_by_subject": {
                subject["id"]: sum(1 for item in included if item["subject"] == subject["id"])
                for subject in config["subjects"]
            },
        },
    )
    print(f"Saved {output_dir / 'real_manifest.json'}")


if __name__ == "__main__":
    main()
