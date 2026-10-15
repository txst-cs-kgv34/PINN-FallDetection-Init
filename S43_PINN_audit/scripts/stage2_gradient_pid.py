"""Gradient-based Stage-2 inverse controller identification.

Stage-1 is frozen. Only Kp, Kd, Ki and a continuous response delay are
trainable. The objective is the normalized inverted-pendulum physics residual;
there is no nuisance torque, effective-torque matching term, torque saturation,
or Stage-1 weight update.
"""

from __future__ import annotations

from dataclasses import dataclass

import autograd.numpy as anp
import numpy as np
from autograd import grad
from autograd.tracer import getval
from scipy.optimize import minimize

from frozen_stage1 import GRAVITY_M_S2, stage1_outputs


@dataclass(frozen=True)
class ParameterBounds:
    alpha_kp: tuple[float, float]
    beta_kd: tuple[float, float]
    kappa_ki: tuple[float, float]
    delay_s: tuple[float, float]


def _network_arrays(state_dict, prefix):
    layer_indices = sorted(
        {
            int(name.split(".")[1])
            for name in state_dict
            if name.startswith(prefix + ".") and name.endswith(".weight")
        }
    )
    arrays = []
    for index in layer_indices:
        weight = np.asarray(state_dict[f"{prefix}.{index}.weight"], dtype=float)
        bias = np.asarray(state_dict[f"{prefix}.{index}.bias"], dtype=float)
        arrays.extend([weight.T, bias])
    return arrays


def load_frozen_stage1(checkpoint, architecture=None):
    """Convert a saved PyTorch checkpoint into the exact frozen array model."""

    del architecture
    trajectory = _network_arrays(checkpoint["state_dict"], "trajectory")
    torque = _network_arrays(checkpoint["state_dict"], "effective_torque")
    arrays = trajectory + torque
    return {
        "flat_parameters": np.concatenate([array.ravel() for array in arrays]),
        "parameter_shapes": [array.shape for array in arrays],
        "parameter_sizes": [array.size for array in arrays],
        "split_index": len(trajectory),
        "time_scale_s": float(checkpoint["time_scale_s"]),
    }


def _stage1_theta(model, query_time, trial, need_acceleration):
    count = len(query_time)
    condition = anp.tile(anp.asarray(trial["condition_scaled"]), (count, 1))
    initial_position = anp.tile(anp.asarray(trial["initial_position"]), (count, 1))
    initial_velocity = anp.tile(anp.asarray(trial["initial_velocity"]), (count, 1))
    torque_scale = anp.full((count, 1), trial["torque_scale"])

    def theta_function(time_values):
        position, _ = stage1_outputs(
            model["flat_parameters"], model["parameter_shapes"],
            model["parameter_sizes"], model["split_index"], time_values,
            condition, initial_position, initial_velocity,
            model["time_scale_s"], torque_scale,
        )
        return anp.arctan2(position[:, 0], position[:, 1])

    theta = theta_function(query_time)
    omega_function = grad(lambda values: anp.sum(theta_function(values)))
    omega = omega_function(query_time)
    result = {"theta": theta, "omega": omega}
    if need_acceleration:
        result["alpha"] = grad(lambda values: anp.sum(omega_function(values)))(query_time)
    return result


def prepare_frozen_records(
    model, trials, mass_kg, damping_nms, time_scale_s,
    collocation_points, maximum_delay_s,
):
    """Cache current-time states; delayed states remain in the gradient graph."""

    del time_scale_s
    records = []
    for trial in trials:
        time_s = np.linspace(0.0, trial["duration_s"], collocation_points)
        if time_s[-1] <= maximum_delay_s:
            raise ValueError(f"{trial['trial']} is shorter than maximum delay")
        current = _stage1_theta(model, time_s, trial, need_acceleration=True)
        theta = np.asarray(current["theta"])
        integral = np.concatenate(
            [[0.0], np.cumsum(0.5 * (theta[1:] + theta[:-1]) * np.diff(time_s))]
        )
        mask = time_s >= maximum_delay_s - 1e-12
        records.append({
            "kind": "stage1", "trial": trial, "model": model,
            "time_s": time_s[mask], "theta": theta[mask],
            "omega": np.asarray(current["omega"])[mask],
            "alpha": np.asarray(current["alpha"])[mask],
            "integral": integral[mask],
            "inertia": mass_kg * trial["length_m"] ** 2,
            "gravity_scale": trial["torque_scale"],
            "damping_nms": damping_nms,
        })
    return records


