from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Missing required file: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def resolve_from(base_file: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_file.parent / path
    return path.resolve()


def load_study_config(path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    config_file = (path or HERE / "study_config.json").expanduser().resolve()
    return config_file, read_json(config_file)


def resolve_physics_dir(
    config_file: Path, config: dict[str, Any], override: Path | None
) -> Path:
    path = (
        override.expanduser().resolve()
        if override is not None
        else resolve_from(config_file, str(config["physics_directory"]))
    )
    required = (path / "operator_core.py", path / "experiment.json")
    missing = [item for item in required if not item.is_file()]
    if missing:
        raise ValueError(
            "Physics directory is incomplete: " + ", ".join(map(str, missing))
        )
    return path


def load_physics_core(physics_dir: Path):
    module_path = physics_dir / "operator_core.py"
    module_name = "full_fall_physics_operator_core"
    if module_name in sys.modules:
        existing = sys.modules[module_name]
        if Path(existing.__file__).resolve() != module_path.resolve():
            del sys.modules[module_name]
        else:
            return existing
    specification = importlib.util.spec_from_file_location(module_name, module_path)
    if specification is None or specification.loader is None:
        raise ImportError(f"Cannot import {module_path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write an empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
