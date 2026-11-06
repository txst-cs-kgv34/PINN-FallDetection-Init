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


if __name__ == "__main__":
    unittest.main()
