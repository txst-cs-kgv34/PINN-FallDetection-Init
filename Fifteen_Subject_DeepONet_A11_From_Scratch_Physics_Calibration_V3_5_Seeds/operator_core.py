#!/usr/bin/env python3
"""Shared data, DeepONet, and physics utilities for planar and A14 models."""

from __future__ import annotations

import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parent
PLANAR_GAIN_NAMES = ("kp_theta", "kd_theta", "kp_x", "kd_x")
ROTATION_GAIN_NAMES = PLANAR_GAIN_NAMES + ("kp_yaw", "kd_yaw")
BASE_METRICS = (
    "normalized_mse", "theta_rmse_deg", "theta_mae_deg", "x_rmse_cm",
    "x_mae_cm", "theta_w1_deg", "x_w1_cm",
)
YAW_METRICS = ("yaw_rmse_deg", "yaw_mae_deg", "yaw_w1_deg")


def load_config(path: str | Path = "experiment.json") -> dict[str, Any]:
    config_path = Path(path).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["_config_path"] = str(config_path)
    config["_root"] = str(config_path.parent)
    return config


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if hasattr(torch.backends, "cudnn"):
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
        try:
            torch.use_deterministic_algorithms(True, warn_only=True)
        except TypeError:
            torch.use_deterministic_algorithms(True)
    except ImportError:
        pass


def optimization_seeds(config: dict[str, Any]) -> list[int]:
    seeds = [int(value) for value in config["optimization_seeds"]]
    if len(seeds) != 5 or len(seeds) != len(set(seeds)):
        raise ValueError("exactly five distinct optimization seeds are required")
    return seeds


def seed_spec(config: dict[str, Any], seed_index: int) -> tuple[int, str]:
    seeds = optimization_seeds(config)
    if seed_index < 1 or seed_index > len(seeds):
        raise ValueError(f"seed_index must be between 1 and {len(seeds)}")
    value = seeds[seed_index - 1]
    return value, f"seed_{seed_index:02d}_{value}"


def choose_torch_device(requested: str):
    import torch
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if requested == "mps" and not (
        torch.backends.mps.is_available() and torch.backends.mps.is_built()
    ):
        raise RuntimeError("MPS requested but unavailable")
    if requested != "auto":
        device = torch.device(requested)
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"DeepONet device: {device}")
    return device


def fold_by_id(config: dict[str, Any], fold_id: int) -> dict[str, Any]:
    for fold in config["folds"]:
        if int(fold["id"]) == int(fold_id):
            return fold
    raise KeyError(f"unknown fold {fold_id}")


def metric_names(model_group: str) -> tuple[str, ...]:
    return BASE_METRICS + (YAW_METRICS if model_group == "rotation" else ())


@dataclass(frozen=True)
class RealRecord:
    subject: str
    trial: str
    activity: str
    model_group: str
    time_s: np.ndarray
    theta_rad: np.ndarray
    x_m: np.ndarray
    yaw_rad: np.ndarray
    valid_mask: np.ndarray
    physics_mask: np.ndarray
    initial_state: np.ndarray
    demographics: np.ndarray
    mass_kg: float
    height_m: float
    fall_direction: np.ndarray
    activity_vector: np.ndarray


def load_real_records(mode: str, model_group: str) -> list[RealRecord]:
    data_dir = ROOT / "outputs" / f"real_data_{mode}"
    manifest_path = data_dir / f"{model_group}_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing {manifest_path}; run prepare first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = []
    for item in manifest["included_trials"]:
        with np.load(data_dir / model_group / item["data_file"], allow_pickle=False) as data:
            records.append(RealRecord(
                subject=item["subject"], trial=item["trial"], activity=item["activity"],
                model_group=model_group, time_s=data["time_s"].astype(np.float32),
                theta_rad=data["theta_rad"].astype(np.float32),
                x_m=data["x_m"].astype(np.float32), yaw_rad=data["yaw_rad"].astype(np.float32),
                valid_mask=data["valid_mask"].astype(np.float32),
                physics_mask=data["physics_mask"].astype(np.float32),
                initial_state=data["initial_state"].astype(np.float32),
                demographics=data["demographics"].astype(np.float32),
                mass_kg=float(data["mass_kg"]), height_m=float(data["height_m"]),
                fall_direction=data["fall_direction"].astype(np.float32),
                activity_vector=data["activity_vector"].astype(np.float32),
            ))
    return records


