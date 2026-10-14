"""Frozen Stage-1 PINN and full delayed-PID inverse-control utilities.

The retained experiment retrains Stage 1 with the original PyTorch
implementation, saves each fold/seed checkpoint, and freezes it before this
module identifies controller parameters.  The autograd Stage-1 helpers retained
here are portable utilities; the complete runner does not use them to replace
the retained PyTorch training path.  Stage 2 never updates Stage-1 weights:
only controller parameters (and, in the sensitivity branch, a small shared
nuisance-torque basis) are optimized.
"""

from __future__ import annotations

import autograd.numpy as anp
import numpy as np
from autograd import grad
from scipy.optimize import least_squares


GRAVITY_M_S2 = 9.80665


def _initialize_mlp(rng, widths):
    arrays = []
    for input_width, output_width in zip(widths[:-1], widths[1:]):
        arrays.extend(
            [
                rng.normal(
                    0.0,
                    np.sqrt(2.0 / (input_width + output_width)),
                    (input_width, output_width),
                ),
                np.zeros(output_width),
            ]
        )
    return arrays


def initialize_stage1_parameters(condition_size, architecture, seed):
    rng = np.random.default_rng(seed)
    input_size = condition_size + 1
    trajectory_widths = [input_size] + [architecture["trajectory_hidden_size"]] * architecture[
        "trajectory_hidden_layers"
    ] + [2]
    torque_widths = [input_size] + [architecture["torque_hidden_size"]] * architecture[
        "torque_hidden_layers"
    ] + [1]
    arrays = _initialize_mlp(rng, trajectory_widths) + _initialize_mlp(rng, torque_widths)
    shapes = [array.shape for array in arrays]
    sizes = [array.size for array in arrays]
    split_index = 2 * (len(trajectory_widths) - 1)
    flat = np.concatenate([array.ravel() for array in arrays])
    return flat, shapes, sizes, split_index


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
    arrays = unpack(flat, shapes, sizes)
    features = anp.concatenate([time_s[:, None] / time_scale_s, condition], axis=1)
    correction = _mlp(features, arrays[:split_index])
    torque = torque_scale_nm * _mlp(features, arrays[split_index:])[:, 0]
    position = initial_position + initial_velocity * time_s[:, None] + correction * time_s[:, None] ** 2
    return position, torque


def stage1_derivatives(model, time_s, record):
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
        pos = outputs(query)[0]
        return anp.sum(anp.arctan2(pos[:, 0], pos[:, 1]))

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


def stage1_loss_components(flat, metadata, records, weights):
    data_terms = []
    physics_terms = []
    length_terms = []
    torque_terms = []
    torque_rate_terms = []
    for record in records:
        position, _ = stage1_outputs(
            flat,
            metadata["parameter_shapes"],
            metadata["parameter_sizes"],
            metadata["split_index"],
            record["time_data"],
            record["condition_data"],
            record["initial_position_data"],
            record["initial_velocity_data"],
            metadata["time_scale_s"],
            record["torque_scale_data"],
        )
        data_terms.append(anp.mean(((position - record["position_data"]) / record["height_m"]) ** 2))

        def collocation_outputs(query):
            return stage1_outputs(
                flat,
                metadata["parameter_shapes"],
                metadata["parameter_sizes"],
                metadata["split_index"],
                query,
                record["condition_collocation"],
                record["initial_position_collocation"],
                record["initial_velocity_collocation"],
                metadata["time_scale_s"],
                record["torque_scale_collocation"],
            )

        query = record["time_collocation"]
        position_c, torque = collocation_outputs(query)
        theta_function = lambda value: anp.sum(
            anp.arctan2(collocation_outputs(value)[0][:, 0], collocation_outputs(value)[0][:, 1])
        )
        theta_velocity_function = grad(theta_function)
        theta_velocity = theta_velocity_function(query)
        theta_acceleration = grad(lambda value: anp.sum(theta_velocity_function(value)))(query)
        theta = anp.arctan2(position_c[:, 0], position_c[:, 1])
        inertia = record["mass_kg"] * record["length_m"] ** 2
        gravity = record["mass_kg"] * GRAVITY_M_S2 * record["length_m"] * anp.sin(theta)
        residual = inertia * theta_acceleration - gravity - torque + record["damping_nms"] * theta_velocity
        physics_terms.append(anp.mean((residual / record["torque_scale_collocation"]) ** 2))
        radius = anp.sqrt(anp.sum(position_c**2, axis=1))
        length_terms.append(anp.mean(((radius - record["length_m"]) / record["height_m"]) ** 2))
        torque_terms.append(anp.mean((torque / record["torque_scale_collocation"]) ** 2))
        torque_gradient = grad(lambda value: anp.sum(collocation_outputs(value)[1]))(query)
        torque_rate_terms.append(
            anp.mean((torque_gradient / (record["torque_scale_collocation"] / metadata["time_scale_s"])) ** 2)
        )
    components = {
        "data": anp.mean(anp.stack(data_terms)),
        "physics": anp.mean(anp.stack(physics_terms)),
        "rigid_length": anp.mean(anp.stack(length_terms)),
        "effective_torque_l2": anp.mean(anp.stack(torque_terms)),
        "effective_torque_rate": anp.mean(anp.stack(torque_rate_terms)),
    }
    total = components["data"] + sum(weights[name] * components[name] for name in weights)
    return total, components


