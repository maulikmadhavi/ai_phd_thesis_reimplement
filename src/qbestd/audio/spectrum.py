"""Short-time spectra of framed signals."""

import numpy as np


def next_power_of_two(n):
    """Smallest power of two that is >= n (n >= 1)."""
    if n < 1:
        raise ValueError("n must be at least 1")
    return 1 << (int(n) - 1).bit_length()


def magnitude_spectrum(frames, n_fft=None):
    """One-sided FFT magnitude, shape (n_frames, n_fft // 2 + 1).

    ``n_fft=None`` uses the next power of two >= frame length
    (unverified default, not yet checked against the MATLAB code).
    Frames are zero-padded up to ``n_fft``.
    """
    frames = np.asarray(frames, dtype="float64")
    if n_fft is None:
        n_fft = next_power_of_two(frames.shape[-1])
    return np.abs(np.fft.rfft(frames, n=n_fft, axis=-1))


def power_spectrum(frames, n_fft=None):
    """One-sided squared FFT magnitude, shape (n_frames, n_fft // 2 + 1)."""
    return magnitude_spectrum(frames, n_fft) ** 2


def fft_bin_frequencies(n_fft, sample_rate):
    """Centre frequency in Hz of each one-sided FFT bin."""
    return np.arange(n_fft // 2 + 1) * sample_rate / n_fft
