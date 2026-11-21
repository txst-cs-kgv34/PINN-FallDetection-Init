from __future__ import annotations
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ModelShapeTests(unittest.TestCase):
    def setUp(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch unavailable")
        import sys
        sys.path.insert(0,str(ROOT))
        from operator_core import create_model,load_config
        self.torch=torch; self.config=load_config(ROOT/"experiment.json"); self.create_model=create_model
    def run_group(self,group,outputs,gains,channels):
        torch=self.torch; model=self.create_model(self.config,group); batch=2; points=11
        contexts=torch.zeros(batch,4,points,channels); mask=torch.ones(batch,4); demographics=torch.ones(batch,2); activity=torch.zeros(batch,4); direction=torch.tensor([[1.,0.],[0.,1.]])
        controller,_=model.infer_controller(contexts,mask,demographics,activity,direction); self.assertEqual(tuple(controller.shape),(batch,gains))
        initial=torch.zeros(batch,outputs*2); auxiliary=torch.ones(batch,2); time=torch.linspace(0,1,101).repeat(batch,1)
        prediction=model.forward_operator(controller,initial,demographics,activity,direction,auxiliary,time); self.assertEqual(tuple(prediction.shape),(batch,101,outputs))
    def test_a11_planar(self): self.run_group("planar",2,4,5)

if __name__ == "__main__":
    unittest.main()
