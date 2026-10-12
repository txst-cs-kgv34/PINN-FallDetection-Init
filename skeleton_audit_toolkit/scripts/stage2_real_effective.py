"""Utilities for exploratory delayed-feedback fitting to real skeleton falls."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from stage2a_delayed_pd import Controller, PerturbationTrial, Plant, simulate_trials


@dataclass
class RealTrial:
    trial: str
    activity: str
    horizontal_axis: str
    time_s: np.ndarray
    position_m: np.ndarray
    theta_rad: np.ndarray
    initial_theta_rad: float
    initial_omega_rad_s: float
    initial_position_m: np.ndarray
    initial_velocity_m_s: np.ndarray
    onset_length_m: float

    @property
    def duration_s(self):
        return float(self.time_s[-1])


def simulation_trial(record, amplitude_ratio, onset_s, duration_s):
    return PerturbationTrial(
        trial=record.trial,
        split="real",
        initial_theta_rad=record.initial_theta_rad,
        initial_omega_rad_s=record.initial_omega_rad_s,
        pulse_onset_s=onset_s,
        pulse_duration_s=duration_s,
        pulse_amplitude_ratio=amplitude_ratio,
    )


def simulate_record(
    record,
    mass_kg,
    length_scale,
    damping_ratio,
    controller,
    pulse_amplitude_ratio,
    pulse_onset_s,
    pulse_duration_s,
    internal_hz,
    observation_hz,
):
    length = record.onset_length_m * length_scale
    undamped = Plant(mass_kg, length, 0.0)
    plant = Plant(
        mass_kg,
        length,
        damping_ratio * undamped.derivative_gain_scale_nms,
    )
    trial = simulation_trial(
        record, pulse_amplitude_ratio, pulse_onset_s, pulse_duration_s
    )
    result = simulate_trials(
        plant,
        controller,
        [trial],
        record.duration_s,
        internal_hz,
        observation_hz,
    )
    return plant, result["theta_rad"][0]


def recover_real_effective_controller(
    training_records,
    mass_kg,
    length_scale,
    damping_ratio,
    perturbation_model,
    delay_frames,
    observation_hz,
    internal_hz,
    pulse_onset_s,
    pulse_duration_s,
    bounds,
    starts,
    max_nfev,
):
    """Fit common dimensionless feedback parameters across real training trials.

    For ``shared_pulse``, one common normalized pulse amplitude is estimated
    from training trials only. It is an explicit proxy, not a measured force.
    """

    if perturbation_model not in {"zero", "shared_pulse"}:
        raise ValueError(f"unsupported perturbation model: {perturbation_model}")
    fit_pulse = perturbation_model == "shared_pulse"
    parameter_names = ["alpha_kp", "beta_kd", "gamma_torque_limit"]
    lower = [bounds[name][0] for name in parameter_names]
    upper = [bounds[name][1] for name in parameter_names]
    if fit_pulse:
        parameter_names.append("pulse_amplitude_ratio")
        lower.append(bounds["pulse_amplitude_ratio"][0])
        upper.append(bounds["pulse_amplitude_ratio"][1])
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    profiles = []

    for delay_frame in delay_frames:
        delay_s = delay_frame / observation_hz

        def residual(parameters):
            controller = Controller(
                alpha_kp=float(parameters[0]),
                beta_kd=float(parameters[1]),
                delay_s=delay_s,
                gamma_torque_limit=float(parameters[2]),
            )
            pulse = float(parameters[3]) if fit_pulse else 0.0
            pieces = []
            for record in training_records:
                try:
                    _, predicted = simulate_record(
                        record,
                        mass_kg,
                        length_scale,
                        damping_ratio,
                        controller,
                        pulse,
                        pulse_onset_s,
                        pulse_duration_s,
                        internal_hz,
                        observation_hz,
                    )
                except (FloatingPointError, ValueError, OverflowError):
                    return np.full(sum(len(item.time_s) for item in training_records), 1e3)
                if (
                    predicted.shape != record.theta_rad.shape
                    or not np.all(np.isfinite(predicted))
                ):
                    return np.full(sum(len(item.time_s) for item in training_records), 1e3)
                scale = max(float(np.ptp(record.theta_rad)), np.deg2rad(10.0))
                pieces.append(
                    (predicted - record.theta_rad) / scale / np.sqrt(len(record.time_s))
                )
            return np.concatenate(pieces)

        for start_index, raw_start in enumerate(starts):
            start = np.asarray(raw_start[: len(parameter_names)], dtype=float)
            result = least_squares(
                residual,
                np.clip(start, lower, upper),
                bounds=(lower, upper),
                max_nfev=max_nfev,
                xtol=1e-8,
                ftol=1e-8,
                gtol=1e-8,
            )
            profiles.append(
                {
                    "delay_frames": delay_frame,
                    "delay_s": delay_s,
                    "start_index": start_index,
                    "alpha_kp": float(result.x[0]),
                    "beta_kd": float(result.x[1]),
                    "gamma_torque_limit": float(result.x[2]),
                    "pulse_amplitude_ratio": (
                        float(result.x[3]) if fit_pulse else 0.0
                    ),
                    "training_objective_rmse": float(
                        np.sqrt(np.mean(result.fun**2))
                    ),
                    "cost": float(result.cost),
                    "optimality": float(result.optimality),
                    "nfev": int(result.nfev),
                    "success": bool(result.success),
                    "valid_profile": bool(
                        np.all(np.isfinite(result.fun))
                        and np.sqrt(np.mean(result.fun**2)) < 100.0
                    ),
                }
            )
    profiles.sort(
        key=lambda row: (
            not row["valid_profile"],
            row["training_objective_rmse"],
            row["cost"],
        )
    )
    valid_profiles = [row for row in profiles if row["valid_profile"]]
    if not valid_profiles:
        raise RuntimeError(
            "all optimizer profiles produced invalid simulations; "
            "no controller estimate is reportable"
        )
    best = valid_profiles[0]
    controller = Controller(
        alpha_kp=best["alpha_kp"],
        beta_kd=best["beta_kd"],
        delay_s=best["delay_s"],
        gamma_torque_limit=best["gamma_torque_limit"],
    )
    return controller, best["pulse_amplitude_ratio"], profiles


def position_from_theta(theta_rad, length_m):
    return np.column_stack(
        [length_m * np.sin(theta_rad), length_m * np.cos(theta_rad)]
    )


def trajectory_metrics(actual_position, actual_theta, predicted_position, predicted_theta):
    difference = predicted_position - actual_position
    return {
        "horizontal_rmse_m": float(np.sqrt(np.mean(difference[:, 0] ** 2))),
        "vertical_rmse_m": float(np.sqrt(np.mean(difference[:, 1] ** 2))),
        "xy_rmse_m": float(np.sqrt(np.mean(difference**2))),
        "theta_rmse_deg": float(
            np.rad2deg(np.sqrt(np.mean((predicted_theta - actual_theta) ** 2)))
        ),
        "endpoint_error_m": float(np.linalg.norm(difference[-1])),
    }
