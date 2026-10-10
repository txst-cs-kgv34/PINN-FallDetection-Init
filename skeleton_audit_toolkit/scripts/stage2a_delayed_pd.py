"""Stage-2A delayed-PD simulation and parameter recovery utilities.

This module deliberately retains the Stage-1 plant: one rigid link, fixed
pivot, point-mass inertia ``I=m*l**2`` and zero passive damping.  Stage 2A adds
a known external torque and a delayed, saturated PD controller.  Parameters
are expressed in dimensionless subject-scaled form during estimation:

    alpha = Kp / (m*g*l)
    beta  = Kd / sqrt(I*m*g*l)
    gamma = tau_max / (m*g*l)

The delay is searched on the observation-frame grid because a 30 Hz trajectory
cannot support finer delay claims.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares
from scipy.signal import butter, sosfiltfilt


GRAVITY_M_S2 = 9.80665


@dataclass(frozen=True)
class Plant:
    mass_kg: float
    length_m: float
    damping_nms: float = 0.0

    @property
    def inertia_kg_m2(self) -> float:
        return self.mass_kg * self.length_m**2

    @property
    def gravity_torque_scale_nm(self) -> float:
        return self.mass_kg * GRAVITY_M_S2 * self.length_m

    @property
    def derivative_gain_scale_nms(self) -> float:
        return float(
            np.sqrt(self.inertia_kg_m2 * self.gravity_torque_scale_nm)
        )


@dataclass(frozen=True)
class Controller:
    alpha_kp: float
    beta_kd: float
    delay_s: float
    gamma_torque_limit: float

    def physical(self, plant: Plant) -> dict[str, float]:
        return {
            "kp_nm_per_rad": self.alpha_kp * plant.gravity_torque_scale_nm,
            "kd_nms_per_rad": self.beta_kd * plant.derivative_gain_scale_nms,
            "delay_s": self.delay_s,
            "torque_limit_nm": (
                self.gamma_torque_limit * plant.gravity_torque_scale_nm
            ),
        }


@dataclass(frozen=True)
class PerturbationTrial:
    trial: str
    split: str
    initial_theta_rad: float
    initial_omega_rad_s: float
    pulse_onset_s: float
    pulse_duration_s: float
    pulse_amplitude_ratio: float
    pulse2_onset_s: float | None = None
    pulse2_duration_s: float | None = None
    pulse2_amplitude_ratio: float = 0.0


def raised_cosine_pulse(time_s, onset_s, duration_s, amplitude_nm):
    """Smooth one-sided pulse that is zero at both endpoints."""

    time_s = np.asarray(time_s, dtype=float)
    phase = (time_s - onset_s) / duration_s
    inside = (phase >= 0.0) & (phase <= 1.0)
    output = np.zeros_like(time_s)
    output[inside] = amplitude_nm * 0.5 * (
        1.0 - np.cos(2.0 * np.pi * phase[inside])
    )
    return output


def perturbation_torque(time_s, trial: PerturbationTrial, plant: Plant):
    scale = plant.gravity_torque_scale_nm
    torque = raised_cosine_pulse(
        time_s,
        trial.pulse_onset_s,
        trial.pulse_duration_s,
        trial.pulse_amplitude_ratio * scale,
    )
    if trial.pulse2_onset_s is not None:
        torque = torque + raised_cosine_pulse(
            time_s,
            trial.pulse2_onset_s,
            float(trial.pulse2_duration_s),
            trial.pulse2_amplitude_ratio * scale,
        )
    return torque


def _scalar_raised_cosine(t, onset, duration, amplitude):
    phase = (t - onset) / duration
    if phase < 0.0 or phase > 1.0:
        return 0.0
    return amplitude * 0.5 * (1.0 - np.cos(2.0 * np.pi * phase))


def _scalar_perturbation_torque(t, trial: PerturbationTrial, scale):
    torque = _scalar_raised_cosine(
        t,
        trial.pulse_onset_s,
        trial.pulse_duration_s,
        trial.pulse_amplitude_ratio * scale,
    )
    if trial.pulse2_onset_s is not None:
        torque += _scalar_raised_cosine(
            t,
            trial.pulse2_onset_s,
            float(trial.pulse2_duration_s),
            trial.pulse2_amplitude_ratio * scale,
        )
    return torque


def _delayed(history, query_index, initial):
    """Linearly interpolate a previously computed fixed-step state."""

    if query_index <= 0.0:
        return initial
    lower = int(np.floor(query_index))
    fraction = query_index - lower
    if fraction <= 1e-12:
        return history[lower]
    return (1.0 - fraction) * history[lower] + fraction * history[lower + 1]


def simulate_trials(
    plant: Plant,
    controller: Controller,
    trials: list[PerturbationTrial],
    duration_s: float,
    internal_hz: int = 300,
    observation_hz: int = 30,
):
    """Simulate all trials together with a deterministic fixed-step RK4 DDE.

    The pre-history is the trial's initial state.  Delays are required to be at
    least one internal step so every RK4 delayed lookup uses available history.
    """

    if internal_hz % observation_hz:
        raise ValueError("internal_hz must be an integer multiple of observation_hz")
    dt = 1.0 / internal_hz
    delay_steps = controller.delay_s * internal_hz
    if delay_steps < 1.0:
        raise ValueError("delay must be at least one internal integration step")
    steps = int(round(duration_s * internal_hz))
    time = np.arange(steps + 1, dtype=float) * dt
    count = len(trials)
    theta = np.empty((steps + 1, count), dtype=float)
    omega = np.empty_like(theta)
    theta[0] = [trial.initial_theta_rad for trial in trials]
    omega[0] = [trial.initial_omega_rad_s for trial in trials]
    initial_theta = theta[0].copy()
    initial_omega = omega[0].copy()

    physical = controller.physical(plant)
    kp = physical["kp_nm_per_rad"]
    kd = physical["kd_nms_per_rad"]
    torque_limit = physical["torque_limit_nm"]
    inertia = plant.inertia_kg_m2
    gravity_scale = plant.gravity_torque_scale_nm
    damping = plant.damping_nms

    def acceleration(angle, rate, delayed_angle, delayed_rate, external):
        control = np.clip(
            -kp * delayed_angle - kd * delayed_rate,
            -torque_limit,
            torque_limit,
        )
        return (
            gravity_scale * np.sin(angle) + control + external - damping * rate
        ) / inertia

    half_time = np.arange(2 * steps + 1, dtype=float) * (0.5 * dt)
    external_half = np.stack(
        [perturbation_torque(half_time, trial, plant) for trial in trials], axis=1
    )

    for index in range(steps):
        y0 = theta[index]
        v0 = omega[index]

        q1 = index - delay_steps
        td1 = _delayed(theta, q1, initial_theta)
        vd1 = _delayed(omega, q1, initial_omega)
        k1_y = v0
        k1_v = acceleration(y0, v0, td1, vd1, external_half[2 * index])

        q2 = index + 0.5 - delay_steps
        td2 = _delayed(theta, q2, initial_theta)
        vd2 = _delayed(omega, q2, initial_omega)
        y2 = y0 + 0.5 * dt * k1_y
        v2 = v0 + 0.5 * dt * k1_v
        k2_y = v2
        k2_v = acceleration(y2, v2, td2, vd2, external_half[2 * index + 1])

        y3 = y0 + 0.5 * dt * k2_y
        v3 = v0 + 0.5 * dt * k2_v
        k3_y = v3
        k3_v = acceleration(y3, v3, td2, vd2, external_half[2 * index + 1])

        q4 = index + 1.0 - delay_steps
        td4 = _delayed(theta, q4, initial_theta)
        vd4 = _delayed(omega, q4, initial_omega)
        y4 = y0 + dt * k3_y
        v4 = v0 + dt * k3_v
        k4_y = v4
        k4_v = acceleration(y4, v4, td4, vd4, external_half[2 * index + 2])

        theta[index + 1] = y0 + dt * (
            k1_y + 2.0 * k2_y + 2.0 * k3_y + k4_y
        ) / 6.0
        omega[index + 1] = v0 + dt * (
            k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v
        ) / 6.0

    stride = internal_hz // observation_hz
    sample = np.arange(0, steps + 1, stride)
    return {
        "time_s": time[sample],
        "theta_rad": theta[sample].T,
        "omega_rad_s": omega[sample].T,
        "theta_internal_rad": theta.T,
        "omega_internal_rad_s": omega.T,
        "internal_time_s": time,
    }


def zero_phase_filter(values, sample_hz=30.0, cutoff_hz=1.5, order=6):
    """Apply the Stage-1 observation filter along the time axis."""

    values = np.asarray(values, dtype=float)
    sos = butter(order, cutoff_hz, btype="low", fs=sample_hz, output="sos")
    return sosfiltfilt(sos, values, axis=-1)


def make_observations(
    simulation,
    rng,
    noise_sd_rad,
    sample_hz=30.0,
    cutoff_hz=1.5,
    filter_order=6,
):
    noisy = simulation["theta_rad"] + rng.normal(
        0.0, noise_sd_rad, simulation["theta_rad"].shape
    )
    return zero_phase_filter(noisy, sample_hz, cutoff_hz, filter_order)


def filtered_prediction(
    plant,
    controller,
    trials,
    duration_s,
    internal_hz,
    observation_hz,
    cutoff_hz,
    filter_order,
):
    simulated = simulate_trials(
        plant,
        controller,
        trials,
        duration_s,
        internal_hz,
        observation_hz,
    )
    return zero_phase_filter(
        simulated["theta_rad"], observation_hz, cutoff_hz, filter_order
    )


def recover_controller(
    plant: Plant,
    trials: list[PerturbationTrial],
    observed_theta_rad,
    duration_s: float,
    delay_frames: list[int],
    observation_hz: int,
    internal_hz: int,
    cutoff_hz: float,
    filter_order: int,
    bounds: dict,
    starts: list[list[float]],
    max_nfev: int = 80,
):
    """Profile over frame-resolved delays and fit three scaled parameters."""

    observed = np.asarray(observed_theta_rad, dtype=float)
    scale = max(float(np.std(observed)), np.deg2rad(0.25))
    records = []
    lower = np.array(
        [bounds["alpha_kp"][0], bounds["beta_kd"][0], bounds["gamma_torque_limit"][0]]
    )
    upper = np.array(
        [bounds["alpha_kp"][1], bounds["beta_kd"][1], bounds["gamma_torque_limit"][1]]
    )

    for frame_delay in delay_frames:
        delay_s = frame_delay / observation_hz

        def residual(parameters):
            controller = Controller(
                alpha_kp=float(parameters[0]),
                beta_kd=float(parameters[1]),
                delay_s=delay_s,
                gamma_torque_limit=float(parameters[2]),
            )
            predicted = filtered_prediction(
                plant,
                controller,
                trials,
                duration_s,
                internal_hz,
                observation_hz,
                cutoff_hz,
                filter_order,
            )
            difference = (predicted - observed) / scale
            if not np.all(np.isfinite(difference)) or np.max(np.abs(predicted)) > 3.0:
                return np.full(observed.size, 1e3)
            return difference.ravel()

        for start_index, start in enumerate(starts):
            result = least_squares(
                residual,
                np.clip(np.asarray(start, dtype=float), lower, upper),
                bounds=(lower, upper),
                max_nfev=max_nfev,
                xtol=1e-8,
                ftol=1e-8,
                gtol=1e-8,
                verbose=0,
            )
            rmse_rad = float(np.sqrt(np.mean((result.fun * scale) ** 2)))
            records.append(
                {
                    "delay_frames": frame_delay,
                    "delay_s": delay_s,
                    "start_index": start_index,
                    "alpha_kp": float(result.x[0]),
                    "beta_kd": float(result.x[1]),
                    "gamma_torque_limit": float(result.x[2]),
                    "training_theta_rmse_rad": rmse_rad,
                    "cost": float(result.cost),
                    "optimality": float(result.optimality),
                    "nfev": int(result.nfev),
                    "success": bool(result.success),
                }
            )

    records.sort(key=lambda row: (row["training_theta_rmse_rad"], row["cost"]))
    best = records[0]
    controller = Controller(
        alpha_kp=best["alpha_kp"],
        beta_kd=best["beta_kd"],
        delay_s=best["delay_s"],
        gamma_torque_limit=best["gamma_torque_limit"],
    )
    return controller, records


def control_torque_from_state(plant, controller, theta, omega, time_s):
    """Reconstruct controller torque on a sampled state for diagnostics."""

    delay = controller.delay_s
    delayed_theta = np.interp(time_s - delay, time_s, theta, left=theta[0])
    delayed_omega = np.interp(time_s - delay, time_s, omega, left=omega[0])
    physical = controller.physical(plant)
    unsaturated = (
        -physical["kp_nm_per_rad"] * delayed_theta
        - physical["kd_nms_per_rad"] * delayed_omega
    )
    torque = np.clip(
        unsaturated,
        -physical["torque_limit_nm"],
        physical["torque_limit_nm"],
    )
    return torque, unsaturated

