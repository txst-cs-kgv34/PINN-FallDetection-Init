"""Optional offline smoothing for inspection, without changing or retiming source data."""

import numpy as np


def filter_motion(pose, fps, cutoff_hz, order=6):
    """Return a new filtered array plus explicit settings/status.

    SciPy is imported only when this optional comparison is requested.
    Short recordings remain raw: do not silently reduce padding or invent frames.
    """
    from scipy.signal import butter, sosfiltfilt

    if not np.isfinite(fps) or fps <= 0:
        raise ValueError("FPS must be positive and finite")
    if not np.isfinite(cutoff_hz) or not 0 < cutoff_hz < fps / 2:
        raise ValueError("Cutoff must be positive and below half the nominal FPS")
    if not isinstance(order, int) or not 1 <= order <= 12:
        raise ValueError("Filter order must be an integer from 1 to 12")
    sos = butter(order, cutoff_hz, fs=fps, output="sos")
    padlen = int(
        3 * (2 * len(sos) + 1 - min((sos[:, 2] == 0).sum(), (sos[:, 5] == 0).sum()))
    )
    settings = {
        "method": "Butterworth SOS forward-backward",
        "cutoff_hz": cutoff_hz,
        "order_per_pass": order,
        "padlen": padlen,
        "phase": "Offline comparison; uses future frames; not a selected prediction preprocessor",
    }
    if len(pose) <= padlen + 1:
        return None, {**settings, "status": "skipped_short_clip"}
    filtered = sosfiltfilt(sos, pose, axis=0, padlen=padlen)
    if not np.isfinite(filtered).all():
        raise ValueError("Filter produced nonfinite coordinates")
    return filtered, {**settings, "status": "available"}
