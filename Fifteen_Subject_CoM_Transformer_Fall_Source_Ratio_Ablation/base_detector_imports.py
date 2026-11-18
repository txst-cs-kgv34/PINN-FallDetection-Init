from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def load_raw_config(path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    config_path = (path or ROOT / "config.json").expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return config_path, config


def install_base_detector_path(config_path: Path, raw_config: dict[str, Any]) -> Path:
    base = Path(raw_config["base_detector_root"]).expanduser()
    if not base.is_absolute():
        base = config_path.parent / base
    base = base.resolve()
    required = [base / "detector_core.py", base / "model.py", base / "train_scenario.py"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "The fall-source ratio experiment reuses the verified base detector code. "
            f"Missing: {missing}"
        )
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    return base


def prepare_base_imports(config_path: Path | None = None) -> tuple[Path, dict[str, Any], Path]:
    path, raw = load_raw_config(config_path)
    base = install_base_detector_path(path, raw)
    return path, raw, base

