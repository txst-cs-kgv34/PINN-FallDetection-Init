from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import savgol_filter


BASE_BOUNDARY_METRICS = (
    "boundary_theta_position_step_deg",
    "boundary_x_position_step_cm",
    "boundary_theta_velocity_change_deg_s",
    "boundary_x_velocity_change_cm_s",
)
YAW_BOUNDARY_METRICS = (
    "boundary_yaw_position_step_deg",
    "boundary_yaw_velocity_change_deg_s",
)

BASE_KINEMATIC_DISTANCE_METRICS = (
    "theta_displacement_abs_difference_deg",
    "x_displacement_abs_difference_cm",
    "peak_abs_theta_velocity_abs_difference_deg_s",
    "peak_abs_x_velocity_abs_difference_cm_s",
    "peak_abs_theta_acceleration_abs_difference_deg_s2",
    "peak_abs_x_acceleration_abs_difference_cm_s2",
)
YAW_KINEMATIC_DISTANCE_METRICS = (
    "yaw_displacement_abs_difference_deg",
    "peak_abs_yaw_velocity_abs_difference_deg_s",
    "peak_abs_yaw_acceleration_abs_difference_deg_s2",
)


@dataclass(frozen=True)
class Trajectory:
    time_s: np.ndarray
    theta_rad: np.ndarray
    x_m: np.ndarray
    yaw_rad: np.ndarray | None = None


def boundary_metric_names(model_group: str) -> tuple[str, ...]:
    return BASE_BOUNDARY_METRICS + (YAW_BOUNDARY_METRICS if model_group == "rotation" else ())


def kinematic_distance_metric_names(model_group: str) -> tuple[str, ...]:
    return BASE_KINEMATIC_DISTANCE_METRICS + (
        YAW_KINEMATIC_DISTANCE_METRICS if model_group == "rotation" else ()
    )


