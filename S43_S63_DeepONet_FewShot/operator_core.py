#!/usr/bin/env python3
"""Shared utilities, datasets, models, and losses for the operator experiment."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parent
GAIN_NAMES = ("kp_theta", "kd_theta", "kp_x", "kd_x")


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["_config_path"] = str(config_path)
    config["_root"] = str(config_path.parent)
    return config


def resolve_from_config(config: dict[str, Any], value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(config["_root"]) / path
    return path.resolve()


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
    except ImportError:
        pass


def choose_torch_device(requested: str):
    import torch

    if requested != "auto":
        return torch.device(requested)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


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


def load_teacher_records(config: dict[str, Any], mode: str) -> list[TeacherRecord]:
    data_dir = ROOT / "outputs" / f"teacher_data_{mode}"
    manifest_path = data_dir / "teacher_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Teacher manifest not found: {manifest_path}\n"
            f"Run: python export_teacher_data.py --mode {mode}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records: list[TeacherRecord] = []
    for item in manifest["teachers"]:
        path = data_dir / item["data_file"]
        with np.load(path, allow_pickle=False) as data:
            records.append(
                TeacherRecord(
                    teacher_id=item["id"],
                    subject=item["subject"],
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
    if len(records) != 3:
        raise ValueError(f"Expected three teacher datasets, found {len(records)}")
    return records


class TrajectoryDataset:
    """Small in-memory dataset with a torch Dataset-compatible interface."""

    def __init__(self, samples: list[dict[str, Any]]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> dict[str, Any]:
        import torch

        item = self.samples[index]
        return {
            key: torch.as_tensor(value)
            if isinstance(value, np.ndarray)
            else value
            for key, value in item.items()
        }


def build_splits(
    records: list[TeacherRecord],
    seed: int,
    train_fraction: float,
    validation_fraction: float,
    holdout_teacher: str | None,
) -> tuple[TrajectoryDataset, TrajectoryDataset, TrajectoryDataset, dict[str, Any]]:
    counts = {record.theta_rad.shape[0] for record in records}
    if len(counts) != 1:
        raise ValueError("All teachers must have the same number of matched initial conditions.")
    count = counts.pop()
    rng = np.random.default_rng(seed)
    order = rng.permutation(count)

    if holdout_teacher is None:
        n_train = max(1, int(round(count * train_fraction)))
        n_val = max(1, int(round(count * validation_fraction)))
        if n_train + n_val >= count:
            n_train, n_val = max(1, count - 2), 1
        index_sets = {
            "train": set(order[:n_train].tolist()),
            "validation": set(order[n_train : n_train + n_val].tolist()),
            "test": set(order[n_train + n_val :].tolist()),
        }
    else:
        known_ids = {record.teacher_id for record in records}
        if holdout_teacher not in known_ids:
            raise ValueError(f"Unknown holdout teacher {holdout_teacher!r}; choose from {sorted(known_ids)}")
        n_val = max(1, int(round(count * validation_fraction)))
        index_sets = {
            "train": set(order[n_val:].tolist()),
            "validation": set(order[:n_val].tolist()),
            "test": set(range(count)),
        }

    split_samples: dict[str, list[dict[str, Any]]] = {key: [] for key in index_sets}
    for record in records:
        for split_name, indices in index_sets.items():
            if holdout_teacher is not None:
                if split_name == "test" and record.teacher_id != holdout_teacher:
                    continue
                if split_name != "test" and record.teacher_id == holdout_teacher:
                    continue
            for trajectory_index in sorted(indices):
                split_samples[split_name].append(
                    {
                        "teacher_id": record.teacher_id,
                        "trajectory_index": trajectory_index,
                        "time_s": record.time_s,
                        "theta_rad": record.theta_rad[trajectory_index],
                        "x_m": record.x_m[trajectory_index],
                        "initial_state": record.initial_states[trajectory_index],
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

    details = {
        "strategy": "leave_one_teacher_out" if holdout_teacher else "grouped_initial_condition",
        "holdout_teacher": holdout_teacher,
        "shared_initial_condition_indices": {
            key: sorted(value) for key, value in index_sets.items()
        },
        "sample_counts": {key: len(value) for key, value in split_samples.items()},
        "note": (
            "The same initial-condition index is kept in one split across all teachers."
            if holdout_teacher is None
            else "All trajectories from the named teacher are excluded from training and validation."
        ),
    }
    return (
        TrajectoryDataset(split_samples["train"]),
        TrajectoryDataset(split_samples["validation"]),
        TrajectoryDataset(split_samples["test"]),
        details,
    )


def build_context_windows(
    theta_rad,
    x_m,
    time_s,
    number_windows: int,
    maximum_windows: int,
    window_seconds: float,
    region_seconds: float,
    theta_scale: float,
    x_scale: float,
    randomize: bool,
):
    """Create K short windows with angle, position, derivatives, and local time."""
    import torch

    batch, samples = theta_rad.shape
    dt = float(torch.median(time_s[0, 1:] - time_s[0, :-1]).detach().cpu())
    window_points = max(3, min(samples, int(round(window_seconds / dt)) + 1))
    region_points = max(window_points, min(samples, int(round(region_seconds / dt)) + 1))
    max_start = max(0, region_points - window_points)

    theta_dot = torch.gradient(theta_rad, spacing=dt, dim=1)[0]
    x_dot = torch.gradient(x_m, spacing=dt, dim=1)[0]
    relative_time = torch.linspace(0.0, 1.0, window_points, device=theta_rad.device)
    contexts = torch.zeros(
        (batch, maximum_windows, window_points, 5),
        dtype=theta_rad.dtype,
        device=theta_rad.device,
    )
    mask = torch.zeros((batch, maximum_windows), dtype=theta_rad.dtype, device=theta_rad.device)

    for row in range(batch):
        if randomize and max_start > 0:
            starts = torch.randint(0, max_start + 1, (number_windows,), device=theta_rad.device)
            starts, _ = torch.sort(starts)
        elif number_windows == 1:
            starts = torch.zeros(1, dtype=torch.long, device=theta_rad.device)
        else:
            starts = torch.linspace(0, max_start, number_windows, device=theta_rad.device).round().long()
        for slot, start_tensor in enumerate(starts):
            start = int(start_tensor.item())
            stop = start + window_points
            contexts[row, slot, :, 0] = theta_rad[row, start:stop] / theta_scale
            contexts[row, slot, :, 1] = x_m[row, start:stop] / x_scale
            contexts[row, slot, :, 2] = theta_dot[row, start:stop]
            contexts[row, slot, :, 3] = x_dot[row, start:stop] / 0.25
            contexts[row, slot, :, 4] = relative_time
            mask[row, slot] = 1.0
    return contexts, mask


def create_model(config: dict[str, Any]):
    import torch
    from torch import nn

    model_config = config["model"]
    latent_width = int(model_config["latent_width"])
    context_embedding = int(model_config["context_embedding"])
    fourier_modes = int(model_config["fourier_modes"])
    gain_scale = torch.tensor(model_config["gain_scale"], dtype=torch.float32)
    theta_scale = float(model_config["theta_scale_rad"])
    x_scale = float(model_config["x_scale_m"])
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
            flattened = contexts.reshape(batch * windows, points, channels).transpose(1, 2)
            features = self.context_conv(flattened).squeeze(-1)
            features = self.context_projection(features).reshape(batch, windows, -1)
            denominator = mask.sum(dim=1, keepdim=True).clamp_min(1.0)
            return (features * mask.unsqueeze(-1)).sum(dim=1) / denominator

        def infer_gains(self, contexts, mask, demographics):
            encoded = self.encode_context(contexts, mask)
            output = self.gain_head(torch.cat([encoded, demographics], dim=1))
            mean = output[:, :4]
            log_variance = output[:, 4:].clamp(-6.0, 3.0)
            return mean, log_variance

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
            theta0 = initial_state[:, 0:1, None]
            x0 = initial_state[:, 1:2, None]
            theta_dot0 = initial_state[:, 2:3, None]
            x_dot0 = initial_state[:, 3:4, None]
            theta = theta0 + theta_dot0 * time + time.square() * theta_scale * raw[:, :, 0:1]
            x = x0 + x_dot0 * time + time.square() * x_scale * raw[:, :, 1:2]
            return torch.cat([theta, x], dim=2)

        def forward(self, contexts, mask, gains, initial_state, demographics, auxiliary, time_s):
            predicted_gain_mean, predicted_gain_logvar = self.infer_gains(
                contexts, mask, demographics
            )
            normalized_true_gains = gains / self.gain_scale
            true_gain_trajectory = self.forward_operator(
                normalized_true_gains, initial_state, demographics, auxiliary, time_s
            )
            predicted_gain_trajectory = self.forward_operator(
                predicted_gain_mean, initial_state, demographics, auxiliary, time_s
            )
            return {
                "predicted_gain_normalized": predicted_gain_mean,
                "predicted_gain_logvar": predicted_gain_logvar,
                "true_gain_trajectory": true_gain_trajectory,
                "predicted_gain_trajectory": predicted_gain_trajectory,
            }

    return UnifiedOperator()


def physics_residual_loss(prediction, gains, pi_rad, tau_s, time_s, physics: dict[str, float]):
    """Differentiable finite-difference delayed cart-pole residual."""
    import torch
    import torch.nn.functional as functional

    theta = prediction[:, :, 0]
    x = prediction[:, :, 1]
    dt = float(torch.median(time_s[0, 1:] - time_s[0, :-1]).detach().cpu())
    theta_dot = torch.gradient(theta, spacing=dt, dim=1)[0]
    x_dot = torch.gradient(x, spacing=dt, dim=1)[0]
    theta_ddot = (theta[:, 2:] - 2.0 * theta[:, 1:-1] + theta[:, :-2]) / (dt * dt)
    x_ddot = (x[:, 2:] - 2.0 * x[:, 1:-1] + x[:, :-2]) / (dt * dt)

    # All current indices must have a valid centered acceleration and delayed state.
    delay_steps = torch.round(tau_s / dt).long()
    common_delay = int(torch.max(delay_steps).item())
    start = max(1, common_delay + 1)
    stop = theta.shape[1] - 1
    if stop <= start:
        return prediction.new_tensor(0.0)
    current = torch.arange(start, stop, device=prediction.device)
    acceleration_index = current - 1

    residual_1_rows = []
    residual_2_rows = []
    m = float(physics["stick_mass_kg"])
    m0 = float(physics["effective_cart_mass_kg"])
    length = float(physics["stick_length_m"])
    gravity = float(physics["gravity_m_s2"])
    mass_11 = (1.0 / 3.0) * m * length * length
    mass_22 = m + m0
    sharpness = float(physics["deadzone_sharpness"])

    for row in range(theta.shape[0]):
        delayed = current - int(delay_steps[row].item())
        theta_now = theta[row, current]
        theta_delayed = theta[row, delayed]
        gate = torch.sigmoid(sharpness * (torch.abs(theta_delayed) - pi_rad[row]))
        theta_perceived = gate * theta_delayed
        force = (
            gains[row, 0] * theta_perceived
            + gains[row, 1] * theta_dot[row, delayed]
            + gains[row, 2] * x[row, delayed]
            + gains[row, 3] * x_dot[row, delayed]
        )
        cross = 0.5 * m * length * torch.cos(theta_now)
        r1 = (
            mass_11 * theta_ddot[row, acceleration_index]
            + cross * x_ddot[row, acceleration_index]
            - 0.5 * m * gravity * length * torch.sin(theta_now)
        ) / mass_11
        r2 = (
            cross * theta_ddot[row, acceleration_index]
            + mass_22 * x_ddot[row, acceleration_index]
            - 0.5 * m * length * theta_dot[row, current].square() * torch.sin(theta_now)
            - force
        ) / mass_22
        residual_1_rows.append(r1)
        residual_2_rows.append(r2)
    residual_1 = torch.stack(residual_1_rows)
    residual_2 = torch.stack(residual_2_rows)
    zeros_1 = torch.zeros_like(residual_1)
    zeros_2 = torch.zeros_like(residual_2)
    return functional.smooth_l1_loss(residual_1, zeros_1) + functional.smooth_l1_loss(
        residual_2, zeros_2
    )


def batch_to_device(batch: dict[str, Any], device) -> dict[str, Any]:
    moved: dict[str, Any] = {}
    for key, value in batch.items():
        moved[key] = value.to(device) if hasattr(value, "to") else value
    return moved


def iter_batches(dataset: TrajectoryDataset, batch_size: int, shuffle: bool, seed: int) -> Iterable[dict[str, Any]]:
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
