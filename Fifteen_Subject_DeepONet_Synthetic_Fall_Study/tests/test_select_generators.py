from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from select_generators import run_selection
from tests.fixture_factory import create_results_fixture


class GeneratorSelectionTests(unittest.TestCase):
    def test_top_two_are_selected_with_copied_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            results = create_results_fixture(root)
            output = root / "study_output"
            payload = run_selection(results, output, 5, 5, 2, True, False)
            self.assertEqual(payload["candidate_count"], 25)
            self.assertEqual(payload["selected_count"], 10)
            selected = [row for row in payload["rankings"] if row["selected"]]
            for fold in range(1, 6):
                fold_rows = [row for row in selected if row["fold"] == fold]
                self.assertEqual([row["seed_index"] for row in fold_rows], [2, 3])
            copied = list(
                (output / "selected_generators").glob(
                    "fold_*/rank_*_seed_*_*/final_best_model_state.pt"
                )
            )
            self.assertEqual(len(copied), 10)

    def test_test_metrics_do_not_control_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            results = create_results_fixture(root)
            output = root / "study_output"
            payload = run_selection(results, output, 5, 5, 1, False, False)
            selected = [row for row in payload["rankings"] if row["selected"]]
            self.assertEqual({row["seed_index"] for row in selected}, {2})
            self.assertTrue(all("test_pooled_metrics" not in row for row in selected))
            self.assertFalse(payload["protocol"]["test_metrics_used_for_selection"])

    def test_leakage_flag_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            results = create_results_fixture(root)
            path = (
                results
                / "seed_01_20261101"
                / "fold_01"
                / "training_selection.json"
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["test_subject_used_for_selection"] = True
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "leakage"):
                run_selection(results, root / "output", 5, 5, 2, False, False)


if __name__ == "__main__":
    unittest.main()
