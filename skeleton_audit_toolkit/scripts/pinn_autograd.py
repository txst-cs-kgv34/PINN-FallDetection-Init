"""Small deterministic autograd PINN used by the A13 pilot."""

import autograd.numpy as anp
import numpy as np
from autograd import grad


GRAVITY_M_S2 = 9.80665


def initialize_parameters(input_size, hidden_size, seed):
    rng = np.random.default_rng(seed)
    arrays = [
        rng.normal(
            0, np.sqrt(2 / (input_size + hidden_size)), (input_size, hidden_size)
        ),
        np.zeros(hidden_size),
        rng.normal(0, np.sqrt(2 / (2 * hidden_size)), (hidden_size, hidden_size)),
        np.zeros(hidden_size),
        rng.normal(0, np.sqrt(2 / (hidden_size + 6)), (hidden_size, 6)),
        np.zeros(6),
    ]
    shapes = [array.shape for array in arrays]
    sizes = [array.size for array in arrays]
    flat = np.concatenate([array.ravel() for array in arrays])
    return flat, shapes, sizes


def unpack_parameters(flat, shapes, sizes):
    arrays = []
    start = 0
    for shape, size in zip(shapes, sizes):
        arrays.append(anp.reshape(flat[start : start + size], shape))
        start += size
    return arrays


def network_outputs(flat, shapes, sizes, time_s, condition, time_scale_s):
    w1, b1, w2, b2, w3, b3 = unpack_parameters(flat, shapes, sizes)
    features = anp.concatenate([time_s[:, None] / time_scale_s, condition], axis=1)
    hidden1 = anp.tanh(anp.dot(features, w1) + b1)
    hidden2 = anp.tanh(anp.dot(hidden1, w2) + b2)
    return anp.dot(hidden2, w3) + b3


def position_and_effective_acceleration(
    flat, shapes, sizes, time_s, condition, initial_velocity, time_scale_s
):
    outputs = network_outputs(flat, shapes, sizes, time_s, condition, time_scale_s)
    correction = outputs[:, :3]
    effective_acceleration = GRAVITY_M_S2 * outputs[:, 3:]
    position = initial_velocity * time_s[:, None] + correction * time_s[:, None] ** 2
    return position, effective_acceleration


def time_derivatives(
    flat, shapes, sizes, time_s, condition, initial_velocity, time_scale_s
):
    velocities = []
    accelerations = []
    jerks = []
    for axis in range(3):

        def position_sum(query_time):
            position, _ = position_and_effective_acceleration(
                flat,
                shapes,
                sizes,
                query_time,
                condition,
                initial_velocity,
                time_scale_s,
            )
            return anp.sum(position[:, axis])

        velocity_function = grad(position_sum)
        velocity = velocity_function(time_s)
        acceleration = grad(lambda query_time: anp.sum(velocity_function(query_time)))(
            time_s
        )
        velocities.append(velocity)
        accelerations.append(acceleration)

        def effective_acceleration_sum(query_time):
            _, effective = position_and_effective_acceleration(
                flat,
                shapes,
                sizes,
                query_time,
                condition,
                initial_velocity,
                time_scale_s,
            )
            return anp.sum(effective[:, axis])

        jerks.append(grad(effective_acceleration_sum)(time_s))
    return (
        anp.stack(velocities, axis=1),
        anp.stack(accelerations, axis=1),
        anp.stack(jerks, axis=1),
    )


def loss_components(flat, shapes, sizes, trials, time_scale_s, weights):
    data_terms = []
    physics_terms = []
    force_terms = []
    jerk_terms = []
    gravity = anp.array([0.0, -GRAVITY_M_S2, 0.0])
    for trial in trials:
        predicted, _ = position_and_effective_acceleration(
            flat,
            shapes,
            sizes,
            trial["time_data"],
            trial["condition_data"],
            trial["initial_velocity_data"],
            time_scale_s,
        )
        data_terms.append(
            anp.mean(((predicted - trial["position_data"]) / trial["height_m"]) ** 2)
        )
        _, acceleration, effective_jerk = time_derivatives(
            flat,
            shapes,
            sizes,
            trial["time_collocation"],
            trial["condition_collocation"],
            trial["initial_velocity_collocation"],
            time_scale_s,
        )
        _, effective_acceleration = position_and_effective_acceleration(
            flat,
            shapes,
            sizes,
            trial["time_collocation"],
            trial["condition_collocation"],
            trial["initial_velocity_collocation"],
            time_scale_s,
        )
        residual = acceleration - gravity - effective_acceleration
        physics_terms.append(anp.mean((residual / GRAVITY_M_S2) ** 2))
        force_terms.append(anp.mean((effective_acceleration / GRAVITY_M_S2) ** 2))
        jerk_scale = GRAVITY_M_S2 / time_scale_s
        jerk_terms.append(anp.mean((effective_jerk / jerk_scale) ** 2))
    components = {
        "data": anp.mean(anp.stack(data_terms)),
        "physics": anp.mean(anp.stack(physics_terms)),
        "effective_acceleration_l2": anp.mean(anp.stack(force_terms)),
        "effective_acceleration_jerk": anp.mean(anp.stack(jerk_terms)),
    }
    total = sum(weights[name] * value for name, value in components.items())
    return total, components


def train_pinn(
    trials,
    condition_size,
    time_scale_s,
    hidden_size,
    epochs,
    learning_rate,
    weights,
    seed,
):
    flat, shapes, sizes = initialize_parameters(condition_size + 1, hidden_size, seed)

    def objective(parameters):
        return loss_components(
            parameters, shapes, sizes, trials, time_scale_s, weights
        )[0]

    objective_gradient = grad(objective)
    first_moment = np.zeros_like(flat)
    second_moment = np.zeros_like(flat)
    history = []
    for epoch in range(1, epochs + 1):
        gradient = np.asarray(objective_gradient(flat))
        first_moment = 0.9 * first_moment + 0.1 * gradient
        second_moment = 0.999 * second_moment + 0.001 * gradient**2
        corrected_first = first_moment / (1 - 0.9**epoch)
        corrected_second = second_moment / (1 - 0.999**epoch)
        flat = flat - learning_rate * corrected_first / (
            np.sqrt(corrected_second) + 1e-8
        )
        if epoch == 1 or epoch % 50 == 0 or epoch == epochs:
            total, components = loss_components(
                flat, shapes, sizes, trials, time_scale_s, weights
            )
            history.append(
                {
                    "epoch": epoch,
                    "total_loss": float(total),
                    **{name: float(value) for name, value in components.items()},
                }
            )
    return {
        "flat_parameters": flat,
        "parameter_shapes": shapes,
        "parameter_sizes": sizes,
        "history": history,
    }


def evaluate_pinn(model, time_s, condition, initial_velocity, time_scale_s):
    flat = model["flat_parameters"]
    shapes = model["parameter_shapes"]
    sizes = model["parameter_sizes"]
    position, effective_acceleration = position_and_effective_acceleration(
        flat, shapes, sizes, time_s, condition, initial_velocity, time_scale_s
    )
    velocity, acceleration, _ = time_derivatives(
        flat, shapes, sizes, time_s, condition, initial_velocity, time_scale_s
    )
    gravity = np.array([0.0, -GRAVITY_M_S2, 0.0])
    residual = acceleration - gravity - effective_acceleration
    return {
        "position": np.asarray(position),
        "velocity": np.asarray(velocity),
        "acceleration": np.asarray(acceleration),
        "effective_acceleration": np.asarray(effective_acceleration),
        "physics_residual": np.asarray(residual),
    }
