from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from validate_setup import validate_protocol


ROOT = Path(__file__).resolve().parents[1]


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "experiment.json").read_text(encoding="utf-8"))

    def test_protocol(self):
        self.assertEqual(validate_protocol(self.config), [])

    def test_balanced_subject_roles(self):
        subjects = {item["id"] for item in self.config["subjects"]}
        training = Counter(subject for fold in self.config["folds"] for subject in fold["train"])
        validation = Counter(fold["validation"] for fold in self.config["folds"])
        testing = Counter(fold["test"] for fold in self.config["folds"])
        self.assertEqual(set(training), subjects)
        self.assertTrue(all(training[subject] == 3 for subject in subjects))
        self.assertTrue(all(validation[subject] == 1 for subject in subjects))
        self.assertTrue(all(testing[subject] == 1 for subject in subjects))

    def test_four_window_context(self):
        model = self.config["model"]
        self.assertEqual(model["context_windows"], 4)
        self.assertAlmostEqual(model["context_window_s"], 0.10)
        self.assertAlmostEqual(model["context_region_s"], 0.40)

    def test_matched_b_no_physics_ablation(self):
        self.assertEqual(self.config["training_regime"], "direct_no_physics")
        self.assertEqual(self.config["training_sources"], ["real"])
        self.assertFalse(self.config["requires_teachers"])
        self.assertEqual(
            self.config["model"]["controller_semantics"], "physical_gains"
        )
        self.assertFalse(self.config["training"]["use_physics"])
        self.assertEqual(self.config["training"]["physics_weight"], 0.0)


if __name__ == "__main__":
    unittest.main()
