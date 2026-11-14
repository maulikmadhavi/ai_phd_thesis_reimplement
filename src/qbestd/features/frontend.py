"""Shared front-end steps for the feature extractors."""

import numpy as np

from qbestd.audio.pipeline import prepare_frames
from qbestd.audio.spectrum import next_power_of_two

PCM_SCALE = 32768.0  # MATLAB code multiplies by 2^15 before the FFT


def scale_waveform(samples, normalize_peak=True, pcm_scale=PCM_SCALE):
    """Peak-normalise (optional) and scale to 16-bit PCM range.

    Mirrors the MATLAB ``x / max|x|`` followed by ``32768 * x``. Silence is
    returned unchanged (scaled only) to avoid dividing by zero.
    """
    samples = np.asarray(samples, dtype="float64")
    peak = np.max(np.abs(samples)) if samples.size else 0.0
    if normalize_peak and peak > 0:
        samples = samples / peak
    return samples * pcm_scale


def windowed_frames(samples, sample_rate, config):
    """Scale, then run the Stage 1 front end; returns (frames, rate, n_fft).

    ``config`` is an ``AudioFrontEndConfig`` subclass that also provides
    ``normalize_peak`` and ``pcm_scale``.
    """
    scaled = scale_waveform(samples, config.normalize_peak, config.pcm_scale)
    frames = prepare_frames(scaled, sample_rate, config)
    rate = config.sample_rate or sample_rate
    n_fft = config.n_fft or next_power_of_two(frames.shape[1])
    return frames, rate, n_fft
