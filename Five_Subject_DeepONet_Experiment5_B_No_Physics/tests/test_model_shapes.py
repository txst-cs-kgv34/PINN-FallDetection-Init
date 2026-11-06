from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import torch
except ImportError:  # Allows protocol-only verification before dependencies are installed.
    torch = None

from operator_core import create_model


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(torch is not None, "PyTorch is not installed")
class ModelShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "experiment.json").read_text(encoding="utf-8"))

    def test_forward_operator_shapes(self):
        model = create_model(self.config)
        batch = 2
        samples = 81
        controller = torch.full((batch, 4), 0.6)
        initial_state = torch.zeros(batch, 4)
        demographics = torch.ones(batch, 2)
        auxiliary = torch.ones(batch, 2)
        time_s = torch.linspace(0.0, 0.8, samples).repeat(batch, 1)
        output = model.forward_operator(
            controller, initial_state, demographics, auxiliary, time_s
        )
        self.assertEqual(tuple(output.shape), (batch, samples, 2))

    def test_controller_head_remains_positive_like_model_b(self):
        model = create_model(self.config)
        batch = 2
        demographics = torch.ones(batch, 2)
        windows = int(self.config["model"]["context_windows"])
        contexts = torch.randn(batch, windows, 11, 5)
        mask = torch.ones(batch, windows)
        controller, _ = model.infer_controller(contexts, mask, demographics)
        self.assertTrue(model.physical_controller)
        self.assertEqual(tuple(controller.shape), (batch, 4))
        self.assertTrue(torch.all(controller > 0.0))


if __name__ == "__main__":
    unittest.main()
