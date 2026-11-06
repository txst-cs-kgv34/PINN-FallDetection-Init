"""Compute descriptive foot geometry in the camera frame; no support/contact inference."""

import numpy as np


def compute_foot_geometry(pose, com):
    """Return framewise foot midpoint, separations and CoM displacement from it.

    pose is (frames,32,3) in metres; CoM is (frames,3). The X/Z projection
    is named by camera axes, never assumed to be a calibrated ground plane.
    """
    left = pose[:, 21, :]
    right = pose[:, 25, :]
    midpoint = (left + right) / 2
    difference = left - right
    return {
        "foot_midpoint": midpoint,
        "com_relative_to_foot_midpoint": com - midpoint,
        "foot_separation_camera_xz": np.linalg.norm(difference[:, [0, 2]], axis=1),
        "foot_separation_camera_x": np.abs(difference[:, 0]),
    }