class TrajectoryDataset:
    def __init__(self, records: list[RealRecord]):
        if not records:
            raise ValueError("trajectory dataset cannot be empty")
        self.records = records

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        import torch
        record = self.records[index]
        return {
            "subject": record.subject, "trial": record.trial, "activity": record.activity,
            "time_s": torch.as_tensor(record.time_s), "theta_rad": torch.as_tensor(record.theta_rad),
            "x_m": torch.as_tensor(record.x_m), "yaw_rad": torch.as_tensor(record.yaw_rad),
            "valid_mask": torch.as_tensor(record.valid_mask),
            "physics_mask": torch.as_tensor(record.physics_mask),
            "initial_state": torch.as_tensor(record.initial_state),
            "demographics": torch.as_tensor(record.demographics),
            "mass_kg": torch.as_tensor(record.mass_kg, dtype=torch.float32),
            "height_m": torch.as_tensor(record.height_m, dtype=torch.float32),
            "fall_direction": torch.as_tensor(record.fall_direction),
            "activity_vector": torch.as_tensor(record.activity_vector),
        }


def build_dataset(records: list[RealRecord], subjects: list[str] | str, limit_per_subject: int | None = None) -> TrajectoryDataset:
    selected = {subjects} if isinstance(subjects, str) else set(subjects)
    counts: Counter[str] = Counter()
    output = []
    for record in records:
        if record.subject not in selected:
            continue
        if limit_per_subject is not None and counts[record.subject] >= limit_per_subject:
            continue
        counts[record.subject] += 1
        output.append(record)
    if not output:
        raise ValueError(f"no eligible trajectories for requested subjects {sorted(selected)}")
    return TrajectoryDataset(output)


def build_context_windows(batch: dict[str, Any], config: dict[str, Any], model_group: str):
    import torch
    theta, x, time_s = batch["theta_rad"], batch["x_m"], batch["time_s"]
    yaw = batch["yaw_rad"]
    model_cfg = config["model"]
    windows = int(model_cfg["context_windows"])
    dt = float(torch.median(time_s[0, 1:] - time_s[0, :-1]).detach().cpu())
    points = int(round(float(model_cfg["context_window_s"]) / dt)) + 1
    region = int(round(float(model_cfg["context_region_s"]) / dt)) + 1
    starts = torch.linspace(0, region - points, windows, device=theta.device).round().long()
    theta_dot = torch.gradient(theta, spacing=dt, dim=1)[0]
    x_dot = torch.gradient(x, spacing=dt, dim=1)[0]
    yaw_dot = torch.gradient(yaw, spacing=dt, dim=1)[0]
    channels = 5 if model_group == "planar" else 7
    context = torch.zeros((theta.shape[0], windows, points, channels), dtype=theta.dtype, device=theta.device)
    local_time = torch.linspace(0.0, 1.0, points, device=theta.device)
    for slot, start_value in enumerate(starts):
        start = int(start_value.item()); stop = start + points
        values = [
            theta[:, start:stop] / float(model_cfg["theta_scale_rad"]),
            x[:, start:stop] / float(model_cfg["x_scale_m"]),
            theta_dot[:, start:stop], x_dot[:, start:stop] / 0.25,
        ]
        if model_group == "rotation":
            values.extend([
                yaw[:, start:stop] / float(model_cfg["yaw_scale_rad"]),
                yaw_dot[:, start:stop],
            ])
        values.append(local_time.expand(theta.shape[0], -1))
        context[:, slot] = torch.stack(values, dim=2)
    mask = torch.ones((theta.shape[0], windows), dtype=theta.dtype, device=theta.device)
    return context, mask


