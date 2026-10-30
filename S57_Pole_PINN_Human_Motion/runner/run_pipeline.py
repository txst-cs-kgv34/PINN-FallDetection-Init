#!/usr/bin/env python3
"""Run the unchanged pole PINN source with S57 A11 adapter inputs."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "pinn_pole_synthetic_data_generation.py"
INPUTS = ROOT / "data" / "pole_compatible" / "A11"
RUNTIME_OVERRIDES = ROOT / "config" / "S57_runtime_overrides.json"


def load_pipeline():
    spec = importlib.util.spec_from_file_location("unchanged_pole_pipeline", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("input-check", "smoke", "full"), default="input-check")
    args = parser.parse_args()

    pipeline = load_pipeline()
    runtime_overrides = json.loads(RUNTIME_OVERRIDES.read_text(encoding="utf-8"))
    pipeline.CFG.minimum_trial_seconds = float(runtime_overrides["minimum_trial_seconds"])
    output = ROOT / "results" / ("smoke_run" if args.mode == "smoke" else "full_run")
    pipeline.CFG.data_folder = str(INPUTS)
    pipeline.CFG.output_folder = str(output)

    if args.mode == "input-check":
        trials = pipeline.load_trials()
        result = {
            "mode": args.mode,
            "accepted_trials": len(trials),
            "trials": [
                {
                    "name": trial.name,
                    "samples": len(trial.t),
                    "duration_s": trial.duration,
                    "theta0_deg": float(trial.theta0 * 180.0 / 3.141592653589793),
                    "x0_m": trial.x0,
                }
                for trial in trials
            ],
        }
        path = ROOT / "results" / "original_loader_check.json"
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return

    if args.mode == "smoke":
        # Only optimization duration/batch size and output count are reduced.
        # Network architecture, equations, losses, stages, and controller are unchanged.
        pipeline.CFG.stage1_epochs = 2
        pipeline.CFG.stage1_data_warmup_epochs = 1
        pipeline.CFG.stage1_batch_size = 64
        pipeline.CFG.stage2_epochs = 2
        pipeline.CFG.stage2_pi_freeze_epochs = 1
        pipeline.CFG.stage2_batch_size = 64
        pipeline.CFG.stage3_epochs = 2
        pipeline.CFG.stage3_batch_size = 64
        pipeline.CFG.number_generated_trajectories = 3
        pipeline.CFG.number_plotted_trajectories = 3
        pipeline.CFG.print_every = 1

    output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "mode": args.mode,
        "source_file": str(SOURCE.relative_to(ROOT)),
        "source_modified": False,
        "input_folder": str(INPUTS.relative_to(ROOT)),
        "runtime_overrides": {
            "minimum_trial_seconds": pipeline.CFG.minimum_trial_seconds,
            "reason": runtime_overrides["reason"],
        },
        "note": (
            "Smoke mode shortens epochs/batches only and is not a scientific result."
            if args.mode == "smoke"
            else "Full mode preserves the architecture and training/generation settings; only paths and the documented S57 input-duration eligibility gate are overridden."
        ),
    }
    (output / "run_mode.json").write_text(json.dumps(metadata, indent=2) + "\n")
    pipeline.main()


if __name__ == "__main__":
    main()
