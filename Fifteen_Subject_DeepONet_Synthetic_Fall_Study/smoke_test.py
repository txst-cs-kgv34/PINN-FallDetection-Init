#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from select_generators import run_selection
from tests.fixture_factory import create_results_fixture


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        results = create_results_fixture(root)
        output = root / "selection"
        payload = run_selection(results, output, 5, 5, 2, True, False)
        if payload["candidate_count"] != 25 or payload["selected_count"] != 10:
            raise AssertionError("Smoke selection counts are incorrect")
        selected = [row for row in payload["rankings"] if row["selected"]]
        if {row["seed_index"] for row in selected} != {2, 3}:
            raise AssertionError("Smoke selection ranking is incorrect")
        copied = list(
            (output / "selected_generators").glob(
                "fold_*/rank_*_seed_*_*/final_best_model_state.pt"
            )
        )
        if len(copied) != 10:
            raise AssertionError("Smoke checkpoint materialization is incomplete")
    print("Smoke test passed: 25 candidates validated; top two per fold selected.")


if __name__ == "__main__":
    main()
