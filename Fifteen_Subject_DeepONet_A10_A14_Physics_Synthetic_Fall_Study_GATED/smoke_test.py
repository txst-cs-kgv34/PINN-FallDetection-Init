#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from select_generators import run_selection
from tests.fixture_factory import create_fixture


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        config_file, config = create_fixture(root)
        payload = run_selection(
            config_file,
            config,
            root / "selection",
            None,
            None,
            True,
            False,
        )
        if payload["selected_count"] != 20:
            raise AssertionError("expected two groups x five folds x top two models")
        if any(float(row["physics_weight"]) <= 0 for row in payload["materialized_generators"]):
            raise AssertionError("lambda=0 entered the synthetic generator pool")
    print("Smoke test passed: top-two direct-physics selection validated for both groups.")


if __name__ == "__main__":
    main()

