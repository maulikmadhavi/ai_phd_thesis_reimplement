"""Splitting a waveform into overlapping analysis frames."""

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def count_frames(n_samples, frame_len, shift_len):
    """Number of complete frames, HTK style (no padding).

    n_frames = 1 + (n_samples - frame_len) // shift_len, or 0 when the
    signal is shorter than one frame.
    """
    if n_samples < frame_len:
        return 0
    return 1 + (n_samples - frame_len) // shift_len


def frame_signal(samples, sample_rate, frame_ms=25.0, shift_ms=10.0):
    """Cut ``samples`` into frames of shape (n_frames, frame_len).

    Frame k starts at sample k * shift_len. Only complete frames are kept and
    the tail is never padded (HTK convention). A signal shorter than one
    frame yields shape (0, frame_len).
    """
    samples = np.asarray(samples, dtype="float64")
    frame_len = int(round(sample_rate * frame_ms / 1000.0))
    shift_len = int(round(sample_rate * shift_ms / 1000.0))
    n_frames = count_frames(len(samples), frame_len, shift_len)
    if n_frames == 0:
        return np.zeros((0, frame_len))
    windows = sliding_window_view(samples, frame_len)
    return windows[::shift_len][:n_frames].copy()
