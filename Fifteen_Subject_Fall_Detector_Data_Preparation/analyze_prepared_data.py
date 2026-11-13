#!/usr/bin/env python3
"""Summarize prepared trajectory ranges and real/synthetic context alignment."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from detector_data_core import dump_json, write_csv


HERE = Path(__file__).resolve().parent


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE / "outputs")
    args = parser.parse_args()
    root = args.output_dir.expanduser().resolve()
    manifest = json.loads((root / "dataset_manifest.json").read_text(encoding="utf-8"))
    samples = manifest["samples"]

    trial_rows: list[dict[str, Any]] = []
    real_by_trial: dict[str, dict[str, Any]] = {}
    loaded: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for row in samples:
        with np.load(root / row["data_file"], allow_pickle=False) as data:
            time = np.asarray(data["time_s"], dtype=np.float64)
            theta = np.asarray(data["theta_rad"], dtype=np.float64)
            x_m = np.asarray(data["x_m"], dtype=np.float64)
        loaded[str(row["sample_id"])] = (time, theta, x_m)
        trial_rows.append(
            {
                "sample_id": row["sample_id"],
                "source_kind": row["source_kind"],
                "subject": row["subject"],
                "activity_code": row["activity_code"],
                "duration_s": row["duration_s"],
                "maximum_abs_theta_deg": float(np.degrees(np.max(np.abs(theta)))),
                "theta_range_deg": float(np.degrees(np.ptp(theta))),
                "maximum_abs_x_m": float(np.max(np.abs(x_m))),
                "x_range_m": float(np.ptp(x_m)),
            }
        )
        if row["source_kind"] == "real_fall":
            real_by_trial[str(row["trial"])] = row

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trial_rows:
        grouped[str(row["source_kind"])].append(row)
    range_summary: list[dict[str, Any]] = []
    for kind, rows in sorted(grouped.items()):
        result: dict[str, Any] = {"source_kind": kind, "sample_count": len(rows)}
        for metric in (
            "maximum_abs_theta_deg", "theta_range_deg", "maximum_abs_x_m", "x_range_m"
        ):
            values = [float(row[metric]) for row in rows]
            result[f"median_{metric}"] = float(np.median(values))
            result[f"p95_{metric}"] = percentile(values, 95.0)
            result[f"maximum_{metric}"] = float(np.max(values))
        range_summary.append(result)

    alignment: list[dict[str, Any]] = []
    for row in samples:
        if row["source_kind"] != "synthetic_fall":
            continue
        real = real_by_trial.get(str(row["source_real_trial"]))
        if real is None:
            raise ValueError(f"No prepared real source for {row['sample_id']}")
        syn_time, syn_theta, syn_x = loaded[str(row["sample_id"])]
        real_time, real_theta, real_x = loaded[str(real["sample_id"])]
        count = min(
            int(np.sum(syn_time <= 0.4 + 1e-6)),
            int(np.sum(real_time <= 0.4 + 1e-6)),
        )
        theta_error = syn_theta[:count] - real_theta[:count]
        x_error = syn_x[:count] - real_x[:count]
        alignment.append(
            {
                "synthetic_sample_id": row["sample_id"],
                "source_real_trial": row["source_real_trial"],
                "source_subject": row["source_subject"],
                "context_samples_compared": count,
                "theta_context_rmse_deg": float(np.degrees(np.sqrt(np.mean(theta_error**2)))),
                "x_context_rmse_cm": float(100.0 * np.sqrt(np.mean(x_error**2))),
                "maximum_abs_theta_context_error_deg": float(np.degrees(np.max(np.abs(theta_error)))),
                "maximum_abs_x_context_error_cm": float(100.0 * np.max(np.abs(x_error))),
            }
        )

    write_csv(root / "trajectory_range_by_sample.csv", trial_rows)
    write_csv(root / "trajectory_range_summary.csv", range_summary)
    write_csv(root / "real_synthetic_context_alignment.csv", alignment)
    dump_json(
        root / "analysis_summary.json",
        {
            "range_summary": range_summary,
            "real_synthetic_context_alignment": {
                "comparison_count": len(alignment),
                "median_theta_context_rmse_deg": float(
                    np.median([row["theta_context_rmse_deg"] for row in alignment])
                ),
                "maximum_theta_context_rmse_deg": float(
                    np.max([row["theta_context_rmse_deg"] for row in alignment])
                ),
                "median_x_context_rmse_cm": float(
                    np.median([row["x_context_rmse_cm"] for row in alignment])
                ),
                "maximum_x_context_rmse_cm": float(
                    np.max([row["x_context_rmse_cm"] for row in alignment])
                ),
                "interpretation": "Small nonzero differences are expected because real skeletons are converted directly at 30 Hz while generator contexts passed through the earlier 30-to-250-to-100 Hz preparation before this package resampled them to 30 Hz.",
            },
        },
    )
    print(f"Analyzed {len(trial_rows)} trajectories and {len(alignment)} synthetic contexts.")


if __name__ == "__main__":
    main()