def validate_trajectory(trajectory: Trajectory) -> None:
    arrays = [trajectory.time_s, trajectory.theta_rad, trajectory.x_m]
    if trajectory.yaw_rad is not None:
        arrays.append(trajectory.yaw_rad)
    lengths = {len(array) for array in arrays}
    if len(lengths) != 1 or next(iter(lengths)) < 5:
        raise ValueError("trajectory arrays must have equal length >= 5")
    if not all(np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("trajectory contains non-finite values")
    if not np.all(np.diff(trajectory.time_s) > 0.0):
        raise ValueError("trajectory time must be strictly increasing")


def forecast_trajectory(
    time_s: np.ndarray,
    theta_rad: np.ndarray,
    x_m: np.ndarray,
    valid_mask: np.ndarray,
    context_region_s: float,
    yaw_rad: np.ndarray | None = None,
) -> Trajectory:
    mask = (np.asarray(valid_mask) > 0.5) & (np.asarray(time_s) >= float(context_region_s))
    if int(mask.sum()) < 5:
        raise ValueError("fewer than five valid forecast samples")
    trajectory = Trajectory(
        time_s=np.asarray(time_s, dtype=np.float64)[mask],
        theta_rad=np.asarray(theta_rad, dtype=np.float64)[mask],
        x_m=np.asarray(x_m, dtype=np.float64)[mask],
        yaw_rad=None if yaw_rad is None else np.asarray(yaw_rad, dtype=np.float64)[mask],
    )
    validate_trajectory(trajectory)
    return trajectory


def boundary_continuity_metrics(
    time_s: np.ndarray,
    theta_rad: np.ndarray,
    x_m: np.ndarray,
    valid_mask: np.ndarray,
    context_region_s: float,
    yaw_rad: np.ndarray | None = None,
) -> dict[str, float]:
    time = np.asarray(time_s, dtype=np.float64)
    valid = np.asarray(valid_mask) > 0.5
    context = np.flatnonzero(valid & (time <= float(context_region_s)))
    if len(context) < 2:
        raise ValueError("boundary metrics require two context samples")
    anchor, previous = int(context[-1]), int(context[-2])
    later = np.flatnonzero(valid & (time > time[anchor]))
    if len(later) == 0:
        raise ValueError("boundary metrics require a forecast sample")
    following = int(later[0])
    before_dt = float(time[anchor] - time[previous])
    after_dt = float(time[following] - time[anchor])
    if before_dt <= 0.0 or after_dt <= 0.0:
        raise ValueError("boundary times are not increasing")

    result: dict[str, float] = {}
    channels = (
        ("theta", np.asarray(theta_rad, dtype=np.float64), 180.0 / np.pi, "deg"),
        ("x", np.asarray(x_m, dtype=np.float64), 100.0, "cm"),
    )
    if yaw_rad is not None:
        channels += (("yaw", np.asarray(yaw_rad, dtype=np.float64), 180.0 / np.pi, "deg"),)
    for name, values, scale, unit in channels:
        before_velocity = (values[anchor] - values[previous]) / before_dt
        after_velocity = (values[following] - values[anchor]) / after_dt
        result[f"boundary_{name}_position_step_{unit}"] = float(
            scale * abs(values[following] - values[anchor])
        )
        velocity_unit = "deg_s" if unit == "deg" else "cm_s"
        result[f"boundary_{name}_velocity_change_{velocity_unit}"] = float(
            scale * abs(after_velocity - before_velocity)
        )
    return result


def phase_resample(values: np.ndarray, points: int) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if points < 5 or len(values) < 2:
        raise ValueError("invalid phase resampling request")
    return np.interp(
        np.linspace(0.0, 1.0, points),
        np.linspace(0.0, 1.0, len(values)),
        values,
    )


def normalized_dtw(first: np.ndarray, second: np.ndarray) -> float:
    if first.ndim != 2 or second.ndim != 2 or first.shape[1] != second.shape[1]:
        raise ValueError("DTW inputs must have shape [time, matching features]")
    previous = np.full(second.shape[0] + 1, np.inf, dtype=np.float64)
    previous[0] = 0.0
    for first_row in first:
        current = np.full_like(previous, np.inf)
        for column, second_row in enumerate(second, start=1):
            cost = float(np.linalg.norm(first_row - second_row))
            current[column] = cost + min(previous[column], current[column - 1], previous[column - 1])
        previous = current
    return float(previous[-1] / (first.shape[0] + second.shape[0]))


def smooth(values: np.ndarray, window: int, polynomial_order: int) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    usable = min(int(window), len(values) if len(values) % 2 else len(values) - 1)
    if usable % 2 == 0:
        usable -= 1
    if usable <= polynomial_order or usable < 5:
        return values.copy()
    return savgol_filter(values, usable, polynomial_order)


def kinematic_features(
    trajectory: Trajectory, smoothing_window: int, polynomial_order: int
) -> dict[str, float]:
    validate_trajectory(trajectory)
    channels = (
        ("theta", trajectory.theta_rad, 180.0 / np.pi, "deg"),
        ("x", trajectory.x_m, 100.0, "cm"),
    )
    if trajectory.yaw_rad is not None:
        channels += (("yaw", trajectory.yaw_rad, 180.0 / np.pi, "deg"),)
    result = {"duration_s": float(trajectory.time_s[-1] - trajectory.time_s[0])}
    for name, values, scale, unit in channels:
        filtered = smooth(values, smoothing_window, polynomial_order)
        velocity = np.gradient(filtered, trajectory.time_s)
        acceleration = np.gradient(velocity, trajectory.time_s)
        result[f"{name}_displacement_{unit}"] = float(scale * (filtered[-1] - filtered[0]))
        result[f"peak_abs_{name}_velocity_{unit}_s"] = float(scale * np.max(np.abs(velocity)))
        result[f"peak_abs_{name}_acceleration_{unit}_s2"] = float(scale * np.max(np.abs(acceleration)))
    return result


def pair_distances(
    first: Trajectory,
    second: Trajectory,
    phase_points: int,
    theta_scale_rad: float,
    x_scale_m: float,
    yaw_scale_rad: float | None,
    smoothing_window: int,
    polynomial_order: int,
) -> dict[str, float]:
    validate_trajectory(first)
    validate_trajectory(second)
    rotation = first.yaw_rad is not None or second.yaw_rad is not None
    if rotation and (first.yaw_rad is None or second.yaw_rad is None or yaw_scale_rad is None):
        raise ValueError("rotation comparison requires yaw on both trajectories and yaw scale")
    first_channels = [
        phase_resample(first.theta_rad, phase_points),
        phase_resample(first.x_m, phase_points),
    ]
    second_channels = [
        phase_resample(second.theta_rad, phase_points),
        phase_resample(second.x_m, phase_points),
    ]
    scales = [theta_scale_rad, x_scale_m]
    names = [("theta", 180.0 / np.pi, "deg"), ("x", 100.0, "cm")]
    if rotation:
        first_channels.append(phase_resample(first.yaw_rad, phase_points))
        second_channels.append(phase_resample(second.yaw_rad, phase_points))
        scales.append(float(yaw_scale_rad))
        names.append(("yaw", 180.0 / np.pi, "deg"))
    first_array = np.column_stack(first_channels)
    second_array = np.column_stack(second_channels)
    scale_array = np.asarray(scales, dtype=np.float64)
    normalized_first = first_array / scale_array
    normalized_second = second_array / scale_array
    error = first_array - second_array
    result = {
        "normalized_rmse": float(np.sqrt(np.mean(np.sum((error / scale_array) ** 2, axis=1)))),
        "dtw_normalized": normalized_dtw(normalized_first, normalized_second),
    }
    for index, (name, unit_scale, unit) in enumerate(names):
        result[f"{name}_rmse_{unit}"] = float(unit_scale * np.sqrt(np.mean(error[:, index] ** 2)))
    first_features = kinematic_features(first, smoothing_window, polynomial_order)
    second_features = kinematic_features(second, smoothing_window, polynomial_order)
    result["duration_abs_difference_s"] = abs(first_features["duration_s"] - second_features["duration_s"])
    for name, _, unit in names:
        for feature in (
            f"{name}_displacement_{unit}",
            f"peak_abs_{name}_velocity_{unit}_s",
            f"peak_abs_{name}_acceleration_{unit}_s2",
        ):
            result[f"{feature}_abs_difference" if not feature.startswith("peak_abs") else feature.replace("peak_abs_", "peak_abs_") + "_abs_difference"] = abs(
                first_features[feature] - second_features[feature]
            )
    # Rename mechanically generated fields to the established schema.
    renames = {}
    for key in list(result):
        if key.endswith("_abs_difference"):
            base = key[: -len("_abs_difference")]
            if base.startswith("peak_abs_"):
                parts = base.split("_")
                # peak_abs_theta_velocity_deg_s -> peak_abs_theta_velocity_abs_difference_deg_s
                name, derivative = parts[2], parts[3]
                unit_tail = "_".join(parts[4:])
                renames[key] = f"peak_abs_{name}_{derivative}_abs_difference_{unit_tail}"
            else:
                # theta_displacement_deg -> theta_displacement_abs_difference_deg
                name, derivative, unit = base.split("_", 2)
                renames[key] = f"{name}_{derivative}_abs_difference_{unit}"
    for old, new in renames.items():
        result[new] = result.pop(old)
    return result


def direction_consistent(
    synthetic: Trajectory, source: Trajectory, minimum_source_displacement_cm: float
) -> bool:
    source_displacement = 100.0 * float(source.x_m[-1] - source.x_m[0])
    synthetic_displacement = 100.0 * float(synthetic.x_m[-1] - synthetic.x_m[0])
    if abs(source_displacement) < float(minimum_source_displacement_cm):
        return True
    return bool(np.sign(source_displacement) == np.sign(synthetic_displacement))


def percentile_threshold(values: list[float], percentile: float) -> float:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("threshold values must be nonempty and finite")
    return float(np.percentile(array, percentile, method="higher"))