def _linear_interpolate(query, grid, values):
    """Uniform-grid interpolation, differentiable with respect to query."""

    numeric_query = np.asarray(getval(query), dtype=float)
    numeric_grid = np.asarray(grid, dtype=float)
    numeric_query = np.clip(numeric_query, numeric_grid[0], numeric_grid[-1])
    indices = np.searchsorted(numeric_grid, numeric_query, side="right") - 1
    indices = np.clip(indices, 0, len(numeric_grid) - 2)
    left_t, right_t = grid[indices], grid[indices + 1]
    weight = (query - left_t) / (right_t - left_t)
    return values[indices] * (1.0 - weight) + values[indices + 1] * weight


def _delayed_state(record, delay_s):
    query = record["time_s"] - delay_s
    if record["kind"] == "synthetic":
        return (
            _linear_interpolate(query, record["full_time"], record["full_theta"]),
            _linear_interpolate(query, record["full_time"], record["full_omega"]),
        )
    delayed = _stage1_theta(record["model"], query, record["trial"], False)
    return delayed["theta"], delayed["omega"]


def _logit(value):
    value = np.clip(value, 1e-7, 1.0 - 1e-7)
    return float(np.log(value / (1.0 - value)))


def _raw_start(start, bounds):
    intervals = [bounds.alpha_kp, bounds.beta_kd, bounds.kappa_ki, bounds.delay_s]
    return np.asarray([
        _logit((value - lower) / (upper - lower))
        for value, (lower, upper) in zip(start, intervals)
    ], dtype=float)


def _bounded_parameters(raw, bounds):
    intervals = anp.asarray(
        [bounds.alpha_kp, bounds.beta_kd, bounds.kappa_ki, bounds.delay_s]
    )
    sigmoid = 1.0 / (1.0 + anp.exp(-raw))
    values = intervals[:, 0] + (intervals[:, 1] - intervals[:, 0]) * sigmoid
    return {
        "alpha_kp": values[0], "beta_kd": values[1],
        "kappa_ki": values[2], "delay_s": values[3],
    }


def _physical_parameters(scaled, mass_kg, reference_length_m, integral_time_reference_s):
    torque_reference = mass_kg * GRAVITY_M_S2 * reference_length_m
    inertia_reference = mass_kg * reference_length_m**2
    derivative_reference = np.sqrt(inertia_reference * torque_reference)
    return {
        "kp": scaled["alpha_kp"] * torque_reference,
        "kd": scaled["beta_kd"] * derivative_reference,
        "ki": scaled["kappa_ki"] * torque_reference / integral_time_reference_s,
        "delay_s": scaled["delay_s"],
    }


def physics_loss(
    raw, records, bounds, mass_kg, reference_length_m,
    integral_time_reference_s,
):
    scaled = _bounded_parameters(raw, bounds)
    physical = _physical_parameters(
        scaled, mass_kg, reference_length_m, integral_time_reference_s
    )
    trial_losses, residuals = [], []
    for record in records:
        delayed_theta, delayed_omega = _delayed_state(record, physical["delay_s"])
        torque_control = (
            -physical["kp"] * delayed_theta
            - physical["kd"] * delayed_omega
            - physical["ki"] * record["integral"]
        )
        residual = (
            record["inertia"] * record["alpha"]
            - record["gravity_scale"] * anp.sin(record["theta"])
            + record["damping_nms"] * record["omega"]
            - torque_control
        )
        trial_losses.append(anp.mean((residual / record["gravity_scale"]) ** 2))
        residuals.append(residual)
    return anp.mean(anp.stack(trial_losses)), scaled, physical, residuals


