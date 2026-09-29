"""Construct a fixed standing-body coordinate frame for one skeleton trial."""

import numpy as np

HEAD = 26
NOSE = 27
HIP_LEFT = 18
HIP_RIGHT = 22
SHOULDER_LEFT = 5
SHOULDER_RIGHT = 12
FOOT_LEFT = 21
FOOT_RIGHT = 25


def normalize(vector, label):
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm < 1e-8:
        raise ValueError(f"cannot define {label}: vector norm is {norm}")
    return vector / norm


def standing_body_frame(pose, standing_frame0, radius=2):
    """Return origin and anatomical-axis proxies from a local median standing pose.

    pose is (frames, 32, 3) in metres. The axes are fixed for the whole trial:
    lateral points from left to right hip, vertical from foot midpoint to head,
    and forward is the orthogonal cross-product oriented toward the nose proxy.
    These are body-frame proxies, not calibrated world/floor axes.
    """
    start = max(0, standing_frame0 - radius)
    stop = min(len(pose), standing_frame0 + radius + 1)
    standing = np.median(pose[start:stop], axis=0)
    origin = (standing[FOOT_LEFT] + standing[FOOT_RIGHT]) / 2
    vertical = normalize(standing[HEAD] - origin, "standing vertical")

    lateral_raw = standing[HIP_RIGHT] - standing[HIP_LEFT]
    lateral_raw = lateral_raw - np.dot(lateral_raw, vertical) * vertical
    if np.linalg.norm(lateral_raw) < 1e-8:
        lateral_raw = standing[SHOULDER_RIGHT] - standing[SHOULDER_LEFT]
        lateral_raw = lateral_raw - np.dot(lateral_raw, vertical) * vertical
    lateral = normalize(lateral_raw, "standing lateral")

    forward = normalize(np.cross(lateral, vertical), "standing forward proxy")
    nose = standing[NOSE] - standing[HEAD]
    nose = nose - np.dot(nose, vertical) * vertical - np.dot(nose, lateral) * lateral
    nose_norm = float(np.linalg.norm(nose))
    nose_alignment = None
    if nose_norm >= 1e-8:
        nose /= nose_norm
        if np.dot(forward, nose) < 0:
            forward = -forward
        nose_alignment = float(np.dot(forward, nose))

    basis = np.column_stack([lateral, vertical, forward])
    if not np.allclose(basis.T @ basis, np.eye(3), atol=1e-10):
        raise ValueError("standing-body basis is not orthonormal")
    return {
        "origin_camera_m": origin,
        "basis_camera_columns": basis,
        "lateral_right_camera": lateral,
        "vertical_headward_camera": vertical,
        "forward_nose_proxy_camera": forward,
        "basis_determinant": float(np.linalg.det(basis)),
        "nose_alignment": nose_alignment,
        "standing_window_start_frame0": start,
        "standing_window_end_frame0": stop - 1,
        "standing_head_to_foot_midpoint_m": float(
            np.linalg.norm(standing[HEAD] - origin)
        ),
    }


def to_subject_frame(points, frame):
    """Transform (..., 3) camera-frame points into the fixed subject frame."""
    return (points - frame["origin_camera_m"]) @ frame["basis_camera_columns"]
