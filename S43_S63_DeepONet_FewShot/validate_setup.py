#!/usr/bin/env python3
"""Validate source pipelines, exact checkpoints, and gain metadata without training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from operator_core import GAIN_NAMES, load_config, resolve_from_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="experiment.json")
    args = parser.parse_args()
    config = load_config(args.config)
    errors: list[str] = []
    rows = []
    for teacher in config["teachers"]:
        resolved = {
            name: resolve_from_config(config, teacher[name])
            for name in ("pipeline_source", "checkpoint", "gain_result")
        }
        for name, path in resolved.items():
            if not path.is_file():
                errors.append(f"{teacher['id']}: missing {name}: {path}")
        gains = None
        if resolved["gain_result"].is_file():
            result = json.loads(resolved["gain_result"].read_text(encoding="utf-8"))
            missing = [name for name in GAIN_NAMES if name not in result]
            if missing:
                errors.append(f"{teacher['id']}: gain result missing {missing}")
            else:
                gains = [float(result[name]) for name in GAIN_NAMES]
        rows.append(
            {
                "teacher": teacher["id"],
                "subject": teacher["subject"],
                "checkpoint": str(resolved["checkpoint"]),
                "gains": gains,
            }
        )
    print(json.dumps(rows, indent=2))
    if errors:
        print("\nSETUP ERRORS:")
        for error in errors:
            print(f"- {error}")
        print("\nEdit experiment.json so each path points to the corresponding local project file.")
        raise SystemExit(1)
    print("\nSetup validation passed for all three exact teacher checkpoints.")


if __name__ == "__main__":
    main()
