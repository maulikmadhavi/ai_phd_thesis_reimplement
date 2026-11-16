"""Median F0 of an utterance by frame-wise autocorrelation (numpy only).

Used by the Stage 4 warp check (cycle 8, W1): does the VTLN warp factor of an
utterance track the speaker's pitch? It is a rough estimator, enough for a
rank correlation, not a pitch tracker: no smoothing, no octave repair beyond
the window-bias correction. Not part of the feature code, so it is not in the
feature source digest.
"""

import numpy as np

FRAME_MS = 40.0
SHIFT_MS = 10.0
F0_MIN_HZ = 50.0
F0_MAX_HZ = 400.0
VOICING_THRESHOLD = 0.3  # normalised autocorrelation peak
ENERGY_RATIO = 0.01  # frame energy relative to the loudest frame


def _frames(samples, rate):
    length = int(round(FRAME_MS * rate / 1000.0))
    shift = int(round(SHIFT_MS * rate / 1000.0))
    if len(samples) < length:
        return np.zeros((0, length))
    count = 1 + (len(samples) - length) // shift
    index = np.arange(length)[None, :] + shift * np.arange(count)[:, None]
    return samples[index]


def _autocorrelation(frames):
    """Autocorrelation of every row (zero padded), shape (n, length)."""
    length = frames.shape[1]
    spectrum = np.fft.rfft(frames, 2 * length, axis=1)
    return np.fft.irfft(np.abs(spectrum) ** 2, axis=1)[:, :length]


def frame_f0(samples, rate, f0_min=F0_MIN_HZ, f0_max=F0_MAX_HZ,
             threshold=VOICING_THRESHOLD):
    """F0 per frame in Hz, ``nan`` for unvoiced or silent frames.

    The frame is Hann-windowed and mean-removed; the autocorrelation is
    divided by that of the window (so a long lag is not penalised) and by its
    value at lag 0. A frame is voiced when the best peak inside
    ``[rate / f0_max, rate / f0_min]`` reaches ``threshold`` and the frame
    holds at least ``ENERGY_RATIO`` of the loudest frame's energy.
    """
    samples = np.asarray(samples, dtype="float64")
    frames = _frames(samples, rate)
    if len(frames) == 0:
        return np.zeros(0)
    window = np.hanning(frames.shape[1])
    frames = (frames - frames.mean(axis=1, keepdims=True)) * window
    energy = np.sum(frames ** 2, axis=1)
    acf = _autocorrelation(frames)
    window_acf = _autocorrelation(window[None, :])[0]
    low = max(int(np.floor(rate / f0_max)), 1)
    high = min(int(np.ceil(rate / f0_min)), frames.shape[1] - 2)
    safe = np.where(acf[:, :1] > 0, acf[:, :1], 1.0)
    ratio = acf / safe / (window_acf / window_acf[0])[None, :]
    inner = ratio[:, low:high + 1]
    is_peak = ((inner >= ratio[:, low - 1:high])
               & (inner > ratio[:, low + 1:high + 2]))
    peaks = np.where(is_peak, inner, -np.inf)
    top = peaks.max(axis=1)
    # the first peak near the best one, so 2x the period is not preferred
    first = np.argmax(peaks >= 0.9 * top[:, None], axis=1)
    peak = top
    best = first
    voiced = (peak >= threshold) & (energy >= ENERGY_RATIO * energy.max())         & (energy > 0)
    f0 = np.full(len(frames), np.nan)
    f0[voiced] = rate / (low + best[voiced])
    return f0


def median_f0(samples, rate, **kwargs):
    """Median of the voiced frames' F0 in Hz, ``nan`` without any."""
    f0 = frame_f0(samples, rate, **kwargs)
    f0 = f0[np.isfinite(f0)]
    return float(np.median(f0)) if len(f0) else float("nan")