def train_frozen_stage1(records, condition_size, time_scale_s, architecture, settings, seed):
    flat, shapes, sizes, split_index = initialize_stage1_parameters(condition_size, architecture, seed)
    metadata = {
        "parameter_shapes": shapes,
        "parameter_sizes": sizes,
        "split_index": split_index,
        "time_scale_s": time_scale_s,
    }
    objective = lambda parameters: stage1_loss_components(
        parameters, metadata, records, settings["loss_weights"]
    )[0]
    objective_gradient = grad(objective)
    first = np.zeros_like(flat)
    second = np.zeros_like(flat)
    history = []
    for epoch in range(1, settings["epochs"] + 1):
        gradient = np.asarray(objective_gradient(flat))
        first = 0.9 * first + 0.1 * gradient
        second = 0.999 * second + 0.001 * gradient**2
        flat = flat - settings["learning_rate"] * (first / (1 - 0.9**epoch)) / (
            np.sqrt(second / (1 - 0.999**epoch)) + 1e-8
        )
        if epoch == 1 or epoch % settings["history_interval"] == 0 or epoch == settings["epochs"]:
            total, components = stage1_loss_components(flat, metadata, records, settings["loss_weights"])
            history.append({"epoch": epoch, "total_loss": float(total), **{k: float(v) for k, v in components.items()}})
    return {
        "flat_parameters": np.asarray(flat),
        "parameter_shapes": shapes,
        "parameter_sizes": sizes,
        "split_index": split_index,
        "time_scale_s": time_scale_s,
        "history": history,
    }


def raised_cosine_basis(time_s, duration_s, count=3):
    phase = np.clip(np.asarray(time_s) / max(duration_s, 1e-9), 0.0, 1.0)
    basis = np.zeros((len(phase), count))
    edges = np.linspace(0.0, 1.0, count + 1)
    for index in range(count):
        local = (phase - edges[index]) / (edges[index + 1] - edges[index])
        inside = (local >= 0.0) & (local <= 1.0)
        basis[inside, index] = 0.5 * (1.0 - np.cos(2.0 * np.pi * local[inside]))
    return basis


def delayed(values, time_s, delay_s, initial):
    return np.interp(time_s - delay_s, time_s, values, left=initial, right=values[-1])


