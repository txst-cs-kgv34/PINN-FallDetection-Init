#!/usr/bin/env python3
"""Validate the adapter output against the unchanged pole loader contract."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CORE_SHA256 = "604985d2344350789929c3554f9ce4351b826f69be1dfe9dee0b20acb586e0a9"


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def exact_resample(signal: np.ndarray) -> tuple[np.ndarray, str]:
    try:
        import resampy

        return resampy.resample(signal, 250, 100), "resampy (exact pole loader method)"
    except ModuleNotFoundError:
        from scipy.signal import resample_poly

        return resample_poly(signal, 2, 5), "scipy fallback (install resampy for exact check)"


def main() -> None:
    manifest = json.loads((ROOT / "results" / "adapter_manifest.json").read_text())
    runtime_overrides = json.loads((ROOT / "config" / "S55_runtime_overrides.json").read_text())
    minimum_duration_s = float(runtime_overrides["minimum_trial_seconds"])
    core_path = ROOT / manifest["core_pipeline"]["file"]
    core_hash = sha256(core_path)
    if core_hash != EXPECTED_CORE_SHA256 or core_hash != manifest["core_pipeline"]["sha256"]:
        raise AssertionError("the supplied pole main file was modified")

    expected_files = sorted(Path(item["pole_input_file"]).name for item in manifest["trials"])
    actual_files = sorted(
        path.name for path in (ROOT / "data" / "pole_compatible" / "A11").glob("SubjectB_*.tsv")
    )
    if actual_files != expected_files:
        missing = sorted(set(expected_files) - set(actual_files))
        unexpected = sorted(set(actual_files) - set(expected_files))
        raise AssertionError(
            f"subject input inventory mismatch: missing={missing}; unexpected={unexpected}"
        )

    report = {
        "status": "pass",
        "core_pipeline_sha256": core_hash,
        "core_pipeline_unchanged": True,
        "minimum_trial_seconds": minimum_duration_s,
        "duration_override_reason": runtime_overrides["reason"],
        "input_inventory_validated": True,
        "input_files": actual_files,
        "trials": [],
    }
    for item in manifest["trials"]:
        path = ROOT / item["pole_input_file"]
        data = np.loadtxt(path, delimiter="\t", ndmin=2)
        if data.shape[1] != 6:
            raise AssertionError(f"{path.name}: expected six columns")
        if not np.allclose(data[:1024], data[0], atol=1e-12, rtol=0.0):
            raise AssertionError(f"{path.name}: warmup padding is not constant")
        data = data[1024:]
        length = np.linalg.norm(data[:, :3] - data[:, 3:], axis=1)
        theta_250 = np.arcsin(np.clip((data[:, 0] - data[:, 3]) / length, -1.0, 1.0))
        x_mm_250 = data[:, 3]
        theta, method = exact_resample(theta_250)
        x_mm, _ = exact_resample(x_mm_250)
        x_m = x_mm * 0.001
        baseline = min(len(x_m), 50)
        x_m -= np.median(x_m[:baseline])

        crossing = np.flatnonzero(np.abs(theta) >= math.radians(20.0))
        usable_end = max(1, int(crossing[0]) - 8) if len(crossing) else len(theta)
        duration_s = (usable_end - 1) / 100.0
        if duration_s < minimum_duration_s:
            raise AssertionError(f"{path.name}: only {duration_s:.3f} s survives pole trimming")
        if not np.isfinite(theta).all() or not np.isfinite(x_m).all():
            raise AssertionError(f"{path.name}: non-finite decoded values")

        report["trials"].append(
            {
                "trial": item["trial"],
                "resampling_check": method,
                "decoded_samples_100hz": int(len(theta)),
                "usable_samples_after_20deg_rule": usable_end,
                "usable_duration_s": duration_s,
                "theta0_deg": float(np.degrees(theta[0])),
                "theta_range_deg_before_trim": [
                    float(np.degrees(theta).min()),
                    float(np.degrees(theta).max()),
                ],
                "centered_x_range_m_before_trim": [float(x_m.min()), float(x_m.max())],
            }
        )

    output = ROOT / "results" / "input_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(report['trials'])} trials satisfy the S55 adapter contract")
    print(f"Core SHA-256: {core_hash}")
    for item in report["trials"]:
        print(f"  {item['trial']}: {item['usable_duration_s']:.2f} s usable")
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
