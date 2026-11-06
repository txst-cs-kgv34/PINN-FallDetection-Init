#!/usr/bin/env python3
"""Shared data, model, loss, and protocol utilities for Experiments 2–4."""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parent
GAIN_NAMES = ("kp_theta", "kd_theta", "kp_x", "kd_x")
METRICS = (
    "normalized_mse",
    "theta_rmse_deg",
    "theta_mae_deg",
    "x_rmse_cm",
    "x_mae_cm",
    "theta_w1_deg",
    "x_w1_cm",
)


def load_config(path: str | Path = "experiment.json") -> dict[str, Any]:
    config_path = Path(path).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["_config_path"] = str(config_path)
    config["_root"] = str(config_path.parent)
    return config


def resolve_path(config: dict[str, Any], value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(config["_root"]) / path
    return path.resolve()


def resolve_glob(config: dict[str, Any], pattern: str) -> list[Path]:
    path = Path(pattern).expanduser()
    if not path.is_absolute():
        path = Path(config["_root"]) / path
    return sorted(path.parent.resolve().glob(path.name))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def choose_torch_device(requested: str):
    import torch

    if requested != "auto":
        device = torch.device(requested)
    elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
        device = torch.device("mps")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    print(f"DeepONet device: {device}")
    return device


def fold_by_id(config: dict[str, Any], fold_id: int) -> dict[str, Any]:
    for fold in config["folds"]:
        if int(fold["id"]) == int(fold_id):
            return fold
    raise KeyError(f"Unknown fold {fold_id}")


@dataclass(frozen=True)
class TeacherRecord:
    teacher_id: str
    subject: str
    mass_kg: float
    height_m: float
    gains: np.ndarray
    pi_rad: float
    tau_s: float
    time_s: np.ndarray
    theta_rad: np.ndarray
    x_m: np.ndarray
    initial_states: np.ndarray


@dataclass(frozen=True)
class RealRecord:
    subject: str
    trial: str
    mass_kg: float
    height_m: float
    time_s: np.ndarray
    theta_rad: np.ndarray
    x_m: np.ndarray
    valid_mask: np.ndarray
    initial_state: np.ndarray
    usable_samples: int
    usable_duration_s: float


def load_teacher_records(mode: str) -> list[TeacherRecord]:
    data_dir = ROOT / "outputs" / f"teacher_data_{mode}"
    manifest_path = data_dir / "teacher_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing {manifest_path}; run prepare first.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records: list[TeacherRecord] = []
    for item in manifest["teachers"]:
        with np.load(data_dir / item["data_file"], allow_pickle=False) as data:
            records.append(
                TeacherRecord(
                    teacher_id=str(item["id"]),
                    subject=str(item["subject"]),
                    mass_kg=float(item["mass_kg"]),
                    height_m=float(item["height_m"]),
                    gains=np.asarray(item["gains"], dtype=np.float32),
                    pi_rad=float(item["pi_rad"]),
                    tau_s=float(item["tau_s"]),
                    time_s=data["time_s"].astype(np.float32),
                    theta_rad=data["theta_rad"].astype(np.float32),
                    x_m=data["x_m"].astype(np.float32),
                    initial_states=data["initial_states"].astype(np.float32),
                )
            )
    return records


def load_real_records(mode: str) -> list[RealRecord]:
    data_dir = ROOT / "outputs" / f"real_data_{mode}"
    manifest_path = data_dir / "real_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing {manifest_path}; run prepare first.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records: list[RealRecord] = []
    for item in manifest["included_trials"]:
        with np.load(data_dir / item["data_file"], allow_pickle=False) as data:
            records.append(
                RealRecord(
                    subject=str(item["subject"]),
                    trial=str(item["trial"]),
                    mass_kg=float(item["mass_kg"]),
                    height_m=float(item["height_m"]),
                    time_s=data["time_s"].astype(np.float32),
                    theta_rad=data["theta_rad"].astype(np.float32),
                    x_m=data["x_m"].astype(np.float32),
                    valid_mask=data["valid_mask"].astype(np.float32),
                    initial_state=data["initial_state"].astype(np.float32),
                    usable_samples=int(item["usable_samples"]),
                    usable_duration_s=float(item["usable_duration_s"]),
                )
            )
    return records


class TrajectoryDataset:
    def __init__(self, samples: list[dict[str, Any]]):
        if not samples:
            raise ValueError("TrajectoryDataset cannot be empty")
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> dict[str, Any]:
        import torch

        item = self.samples[index]
        return {
            key: torch.as_tensor(value) if isinstance(value, np.ndarray) else value
            for key, value in item.items()
        }


def fixed_auxiliary(config: dict[str, Any]) -> tuple[float, float]:
    return (
        float(config["physics"]["fixed_pi_rad"]),
        float(config["physics"]["fixed_tau_s"]),
    )


def build_real_dataset(
    records: list[RealRecord],
    subjects: list[str] | str,
    config: dict[str, Any],
    limit_per_subject: int | None = None,
) -> TrajectoryDataset:
    selected_subjects = {subjects} if isinstance(subjects, str) else set(subjects)
    pi_rad, tau_s = fixed_auxiliary(config)
    samples: list[dict[str, Any]] = []
    counts = {subject: 0 for subject in selected_subjects}
    for record in records:
        if record.subject not in selected_subjects:
            continue
        if limit_per_subject is not None and counts[record.subject] >= limit_per_subject:
            continue
        counts[record.subject] += 1
        samples.append(
            {
                "sample_source": "real",
                "subject": record.subject,
                "trial": record.trial,
                "trajectory_index": -1,
                "time_s": record.time_s,
                "theta_rad": record.theta_rad,
                "x_m": record.x_m,
                "valid_mask": record.valid_mask,
                "initial_state": record.initial_state,
                "demographics": np.asarray(
                    [record.mass_kg / 80.0, record.height_m / 1.70], dtype=np.float32
                ),
                "auxiliary": np.asarray(
                    [pi_rad / math.radians(4.0), tau_s / 0.23], dtype=np.float32
                ),
                "pi_rad": np.asarray(pi_rad, dtype=np.float32),
                "tau_s": np.asarray(tau_s, dtype=np.float32),
            }
        )
    missing = selected_subjects - {item["subject"] for item in samples}
    if missing:
        raise ValueError(f"No eligible real trajectories for {sorted(missing)}")
    return TrajectoryDataset(samples)


def build_synthetic_dataset(
    records: list[TeacherRecord], subjects: list[str], limit_per_subject: int | None = None
) -> TrajectoryDataset:
    selected = [record for record in records if record.subject in set(subjects)]
    if {record.subject for record in selected} != set(subjects):
        raise ValueError("Teacher data does not cover every requested training subject")
    samples: list[dict[str, Any]] = []
    for record in selected:
        count = record.theta_rad.shape[0]
        if limit_per_subject is not None:
            count = min(count, limit_per_subject)
        for index in range(count):
            samples.append(
                {
                    "sample_source": "synthetic",
                    "teacher_id": record.teacher_id,
                    "subject": record.subject,
                    "trial": f"{record.teacher_id}_{index:03d}",
                    "trajectory_index": index,
                    "time_s": record.time_s,
                    "theta_rad": record.theta_rad[index],
                    "x_m": record.x_m[index],
                    "valid_mask": np.ones_like(record.time_s, dtype=np.float32),
                    "initial_state": record.initial_states[index],
                    "gains": record.gains,
                    "demographics": np.asarray(
                        [record.mass_kg / 80.0, record.height_m / 1.70], dtype=np.float32
                    ),
                    "auxiliary": np.asarray(
                        [record.pi_rad / math.radians(4.0), record.tau_s / 0.23],
                        dtype=np.float32,
                    ),
                    "pi_rad": np.asarray(record.pi_rad, dtype=np.float32),
                    "tau_s": np.asarray(record.tau_s, dtype=np.float32),
                }
            )
    return TrajectoryDataset(samples)


def build_context_windows(theta_rad, x_m, time_s, config: dict[str, Any]):
    import torch

    model_cfg = config["model"]
    number_windows = int(model_cfg["context_windows"])
    batch, samples = theta_rad.shape
    dt = float(torch.median(time_s[0, 1:] - time_s[0, :-1]).detach().cpu())
    window_points = int(round(float(model_cfg["context_window_s"]) / dt)) + 1
    region_points = int(round(float(model_cfg["context_region_s"]) / dt)) + 1
    if region_points > samples or window_points > region_points:
        raise ValueError("Configured context does not fit the trajectory grid")
    max_start = region_points - window_points
    starts = torch.linspace(0, max_start, number_windows, device=theta_rad.device).round().long()
    theta_dot = torch.gradient(theta_rad, spacing=dt, dim=1)[0]
    x_dot = torch.gradient(x_m, spacing=dt, dim=1)[0]
    relative_time = torch.linspace(0.0, 1.0, window_points, device=theta_rad.device)
    contexts = torch.zeros(
        (batch, number_windows, window_points, 5),
        dtype=theta_rad.dtype,
        device=theta_rad.device,
    )
    mask = torch.ones((batch, number_windows), dtype=theta_rad.dtype, device=theta_rad.device)
    for slot, start_tensor in enumerate(starts):
        start = int(start_tensor.item())
        stop = start + window_points
        contexts[:, slot, :, 0] = theta_rad[:, start:stop] / float(model_cfg["theta_scale_rad"])
        contexts[:, slot, :, 1] = x_m[:, start:stop] / float(model_cfg["x_scale_m"])
        contexts[:, slot, :, 2] = theta_dot[:, start:stop]
        contexts[:, slot, :, 3] = x_dot[:, start:stop] / 0.25
        contexts[:, slot, :, 4] = relative_time
    return contexts, mask


def create_model(config: dict[str, Any]):
    """Create the shared four-window context encoder and conditional DeepONet."""
    import torch
    import torch.nn.functional as functional
    from torch import nn

    model_cfg = config["model"]
    latent_width = int(model_cfg["latent_width"])
    context_embedding = int(model_cfg["context_embedding"])
    fourier_modes = int(model_cfg["fourier_modes"])
    gain_scale = torch.tensor(model_cfg["gain_scale"], dtype=torch.float32)
    theta_scale = float(model_cfg["theta_scale_rad"])
    x_scale = float(model_cfg["x_scale_m"])
    horizon = float(config["data"]["horizon_s"])
    physical_controller = str(model_cfg["controller_semantics"]) == "physical_gains"

    class MLP(nn.Module):
        def __init__(self, in_width: int, hidden: int, out_width: int):
            super().__init__()
            self.network = nn.Sequential(
                nn.Linear(in_width, hidden),
                nn.GELU(),
                nn.Linear(hidden, hidden),
                nn.GELU(),
                nn.Linear(hidden, out_width),
            )

        def forward(self, value):
            return self.network(value)

    class UnifiedOperator(nn.Module):
        def __init__(self):
            super().__init__()
            self.context_conv = nn.Sequential(
                nn.Conv1d(5, 32, kernel_size=5, padding=2),
                nn.GELU(),
                nn.Conv1d(32, 64, kernel_size=5, padding=2),
                nn.GELU(),
                nn.AdaptiveAvgPool1d(1),
            )
            self.context_projection = nn.Linear(64, context_embedding)
            self.controller_head = MLP(context_embedding + 2, 128, 8)
            self.branch = MLP(4 + 4 + 2 + 2, 160, 2 * latent_width)
            self.trunk = MLP(1 + 2 * fourier_modes, 160, latent_width)
            self.register_buffer("gain_scale", gain_scale)
            self.physical_controller = physical_controller

        def encode_context(self, contexts, mask):
            batch, windows, points, channels = contexts.shape
            flat = contexts.reshape(batch * windows, points, channels).transpose(1, 2)
            features = self.context_conv(flat).squeeze(-1)
            features = self.context_projection(features).reshape(batch, windows, -1)
            denominator = mask.sum(dim=1, keepdim=True).clamp_min(1.0)
            return (features * mask.unsqueeze(-1)).sum(dim=1) / denominator

        def infer_controller(self, contexts, mask, demographics):
            encoded = self.encode_context(contexts, mask)
            output = self.controller_head(torch.cat([encoded, demographics], dim=1))
            mean = output[:, :4]
            if self.physical_controller:
                mean = functional.softplus(mean)
            return mean, output[:, 4:].clamp(-6.0, 3.0)

        def forward_operator(self, controller, initial_state, demographics, auxiliary, time_s):
            branch_input = torch.cat([controller, initial_state, demographics, auxiliary], dim=1)
            branch = self.branch(branch_input).reshape(-1, 2, latent_width)
            normalized_time = time_s[0] / horizon
            modes = torch.arange(
                1, fourier_modes + 1, device=time_s.device, dtype=time_s.dtype
            ).reshape(1, -1)
            phase = 2.0 * math.pi * normalized_time.reshape(-1, 1) * modes
            trunk_input = torch.cat(
                [normalized_time.reshape(-1, 1), torch.sin(phase), torch.cos(phase)], dim=1
            )
            trunk = self.trunk(trunk_input)
            raw = torch.einsum("bop,tp->bto", branch, trunk) / math.sqrt(latent_width)
            time = time_s[:, :, None]
            theta = (
                initial_state[:, 0:1, None]
                + initial_state[:, 2:3, None] * time
                + time.square() * theta_scale * raw[:, :, 0:1]
            )
            x = (
                initial_state[:, 1:2, None]
                + initial_state[:, 3:4, None] * time
                + time.square() * x_scale * raw[:, :, 1:2]
            )
            return torch.cat([theta, x], dim=2)

    return UnifiedOperator()


def trajectory_target(batch):
    import torch

    return torch.stack([batch["theta_rad"], batch["x_m"]], dim=2)


def masked_normalized_mse(prediction, target, valid_mask, time_s, config, forecast_only: bool):
    model_cfg = config["model"]
    mask = valid_mask
    if forecast_only:
        mask = mask * (time_s >= float(model_cfg["context_region_s"])).to(mask.dtype)
    theta_error = (prediction[:, :, 0] - target[:, :, 0]) / float(model_cfg["theta_scale_rad"])
    x_error = (prediction[:, :, 1] - target[:, :, 1]) / float(model_cfg["x_scale_m"])
    point_error = theta_error.square() + x_error.square()
    per_trajectory = (point_error * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
    return per_trajectory.mean()


def gain_nll(mean, log_variance, target):
    import torch

    return 0.5 * (torch.exp(-log_variance) * (mean - target).square() + log_variance).mean()


def physics_residual_loss(
    prediction,
    gains,
    pi_rad,
    tau_s,
    time_s,
    physics,
    valid_mask=None,
):
    """Delayed cart-pole residual, explicitly included in the training graph."""
    import torch
    import torch.nn.functional as functional

    theta = prediction[:, :, 0]
    x = prediction[:, :, 1]
    dt = float(torch.median(time_s[0, 1:] - time_s[0, :-1]).detach().cpu())
    theta_dot = torch.gradient(theta, spacing=dt, dim=1)[0]
    x_dot = torch.gradient(x, spacing=dt, dim=1)[0]
    theta_ddot = (theta[:, 2:] - 2.0 * theta[:, 1:-1] + theta[:, :-2]) / (dt * dt)
    x_ddot = (x[:, 2:] - 2.0 * x[:, 1:-1] + x[:, :-2]) / (dt * dt)
    delay_steps = torch.round(tau_s / dt).long()
    start = max(1, int(torch.max(delay_steps).item()) + 1)
    stop = theta.shape[1] - 1
    if stop <= start:
        return prediction.new_tensor(0.0)
    current = torch.arange(start, stop, device=prediction.device)
    acceleration_index = current - 1
    m = float(physics["stick_mass_kg"])
    m0 = float(physics["effective_cart_mass_kg"])
    length = float(physics["stick_length_m"])
    gravity = float(physics["gravity_m_s2"])
    mass_11 = (1.0 / 3.0) * m * length * length
    mass_22 = m + m0
    sharpness = float(physics["deadzone_sharpness"])
    r1_values, r2_values = [], []
    for row in range(theta.shape[0]):
        delayed = current - int(delay_steps[row].item())
        keep = torch.ones_like(current, dtype=torch.bool)
        if valid_mask is not None:
            valid = valid_mask[row] > 0.5
            keep = (
                valid[current - 1]
                & valid[current]
                & valid[current + 1]
                & valid[delayed]
            )
        if not torch.any(keep):
            continue
        current_row = current[keep]
        delayed_row = delayed[keep]
        acceleration_row = acceleration_index[keep]
        theta_now = theta[row, current_row]
        theta_delayed = theta[row, delayed_row]
        gate = torch.sigmoid(sharpness * (torch.abs(theta_delayed) - pi_rad[row]))
        force = (
            gains[row, 0] * gate * theta_delayed
            + gains[row, 1] * theta_dot[row, delayed_row]
            + gains[row, 2] * x[row, delayed_row]
            + gains[row, 3] * x_dot[row, delayed_row]
        )
        cross = 0.5 * m * length * torch.cos(theta_now)
        r1_values.append(
            (
                mass_11 * theta_ddot[row, acceleration_row]
                + cross * x_ddot[row, acceleration_row]
                - 0.5 * m * gravity * length * torch.sin(theta_now)
            )
            / mass_11
        )
        r2_values.append(
            (
                cross * theta_ddot[row, acceleration_row]
                + mass_22 * x_ddot[row, acceleration_row]
                - 0.5 * m * length * theta_dot[row, current_row].square() * torch.sin(theta_now)
                - force
            )
            / mass_22
        )
    if not r1_values:
        return prediction.new_tensor(0.0)
    r1 = torch.cat(r1_values)
    r2 = torch.cat(r2_values)
    return functional.smooth_l1_loss(r1, torch.zeros_like(r1)) + functional.smooth_l1_loss(
        r2, torch.zeros_like(r2)
    )


def real_losses(model, batch, config, include_physics: bool):
    contexts, context_mask = build_context_windows(
        batch["theta_rad"], batch["x_m"], batch["time_s"], config
    )
    controller, log_variance = model.infer_controller(
        contexts, context_mask, batch["demographics"]
    )
    prediction = model.forward_operator(
        controller,
        batch["initial_state"],
        batch["demographics"],
        batch["auxiliary"],
        batch["time_s"],
    )
    target = trajectory_target(batch)
    data_loss = masked_normalized_mse(
        prediction, target, batch["valid_mask"], batch["time_s"], config, True
    )
    physics_loss = target.new_tensor(0.0)
    if include_physics and bool(config["training"]["use_physics"]):
        if not model.physical_controller:
            raise AssertionError("Physics requires physical gain semantics")
        physics_loss = physics_residual_loss(
            prediction,
            controller * model.gain_scale,
            batch["pi_rad"],
            batch["tau_s"],
            batch["time_s"],
            config["physics"],
            batch["valid_mask"],
        )
    settings = config["training"]
    total = float(settings["data_weight"]) * data_loss + float(
        settings["physics_weight"]
    ) * physics_loss
    return {
        "total": total,
        "data": data_loss,
        "physics": physics_loss,
        "prediction": prediction,
        "controller": controller,
        "controller_logvar": log_variance,
    }


def synthetic_losses(model, batch, config, include_physics: bool):
    contexts, context_mask = build_context_windows(
        batch["theta_rad"], batch["x_m"], batch["time_s"], config
    )
    controller, log_variance = model.infer_controller(
        contexts, context_mask, batch["demographics"]
    )
    target = trajectory_target(batch)
    normalized_true_gain = batch["gains"] / model.gain_scale
    true_gain_prediction = model.forward_operator(
        normalized_true_gain,
        batch["initial_state"],
        batch["demographics"],
        batch["auxiliary"],
        batch["time_s"],
    )
    inferred_gain_prediction = model.forward_operator(
        controller,
        batch["initial_state"],
        batch["demographics"],
        batch["auxiliary"],
        batch["time_s"],
    )
    data_loss = masked_normalized_mse(
        true_gain_prediction, target, batch["valid_mask"], batch["time_s"], config, False
    )
    gain_loss = gain_nll(controller, log_variance, normalized_true_gain)
    consistency_loss = masked_normalized_mse(
        inferred_gain_prediction, target, batch["valid_mask"], batch["time_s"], config, False
    )
    physics_loss = target.new_tensor(0.0)
    if include_physics and bool(config["training"]["use_physics"]):
        physics_loss = physics_residual_loss(
            true_gain_prediction,
            batch["gains"],
            batch["pi_rad"],
            batch["tau_s"],
            batch["time_s"],
            config["physics"],
            batch["valid_mask"],
        )
    settings = config["training"]
    total = (
        float(settings["data_weight"]) * data_loss
        + float(settings["gain_weight"]) * gain_loss
        + float(settings["consistency_weight"]) * consistency_loss
        + float(settings["physics_weight"]) * physics_loss
    )
    return {
        "total": total,
        "data": data_loss,
        "gain": gain_loss,
        "consistency": consistency_loss,
        "physics": physics_loss,
    }


def infer_real(model, batch, config):
    contexts, context_mask = build_context_windows(
        batch["theta_rad"], batch["x_m"], batch["time_s"], config
    )
    controller, log_variance = model.infer_controller(
        contexts, context_mask, batch["demographics"]
    )
    prediction = model.forward_operator(
        controller,
        batch["initial_state"],
        batch["demographics"],
        batch["auxiliary"],
        batch["time_s"],
    )
    loss = masked_normalized_mse(
        prediction,
        trajectory_target(batch),
        batch["valid_mask"],
        batch["time_s"],
        config,
        True,
    )
    return loss, prediction, controller, log_variance


def batch_to_device(batch: dict[str, Any], device) -> dict[str, Any]:
    return {key: value.to(device) if hasattr(value, "to") else value for key, value in batch.items()}


def iter_batches(
    dataset: TrajectoryDataset, batch_size: int, shuffle: bool, seed: int
) -> Iterable[dict[str, Any]]:
    import torch
    from torch.utils.data import DataLoader

    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        generator=generator,
    )