def create_model(config: dict[str, Any], model_group: str):
    """Model B architecture extended only by activity/direction and A14 yaw."""
    import torch
    import torch.nn.functional as functional
    from torch import nn

    cfg = config["model"]
    latent = int(cfg["latent_width"]); embedding = int(cfg["context_embedding"])
    modes = int(cfg["fourier_modes"]); activity_count = int(cfg["activity_count"])
    output_width = 2 if model_group == "planar" else 3
    gain_scale_values = list(cfg["cartpole_gain_scale"])
    if model_group == "rotation":
        gain_scale_values += list(cfg["rotation_gain_scale"])
    gain_scale = torch.tensor(gain_scale_values, dtype=torch.float32)
    gain_count = len(gain_scale_values)
    initial_count = output_width * 2
    context_channels = 5 if model_group == "planar" else 7
    scales = [float(cfg["theta_scale_rad"]), float(cfg["x_scale_m"])]
    if model_group == "rotation": scales.append(float(cfg["yaw_scale_rad"]))
    horizon = float(config["data"]["horizon_s"])

    class MLP(nn.Module):
        def __init__(self, inputs: int, hidden: int, outputs: int):
            super().__init__()
            self.network = nn.Sequential(nn.Linear(inputs, hidden), nn.GELU(), nn.Linear(hidden, hidden), nn.GELU(), nn.Linear(hidden, outputs))
        def forward(self, value): return self.network(value)

    class UnifiedOperator(nn.Module):
        def __init__(self):
            super().__init__()
            self.context_conv = nn.Sequential(
                nn.Conv1d(context_channels, 32, 5, padding=2), nn.GELU(),
                nn.Conv1d(32, 64, 5, padding=2), nn.GELU(), nn.AdaptiveAvgPool1d(1),
            )
            self.context_projection = nn.Linear(64, embedding)
            condition_count = 2 + activity_count + 2
            self.controller_head = MLP(embedding + condition_count, 128, 2 * gain_count)
            branch_inputs = gain_count + initial_count + condition_count + 2
            self.branch = MLP(branch_inputs, 160, output_width * latent)
            self.trunk = MLP(1 + 2 * modes, 160, latent)
            self.register_buffer("gain_scale", gain_scale)
            self.register_buffer("output_scales", torch.tensor(scales, dtype=torch.float32))
            self.model_group = model_group
            self.output_width = output_width

        def conditions(self, demographics, activity_vector, fall_direction):
            return torch.cat([demographics, activity_vector, fall_direction], dim=1)

        def encode_context(self, contexts, mask):
            batch, windows, points, channels = contexts.shape
            flat = contexts.reshape(batch * windows, points, channels).transpose(1, 2)
            features = self.context_projection(self.context_conv(flat).squeeze(-1)).reshape(batch, windows, -1)
            return (features * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True).clamp_min(1.0)

        def infer_controller(self, contexts, mask, demographics, activity_vector, fall_direction):
            encoded = self.encode_context(contexts, mask)
            output = self.controller_head(torch.cat([encoded, self.conditions(demographics, activity_vector, fall_direction)], dim=1))
            return functional.softplus(output[:, :gain_count]), output[:, gain_count:].clamp(-6.0, 3.0)

        def forward_operator(self, controller, initial_state, demographics, activity_vector, fall_direction, auxiliary, time_s):
            condition = self.conditions(demographics, activity_vector, fall_direction)
            branch_input = torch.cat([controller, initial_state, condition, auxiliary], dim=1)
            branch = self.branch(branch_input).reshape(-1, output_width, latent)
            normalized = time_s[0] / horizon
            mode = torch.arange(1, modes + 1, device=time_s.device, dtype=time_s.dtype).reshape(1, -1)
            phase = 2.0 * math.pi * normalized.reshape(-1, 1) * mode
            trunk = self.trunk(torch.cat([normalized.reshape(-1, 1), torch.sin(phase), torch.cos(phase)], dim=1))
            raw = torch.einsum("bop,tp->bto", branch, trunk) / math.sqrt(latent)
            time = time_s[:, :, None]
            q0 = initial_state[:, :output_width, None].transpose(1, 2)
            qdot0 = initial_state[:, output_width:, None].transpose(1, 2)
            return q0 + qdot0 * time + time.square() * self.output_scales * raw

    return UnifiedOperator()


def trajectory_target(batch: dict[str, Any], model_group: str):
    import torch
    values = [batch["theta_rad"], batch["x_m"]]
    if model_group == "rotation": values.append(batch["yaw_rad"])
    return torch.stack(values, dim=2)


