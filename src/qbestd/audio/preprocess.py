"""Waveform conditioning before framing."""

import numpy as np

# unverified default: HTK-style 0.97, not yet checked against the MATLAB code.
DEFAULT_PREEMPHASIS_COEFFICIENT = 0.97


def apply_preemphasis(samples, coefficient=DEFAULT_PREEMPHASIS_COEFFICIENT):
    """Apply y[n] = x[n] - coefficient * x[n-1], with y[0] = x[0]."""
    samples = np.asarray(samples, dtype="float64")
    emphasized = samples.copy()
    emphasized[1:] -= coefficient * samples[:-1]
    return emphasized


def remove_dc_offset(samples):
    """Subtract the mean so the waveform has zero mean."""
    samples = np.asarray(samples, dtype="float64")
    return samples - samples.mean()
