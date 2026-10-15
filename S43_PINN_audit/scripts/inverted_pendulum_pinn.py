"""PyTorch Stage-1 inverted-pendulum PINN for horizontal/vertical CoM."""

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


class InvertedPendulumStage1(nn.Module):
    """Predict 2-D CoM state and a low-capacity effective angular torque.

    The horizontal/vertical trajectory uses a hard initial-state construction:

        q_hat(t) = q0 + qdot0*t + t**2*f(t, condition)

    Therefore position and velocity at marked fall onset are exact.  The angle
    is derived inside the graph as atan2(horizontal, vertical), so angular
    velocity and acceleration are available through automatic differentiation.
    """

    def __init__(
        self,
        condition_size,
        trajectory_hidden_size=32,
        trajectory_hidden_layers=3,
        torque_hidden_size=16,
        torque_hidden_layers=2,
    ):
        super().__init__()
        input_size = condition_size + 1
        self.trajectory = _mlp(
            input_size,
            trajectory_hidden_size,
            trajectory_hidden_layers,
            2,
        )
        self.effective_torque = _mlp(
            input_size,
            torque_hidden_size,
            torque_hidden_layers,
            1,
        )

    def forward(
        self,
        time_s,
        condition,
        initial_position,
        initial_velocity,
        time_scale_s,
        torque_scale_nm,
    ):
        features = torch.cat([time_s / time_scale_s, condition], dim=1)
        correction = self.trajectory(features)
        position = (
            initial_position
            + initial_velocity * time_s
            + correction * time_s.square()
        )
        effective_torque = torque_scale_nm * self.effective_torque(features)
        return position, effective_torque


def _tensor(array, requires_grad=False):
    return torch.tensor(array, dtype=DTYPE, requires_grad=requires_grad)


def state_derivatives(position, effective_torque, time_s):
    velocity_axes = []
    acceleration_axes = []
    for axis in range(2):
        velocity = torch.autograd.grad(
            position[:, axis].sum(),
            time_s,
            create_graph=True,
            retain_graph=True,
        )[0]
        acceleration = torch.autograd.grad(
            velocity.sum(),
            time_s,
            create_graph=True,
            retain_graph=True,
        )[0]
        velocity_axes.append(velocity[:, 0])
        acceleration_axes.append(acceleration[:, 0])

    theta = torch.atan2(position[:, 0], position[:, 1])
    theta_velocity = torch.autograd.grad(
        theta.sum(), time_s, create_graph=True, retain_graph=True
    )[0][:, 0]
    theta_acceleration = torch.autograd.grad(
        theta_velocity.sum(), time_s, create_graph=True, retain_graph=True
    )[0][:, 0]
    torque_rate = torch.autograd.grad(
        effective_torque.sum(), time_s, create_graph=True, retain_graph=True
    )[0][:, 0]
    return {
        "velocity": torch.stack(velocity_axes, dim=1),
        "acceleration": torch.stack(acceleration_axes, dim=1),
        "theta": theta,
        "theta_velocity": theta_velocity,
        "theta_acceleration": theta_acceleration,
        "torque_rate": torque_rate,
    }


def pendulum_residual(
    theta,
    theta_velocity,
    theta_acceleration,
    effective_torque,
    mass_kg,
    pendulum_length_m,
    damping_nms,
):
    """Return I*theta_ddot - m*g*l*sin(theta) - tau + b*theta_dot.

    This is the Stage-1 equation from the framework with the unmeasured human
    control and external perturbation combined into effective_torque.  A point
    mass approximation I=m*l**2 is used and documented as an assumption.
    """

    inertia = mass_kg * pendulum_length_m.square()
    gravity_torque = (
        mass_kg * GRAVITY_M_S2 * pendulum_length_m * torch.sin(theta)
    )
    return (
        inertia * theta_acceleration
        - gravity_torque
        - effective_torque[:, 0]
        + damping_nms * theta_velocity
    )


@dataclass(frozen=True)
class LossWeights:
    physics: float
    rigid_length: float
    effective_torque_l2: float
    effective_torque_rate: float


