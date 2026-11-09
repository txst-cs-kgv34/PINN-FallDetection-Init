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
        testing = Counter(subject for fold in self.config["folds"] for subject in fold["test"])
        self.assertEqual(set(training), subjects)
        self.assertEqual(len(set(validation)), 5)
        self.assertTrue(all(validation[subject] <= 1 for subject in subjects))
        self.assertTrue(all(testing[subject] == 1 for subject in subjects))
        self.assertTrue(
            all(training[subject] == 4 - validation[subject] for subject in subjects)
        )

    def test_grouped_test_order_is_reproducible(self):
        testing = [subject for fold in self.config["folds"] for subject in fold["test"]]
        self.assertEqual(testing, self.config["randomized_subject_order"])

    def test_four_window_context(self):
        model = self.config["model"]
        self.assertEqual(model["context_windows"], 4)
        self.assertAlmostEqual(model["context_window_s"], 0.10)
        self.assertAlmostEqual(model["context_region_s"], 0.40)

    def test_no_physics_ablation_contract(self):
        training = self.config["training"]
        model = self.config["model"]
        self.assertEqual(self.config["model_id"], "B-no-physics")
        self.assertEqual(
            self.config["training_regime"], "direct_no_physics_ablation"
        )
        self.assertFalse(training["use_physics"])
        self.assertEqual(training["physics_weight"], 0.0)
        self.assertEqual(training["data_weight"], 1.0)
        self.assertEqual(training["gain_weight"], 0.0)
        self.assertEqual(training["synthetic_source_weight"], 0.0)
        self.assertEqual(model["controller_semantics"], "physical_gains")
        self.assertEqual(model["latent_width"], 96)
        self.assertEqual(model["context_embedding"], 96)
        self.assertEqual(model["fourier_modes"], 12)

    def test_reference_optimization_settings_are_preserved(self):
        training = self.config["training"]
        self.assertEqual(self.config["seed"], 20261101)
        self.assertEqual(self.config["split_seed"], 220)
        self.assertEqual(training["epochs"], 800)
        self.assertEqual(training["real_batch_size"], 4)
        self.assertAlmostEqual(training["learning_rate"], 0.0005)
        self.assertAlmostEqual(training["weight_decay"], 0.000001)
        self.assertEqual(training["early_stopping_patience"], 100)
        self.assertEqual(training["gradient_clip_norm"], 5.0)


if __name__ == "__main__":
    unittest.main()
