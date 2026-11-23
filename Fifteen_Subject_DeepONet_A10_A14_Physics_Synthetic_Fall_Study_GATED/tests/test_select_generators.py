from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from select_generators import run_selection
from tests.fixture_factory import create_fixture


class GeneratorSelectionTests(unittest.TestCase):
    def test_top_two_direct_physics_models_are_selected_per_group_fold(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_file, config = create_fixture(root)
            payload = run_selection(
                config_file, config, root / "selection", None, None, True, False
            )
            self.assertEqual(payload["selected_count"], 20)
            self.assertEqual(payload["groups"]["planar"]["candidate_count"], 15)
            self.assertEqual(payload["groups"]["rotation"]["candidate_count"], 10)
            copied = list(
                (root / "selection/selected_generators").glob(
                    "*/fold_*/rank_*/final_best_model_state.pt"
                )
            )
            self.assertEqual(len(copied), 20)
            self.assertTrue(
                all(float(row["physics_weight"]) > 0 for row in payload["materialized_generators"])
            )

    def test_planar_test_access_flag_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_file, config = create_fixture(root)
            manifest = next(
                (root / "planar/results/candidates/full").glob(
                    "lambda_*/seed_*/fold_*/candidate_manifest.json"
                )
            )
            payload = json.loads(manifest.read_text())
            payload["test_data_accessed"] = True
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "test data"):
                run_selection(
                    config_file, config, root / "selection", None, None, False, False
                )


if __name__ == "__main__":
    unittest.main()