def identify_pid(
    frozen_records,
    mass_kg,
    reference_length_m,
    controller_type,
    perturbation_policy,
    delay_frames,
    observation_hz,
    bounds,
    starts,
    nuisance_penalty,
    max_nfev,
):
    """Fit PID parameters to frozen Stage-1 torque and equation residuals."""

    if controller_type not in {"pd", "pid"}:
        raise ValueError(controller_type)
    if perturbation_policy not in {"zero", "nuisance"}:
        raise ValueError(perturbation_policy)
    names = ["alpha_kp", "beta_kd"]
    if controller_type == "pid":
        names.append("kappa_ki")
    names.append("gamma_torque_limit")
    nuisance_count = 3 if perturbation_policy == "nuisance" else 0
    names.extend([f"nuisance_{index}" for index in range(nuisance_count)])
    lower = [bounds.get(name, [-0.5, 0.5])[0] for name in names]
    upper = [bounds.get(name, [-0.5, 0.5])[1] for name in names]
    torque_reference = mass_kg * GRAVITY_M_S2 * reference_length_m
    derivative_reference = np.sqrt((mass_kg * reference_length_m**2) * torque_reference)
    profiles = []

    for delay_frame in delay_frames:
        delay_s = delay_frame / observation_hz

        def residual(parameters):
            index = 0
            kp = parameters[index] * torque_reference; index += 1
            kd = parameters[index] * derivative_reference; index += 1
            if controller_type == "pid":
                ki = parameters[index] * torque_reference; index += 1
            else:
                ki = 0.0
            torque_limit = parameters[index] * torque_reference; index += 1
            nuisance_coefficients = parameters[index:]
            pieces = []
            for record in frozen_records:
                time_s = record["time_s"]
                theta = record["theta"]
                omega = record["theta_velocity"]
                delayed_theta = delayed(theta, time_s, delay_s, theta[0])
                delayed_omega = delayed(omega, time_s, delay_s, omega[0])
                integral = np.concatenate([[0.0], np.cumsum(0.5 * (theta[1:] + theta[:-1]) * np.diff(time_s))])
                raw_control = -kp * delayed_theta - kd * delayed_omega - ki * integral
                control = np.clip(raw_control, -torque_limit, torque_limit)
                nuisance = np.zeros_like(theta)
                if nuisance_count:
                    nuisance = record["torque_scale"] * (raised_cosine_basis(time_s, record["duration_s"], nuisance_count) @ nuisance_coefficients)
                dynamic_required = (
                    record["inertia"] * record["theta_acceleration"]
                    - record["torque_scale"] * np.sin(theta)
                    + record["damping_nms"] * omega
                )
                scale = record["torque_scale"] * np.sqrt(len(theta))
                pieces.append((record["effective_torque"] - control - nuisance) / scale)
                pieces.append((dynamic_required - control - nuisance) / scale)
            if nuisance_count:
                pieces.append(np.sqrt(nuisance_penalty) * np.asarray(nuisance_coefficients))
            return np.concatenate(pieces)

        for start_index, start_values in enumerate(starts):
            start_map = dict(zip(bounds["start_order"], start_values))
            start = np.asarray([start_map.get(name, 0.0) for name in names])
            result = least_squares(
                residual,
                np.clip(start, lower, upper),
                bounds=(lower, upper),
                max_nfev=max_nfev,
                xtol=1e-9,
                ftol=1e-9,
                gtol=1e-9,
            )
            row = {
                "controller_type": controller_type,
                "perturbation_policy": perturbation_policy,
                "delay_frames": delay_frame,
                "delay_s": delay_s,
                "start_index": start_index,
                "training_residual_rmse": float(np.sqrt(np.mean(result.fun**2))),
                "cost": float(result.cost),
                "nfev": int(result.nfev),
                "success": bool(result.success),
                "alpha_kp": float(result.x[0]),
                "beta_kd": float(result.x[1]),
            }
            cursor = 2
            row["kappa_ki"] = float(result.x[cursor]) if controller_type == "pid" else 0.0
            cursor += 1 if controller_type == "pid" else 0
            row["gamma_torque_limit"] = float(result.x[cursor]); cursor += 1
            for nuisance_index in range(3):
                row[f"nuisance_{nuisance_index}"] = (
                    float(result.x[cursor + nuisance_index]) if nuisance_count else 0.0
                )
            row.update(
                {
                    "kp_nm_per_rad": row["alpha_kp"] * torque_reference,
                    "kd_nms_per_rad": row["beta_kd"] * derivative_reference,
                    "ki_nm_per_rad_s": row["kappa_ki"] * torque_reference,
                    "torque_limit_nm": row["gamma_torque_limit"] * torque_reference,
                }
            )
            profiles.append(row)
    profiles.sort(key=lambda row: (row["training_residual_rmse"], row["cost"]))
    return profiles[0], profiles


