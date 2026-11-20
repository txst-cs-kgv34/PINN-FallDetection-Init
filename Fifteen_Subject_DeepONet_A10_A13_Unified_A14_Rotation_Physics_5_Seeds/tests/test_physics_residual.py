from __future__ import annotations
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class PhysicsResidualTests(unittest.TestCase):
    def setUp(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch unavailable")
        import sys
        sys.path.insert(0,str(ROOT))
        from operator_core import load_config,physics_residual_components
        self.torch=torch; self.config=load_config(ROOT/"experiment.json"); self.physics_residual_components=physics_residual_components
    def test_planar_residual_shape_and_mask(self):
        torch=self.torch; time=torch.linspace(0,1,101).repeat(2,1); prediction=torch.zeros(2,101,2); gains=torch.ones(2,4); mask=torch.ones(2,101)
        r1,r2,ryaw,valid=self.physics_residual_components(prediction,gains,time,torch.tensor([60.,80.]),torch.tensor([1.6,1.8]),self.config["physics"],mask,"planar")
        self.assertEqual(r1.shape,prediction[:,:,0].shape); self.assertTrue(valid.any()); self.assertTrue(torch.allclose(r1[valid],torch.zeros_like(r1[valid]))); self.assertTrue(torch.allclose(r2[valid],torch.zeros_like(r2[valid])))
    def test_rotation_adds_finite_yaw_residual(self):
        torch=self.torch; time=torch.linspace(0,1,101).repeat(1,1); prediction=torch.zeros(1,101,3); gains=torch.ones(1,6); mask=torch.ones(1,101)
        _,_,ryaw,valid=self.physics_residual_components(prediction,gains,time,torch.tensor([70.]),torch.tensor([1.7]),self.config["physics"],mask,"rotation")
        self.assertTrue(torch.isfinite(ryaw[valid]).all())

if __name__=="__main__": unittest.main()
