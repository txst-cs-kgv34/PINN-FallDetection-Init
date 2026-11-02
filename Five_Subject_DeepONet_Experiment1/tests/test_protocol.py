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

    def test_balanced_protocol(self):
        self.assertEqual(validate_protocol(self.config), [])

    def test_each_subject_is_tested_and_validated_once(self):
        validation = Counter(fold["validation"] for fold in self.config["folds"])
        test = Counter(fold["test"] for fold in self.config["folds"])
        subjects = {item["id"] for item in self.config["subjects"]}
        self.assertEqual(set(validation), subjects)
        self.assertEqual(set(test), subjects)
        self.assertTrue(all(validation[subject] == 1 for subject in subjects))
        self.assertTrue(all(test[subject] == 1 for subject in subjects))

    def test_primary_teacher_choices(self):
        choices = {item["id"]: item["selected_chunk"] for item in self.config["subjects"]}
        self.assertEqual(choices, {"S43": 1, "S63": 6, "S55": 5, "S57": 9, "S62": 1})

    def test_four_window_context(self):
        model = self.config["model"]
        self.assertEqual(model["context_windows"], 4)
        self.assertAlmostEqual(model["context_region_s"], 0.40)
        self.assertAlmostEqual(model["context_window_s"], 0.10)


if __name__ == "__main__":
    unittest.main()
