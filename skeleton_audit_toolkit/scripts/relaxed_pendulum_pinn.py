"""Stage-1.5 PINN with predicted time-varying pendulum length.

The trajectory network predicts the two-dimensional CoM position relative to
the selected pivot.  Its radius therefore defines l(t); no held-out CoM radius
is supplied to the network.  The angular residual includes the polar-coordinate
coupling term 2*m*l*l_dot*theta_dot.  An optional measured horizontal support
proxy acceleration can be included for a diagnostic moving-pivot experiment.
"""

from dataclasses import dataclass

import numpy as np
import torch

from inverted_pendulum_pinn import (
    DTYPE,
    GRAVITY_M_S2,
    InvertedPendulumStage1,
    _tensor,
)


def relaxed_state_derivatives(position, effective_torque, time_s):
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

    radius = torch.sqrt(torch.sum(position.square(), dim=1) + 1e-12)
    radius_rate = torch.autograd.grad(
        radius.sum(), time_s, create_graph=True, retain_graph=True
    )[0][:, 0]
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
        "radius": radius,
        "radius_rate": radius_rate,
        "theta": theta,
        "theta_velocity": theta_velocity,
        "theta_acceleration": theta_acceleration,
        "torque_rate": torque_rate,
    }


def variable_length_residual(
    theta,
    theta_velocity,
    theta_acceleration,
    radius,
    radius_rate,
    effective_torque,
    mass_kg,
    damping_nms,
    pivot_acceleration_horizontal,
):
    """Tangential point-mass balance for l=l(t) and a translating pivot.

    m*l^2*theta_ddot + 2*m*l*l_dot*theta_dot
      = m*g*l*sin(theta) + tau_effective - b*theta_dot
        - m*l*pivot_ddot dot e_theta

    The implemented support proxy moves horizontally only, so
    pivot_ddot dot e_theta = pivot_ddot_x*cos(theta).
    """

    inertia_term = mass_kg * radius.square() * theta_acceleration
    radial_coupling = (
        2.0 * mass_kg * radius * radius_rate * theta_velocity
    )
    gravity_torque = mass_kg * GRAVITY_M_S2 * radius * torch.sin(theta)
    translating_pivot = (
        mass_kg
        * radius
        * pivot_acceleration_horizontal
        * torch.cos(theta)
    )
    return (
        inertia_term
        + radial_coupling
        - gravity_torque
        - effective_torque[:, 0]
        + damping_nms * theta_velocity
        + translating_pivot
    )


@dataclass(frozen=True)
class RelaxedLossWeights:
    physics: float
    effective_torque_l2: float
    effective_torque_rate: float


def loss_components(model, trials, time_scale_s, weights):
    data_terms = []
    physics_terms = []
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
        derivatives = relaxed_state_derivatives(
            position, torque, collocation_time
        )
        residual = variable_length_residual(
            derivatives["theta"],
            derivatives["theta_velocity"],
            derivatives["theta_acceleration"],
            derivatives["radius"],
            derivatives["radius_rate"],
            torque,
            _tensor(trial["mass_collocation"]),
            _tensor(trial["damping_collocation"]),
            _tensor(trial["pivot_acceleration_collocation"]),
        )
        torque_scale = _tensor(trial["torque_scale_collocation"][:, 0])
        physics_terms.append(torch.mean((residual / torque_scale) ** 2))
        torque_terms.append(torch.mean((torque[:, 0] / torque_scale) ** 2))
        torque_rate_scale = torque_scale / time_scale_s
        torque_rate_terms.append(
            torch.mean((derivatives["torque_rate"] / torque_rate_scale) ** 2)
        )

    components = {
        "data": torch.stack(data_terms).mean(),
        "physics": torch.stack(physics_terms).mean(),
        "effective_torque_l2": torch.stack(torque_terms).mean(),
        "effective_torque_rate": torch.stack(torque_rate_terms).mean(),
    }
    total = (
        components["data"]
        + weights.physics * components["physics"]
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
    onset_length_m,
    damping_nms,
    pivot_acceleration_horizontal,
    use_effective_torque,
):
    time_s = np.asarray(time_s)
    query_time = _tensor(time_s[:, None], requires_grad=True)
    torque_scale = np.full(
        (len(time_s), 1), mass_kg * GRAVITY_M_S2 * onset_length_m
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
    derivatives = relaxed_state_derivatives(
        position, effective_torque, query_time
    )
    residual = variable_length_residual(
        derivatives["theta"],
        derivatives["theta_velocity"],
        derivatives["theta_acceleration"],
        derivatives["radius"],
        derivatives["radius_rate"],
        effective_torque,
        _tensor(np.full(len(time_s), mass_kg)),
        _tensor(np.full(len(time_s), damping_nms)),
        _tensor(np.asarray(pivot_acceleration_horizontal)),
    )
    return {
        "position_relative": position.detach().numpy(),
        "velocity_relative": derivatives["velocity"].detach().numpy(),
        "acceleration_relative": derivatives["acceleration"].detach().numpy(),
        "theta": derivatives["theta"].detach().numpy(),
        "theta_velocity": derivatives["theta_velocity"].detach().numpy(),
        "theta_acceleration": derivatives["theta_acceleration"].detach().numpy(),
        "effective_torque": effective_torque[:, 0].detach().numpy(),
        "physics_residual": residual.detach().numpy(),
        "radius": derivatives["radius"].detach().numpy(),
        "radius_rate": derivatives["radius_rate"].detach().numpy(),
    }