def fixed_delay_physics_loss(
    scaled_gains, fixed_delay_s, records, mass_kg, reference_length_m,
    integral_time_reference_s,
):
    """Physics loss at a fixed delay; only the three PID gains are variables."""

    scaled = {
        "alpha_kp": scaled_gains[0],
        "beta_kd": scaled_gains[1],
        "kappa_ki": scaled_gains[2],
        "delay_s": anp.asarray(fixed_delay_s),
    }
    physical = _physical_parameters(
        scaled, mass_kg, reference_length_m, integral_time_reference_s
    )
    trial_losses, residuals = [], []
    for record in records:
        delayed_theta, delayed_omega = _delayed_state(record, fixed_delay_s)
        torque_control = (
            -physical["kp"] * delayed_theta
            - physical["kd"] * delayed_omega
            - physical["ki"] * record["integral"]
        )
        residual = (
            record["inertia"] * record["alpha"]
            - record["gravity_scale"] * anp.sin(record["theta"])
            + record["damping_nms"] * record["omega"]
            - torque_control
        )
        trial_losses.append(anp.mean((residual / record["gravity_scale"]) ** 2))
        residuals.append(residual)
    return anp.mean(anp.stack(trial_losses)), scaled, physical, residuals


def _projected_gradient(values, gradient_values, lower, upper, tolerance=1e-8):
    """Return a box-constrained projected gradient for convergence reporting."""

    projected = np.asarray(gradient_values, dtype=float).copy()
    values = np.asarray(values, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    projected[(values <= lower + tolerance) & (projected > 0.0)] = 0.0
    projected[(values >= upper - tolerance) & (projected < 0.0)] = 0.0
    return projected


def identify_fixed_delay_gains(
    records, fixed_delay_s, mass_kg, reference_length_m, bounds, starts,
    lbfgs_max_iter=200, integral_time_reference_s=1.0,
):
    """Optimize Kp, Kd and Ki by exact gradients at one predeclared delay."""

    lower = np.asarray(
        [bounds.alpha_kp[0], bounds.beta_kd[0], bounds.kappa_ki[0]], dtype=float
    )
    upper = np.asarray(
        [bounds.alpha_kp[1], bounds.beta_kd[1], bounds.kappa_ki[1]], dtype=float
    )
    scipy_bounds = list(zip(lower, upper))
    objective = lambda gains: fixed_delay_physics_loss(
        gains, fixed_delay_s, records, mass_kg, reference_length_m,
        integral_time_reference_s,
    )[0]
    objective_gradient = grad(objective)
    profiles = []
    for start_index, start in enumerate(starts):
        initial = np.clip(np.asarray(start[:3], dtype=float), lower, upper)
        result = minimize(
            lambda values: float(objective(values)),
            initial,
            jac=lambda values: np.asarray(objective_gradient(values), dtype=float),
            method="L-BFGS-B",
            bounds=scipy_bounds,
            options={"maxiter": lbfgs_max_iter, "ftol": 1e-14, "gtol": 1e-10},
        )
        gains = np.asarray(result.x, dtype=float)
        final_loss, scaled, physical, residuals = fixed_delay_physics_loss(
            gains, fixed_delay_s, records, mass_kg, reference_length_m,
            integral_time_reference_s,
        )
        gradient_values = np.asarray(objective_gradient(gains), dtype=float)
        projected = _projected_gradient(gains, gradient_values, lower, upper)
        residual_nm = np.concatenate([np.asarray(item, dtype=float) for item in residuals])
        profiles.append({
            "start_index": start_index,
            "start_alpha_kp": float(start[0]),
            "start_beta_kd": float(start[1]),
            "start_kappa_ki": float(start[2]),
            "training_physics_loss": float(final_loss),
            "training_normalized_physics_rmse": float(np.sqrt(final_loss)),
            "training_physics_rmse_nm": float(np.sqrt(np.mean(residual_nm**2))),
            "final_gradient_norm": float(np.linalg.norm(gradient_values)),
            "projected_gradient_norm": float(np.linalg.norm(projected)),
            "optimizer_success": bool(result.success),
            "optimizer_iterations": int(result.nit),
            "alpha_kp": float(scaled["alpha_kp"]),
            "beta_kd": float(scaled["beta_kd"]),
            "kappa_ki": float(scaled["kappa_ki"]),
            "delay_s": float(fixed_delay_s),
            "kp_nm_per_rad": float(physical["kp"]),
            "kd_nms_per_rad": float(physical["kd"]),
            "ki_nm_per_rad_s": float(physical["ki"]),
        })
    profiles.sort(key=lambda item: item["training_physics_loss"])
    return profiles[0], profiles


def identify_gradient_pid(
    records, mass_kg, reference_length_m, bounds, starts, adam_epochs,
    adam_learning_rate, lbfgs_max_iter, gradient_clip_norm,
    integral_time_reference_s=1.0,
):
    """Optimize the four controller variables with exact automatic gradients."""

    objective = lambda raw: physics_loss(
        raw, records, bounds, mass_kg, reference_length_m,
        integral_time_reference_s,
    )[0]
    objective_gradient = grad(objective)
    profiles = []
    for start_index, start in enumerate(starts):
        raw = _raw_start(start, bounds)
        first, second = np.zeros_like(raw), np.zeros_like(raw)
        history = []
        for epoch in range(1, adam_epochs + 1):
            gradient = np.asarray(objective_gradient(raw), dtype=float)
            norm = np.linalg.norm(gradient)
            if norm > gradient_clip_norm:
                gradient = gradient * gradient_clip_norm / norm
            first = 0.9 * first + 0.1 * gradient
            second = 0.999 * second + 0.001 * gradient**2
            raw = raw - adam_learning_rate * (first / (1.0 - 0.9**epoch)) / (
                np.sqrt(second / (1.0 - 0.999**epoch)) + 1e-8
            )
            if epoch == 1 or epoch % 100 == 0 or epoch == adam_epochs:
                history.append({"epoch": epoch, "loss": float(objective(raw))})
        if lbfgs_max_iter:
            result = minimize(
                lambda values: float(objective(values)), raw,
                jac=lambda values: np.asarray(objective_gradient(values), dtype=float),
                method="L-BFGS-B",
                options={"maxiter": lbfgs_max_iter, "ftol": 1e-14, "gtol": 1e-10},
            )
            raw = np.asarray(result.x, dtype=float)
        final_loss, scaled, physical, residuals = physics_loss(
            raw, records, bounds, mass_kg, reference_length_m,
            integral_time_reference_s,
        )
        residual_nm = np.concatenate([np.asarray(item, dtype=float) for item in residuals])
        profiles.append({
            "start_index": start_index,
            "start_alpha_kp": float(start[0]), "start_beta_kd": float(start[1]),
            "start_kappa_ki": float(start[2]), "start_delay_s": float(start[3]),
            "training_physics_loss": float(final_loss),
            "training_normalized_physics_rmse": float(np.sqrt(final_loss)),
            "training_physics_rmse_nm": float(np.sqrt(np.mean(residual_nm**2))),
            "final_gradient_norm": float(np.linalg.norm(objective_gradient(raw))),
            "alpha_kp": float(scaled["alpha_kp"]),
            "beta_kd": float(scaled["beta_kd"]),
            "kappa_ki": float(scaled["kappa_ki"]),
            "delay_s": float(scaled["delay_s"]),
            "kp_nm_per_rad": float(physical["kp"]),
            "kd_nms_per_rad": float(physical["kd"]),
            "ki_nm_per_rad_s": float(physical["ki"]),
            "history": history,
        })
    profiles.sort(key=lambda item: item["training_physics_loss"])
    return profiles[0], profiles


def _history(values, query_index, initial):
    if query_index <= 0.0:
        return float(initial)
    upper = len(values) - 1
    if query_index >= upper:
        return float(values[upper])
    left = int(np.floor(query_index))
    weight = query_index - left
    return float(values[left] * (1.0 - weight) + values[left + 1] * weight)


def simulate_unbounded_pid(
    time_s, initial_theta, initial_omega, mass_kg, length_m,
    damping_nms, fit, internal_hz,
):
    """Forward-simulate unsaturated PID with zero perturbation torque."""

    duration_s = float(time_s[-1])
    steps = int(np.ceil(duration_s * internal_hz))
    internal_time = np.arange(steps + 1, dtype=float) / internal_hz
    dt = 1.0 / internal_hz
    theta, omega, integral = (np.zeros(steps + 1) for _ in range(3))
    theta[0], omega[0] = initial_theta, initial_omega
    delay_steps = fit["delay_s"] * internal_hz
    inertia = mass_kg * length_m**2
    gravity_scale = mass_kg * GRAVITY_M_S2 * length_m

    def acceleration(angle, rate, integ, delayed_angle, delayed_rate):
        torque = (
            -fit["kp_nm_per_rad"] * delayed_angle
            - fit["kd_nms_per_rad"] * delayed_rate
            - fit["ki_nm_per_rad_s"] * integ
        )
        return (gravity_scale * np.sin(angle) + torque - damping_nms * rate) / inertia

    for step in range(steps):
        td1 = _history(theta, step - delay_steps, initial_theta)
        vd1 = _history(omega, step - delay_steps, initial_omega)
        k1 = (omega[step], acceleration(theta[step], omega[step], integral[step], td1, vd1), theta[step])
        td2 = _history(theta, step + 0.5 - delay_steps, initial_theta)
        vd2 = _history(omega, step + 0.5 - delay_steps, initial_omega)
        s2 = (theta[step] + 0.5*dt*k1[0], omega[step] + 0.5*dt*k1[1], integral[step] + 0.5*dt*k1[2])
        k2 = (s2[1], acceleration(*s2, td2, vd2), s2[0])
        s3 = (theta[step] + 0.5*dt*k2[0], omega[step] + 0.5*dt*k2[1], integral[step] + 0.5*dt*k2[2])
        k3 = (s3[1], acceleration(*s3, td2, vd2), s3[0])
        td4 = _history(theta, step + 1.0 - delay_steps, initial_theta)
        vd4 = _history(omega, step + 1.0 - delay_steps, initial_omega)
        s4 = (theta[step] + dt*k3[0], omega[step] + dt*k3[1], integral[step] + dt*k3[2])
        k4 = (s4[1], acceleration(*s4, td4, vd4), s4[0])
        theta[step + 1] = theta[step] + dt*(k1[0] + 2*k2[0] + 2*k3[0] + k4[0])/6.0
        omega[step + 1] = omega[step] + dt*(k1[1] + 2*k2[1] + 2*k3[1] + k4[1])/6.0
        integral[step + 1] = integral[step] + dt*(k1[2] + 2*k2[2] + 2*k3[2] + k4[2])/6.0
        if not np.isfinite(theta[step + 1]) or abs(theta[step + 1]) > 100.0:
            theta[step + 1:], omega[step + 1:], integral[step + 1:] = np.nan, np.nan, np.nan
            break
    return np.interp(time_s, internal_time, theta), internal_time, theta, omega, integral


def build_synthetic_records(
    mass_kg, length_m, damping_nms, true_fit, initial_states,
    duration_s, internal_hz, maximum_delay_s,
):
    observation_time = np.arange(int(round(duration_s * internal_hz)) + 1) / internal_hz
    records = []
    for initial_theta, initial_omega in initial_states:
        _, full_time, theta, omega, integral = simulate_unbounded_pid(
            observation_time, initial_theta, initial_omega, mass_kg, length_m,
            damping_nms, true_fit, internal_hz,
        )
        delay_steps = true_fit["delay_s"] * internal_hz
        inertia = mass_kg * length_m**2
        gravity_scale = mass_kg * GRAVITY_M_S2 * length_m
        alpha = np.empty_like(theta)
        for index in range(len(theta)):
            td = _history(theta, index - delay_steps, initial_theta)
            vd = _history(omega, index - delay_steps, initial_omega)
            torque = -true_fit["kp_nm_per_rad"]*td - true_fit["kd_nms_per_rad"]*vd - true_fit["ki_nm_per_rad_s"]*integral[index]
            alpha[index] = (gravity_scale*np.sin(theta[index]) + torque - damping_nms*omega[index]) / inertia
        mask = full_time >= maximum_delay_s - 1e-12
        records.append({
            "kind": "synthetic", "time_s": full_time[mask], "theta": theta[mask],
            "omega": omega[mask], "alpha": alpha[mask], "integral": integral[mask],
            "inertia": inertia, "gravity_scale": gravity_scale,
            "damping_nms": damping_nms, "full_time": full_time,
            "full_theta": theta, "full_omega": omega,
        })
    return records
