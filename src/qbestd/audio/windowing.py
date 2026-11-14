"""Analysis window functions."""

import numpy as np

# unverified default: Hamming, not yet checked against the MATLAB code.
DEFAULT_WINDOW_NAME = "hamming"

_WINDOW_NAMES = ("hamming", "hann", "rectangular")


def make_window(name, length):
    """Build a symmetric window (denominator length - 1, as in HTK).

    Supported names: hamming, hann, rectangular.

    Raises:
        ValueError: for an unknown window name.
    """
    name = name.lower()
    if name not in _WINDOW_NAMES:
        raise ValueError(
            f"Unknown window '{name}'; choose one of {_WINDOW_NAMES}")
    if name == "rectangular" or length == 1:
        return np.ones(length)
    phase = 2 * np.pi * np.arange(length) / (length - 1)
    if name == "hamming":
        return 0.54 - 0.46 * np.cos(phase)
    return 0.5 - 0.5 * np.cos(phase)


def apply_window(frames, window):
    """Multiply every row of ``frames`` (n_frames, frame_len) by ``window``."""
    frames = np.asarray(frames, dtype="float64")
    if frames.shape[-1] != len(window):
        raise ValueError(
            f"Window length {len(window)} != frame length {frames.shape[-1]}")
    return frames * window