def loss_components(model, trials, time_scale_s, weights):
    data_terms = []
    physics_terms = []
    length_terms = []
    torque_terms = []
    torque_rate_terms = []

    for trial in trials:
        data_time = _tensor(trial["time_data"][:, None])
        predicted, _ = model(
            data_time,
            _tensor(trial["condition_data"]),
            _tensor(trial["initial_position_data"]),
            _tensor(trial["initial_velocity_data"]),
            time_scale_s,
            _tensor(trial["torque_scale_data"]),
        )
        target = _tensor(trial["position_data"])
        data_terms.append(
            torch.mean(((predicted - target) / trial["height_m"]) ** 2)
        )

        collocation_time = _tensor(
            trial["time_collocation"][:, None], requires_grad=True
        )
        position, torque = model(
            collocation_time,
            _tensor(trial["condition_collocation"]),
            _tensor(trial["initial_position_collocation"]),
            _tensor(trial["initial_velocity_collocation"]),
            time_scale_s,
            _tensor(trial["torque_scale_collocation"]),
        )
        derivatives = state_derivatives(position, torque, collocation_time)
        mass = _tensor(trial["mass_collocation"])
        length = _tensor(trial["length_collocation"])
        damping = _tensor(trial["damping_collocation"])
        residual = pendulum_residual(
            derivatives["theta"],
            derivatives["theta_velocity"],
            derivatives["theta_acceleration"],
            torque,
            mass,
            length,
            damping,
        )
        torque_scale = trial["torque_scale_collocation"][:, 0]
        physics_terms.append(
            torch.mean((residual / _tensor(torque_scale)) ** 2)
        )
        radius = torch.linalg.vector_norm(position, dim=1)
        length_terms.append(
            torch.mean(((radius - length) / trial["height_m"]) ** 2)
        )
        torque_terms.append(
            torch.mean((torque[:, 0] / _tensor(torque_scale)) ** 2)
        )
        torque_rate_scale = _tensor(torque_scale / time_scale_s)
        torque_rate_terms.append(
            torch.mean((derivatives["torque_rate"] / torque_rate_scale) ** 2)
        )

    components = {
        "data": torch.stack(data_terms).mean(),
        "physics": torch.stack(physics_terms).mean(),
        "rigid_length": torch.stack(length_terms).mean(),
        "effective_torque_l2": torch.stack(torque_terms).mean(),
        "effective_torque_rate": torch.stack(torque_rate_terms).mean(),
    }
    total = (
        components["data"]
        + weights.physics * components["physics"]
        + weights.rigid_length * components["rigid_length"]
        + weights.effective_torque_l2 * components["effective_torque_l2"]
        + weights.effective_torque_rate * components["effective_torque_rate"]
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
    model = InvertedPendulumStage1(
        condition_size=condition_size, **architecture
    ).to(DTYPE)
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


def evaluate_model(
    model,
    time_s,
    condition,
    initial_position,
    initial_velocity,
    time_scale_s,
    mass_kg,
    pendulum_length_m,
    damping_nms,
    use_effective_torque,
):
    time_s = np.asarray(time_s)
    query_time = _tensor(time_s[:, None], requires_grad=True)
    torque_scale = np.full(
        (len(time_s), 1),
        mass_kg * GRAVITY_M_S2 * pendulum_length_m,
    )
    position, effective_torque = model(
        query_time,
        _tensor(condition),
        _tensor(initial_position),
        _tensor(initial_velocity),
        time_scale_s,
        _tensor(torque_scale),
    )
    if not use_effective_torque:
        effective_torque = effective_torque * 0.0
    derivatives = state_derivatives(position, effective_torque, query_time)
    mass = _tensor(np.full(len(time_s), mass_kg))
    length = _tensor(np.full(len(time_s), pendulum_length_m))
    damping = _tensor(np.full(len(time_s), damping_nms))
    residual = pendulum_residual(
        derivatives["theta"],
        derivatives["theta_velocity"],
        derivatives["theta_acceleration"],
        effective_torque,
        mass,
        length,
        damping,
    )
    return {
        "position": position.detach().numpy(),
        "velocity": derivatives["velocity"].detach().numpy(),
        "acceleration": derivatives["acceleration"].detach().numpy(),
        "theta": derivatives["theta"].detach().numpy(),
        "theta_velocity": derivatives["theta_velocity"].detach().numpy(),
        "theta_acceleration": derivatives["theta_acceleration"].detach().numpy(),
        "effective_torque": effective_torque[:, 0].detach().numpy(),
        "physics_residual": residual.detach().numpy(),
        "radius": torch.linalg.vector_norm(position, dim=1).detach().numpy(),
    }
