"""Log compression, DCT cepstra and cepstral liftering."""

import numpy as np
from scipy.fft import dct

LOG_FLOOR = 1e-10


def log_compress(values, floor=LOG_FLOOR):
    """Natural log with an explicit floor, so the result is always finite."""
    return np.log(np.maximum(np.asarray(values, dtype="float64"), floor))


def dct_cepstra(log_energies, n_ceps=13, include_c0=True):
    """Orthonormal DCT-II of log filterbank energies, shape (n_frames, n_ceps).

    Matches MATLAB ``dct(eye(p))`` and ``Fx_dctmat(Nc, p, 2)``. With
    ``include_c0=True`` the output holds c0..c(n_ceps-1) (MATLAB rows 1:Nc).
    With ``include_c0=False`` it holds c1..c(n_ceps), the form written in the
    thesis MFCC-TMP formula.

    Raises:
        ValueError: if more coefficients are requested than are available.
    """
    log_energies = np.asarray(log_energies, dtype="float64")
    start = 0 if include_c0 else 1
    if start + n_ceps > log_energies.shape[-1]:
        raise ValueError(
            f"Cannot take {n_ceps} coefficients from {log_energies.shape[-1]} "
            f"filters (include_c0={include_c0})")
    full = dct(log_energies, type=2, norm="ortho", axis=-1)
    return full[..., start:start + n_ceps]


def lifter_weights(n_ceps, lifter_length, first_index=0):
    """HTK sine lifter 1 + (L / 2) * sin(pi * n / L) for n = first_index..."""
    index = np.arange(first_index, first_index + n_ceps)
    if lifter_length <= 0:
        return np.ones(n_ceps)
    return 1.0 + (lifter_length / 2.0) * np.sin(np.pi * index / lifter_length)


def lifter_cepstra(ceps, lifter_length=0, first_index=0):
    """Apply the HTK sine lifter; ``lifter_length`` 0 means no liftering.

    ``first_index`` is the cepstral index of column 0 (1 when c0 was dropped).
    MATLAB ``Nlift = -20`` (rastamat) corresponds to ``lifter_length=20``.
    """
    ceps = np.asarray(ceps, dtype="float64")
    return ceps * lifter_weights(ceps.shape[-1], lifter_length, first_index)
