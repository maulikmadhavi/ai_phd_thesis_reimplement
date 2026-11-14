"""Delta (velocity) and acceleration features."""

import numpy as np


def compute_deltas(features, window=2):
    """Regression deltas along the frame axis, as in MATLAB ``Deltacep.m``.

    d[t] = sum_{k=1..N} k * (x[t+k] - x[t-k]) / (2 * sum_{k=1..N} k^2),
    with the first and last frames replicated ``window`` times at the edges.
    ``features`` has shape (n_frames, n_dims); the output has the same shape.

    Raises:
        ValueError: if window is not a positive integer.
    """
    features = np.asarray(features, dtype="float64")
    if int(window) != window or window < 1:
        raise ValueError("window must be a positive integer")
    n_frames = features.shape[0]
    if n_frames == 0:
        return features.copy()
    padded = np.pad(features, ((window, window), (0, 0)), mode="edge")
    numerator = np.zeros_like(features)
    for offset in range(1, window + 1):
        ahead = padded[window + offset:window + offset + n_frames]
        behind = padded[window - offset:window - offset + n_frames]
        numerator += offset * (ahead - behind)
    return numerator / (2.0 * sum(k * k for k in range(1, window + 1)))


def append_deltas(static, window=2, order=2):
    """Stack static features with their deltas up to ``order`` (13 -> 39).

    Order 1 appends deltas only; order 2 also appends the deltas of the
    deltas (acceleration).
    """
    if order < 0:
        raise ValueError("order must be non-negative")
    blocks = [np.asarray(static, dtype="float64")]
    for _ in range(order):
        blocks.append(compute_deltas(blocks[-1], window))
    return np.hstack(blocks)
