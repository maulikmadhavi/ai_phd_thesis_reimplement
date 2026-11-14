"""Sample-rate conversion and time-axis scaling (VTL warping by resampling)."""

from math import gcd

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import filtfilt, firwin, resample_poly


ANTIALIAS_TAPS = 101
ANTIALIAS_CUTOFF_RATIO = 0.95


def resample_audio(samples, source_rate, target_rate):
    """Resample ``samples`` from ``source_rate`` to ``target_rate`` (Hz).

    Uses polyphase filtering with an anti-aliasing low-pass. Returns a copy
    unchanged when the two rates are equal.
    """
    samples = np.asarray(samples, dtype="float64")
    _require_positive_integer_rate(source_rate, "source_rate")
    _require_positive_integer_rate(target_rate, "target_rate")
    if source_rate == target_rate:
        return samples.copy()
    divisor = gcd(int(source_rate), int(target_rate))
    up = int(target_rate) // divisor
    down = int(source_rate) // divisor
    return resample_poly(samples, up, down)


def scale_time_axis(samples, warp_factor, antialias=True):
    """Return y(n) = x(warp_factor * n), sampled by cubic-spline interpolation.

    By the scaling property x(at) <-> X(f/a)/|a|, a spectral component at
    frequency f moves to f * warp_factor (a > 1 shortens the signal and raises
    frequencies; a < 1 lengthens it and lowers them). This is the time
    resampling route to vocal-tract-length warping.

    For warp_factor > 1 and ``antialias=True``, the input is first low-passed
    with a zero-phase FIR (``firwin`` with ANTIALIAS_TAPS Hamming-window taps
    applied by ``filtfilt``) whose cutoff is 0.95 * Nyquist / warp_factor, so
    components that would be pushed past Nyquist are removed instead of
    folding back. Empty input returns an empty array and a one-sample input
    returns a copy.

    Raises:
        ValueError: if warp_factor is not positive.
    """
    if warp_factor <= 0:
        raise ValueError("warp_factor must be positive")
    samples = np.asarray(samples, dtype="float64")
    if len(samples) <= 1:
        return samples.copy()
    if antialias and warp_factor > 1:
        samples = _lowpass_before_speedup(samples, warp_factor)
    n_out = int(np.floor((len(samples) - 1) / warp_factor)) + 1
    source_positions = np.arange(n_out) * warp_factor
    spline = CubicSpline(np.arange(len(samples)), samples)
    return spline(source_positions)


def _require_positive_integer_rate(rate, name):
    if not float(rate).is_integer() or rate <= 0:
        raise ValueError(f"{name} must be a positive integer, got {rate!r}")


def _lowpass_before_speedup(samples, warp_factor):
    cutoff = ANTIALIAS_CUTOFF_RATIO / warp_factor  # fraction of Nyquist
    taps = firwin(ANTIALIAS_TAPS, cutoff)
    padlen = min(3 * ANTIALIAS_TAPS, len(samples) - 1)
    return filtfilt(taps, [1.0], samples, padlen=padlen)
