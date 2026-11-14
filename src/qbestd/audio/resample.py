"""Sample-rate conversion and time-axis scaling (VTL warping by resampling)."""

from math import gcd

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import resample_poly


def resample_audio(samples, source_rate, target_rate):
    """Resample ``samples`` from ``source_rate`` to ``target_rate`` (Hz).

    Uses polyphase filtering with an anti-aliasing low-pass. Returns a copy
    unchanged when the two rates are equal.
    """
    samples = np.asarray(samples, dtype="float64")
    if source_rate == target_rate:
        return samples.copy()
    divisor = gcd(int(source_rate), int(target_rate))
    up = int(target_rate) // divisor
    down = int(source_rate) // divisor
    return resample_poly(samples, up, down)


def scale_time_axis(samples, warp_factor):
    """Return y(n) = x(warp_factor * n), sampled by cubic-spline interpolation.

    By the scaling property x(at) <-> X(f/a)/|a|, a spectral component at
    frequency f moves to f * warp_factor (a > 1 shortens the signal and raises
    frequencies; a < 1 lengthens it and lowers them). This is the time
    resampling route to vocal-tract-length warping. No anti-aliasing is
    applied, so components pushed past Nyquist alias.
    """
    if warp_factor <= 0:
        raise ValueError("warp_factor must be positive")
    samples = np.asarray(samples, dtype="float64")
    n_out = int(np.floor((len(samples) - 1) / warp_factor)) + 1
    source_positions = np.arange(n_out) * warp_factor
    spline = CubicSpline(np.arange(len(samples)), samples)
    return spline(source_positions)
