#!/usr/bin/env python3
"""Shared protocol, data, model, and loss utilities for Experiment 1."""

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


def subject_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in config["subjects"]}


def fold_by_id(config: dict[str, Any], fold_id: int) -> dict[str, Any]:
    for fold in config["folds"]:
        if int(fold["id"]) == int(fold_id):
            return fold
    raise KeyError(f"Unknown fold {fold_id}; expected one of {[x['id'] for x in config['folds']]}")


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
        raise FileNotFoundError(f"Missing {manifest_path}; run export_teacher_data.py first.")
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
        raise FileNotFoundError(f"Missing {manifest_path}; run prepare_real_data.py first.")
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
                    "teacher_id": record.teacher_id,
                    "subject": record.subject,
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


def build_real_dataset(
    records: list[RealRecord], subject: str, mean_pi_rad: float, mean_tau_s: float
) -> TrajectoryDataset:
    samples: list[dict[str, Any]] = []
    for record in records:
        if record.subject != subject:
            continue
        samples.append(
            {
                "teacher_id": "held_out_real",
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
                    [mean_pi_rad / math.radians(4.0), mean_tau_s / 0.23], dtype=np.float32
                ),
                "pi_rad": np.asarray(mean_pi_rad, dtype=np.float32),
                "tau_s": np.asarray(mean_tau_s, dtype=np.float32),
            }
        )
    if not samples:
        raise ValueError(f"No eligible real trajectories for {subject}")
    return TrajectoryDataset(samples)


def build_context_windows(theta_rad, x_m, time_s, config: dict[str, Any]):
    """Build the fixed four-window context selected by the preliminary experiment."""
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
    """Create the preliminary experiment's context encoder and conditional DeepONet."""
    import torch
    from torch import nn

    model_cfg = config["model"]
    latent_width = int(model_cfg["latent_width"])
    context_embedding = int(model_cfg["context_embedding"])
    fourier_modes = int(model_cfg["fourier_modes"])
    gain_scale = torch.tensor(model_cfg["gain_scale"], dtype=torch.float32)
    theta_scale = float(model_cfg["theta_scale_rad"])
    x_scale = float(model_cfg["x_scale_m"])
    horizon = float(config["teacher_generation"]["horizon_s"])

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
            self.gain_head = MLP(context_embedding + 2, 128, 8)
            self.branch = MLP(4 + 4 + 2 + 2, 160, 2 * latent_width)
            self.trunk = MLP(1 + 2 * fourier_modes, 160, latent_width)
            self.register_buffer("gain_scale", gain_scale)

        def encode_context(self, contexts, mask):
            batch, windows, points, channels = contexts.shape
            flat = contexts.reshape(batch * windows, points, channels).transpose(1, 2)
            features = self.context_conv(flat).squeeze(-1)
            features = self.context_projection(features).reshape(batch, windows, -1)
            denominator = mask.sum(dim=1, keepdim=True).clamp_min(1.0)
            return (features * mask.unsqueeze(-1)).sum(dim=1) / denominator

        def infer_gains(self, contexts, mask, demographics):
            encoded = self.encode_context(contexts, mask)
            output = self.gain_head(torch.cat([encoded, demographics], dim=1))
            return output[:, :4], output[:, 4:].clamp(-6.0, 3.0)

        def forward_operator(self, normalized_gains, initial_state, demographics, auxiliary, time_s):
            branch_input = torch.cat(
                [normalized_gains, initial_state, demographics, auxiliary], dim=1
            )
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

        def forward(self, contexts, mask, gains, initial_state, demographics, auxiliary, time_s):
            predicted_mean, predicted_logvar = self.infer_gains(contexts, mask, demographics)
            return {
                "predicted_gain_normalized": predicted_mean,
                "predicted_gain_logvar": predicted_logvar,
                "true_gain_trajectory": self.forward_operator(
                    gains / self.gain_scale, initial_state, demographics, auxiliary, time_s
                ),
                "predicted_gain_trajectory": self.forward_operator(
                    predicted_mean, initial_state, demographics, auxiliary, time_s
                ),
            }

    return UnifiedOperator()


def trajectory_target(batch):
    import torch

    return torch.stack([batch["theta_rad"], batch["x_m"]], dim=2)


