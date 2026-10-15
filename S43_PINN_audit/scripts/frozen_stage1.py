"""Read-only evaluation utilities for retained frozen Stage-1 checkpoints.

These functions reproduce the Stage-1 trajectory and effective-torque network
using plain arrays and automatic differentiation. They contain no Stage-2
controller fitting, nuisance torque, saturation, or optimizer code.
"""

from __future__ import annotations

import autograd.numpy as anp
import numpy as np
from autograd import grad


GRAVITY_M_S2 = 9.80665


def unpack(flat, shapes, sizes):
    arrays = []
    offset = 0
    for shape, size in zip(shapes, sizes):
        arrays.append(anp.reshape(flat[offset : offset + size], shape))
        offset += size
    return arrays


def _mlp(features, arrays):
    value = features
    for index in range(0, len(arrays), 2):
        value = anp.dot(value, arrays[index]) + arrays[index + 1]
        if index < len(arrays) - 2:
            value = anp.tanh(value)
    return value


def stage1_outputs(
    flat,
    shapes,
    sizes,
    split_index,
    time_s,
    condition,
    initial_position,
    initial_velocity,
    time_scale_s,
    torque_scale_nm,
):
    """Evaluate a frozen Stage-1 checkpoint without changing its weights."""

    arrays = unpack(flat, shapes, sizes)
    features = anp.concatenate([time_s[:, None] / time_scale_s, condition], axis=1)
    correction = _mlp(features, arrays[:split_index])
    torque = torque_scale_nm * _mlp(features, arrays[split_index:])[:, 0]
    position = (
        initial_position
        + initial_velocity * time_s[:, None]
        + correction * time_s[:, None] ** 2
    )
    return position, torque


def stage1_derivatives(model, time_s, record):
    """Evaluate frozen position and its automatic time derivatives."""

    flat = model["flat_parameters"]
    shapes = model["parameter_shapes"]
    sizes = model["parameter_sizes"]
    split_index = model["split_index"]

    def outputs(query_time):
        return stage1_outputs(
            flat,
            shapes,
            sizes,
            split_index,
            query_time,
            record["condition"],
            record["initial_position"],
            record["initial_velocity"],
            model["time_scale_s"],
            record["torque_scale"],
        )

    position, torque = outputs(time_s)
    velocity_axes = []
    acceleration_axes = []
    for axis in range(2):
        position_gradient = grad(lambda query: anp.sum(outputs(query)[0][:, axis]))
        velocity = position_gradient(time_s)
        acceleration = grad(lambda query: anp.sum(position_gradient(query)))(time_s)
        velocity_axes.append(velocity)
        acceleration_axes.append(acceleration)

    def theta_sum(query):
        value = outputs(query)[0]
        return anp.sum(anp.arctan2(value[:, 0], value[:, 1]))

    theta_gradient = grad(theta_sum)
    theta_velocity = theta_gradient(time_s)
    theta_acceleration = grad(lambda query: anp.sum(theta_gradient(query)))(time_s)
    return {
        "position": np.asarray(position),
        "velocity": np.asarray(anp.stack(velocity_axes, axis=1)),
        "acceleration": np.asarray(anp.stack(acceleration_axes, axis=1)),
        "theta": np.asarray(anp.arctan2(position[:, 0], position[:, 1])),
        "theta_velocity": np.asarray(theta_velocity),
        "theta_acceleration": np.asarray(theta_acceleration),
        "effective_torque": np.asarray(torque),
    }
