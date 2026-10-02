"""PyTorch models and losses for controlled CoM PINN comparisons."""

from dataclasses import dataclass

import numpy as np
import torch
from torch import nn


GRAVITY_M_S2 = 9.80665
DTYPE = torch.float64


def _mlp(input_size, hidden_size, hidden_layers, output_size):
    layers = []
    width = input_size
    for _ in range(hidden_layers):
        layers.extend([nn.Linear(width, hidden_size), nn.Tanh()])
        width = hidden_size
    layers.append(nn.Linear(width, output_size))
    return nn.Sequential(*layers)


class CoMDynamicsModel(nn.Module):
    """Hard-initial-state trajectory plus a low-capacity effective residual."""

    def __init__(
        self,
        condition_size,
        trajectory_hidden_size=32,
        trajectory_hidden_layers=3,
        residual_hidden_size=16,
        residual_hidden_layers=2,
    ):
        super().__init__()
        input_size = condition_size + 1
        self.trajectory = _mlp(
            input_size,
            trajectory_hidden_size,
            trajectory_hidden_layers,
            3,
        )
        self.effective_residual = _mlp(
            input_size,
            residual_hidden_size,
            residual_hidden_layers,
            3,
        )

    def forward(self, time_s, condition, initial_velocity, time_scale_s):
        features = torch.cat([time_s / time_scale_s, condition], dim=1)
        correction = self.trajectory(features)
        effective_acceleration = GRAVITY_M_S2 * self.effective_residual(features)
        position = initial_velocity * time_s + correction * time_s.square()
        return position, effective_acceleration


def _time_derivatives(position, effective_acceleration, time_s):
    velocity_axes = []
    acceleration_axes = []
    jerk_axes = []
    for axis in range(3):
        velocity = torch.autograd.grad(
            position[:, axis].sum(), time_s, create_graph=True, retain_graph=True
        )[0]
        acceleration = torch.autograd.grad(
            velocity.sum(), time_s, create_graph=True, retain_graph=True
        )[0]
        jerk = torch.autograd.grad(
            effective_acceleration[:, axis].sum(),
            time_s,
            create_graph=True,
            retain_graph=True,
        )[0]
        velocity_axes.append(velocity[:, 0])
        acceleration_axes.append(acceleration[:, 0])
        jerk_axes.append(jerk[:, 0])
    return (
        torch.stack(velocity_axes, dim=1),
        torch.stack(acceleration_axes, dim=1),
        torch.stack(jerk_axes, dim=1),
    )


def _tensor(array, requires_grad=False):
    return torch.tensor(array, dtype=DTYPE, requires_grad=requires_grad)


@dataclass(frozen=True)
class LossWeights:
    physics: float
    effective_acceleration_l2: float
    effective_acceleration_jerk: float


def loss_components(model, trials, time_scale_s, weights):
    data_terms = []
    physics_terms = []
    magnitude_terms = []
    jerk_terms = []
    gravity = _tensor([[0.0, -GRAVITY_M_S2, 0.0]])
    for trial in trials:
        data_time = _tensor(trial["time_data"][:, None])
        predicted, _ = model(
            data_time,
            _tensor(trial["condition_data"]),
            _tensor(trial["initial_velocity_data"]),
            time_scale_s,
        )
        target = _tensor(trial["position_data"])
        data_terms.append(torch.mean(((predicted - target) / trial["height_m"]) ** 2))

        collocation_time = _tensor(
            trial["time_collocation"][:, None], requires_grad=True
        )
        position, effective = model(
            collocation_time,
            _tensor(trial["condition_collocation"]),
            _tensor(trial["initial_velocity_collocation"]),
            time_scale_s,
        )
        _, acceleration, effective_jerk = _time_derivatives(
            position, effective, collocation_time
        )
        residual = acceleration - gravity - effective
        physics_terms.append(torch.mean((residual / GRAVITY_M_S2) ** 2))
        magnitude_terms.append(torch.mean((effective / GRAVITY_M_S2) ** 2))
        jerk_scale = GRAVITY_M_S2 / time_scale_s
        jerk_terms.append(torch.mean((effective_jerk / jerk_scale) ** 2))

    components = {
        "data": torch.stack(data_terms).mean(),
        "physics": torch.stack(physics_terms).mean(),
        "effective_acceleration_l2": torch.stack(magnitude_terms).mean(),
        "effective_acceleration_jerk": torch.stack(jerk_terms).mean(),
    }
    total = (
        components["data"]
        + weights.physics * components["physics"]
        + weights.effective_acceleration_l2
        * components["effective_acceleration_l2"]
        + weights.effective_acceleration_jerk
        * components["effective_acceleration_jerk"]
    )
    return total, components


def train_model(
    trials,
    condition_size,
    time_scale_s,
    architecture,
    epochs,
    learning_rate,
    loss_weights,
    seed,
    history_interval=50,
):
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.use_deterministic_algorithms(True)
    model = CoMDynamicsModel(condition_size=condition_size, **architecture).to(DTYPE)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    history = []
    for epoch in range(1, epochs + 1):
        optimizer.zero_grad()
        total, components = loss_components(
            model, trials, time_scale_s, loss_weights
        )
        total.backward()
        optimizer.step()
        if epoch == 1 or epoch % history_interval == 0 or epoch == epochs:
            history.append(
                {
                    "epoch": epoch,
                    "total_loss": float(total.detach()),
                    **{
                        name: float(value.detach())
                        for name, value in components.items()
                    },
                }
            )
    return model, history


def evaluate_model(model, time_s, condition, initial_velocity, time_scale_s):
    query_time = _tensor(np.asarray(time_s)[:, None], requires_grad=True)
    position, effective = model(
        query_time,
        _tensor(condition),
        _tensor(initial_velocity),
        time_scale_s,
    )
    velocity, acceleration, _ = _time_derivatives(position, effective, query_time)
    gravity = _tensor([[0.0, -GRAVITY_M_S2, 0.0]])
    residual = acceleration - gravity - effective
    return {
        "position": position.detach().numpy(),
        "velocity": velocity.detach().numpy(),
        "acceleration": acceleration.detach().numpy(),
        "effective_acceleration": effective.detach().numpy(),
        "physics_residual": residual.detach().numpy(),
    }