def masked_normalized_mse(prediction, target, valid_mask, time_s, config, model_group: str, forecast_only: bool):
    import torch
    scales = [float(config["model"]["theta_scale_rad"]), float(config["model"]["x_scale_m"])]
    if model_group == "rotation": scales.append(float(config["model"]["yaw_scale_rad"]))
    scale = torch.tensor(scales, device=prediction.device, dtype=prediction.dtype)
    mask = valid_mask
    if forecast_only:
        mask = mask * (time_s >= float(config["model"]["context_region_s"])).to(mask.dtype)
    point_error = ((prediction - target) / scale).square().sum(dim=2)
    return ((point_error * mask).sum(1) / mask.sum(1).clamp_min(1.0)).mean()


def controller_force_from_delayed_state(gains, theta, theta_dot, x, x_dot, pi_rad, sharpness: float):
    import torch
    gate = torch.sigmoid(float(sharpness) * (torch.abs(theta) - pi_rad))
    return gains[..., 0] * gate * theta + gains[..., 1] * theta_dot + gains[..., 2] * x + gains[..., 3] * x_dot


def physics_residual_components(prediction, gains, time_s, mass_kg, height_m, physics, valid_mask=None, model_group: str = "planar"):
    """Exact Model B delayed CartPole residual plus the A14 yaw residual."""
    import torch
    theta, x = prediction[:, :, 0], prediction[:, :, 1]
    dt = float(torch.median(time_s[0, 1:] - time_s[0, :-1]).detach().cpu())
    theta_dot = torch.gradient(theta, spacing=dt, dim=1)[0]
    x_dot = torch.gradient(x, spacing=dt, dim=1)[0]
    theta_ddot = (theta[:, 2:] - 2 * theta[:, 1:-1] + theta[:, :-2]) / (dt * dt)
    x_ddot = (x[:, 2:] - 2 * x[:, 1:-1] + x[:, :-2]) / (dt * dt)
    tau = float(physics["fixed_tau_s"]); delay_steps = int(round(tau / dt))
    start = max(1, delay_steps + 1); stop = theta.shape[1] - 1
    r1 = torch.full_like(theta, torch.nan); r2 = torch.full_like(x, torch.nan)
    ryaw = torch.full_like(theta, torch.nan); residual_mask = torch.zeros_like(theta, dtype=torch.bool)
    if stop <= start: return r1, r2, ryaw, residual_mask
    current = torch.arange(start, stop, device=prediction.device); delayed = current - delay_steps
    keep_all = torch.ones((prediction.shape[0], len(current)), dtype=torch.bool, device=prediction.device)
    if valid_mask is not None:
        valid = valid_mask > 0.5
        keep_all = valid[:, current - 1] & valid[:, current] & valid[:, current + 1] & valid[:, delayed]
    m = float(physics["stick_mass_kg"]); m0 = float(physics["effective_cart_mass_kg"])
    length = float(physics["stick_length_m"]); gravity = float(physics["gravity_m_s2"])
    mass11 = (1.0 / 3.0) * m * length * length; mass22 = m + m0
    pi_rad = prediction.new_full((prediction.shape[0],), float(physics["fixed_pi_rad"]))
    for row in range(prediction.shape[0]):
        keep = keep_all[row]
        if not torch.any(keep): continue
        c = current[keep]; d = delayed[keep]; a = c - 1
        force = controller_force_from_delayed_state(
            gains[row, :4].expand(len(c), -1), theta[row, d], theta_dot[row, d], x[row, d], x_dot[row, d],
            pi_rad[row], float(physics["deadzone_sharpness"]),
        )
        cross = 0.5 * m * length * torch.cos(theta[row, c])
        r1[row, c] = (mass11 * theta_ddot[row, a] + cross * x_ddot[row, a] - 0.5 * m * gravity * length * torch.sin(theta[row, c])) / mass11
        r2[row, c] = (cross * theta_ddot[row, a] + mass22 * x_ddot[row, a] - 0.5 * m * length * theta_dot[row, c].square() * torch.sin(theta[row, c]) - force) / mass22
        if model_group == "rotation":
            yaw = prediction[:, :, 2]
            yaw_dot = torch.gradient(yaw, spacing=dt, dim=1)[0]
            yaw_ddot = (yaw[:, 2:] - 2 * yaw[:, 1:-1] + yaw[:, :-2]) / (dt * dt)
            inertia = float(physics["yaw_inertia_mass_height2_fraction"]) * mass_kg[row] * height_m[row].square()
            yaw_torque = gains[row, 4] * yaw[row, d] + gains[row, 5] * yaw_dot[row, d]
            ryaw[row, c] = yaw_ddot[row, a] - yaw_torque / inertia.clamp_min(1e-4)
        residual_mask[row, c] = True
    return r1, r2, ryaw, residual_mask


