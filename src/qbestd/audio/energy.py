"""Short-time energy and the Teager energy operator (TEO)."""

import numpy as np


def short_time_energy(frames):
    """Sum of squared samples (l2 energy) for each frame."""
    frames = np.asarray(frames, dtype="float64")
    return np.sum(frames ** 2, axis=-1)


def log_energy(frames, floor=1e-10):
    """Natural log of the frame energy, with energy floored at ``floor``."""
    return np.log(np.maximum(short_time_energy(frames), floor))


def teager_energy(samples):
    """Teager energy psi{x}(n) = x(n)^2 - x(n+1) * x(n-1).

    Works along the last axis. The two edge values replicate their
    neighbour so the output has the same length as the input.
    """
    samples = np.asarray(samples, dtype="float64")
    if samples.shape[-1] < 3:
        raise ValueError("Teager energy needs at least 3 samples")
    energy = np.empty_like(samples)
    energy[..., 1:-1] = (samples[..., 1:-1] ** 2
                         - samples[..., 2:] * samples[..., :-2])
    energy[..., 0] = energy[..., 1]
    energy[..., -1] = energy[..., -2]
    return energy


def frame_teager_energy(frames):
    """Mean Teager energy of each frame."""
    return teager_energy(frames).mean(axis=-1)
