#!/usr/bin/env python3
"""Matched calibration helpers for four activity-specific CartPole heads."""

from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
from typing import Any, Iterable

from operator_core import (
    ROOT,
    infer,
    masked_normalized_mse,
    physics_residual_components,
    trajectory_target,
)


def candidate_weights(config: dict[str, Any], include_baseline: bool = False) -> list[float]:
    values = [float(value) for value in config["calibration"]["candidate_weights"]]
    if not values or any(value <= 0.0 for value in values):
        raise ValueError("candidate physics weights must be positive")
    if values != sorted(set(values)):
        raise ValueError("candidate physics weights must be unique and increasing")
    return ([float(config["calibration"]["baseline_weight"])] if include_baseline else []) + values


def weight_label(weight: float) -> str:
    if math.isclose(weight, 0.0, abs_tol=1e-15):
        return "lambda_0"
    return "lambda_" + f"{weight:.0e}".replace("+", "").replace("e-0", "e-")


def load_torch_state(path: Path, device):
    import torch

    try:
        return torch.load(path, map_location=device, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=device)


def model_state_sha256(model) -> str:
    """Stable digest used to prove that all lambda arms share initialization."""
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        array = value.detach().cpu().contiguous().numpy()
        digest.update(name.encode("utf-8"))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(str(array.shape).encode("ascii"))
        digest.update(array.tobytes())
    return digest.hexdigest()


def residual_scales(config: dict[str, Any]) -> tuple[float, float]:
    """Return physically anchored scales for the two acceleration residuals."""
    physics = config["physics"]
    gravity = float(physics["gravity_m_s2"])
    length = float(physics["stick_length_m"])
    if gravity <= 0.0 or length <= 0.0:
        raise ValueError("gravity and stick length must be positive")
    return gravity / length, gravity


def calibrated_losses(
    model,
    batch: dict[str, Any],
    config: dict[str, Any],
    current_weight: float,
) -> dict[str, Any]:
    """Forecast loss plus separately nondimensionalized CartPole residuals."""
    import torch
    import torch.nn.functional as functional

    prediction, controller, log_variance = infer(model, batch, config, "planar")
    target = trajectory_target(batch, "planar")
    data = masked_normalized_mse(
        prediction,
        target,
        batch["valid_mask"],
        batch["time_s"],
        config,
        "planar",
        True,
        batch["activity_vector"],
    )
    r1, r2, _, mask = physics_residual_components(
        prediction,
        controller * model.gain_scale,
        batch["time_s"],
        batch["mass_kg"],
        batch["height_m"],
        config["physics"],
        batch["physics_mask"],
        "planar",
    )
    angular_scale, horizontal_scale = residual_scales(config)
    activity_index = batch["activity_vector"].argmax(dim=1)
    angular_by_head = []
    horizontal_by_head = []
    head_diagnostics = {
        f"{activity.lower()}_physics": target.new_tensor(float("nan"))
        for activity in config["data"]["activities"]
    }
    for head_index in range(batch["activity_vector"].shape[1]):
        head_rows = activity_index == head_index
        head_mask = mask & head_rows[:, None]
        if not head_mask.any():
            continue
        angular_values = r1[head_mask] / angular_scale
        horizontal_values = r2[head_mask] / horizontal_scale
        head_angular = functional.smooth_l1_loss(
            angular_values, torch.zeros_like(angular_values)
        )
        head_horizontal = functional.smooth_l1_loss(
            horizontal_values, torch.zeros_like(horizontal_values)
        )
        angular_by_head.append(head_angular)
        horizontal_by_head.append(head_horizontal)
        activity = config["data"]["activities"][head_index]
        head_diagnostics[f"{activity.lower()}_physics"] = head_angular + head_horizontal
    if not angular_by_head:
        angular = target.new_tensor(0.0)
        horizontal = target.new_tensor(0.0)
    else:
        angular = torch.stack(angular_by_head).mean()
        horizontal = torch.stack(horizontal_by_head).mean()
    physics = angular + horizontal
    total = float(config["training"]["data_weight"]) * data + float(current_weight) * physics
    return {
        "total": total,
        "data": data,
        "cartpole_physics": physics,
        "angular_physics": angular,
        "horizontal_physics": horizontal,
        "prediction": prediction,
        "controller": controller,
        "controller_logvar": log_variance,
        **head_diagnostics,
    }


def ramped_weight(target_weight: float, completed_epoch: int, ramp_epochs: int) -> float:
    if target_weight < 0.0:
        raise ValueError("target weight cannot be negative")
    if ramp_epochs <= 0:
        return float(target_weight)
    fraction = min(1.0, max(0.0, float(completed_epoch) / float(ramp_epochs)))
    return float(target_weight) * fraction


def gradient_l2_norm(loss, parameters: Iterable) -> float:
    """Measure one loss gradient without changing accumulated parameter gradients."""
    import torch

    active = [parameter for parameter in parameters if parameter.requires_grad]
    gradients = torch.autograd.grad(loss, active, retain_graph=True, allow_unused=True)
    squared = loss.new_tensor(0.0)
    for gradient in gradients:
        if gradient is not None:
            squared = squared + gradient.detach().square().sum()
    return float(torch.sqrt(squared).cpu())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))