def masked_normalized_mse(prediction, target, valid_mask, time_s, config, forecast_only: bool):
    model_cfg = config["model"]
    mask = valid_mask
    if forecast_only:
        mask = mask * (time_s >= float(model_cfg["context_region_s"])).to(mask.dtype)
    denominator = mask.sum().clamp_min(1.0)
    theta_error = (prediction[:, :, 0] - target[:, :, 0]) / float(model_cfg["theta_scale_rad"])
    x_error = (prediction[:, :, 1] - target[:, :, 1]) / float(model_cfg["x_scale_m"])
    return ((theta_error.square() + x_error.square()) * mask).sum() / denominator


def gain_nll(mean, log_variance, target):
    inverse_variance = torch_exp_negative(log_variance)
    return 0.5 * (inverse_variance * (mean - target).square() + log_variance).mean()


def torch_exp_negative(value):
    import torch

    return torch.exp(-value)


def physics_residual_loss(prediction, gains, pi_rad, tau_s, time_s, physics):
    """Differentiable finite-difference delayed cart-pole residual from the preliminary code."""
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
    r1_rows, r2_rows = [], []
    for row in range(theta.shape[0]):
        delayed = current - int(delay_steps[row].item())
        theta_now = theta[row, current]
        theta_delayed = theta[row, delayed]
        gate = torch.sigmoid(sharpness * (torch.abs(theta_delayed) - pi_rad[row]))
        force = (
            gains[row, 0] * gate * theta_delayed
            + gains[row, 1] * theta_dot[row, delayed]
            + gains[row, 2] * x[row, delayed]
            + gains[row, 3] * x_dot[row, delayed]
        )
        cross = 0.5 * m * length * torch.cos(theta_now)
        r1_rows.append(
            (
                mass_11 * theta_ddot[row, acceleration_index]
                + cross * x_ddot[row, acceleration_index]
                - 0.5 * m * gravity * length * torch.sin(theta_now)
            )
            / mass_11
        )
        r2_rows.append(
            (
                cross * theta_ddot[row, acceleration_index]
                + mass_22 * x_ddot[row, acceleration_index]
                - 0.5 * m * length * theta_dot[row, current].square() * torch.sin(theta_now)
                - force
            )
            / mass_22
        )
    r1 = torch.stack(r1_rows)
    r2 = torch.stack(r2_rows)
    return functional.smooth_l1_loss(r1, torch.zeros_like(r1)) + functional.smooth_l1_loss(
        r2, torch.zeros_like(r2)
    )


def synthetic_losses(model, batch, config, include_physics: bool):
    contexts, context_mask = build_context_windows(
        batch["theta_rad"], batch["x_m"], batch["time_s"], config
    )
    output = model(
        contexts,
        context_mask,
        batch["gains"],
        batch["initial_state"],
        batch["demographics"],
        batch["auxiliary"],
        batch["time_s"],
    )
    target = trajectory_target(batch)
    target_gain = batch["gains"] / model.gain_scale
    losses = {
        "data": masked_normalized_mse(
            output["true_gain_trajectory"], target, batch["valid_mask"], batch["time_s"], config, False
        ),
        "gain": gain_nll(
            output["predicted_gain_normalized"], output["predicted_gain_logvar"], target_gain
        ),
        "consistency": masked_normalized_mse(
            output["predicted_gain_trajectory"], target, batch["valid_mask"], batch["time_s"], config, False
        ),
    }
    losses["physics"] = (
        physics_residual_loss(
            output["true_gain_trajectory"],
            batch["gains"],
            batch["pi_rad"],
            batch["tau_s"],
            batch["time_s"],
            config["physics"],
        )
        if include_physics
        else target.new_tensor(0.0)
    )
    settings = config["training"]
    losses["total"] = (
        float(settings["data_weight"]) * losses["data"]
        + float(settings["gain_weight"]) * losses["gain"]
        + float(settings["consistency_weight"]) * losses["consistency"]
        + float(settings["physics_weight"]) * losses["physics"]
    )
    return losses


def infer_real(model, batch, config):
    contexts, context_mask = build_context_windows(
        batch["theta_rad"], batch["x_m"], batch["time_s"], config
    )
    mean, log_variance = model.infer_gains(contexts, context_mask, batch["demographics"])
    prediction = model.forward_operator(
        mean,
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
    return loss, prediction, mean, log_variance


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
