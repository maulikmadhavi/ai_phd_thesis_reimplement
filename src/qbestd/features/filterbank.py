"""Triangular mel filterbank with optional VTLN frequency warping."""

import numpy as np

from qbestd.audio.spectrum import fft_bin_frequencies
from qbestd.features.scales import (
    hz_to_mel,
    mel_to_hz,
    warp_frequency_piecewise,
)


def mel_filter_edges_hz(n_filters, low_hz, high_hz):
    """Edge frequencies (n_filters + 2) equally spaced on the mel scale."""
    return mel_to_hz(np.linspace(hz_to_mel(low_hz), hz_to_mel(high_hz),
                                 n_filters + 2))


def mel_filter_centers_hz(n_filters, low_hz, high_hz):
    """Peak (centre) frequency of each triangular filter, in Hz."""
    return mel_filter_edges_hz(n_filters, low_hz, high_hz)[1:-1]


def mel_filterbank(n_filters=26, n_fft=256, sample_rate=8000, low_hz=0.0,
                   high_hz=4000.0, warp_factor=1.0):
    """Triangular mel filterbank of shape (n_filters, n_fft // 2 + 1).

    Filters are triangles with unit peak, equally spaced in mel between
    ``low_hz`` and ``high_hz`` (HTK mel scale). When ``warp_factor`` is not 1
    the FFT bin frequencies are first warped by
    ``warp_frequency_piecewise`` and the unchanged triangles are then
    evaluated at the warped frequencies (as in ``Fx_PLPCC_htk.m``). For
    warp_factor > 1 a bin at f is seen at (2 - alpha) * f < f, so every
    filter peak moves to a higher FFT bin; for warp_factor < 1 it moves lower.

    Raises:
        ValueError: if the band is invalid or high_hz exceeds Nyquist.
    """
    if n_filters < 1:
        raise ValueError("n_filters must be at least 1")
    if not 0 <= low_hz < high_hz:
        raise ValueError("require 0 <= low_hz < high_hz")
    if high_hz > sample_rate / 2:
        raise ValueError(
            f"high_hz={high_hz} exceeds Nyquist {sample_rate / 2}")
    bin_hz = fft_bin_frequencies(n_fft, sample_rate)
    if warp_factor != 1.0:
        bin_hz = warp_frequency_piecewise(bin_hz, warp_factor, sample_rate)
    edges = mel_filter_edges_hz(n_filters, low_hz, high_hz)
    lower, center, upper = edges[:-2, None], edges[1:-1, None], edges[2:, None]
    rising = (bin_hz[None, :] - lower) / (center - lower)
    falling = (upper - bin_hz[None, :]) / (upper - center)
    return np.maximum(0.0, np.minimum(rising, falling))
