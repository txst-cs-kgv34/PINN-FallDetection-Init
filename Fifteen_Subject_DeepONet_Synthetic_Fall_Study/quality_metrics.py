from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import savgol_filter


KINEMATIC_FEATURES = (
    "duration_s",
    "theta_displacement_deg",
    "x_displacement_cm",
    "peak_abs_theta_velocity_deg_s",
    "peak_abs_x_velocity_cm_s",
    "peak_abs_theta_acceleration_deg_s2",
    "peak_abs_x_acceleration_cm_s2",
)


@dataclass(frozen=True)
class Trajectory:
    time_s: np.ndarray
    theta_rad: np.ndarray
    x_m: np.ndarray


def validate_trajectory(trajectory: Trajectory) -> None:
    lengths = {
        len(trajectory.time_s),
        len(trajectory.theta_rad),
        len(trajectory.x_m),
    }
    if len(lengths) != 1 or next(iter(lengths)) < 5:
        raise ValueError("Trajectory arrays must have the same length of at least five")
    if not all(
        np.all(np.isfinite(values))
        for values in (trajectory.time_s, trajectory.theta_rad, trajectory.x_m)
    ):
        raise ValueError("Trajectory contains non-finite values")
    if not np.all(np.diff(trajectory.time_s) > 0.0):
        raise ValueError("Trajectory time must be strictly increasing")


def forecast_trajectory(
    time_s: np.ndarray,
    theta_rad: np.ndarray,
    x_m: np.ndarray,
    valid_mask: np.ndarray,
    context_region_s: float,
) -> Trajectory:
    mask = (np.asarray(valid_mask) > 0.5) & (
        np.asarray(time_s) >= float(context_region_s)
    )
    if int(mask.sum()) < 5:
        raise ValueError("Fewer than five valid forecast samples")
    trajectory = Trajectory(
        time_s=np.asarray(time_s, dtype=np.float64)[mask],
        theta_rad=np.asarray(theta_rad, dtype=np.float64)[mask],
        x_m=np.asarray(x_m, dtype=np.float64)[mask],
    )
    validate_trajectory(trajectory)
    return trajectory


def phase_resample(values: np.ndarray, points: int) -> np.ndarray:
    if points < 5:
        raise ValueError("phase-normalized point count must be at least five")
    values = np.asarray(values, dtype=np.float64)
    source = np.linspace(0.0, 1.0, len(values))
    target = np.linspace(0.0, 1.0, points)
    return np.interp(target, source, values)


def normalized_dtw(first: np.ndarray, second: np.ndarray) -> float:
    first = np.asarray(first, dtype=np.float64)
    second = np.asarray(second, dtype=np.float64)
    if first.ndim != 2 or second.ndim != 2 or first.shape[1] != second.shape[1]:
        raise ValueError("DTW inputs must have shape [time, matching_features]")
    previous = np.full(second.shape[0] + 1, np.inf, dtype=np.float64)
    previous[0] = 0.0
    for first_row in first:
        current = np.full_like(previous, np.inf)
        for column, second_row in enumerate(second, start=1):
            cost = float(np.linalg.norm(first_row - second_row))
            current[column] = cost + min(
                previous[column], current[column - 1], previous[column - 1]
            )
        previous = current
    # Both inputs are phase-normalized to the same length. Dividing by their
    # combined length provides a stable average-cost scale across comparisons.
    return float(previous[-1] / (first.shape[0] + second.shape[0]))


def smooth(values: np.ndarray, window: int, polynomial_order: int) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    usable = min(int(window), len(values) if len(values) % 2 == 1 else len(values) - 1)
    if usable % 2 == 0:
        usable -= 1
    if usable <= polynomial_order or usable < 5:
        return values.copy()
    return savgol_filter(values, window_length=usable, polyorder=polynomial_order)