def simulate_pid(
    time_s,
    initial_theta,
    initial_omega,
    mass_kg,
    length_m,
    damping_nms,
    fit,
    perturbation_policy,
    internal_hz,
):
    """Deterministic fixed-step delayed PID simulation with saturation."""

    observation_hz = round(1.0 / np.median(np.diff(time_s)))
    if internal_hz % observation_hz:
        raise ValueError("internal_hz must be a multiple of observation rate")
    duration_s = float(time_s[-1])
    steps = int(round(duration_s * internal_hz))
    dt = 1.0 / internal_hz
    theta = np.empty(steps + 1); omega = np.empty(steps + 1); integral = np.empty(steps + 1)
    theta[0] = initial_theta; omega[0] = initial_omega; integral[0] = 0.0
    delay_steps = fit["delay_s"] * internal_hz
    inertia = mass_kg * length_m**2
    gravity_scale = mass_kg * GRAVITY_M_S2 * length_m
    nuisance_coefficients = np.array([fit[f"nuisance_{i}"] for i in range(3)])

    def history(values, query, initial):
        if query <= 0:
            return initial
        low = int(np.floor(query)); fraction = query - low
        if fraction <= 1e-12:
            return values[low]
        return (1 - fraction) * values[low] + fraction * values[low + 1]

    def acceleration(angle, rate, integ, delayed_angle, delayed_rate, t):
        raw = -fit["kp_nm_per_rad"] * delayed_angle - fit["kd_nms_per_rad"] * delayed_rate - fit["ki_nm_per_rad_s"] * integ
        control = np.clip(raw, -fit["torque_limit_nm"], fit["torque_limit_nm"])
        nuisance = 0.0
        if perturbation_policy == "nuisance":
            nuisance = gravity_scale * float(raised_cosine_basis(np.array([t]), duration_s, 3)[0] @ nuisance_coefficients)
        return (gravity_scale * np.sin(angle) + control + nuisance - damping_nms * rate) / inertia

    for step in range(steps):
        t = step * dt; y = theta[step]; v = omega[step]; q = integral[step]
        td1 = history(theta, step - delay_steps, initial_theta); vd1 = history(omega, step - delay_steps, initial_omega)
        k1y = v; k1v = acceleration(y, v, q, td1, vd1, t); k1q = y
        td2 = history(theta, step + 0.5 - delay_steps, initial_theta); vd2 = history(omega, step + 0.5 - delay_steps, initial_omega)
        y2=y+0.5*dt*k1y; v2=v+0.5*dt*k1v; q2=q+0.5*dt*k1q
        k2y=v2; k2v=acceleration(y2,v2,q2,td2,vd2,t+0.5*dt); k2q=y2
        y3=y+0.5*dt*k2y; v3=v+0.5*dt*k2v; q3=q+0.5*dt*k2q
        k3y=v3; k3v=acceleration(y3,v3,q3,td2,vd2,t+0.5*dt); k3q=y3
        td4=history(theta,step+1-delay_steps,initial_theta); vd4=history(omega,step+1-delay_steps,initial_omega)
        y4=y+dt*k3y; v4=v+dt*k3v; q4=q+dt*k3q
        k4y=v4; k4v=acceleration(y4,v4,q4,td4,vd4,t+dt); k4q=y4
        theta[step+1]=y+dt*(k1y+2*k2y+2*k3y+k4y)/6
        omega[step+1]=v+dt*(k1v+2*k2v+2*k3v+k4v)/6
        integral[step+1]=q+dt*(k1q+2*k2q+2*k3q+k4q)/6
    stride = internal_hz // observation_hz
    sample = np.arange(0, steps + 1, stride)
    return theta[sample], omega[sample], integral[sample]
