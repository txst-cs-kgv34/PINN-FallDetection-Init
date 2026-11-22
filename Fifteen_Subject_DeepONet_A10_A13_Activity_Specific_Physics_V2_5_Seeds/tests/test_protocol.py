from __future__ import annotations
import json, unittest
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]

class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.config=json.loads((ROOT/"experiment.json").read_text())
    def test_seeds(self): self.assertEqual(self.config["optimization_seeds"],[20261101,20261102,20261103,20261104,20261105])
    def test_a10_a13_scope_and_axes(self):
        self.assertEqual(self.config["data"]["activities"],["A10","A11","A12","A13"])
        self.assertEqual(self.config["data"]["expected_trial_count"],257)
        self.assertEqual(self.config["data"]["expected_by_activity"],{"A10":58,"A11":64,"A12":68,"A13":67})
        self.assertEqual(self.config["data"]["activity_axes_subject_frame_lateral_forward"],{"A10":[0.0,-1.0],"A11":[0.0,1.0],"A12":[-1.0,0.0],"A13":[1.0,0.0]})
    def test_calibration_grid_and_selection(self):
        calibration=self.config["calibration"]
        self.assertEqual(calibration["baseline_weight"],0.0)
        self.assertEqual(calibration["candidate_weights"],[.0001,.001,.01])
        self.assertEqual(calibration["selection_metric"],"validation_subject_activity_balanced_forecast_mse")
        self.assertFalse(calibration["test_access_before_selection"])
        self.assertEqual(calibration["initialization"],"same_deterministic_random_state_within_each_seed_and_fold")
        self.assertEqual(calibration["training_epochs"],800)
        self.assertEqual(calibration["minimum_training_epochs"],calibration["ramp_epochs"])
        self.assertAlmostEqual(calibration["learning_rate"],.0005)
    def test_every_subject_tested_once(self):
        counts=Counter(subject for fold in self.config["folds"] for subject in fold["test"])
        self.assertEqual(set(counts),set(self.config["subjects"])); self.assertTrue(all(value==1 for value in counts.values()))
    def test_no_fold_leakage(self):
        expected=set(self.config["subjects"])
        for fold in self.config["folds"]:
            train=set(fold["train"]); validation=set(fold["validation"]); test=set(fold["test"])
            self.assertEqual((len(train),len(validation),len(test)),(10,2,3))
            self.assertFalse(train&validation or train&test or validation&test); self.assertEqual(train|validation|test,expected)
    def test_model_b_constants(self):
        self.assertEqual(self.config["model"]["latent_width"],96); self.assertEqual(self.config["model"]["fourier_modes"],12)
        self.assertAlmostEqual(self.config["model"]["context_region_s"],.40)
        self.assertEqual(self.config["model"]["controller_semantics"],"four_activity_specific_cartpole_gain_heads")
        self.assertAlmostEqual(self.config["physics"]["fixed_tau_s"],.23); self.assertAlmostEqual(self.config["physics"]["fixed_pi_rad"],.0635)

if __name__ == "__main__":
    unittest.main()
