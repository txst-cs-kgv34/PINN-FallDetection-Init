from __future__ import annotations
import json, unittest
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]

class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.config=json.loads((ROOT/"experiment.json").read_text())
    def test_seeds(self): self.assertEqual(self.config["optimization_seeds"],[20261101,20261102,20261103,20261104,20261105])
    def test_frontfall_in_planar(self): self.assertIn("A11",self.config["data"]["planar_activities"])
    def test_every_subject_tested_once(self):
        counts=Counter(subject for fold in self.config["folds"] for subject in fold["test"])
        self.assertEqual(set(counts),set(self.config["subjects"])); self.assertTrue(all(value==1 for value in counts.values()))
    def test_no_fold_leakage(self):
        expected=set(self.config["subjects"])
        for fold in self.config["folds"]:
            train=set(fold["train"]); validation={fold["validation"]}; test=set(fold["test"])
            self.assertFalse(train&validation or train&test or validation&test); self.assertEqual(train|validation|test,expected)
    def test_model_b_constants(self):
        self.assertEqual(self.config["model"]["latent_width"],96); self.assertEqual(self.config["model"]["fourier_modes"],12)
        self.assertAlmostEqual(self.config["model"]["context_region_s"],.40); self.assertAlmostEqual(self.config["training"]["cartpole_physics_weight"],0.0)
        self.assertAlmostEqual(self.config["physics"]["fixed_tau_s"],.23); self.assertAlmostEqual(self.config["physics"]["fixed_pi_rad"],.0635)

if __name__=="__main__": unittest.main()