def kinematic_features(
    trajectory: Trajectory, smoothing_window: int, polynomial_order: int
) -> dict[str, float]:
    validate_trajectory(trajectory)
    theta = smooth(trajectory.theta_rad, smoothing_window, polynomial_order)
    x_m = smooth(trajectory.x_m, smoothing_window, polynomial_order)
    theta_velocity = np.gradient(theta, trajectory.time_s)
    x_velocity = np.gradient(x_m, trajectory.time_s)
    theta_acceleration = np.gradient(theta_velocity, trajectory.time_s)
    x_acceleration = np.gradient(x_velocity, trajectory.time_s)
    return {
        "duration_s": float(trajectory.time_s[-1] - trajectory.time_s[0]),
        "theta_displacement_deg": float(np.degrees(theta[-1] - theta[0])),
        "x_displacement_cm": float(100.0 * (x_m[-1] - x_m[0])),
        "peak_abs_theta_velocity_deg_s": float(
            np.degrees(np.max(np.abs(theta_velocity)))
        ),
        "peak_abs_x_velocity_cm_s": float(100.0 * np.max(np.abs(x_velocity))),
        "peak_abs_theta_acceleration_deg_s2": float(
            np.degrees(np.max(np.abs(theta_acceleration)))
        ),
        "peak_abs_x_acceleration_cm_s2": float(
            100.0 * np.max(np.abs(x_acceleration))
        ),
    }


def pair_distances(
    first: Trajectory,
    second: Trajectory,
    phase_points: int,
    theta_scale_rad: float,
    x_scale_m: float,
    smoothing_window: int,
    polynomial_order: int,
) -> dict[str, float]:
    validate_trajectory(first)
    validate_trajectory(second)
    first_theta = phase_resample(first.theta_rad, phase_points)
    first_x = phase_resample(first.x_m, phase_points)
    second_theta = phase_resample(second.theta_rad, phase_points)
    second_x = phase_resample(second.x_m, phase_points)
    theta_error = first_theta - second_theta
    x_error = first_x - second_x
    first_normalized = np.column_stack(
        [first_theta / theta_scale_rad, first_x / x_scale_m]
    )
    second_normalized = np.column_stack(
        [second_theta / theta_scale_rad, second_x / x_scale_m]
    )
    first_features = kinematic_features(first, smoothing_window, polynomial_order)
    second_features = kinematic_features(second, smoothing_window, polynomial_order)
    result = {
        "normalized_rmse": float(
            np.sqrt(
                np.mean(
                    (theta_error / theta_scale_rad) ** 2
                    + (x_error / x_scale_m) ** 2
                )
            )
        ),
        "dtw_normalized": normalized_dtw(first_normalized, second_normalized),
        "theta_rmse_deg": float(np.degrees(np.sqrt(np.mean(theta_error**2)))),
        "x_rmse_cm": float(100.0 * np.sqrt(np.mean(x_error**2))),
    }
    output_names = {
        "duration_s": "duration_abs_difference_s",
        "theta_displacement_deg": "theta_displacement_abs_difference_deg",
        "x_displacement_cm": "x_displacement_abs_difference_cm",
        "peak_abs_theta_velocity_deg_s": (
            "peak_abs_theta_velocity_abs_difference_deg_s"
        ),
        "peak_abs_x_velocity_cm_s": "peak_abs_x_velocity_abs_difference_cm_s",
        "peak_abs_theta_acceleration_deg_s2": (
            "peak_abs_theta_acceleration_abs_difference_deg_s2"
        ),
        "peak_abs_x_acceleration_cm_s2": (
            "peak_abs_x_acceleration_abs_difference_cm_s2"
        ),
    }
    for feature, output_name in output_names.items():
        result[output_name] = abs(
            first_features[feature] - second_features[feature]
        )
    return result


def percentile_threshold(values: list[float], percentile: float) -> float:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("Threshold values must be nonempty and finite")
    return float(np.percentile(array, percentile, method="higher"))
