from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from operator_core import optimization_seeds, seed_spec
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

    def test_five_distinct_optimization_seeds(self):
        seeds = optimization_seeds(self.config)
        self.assertEqual(seeds, [20261101, 20261102, 20261103, 20261104, 20261105])
        labels = [seed_spec(self.config, index)[1] for index in range(1, 6)]
        self.assertEqual(len(labels), len(set(labels)))

    def test_seed_index_is_one_based_and_bounded(self):
        self.assertEqual(seed_spec(self.config, 1), (20261101, "seed_01_20261101"))
        self.assertEqual(seed_spec(self.config, 5), (20261105, "seed_05_20261105"))
        with self.assertRaises(ValueError):
            seed_spec(self.config, 0)
        with self.assertRaises(ValueError):
            seed_spec(self.config, 6)

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
        self.assertEqual(
            self.config["ablation"]["removed_component"],
            "cart_pole_biomechanics_residual",
        )

    def test_reference_optimization_settings_are_preserved(self):
        training = self.config["training"]
        self.assertEqual(self.config["split_seed"], 220)
        self.assertEqual(training["epochs"], 800)
        self.assertEqual(training["real_batch_size"], 4)
        self.assertAlmostEqual(training["learning_rate"], 0.0005)
        self.assertAlmostEqual(training["weight_decay"], 0.000001)
        self.assertEqual(training["early_stopping_patience"], 100)
        self.assertEqual(training["gradient_clip_norm"], 5.0)


if __name__ == "__main__":
    unittest.main()
