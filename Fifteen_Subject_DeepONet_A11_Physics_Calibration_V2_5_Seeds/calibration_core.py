#!/usr/bin/env python3
"""Physics-calibration helpers layered on the preserved A11 Model B code."""

from __future__ import annotations

import json
import math
import os
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


def baseline_root(config: dict[str, Any]) -> Path:
    override = os.environ.get("A11_BASELINE_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return (Path(config["_root"]) / config["baseline_experiment_root"]).resolve()


def baseline_fold_dir(config: dict[str, Any], seed_label: str, fold_id: int) -> Path:
    return baseline_root(config) / "results" / "no_physics" / "full" / seed_label / f"fold_{fold_id:02d}"


def load_torch_state(path: Path, device):
    import torch

    try:
        return torch.load(path, map_location=device, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=device)


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
    if not mask.any():
        angular = target.new_tensor(0.0)
        horizontal = target.new_tensor(0.0)
    else:
        angular_scale, horizontal_scale = residual_scales(config)
        angular_values = r1[mask] / angular_scale
        horizontal_values = r2[mask] / horizontal_scale
        angular = functional.smooth_l1_loss(angular_values, torch.zeros_like(angular_values))
        horizontal = functional.smooth_l1_loss(horizontal_values, torch.zeros_like(horizontal_values))
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


def require_baseline_fold(config: dict[str, Any], seed_label: str, fold_id: int) -> dict[str, Path]:
    directory = baseline_fold_dir(config, seed_label, fold_id)
    paths = {
        "directory": directory,
        "checkpoint": directory / "final_best_model_state.pt",
        "selection": directory / "training_selection.json",
        "summary": directory / "summary.json",
        "trial_metrics": directory / "test_metrics_by_trial.csv",
        "predictions": directory / "test_predictions",
    }
    missing = [str(path) for name, path in paths.items() if name != "directory" and not path.exists()]
    if missing:
        raise FileNotFoundError("missing completed no-physics baseline files:\n- " + "\n- ".join(missing))
    return paths

