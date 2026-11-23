from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
GROUPS = ("planar", "rotation")


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


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def resolve_from(base_file: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_file.parent / path
    return path.resolve()


def load_study_config(path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    config_file = (path or HERE / "study_config.json").expanduser().resolve()
    config = read_json(config_file)
    for group in GROUPS:
        if group not in config:
            raise ValueError(f"study config is missing {group!r}")
    return config_file, config


def group_settings(config: dict[str, Any], group: str) -> dict[str, Any]:
    if group not in GROUPS:
        raise ValueError(f"unknown model group {group!r}")
    return dict(config[group])


def resolve_physics_dir(
    config_file: Path,
    config: dict[str, Any],
    group: str,
    override: Path | None = None,
) -> Path:
    settings = group_settings(config, group)
    path = (
        override.expanduser().resolve()
        if override is not None
        else resolve_from(config_file, str(settings["physics_directory"]))
    )
    missing = [path / name for name in ("operator_core.py", "experiment.json") if not (path / name).is_file()]
    if missing:
        raise ValueError(
            f"{group} physics directory is incomplete: " + ", ".join(map(str, missing))
        )
    return path


def resolve_results_dir(
    physics_dir: Path, config: dict[str, Any], group: str
) -> Path:
    return (physics_dir / str(group_settings(config, group)["results_subdirectory"])).resolve()


def load_physics_core(physics_dir: Path, group: str):
    module_path = (physics_dir / "operator_core.py").resolve()
    module_name = f"synthetic_study_{group}_operator_core"
    if module_name in sys.modules:
        existing = sys.modules[module_name]
        if Path(existing.__file__).resolve() == module_path:
            return existing
        del sys.modules[module_name]
    specification = importlib.util.spec_from_file_location(module_name, module_path)
    if specification is None or specification.loader is None:
        raise ImportError(f"Cannot import {module_path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def normalized_validation_subjects(fold: dict[str, Any]) -> tuple[str, ...]:
    value = fold["validation"]
    if isinstance(value, str):
        return (value,)
    return tuple(map(str, value))


def validate_fold_split(fold: dict[str, Any]) -> None:
    train = set(map(str, fold["train"]))
    validation = set(normalized_validation_subjects(fold))
    test = set(map(str, fold["test"]))
    if train & validation or train & test or validation & test:
        raise ValueError(f"subject leakage in fold {fold['id']}")
    if len(test) != 3:
        raise ValueError(f"fold {fold['id']} must contain three test subjects")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

