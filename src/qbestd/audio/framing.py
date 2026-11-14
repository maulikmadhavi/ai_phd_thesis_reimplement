"""Splitting a waveform into overlapping analysis frames."""

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def count_frames(n_samples, frame_len, shift_len):
    """Number of complete frames, HTK style (no padding).

    n_frames = 1 + (n_samples - frame_len) // shift_len, or 0 when the
    signal is shorter than one frame.

    Raises:
        ValueError: if frame_len or shift_len is not positive.
    """
    if frame_len <= 0 or shift_len <= 0:
        raise ValueError("frame_len and shift_len must be positive")
    if n_samples < frame_len:
        return 0
    return 1 + (n_samples - frame_len) // shift_len


def frame_signal(samples, sample_rate, frame_ms=25.0, shift_ms=10.0):
    """Cut ``samples`` into frames of shape (n_frames, frame_len).

    Frame k starts at sample k * shift_len. Only complete frames are kept and
    the tail is never padded (HTK convention). A signal shorter than one
    frame yields shape (0, frame_len).

    Raises:
        ValueError: if sample_rate, frame_ms or shift_ms is not positive, or
            if the frame or shift length rounds to zero samples.
    """
    samples = np.asarray(samples, dtype="float64")
    if sample_rate <= 0 or frame_ms <= 0 or shift_ms <= 0:
        raise ValueError("sample_rate, frame_ms and shift_ms must be positive")
    frame_len = int(round(sample_rate * frame_ms / 1000.0))
    shift_len = int(round(sample_rate * shift_ms / 1000.0))
    if frame_len == 0 or shift_len == 0:
        raise ValueError(
            f"frame ({frame_ms} ms) or shift ({shift_ms} ms) rounds to 0 "
            f"samples at {sample_rate} Hz")
    n_frames = count_frames(len(samples), frame_len, shift_len)
    if n_frames == 0:
        return np.zeros((0, frame_len))
    windows = sliding_window_view(samples, frame_len)
    return windows[::shift_len][:n_frames].copy()
