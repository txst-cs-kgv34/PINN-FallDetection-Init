from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import torch
except ImportError:  # Allows protocol-only verification before dependencies are installed.
    torch = None

from operator_core import (
    controller_force_from_delayed_state,
    create_model,
    physics_residual_components,
    physics_residual_loss,
    real_losses,
)


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

    def test_controller_force_sign_convention(self):
        gains = torch.tensor([[2.0, 3.0, 4.0, 5.0]])
        zero = torch.zeros(1)
        positive_angle_force = controller_force_from_delayed_state(
            gains, torch.tensor([0.10]), zero, zero, zero, torch.tensor(0.0), 50.0
        )
        negative_angle_force = controller_force_from_delayed_state(
            gains, torch.tensor([-0.10]), zero, zero, zero, torch.tensor(0.0), 50.0
        )
        positive_x_force = controller_force_from_delayed_state(
            gains, zero, zero, torch.tensor([0.10]), zero, torch.tensor(0.0), 50.0
        )
        self.assertGreater(float(positive_angle_force), 0.0)
        self.assertLess(float(negative_angle_force), 0.0)
        self.assertGreater(float(positive_x_force), 0.0)

    def test_physics_residual_is_finite_and_differentiable(self):
        model = create_model(self.config)
        batch = 2
        samples = 81
        controller = torch.full((batch, 4), 0.6, requires_grad=True)
        initial_state = torch.zeros(batch, 4)
        demographics = torch.ones(batch, 2)
        auxiliary = torch.ones(batch, 2)
        time_s = torch.linspace(0.0, 0.8, samples).repeat(batch, 1)
        prediction = model.forward_operator(
            controller, initial_state, demographics, auxiliary, time_s
        )
        loss = physics_residual_loss(
            prediction,
            controller * model.gain_scale,
            torch.full((batch,), float(self.config["physics"]["fixed_pi_rad"])),
            torch.full((batch,), float(self.config["physics"]["fixed_tau_s"])),
            time_s,
            self.config["physics"],
            torch.ones(batch, samples),
        )
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        self.assertIsNotNone(controller.grad)

    def test_stationary_upright_state_has_zero_residuals(self):
        batch = 1
        samples = 81
        prediction = torch.zeros(batch, samples, 2)
        gains = torch.tensor([[150.0, 18.0, 12.0, 18.0]])
        time_s = torch.linspace(0.0, 0.8, samples).repeat(batch, 1)
        r_theta, r_x, residual_mask = physics_residual_components(
            prediction,
            gains,
            torch.full((batch,), float(self.config["physics"]["fixed_pi_rad"])),
            torch.full((batch,), float(self.config["physics"]["fixed_tau_s"])),
            time_s,
            self.config["physics"],
            torch.ones(batch, samples),
        )
        self.assertTrue(torch.any(residual_mask))
        self.assertTrue(torch.allclose(r_theta[residual_mask], torch.zeros_like(r_theta[residual_mask])))
        self.assertTrue(torch.allclose(r_x[residual_mask], torch.zeros_like(r_x[residual_mask])))

    def test_residual_mask_respects_contact_exclusion(self):
        batch = 1
        samples = 81
        prediction = torch.zeros(batch, samples, 2)
        time_s = torch.linspace(0.0, 0.8, samples).repeat(batch, 1)
        physics_mask = torch.ones(batch, samples)
        physics_mask[:, -4:] = 0.0
        _, _, residual_mask = physics_residual_components(
            prediction,
            torch.ones(batch, 4),
            torch.full((batch,), float(self.config["physics"]["fixed_pi_rad"])),
            torch.full((batch,), float(self.config["physics"]["fixed_tau_s"])),
            time_s,
            self.config["physics"],
            physics_mask,
        )
        self.assertFalse(torch.any(residual_mask[:, -5:]))

    def test_no_physics_total_is_exactly_data_loss(self):
        model = create_model(self.config)
        batch = 2
        samples = 81
        time_s = torch.linspace(0.0, 0.8, samples).repeat(batch, 1)
        zeros = torch.zeros(batch, samples)
        training_batch = {
            "theta_rad": zeros.clone(),
            "x_m": zeros.clone(),
            "time_s": time_s,
            "valid_mask": torch.ones(batch, samples),
            "physics_mask": torch.ones(batch, samples),
            "initial_state": torch.zeros(batch, 4),
            "demographics": torch.ones(batch, 2),
            "auxiliary": torch.ones(batch, 2),
            "pi_rad": torch.full((batch,), float(self.config["physics"]["fixed_pi_rad"])),
            "tau_s": torch.full((batch,), float(self.config["physics"]["fixed_tau_s"])),
        }
        losses = real_losses(model, training_batch, self.config, include_physics=True)
        self.assertEqual(float(losses["physics"]), 0.0)
        self.assertTrue(torch.equal(losses["total"], losses["data"]))


if __name__ == "__main__":
    unittest.main()
