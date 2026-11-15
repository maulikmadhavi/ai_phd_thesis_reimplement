"""Frequency scales and vocal-tract-length (VTLN) frequency warping."""

import numpy as np

# Warp factors alpha = 0.88, 0.90, ..., 1.12 used for VTLN (13 values).
VTLN_WARP_FACTORS = tuple(round(0.88 + 0.02 * step, 2) for step in range(13))

DEFAULT_CUTOFF_RATIO = 0.875
CUTOFF_BACKOFF_STEP = 0.05


def hz_to_mel(frequency_hz):
    """HTK mel scale: 2595 * log10(1 + f / 700)."""
    frequency_hz = np.asarray(frequency_hz, dtype="float64")
    return 2595.0 * np.log10(1.0 + frequency_hz / 700.0)


def mel_to_hz(mel):
    """Inverse of ``hz_to_mel``."""
    return 700.0 * (10.0 ** (np.asarray(mel, dtype="float64") / 2595.0) - 1.0)


def hz_to_bark(frequency_hz):
    """Bark scale used by the thesis code: 6 * asinh(f / 600)."""
    return 6.0 * np.arcsinh(np.asarray(frequency_hz, dtype="float64") / 600.0)


def bark_to_hz(bark):
    """Inverse of ``hz_to_bark``: 600 * sinh(z / 6)."""
    return 600.0 * np.sinh(np.asarray(bark, dtype="float64") / 6.0)


def vtln_cutoff_frequency(warp_factor, sample_rate,
                          cutoff_ratio=DEFAULT_CUTOFF_RATIO, upper_hz=None):
    """Frequency f0 where the VTLN warp switches from the first to second line.

    f0 = cutoff_ratio * upper, where ``upper`` is the anchor frequency that
    the warp maps to itself: ``upper_hz``, or Nyquist when None. As in
    ``Fx_vtln_warp.m``, the ratio is lowered in steps of 0.05 until the
    first line maps f0 strictly below ``upper``.

    Raises:
        ValueError: if no positive cutoff ratio satisfies the condition.
    """
    upper = sample_rate / 2.0 if upper_hz is None else float(upper_hz)
    slope = 2.0 - warp_factor
    ratio = cutoff_ratio
    while slope * ratio * upper >= upper:
        ratio -= CUTOFF_BACKOFF_STEP
        if ratio <= 0:
            raise ValueError(
                f"No valid VTLN cutoff for warp_factor={warp_factor}")
    return ratio * upper


def warp_frequency_piecewise(freqs_hz, warp_factor, sample_rate,
                             cutoff_ratio=DEFAULT_CUTOFF_RATIO,
                             upper_hz=None):
    """Piecewise-linear VTLN warp, as ``Fx_vtln_warp.m`` with a movable anchor.

    f' = (2 - alpha) * f                          for f <= f0
    f' = (2 - alpha) * f0 + m2 * (f - f0)         for f >  f0
    where m2 = (upper - (2 - alpha) f0) / (upper - f0), so that ``upper``
    maps to itself. ``upper_hz`` defaults to Nyquist (the MATLAB script);
    pass the band edge (``high_hz``) for a band-limited filterbank, which
    gives f0 = 3500 Hz for a 4 kHz band (thesis ``Warped_Feature.tex``).
    alpha > 1 lowers frequencies below f0. Frequencies above ``upper`` are
    continued on the second line.
    """
    freqs_hz = np.asarray(freqs_hz, dtype="float64")
    upper = sample_rate / 2.0 if upper_hz is None else float(upper_hz)
    slope = 2.0 - warp_factor
    cutoff = vtln_cutoff_frequency(warp_factor, sample_rate, cutoff_ratio,
                                   upper)
    upper_slope = (upper - slope * cutoff) / (upper - cutoff)
    return np.where(freqs_hz <= cutoff, slope * freqs_hz,
                    slope * cutoff + upper_slope * (freqs_hz - cutoff))


def warp_mel_scale(freqs_hz, warp_factor):
    """Thesis mel warping M_alpha(f) = 2595 * log10(1 + f / (700 * alpha))."""
    if warp_factor <= 0:
        raise ValueError("warp_factor must be positive")
    freqs_hz = np.asarray(freqs_hz, dtype="float64")
    return 2595.0 * np.log10(1.0 + freqs_hz / (700.0 * warp_factor))