def physics_losses(prediction, gains, batch, config, model_group: str):
    import torch
    import torch.nn.functional as functional
    r1, r2, ryaw, mask = physics_residual_components(
        prediction, gains, batch["time_s"], batch["mass_kg"], batch["height_m"],
        config["physics"], batch["physics_mask"], model_group,
    )
    zero = prediction.new_tensor(0.0)
    if not mask.any(): return zero, zero, (r1, r2, ryaw, mask)
    cartpole = functional.smooth_l1_loss(r1[mask], torch.zeros_like(r1[mask])) + functional.smooth_l1_loss(r2[mask], torch.zeros_like(r2[mask]))
    rotation = zero
    if model_group == "rotation":
        rotation = functional.smooth_l1_loss(ryaw[mask], torch.zeros_like(ryaw[mask]))
    return cartpole, rotation, (r1, r2, ryaw, mask)


def infer(model, batch, config, model_group: str):
    contexts, context_mask = build_context_windows(batch, config, model_group)
    controller, log_variance = model.infer_controller(
        contexts, context_mask, batch["demographics"], batch["activity_vector"], batch["fall_direction"]
    )
    auxiliary = torch_auxiliary(batch, config)
    prediction = model.forward_operator(
        controller, batch["initial_state"], batch["demographics"], batch["activity_vector"],
        batch["fall_direction"], auxiliary, batch["time_s"],
    )
    return prediction, controller, log_variance


def torch_auxiliary(batch, config):
    import torch
    pi = float(config["physics"]["fixed_pi_rad"]) / math.radians(4.0)
    tau = float(config["physics"]["fixed_tau_s"]) / 0.23
    return torch.tensor([pi, tau], dtype=batch["time_s"].dtype, device=batch["time_s"].device).expand(batch["time_s"].shape[0], -1)


def real_losses(model, batch, config, model_group: str, include_physics: bool):
    prediction, controller, log_variance = infer(model, batch, config, model_group)
    target = trajectory_target(batch, model_group)
    data = masked_normalized_mse(prediction, target, batch["valid_mask"], batch["time_s"], config, model_group, True)
    cartpole = target.new_tensor(0.0); rotation = target.new_tensor(0.0)
    if include_physics and bool(config["training"]["use_physics"]):
        cartpole, rotation, _ = physics_losses(prediction, controller * model.gain_scale, batch, config, model_group)
    settings = config["training"]
    total = float(settings["data_weight"]) * data + float(settings["cartpole_physics_weight"]) * cartpole
    if model_group == "rotation": total = total + float(settings["rotation_physics_weight"]) * rotation
    return {"total": total, "data": data, "cartpole_physics": cartpole, "rotation_physics": rotation, "prediction": prediction, "controller": controller, "controller_logvar": log_variance}


def batch_to_device(batch: dict[str, Any], device) -> dict[str, Any]:
    return {key: value.to(device) if hasattr(value, "to") else value for key, value in batch.items()}


def iter_batches(dataset: TrajectoryDataset, batch_size: int, shuffle: bool, seed: int, balance: str = "none") -> Iterable[dict[str, Any]]:
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler
    generator = torch.Generator(); generator.manual_seed(seed)
    if shuffle and balance == "subject_activity":
        counts = Counter((r.subject, r.activity) for r in dataset.records)
        weights = torch.tensor([1.0 / counts[(r.subject, r.activity)] for r in dataset.records], dtype=torch.double)
        sampler = WeightedRandomSampler(weights, len(weights), replacement=True, generator=generator)
        return DataLoader(dataset, batch_size=batch_size, sampler=sampler, num_workers=0)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=0, generator=generator)
