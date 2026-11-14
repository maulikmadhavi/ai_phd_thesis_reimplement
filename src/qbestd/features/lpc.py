"""Linear prediction helpers for PLP (autocorrelation -> LPC -> cepstrum).

All functions work on a leading frame axis: arrays are (n_frames, ...).
"""

import numpy as np

LOG_FLOOR = 1e-10


def autocorrelation_from_power(power_bands):
    """Autocorrelation from a one-sided band spectrum (rastamat ``dolpc``).

    The (n_frames, n_bands) spectrum is mirrored to a symmetric
    2 * (n_bands - 1) point spectrum; its real inverse DFT is the
    autocorrelation. Returns (n_frames, n_bands) lags 0..n_bands-1.
    """
    power_bands = np.asarray(power_bands, dtype="float64")
    n_bands = power_bands.shape[-1]
    if n_bands < 2:
        raise ValueError("need at least 2 bands")
    tail = power_bands[..., -2:0:-1]
    mirrored = np.concatenate([power_bands, tail], axis=-1)
    return np.real(np.fft.ifft(mirrored, axis=-1))[..., :n_bands]


def levinson_durbin(autocorr, order):
    """Solve the normal equations by Levinson-Durbin recursion.

    Args:
        autocorr: (n_frames, n_lags) or (n_lags,), lags 0..n_lags-1.
        order: prediction order, requires n_lags >= order + 1.

    Returns:
        (lpc_coeffs, gain): coefficients a[0..order] with a[0] = 1 for
        A(z) = 1 + sum a_k z^-k, shaped (n_frames, order + 1), and the final
        prediction error power (n_frames,). A frame with zero energy gets
        a = [1, 0, ...] and gain 0.

    Raises:
        ValueError: if order < 1 or there are too few lags.
    """
    autocorr = np.atleast_2d(np.asarray(autocorr, dtype="float64"))
    if order < 1:
        raise ValueError("order must be at least 1")
    if autocorr.shape[-1] < order + 1:
        raise ValueError(
            f"order {order} needs {order + 1} lags, got {autocorr.shape[-1]}")
    n_frames = autocorr.shape[0]
    coeffs = np.zeros((n_frames, order + 1))
    coeffs[:, 0] = 1.0
    error = autocorr[:, 0].copy()
    for step in range(1, order + 1):
        projection = np.sum(coeffs[:, :step] * autocorr[:, step:0:-1], axis=1)
        safe_error = np.where(error > 0, error, 1.0)
        reflection = np.where(error > 0, -projection / safe_error, 0.0)
        # a_j <- a_j + k * a_(step-j) for j = 1..step (a_step starts at 0)
        mirrored = coeffs[:, step - 1::-1].copy()
        coeffs[:, 1:step + 1] += reflection[:, None] * mirrored
        error = error * (1.0 - reflection ** 2)
    return coeffs, error


def lpc_to_cepstrum(lpc_coeffs, gain, n_ceps):
    """Cepstrum of the all-pole model gain / A(z), HTK ``LPC2Cepstrum``.

    c0 = log(gain) (floored), and for n >= 1
    c_n = -a_n - (1/n) * sum_{k=1}^{n-1} (n - k) * a_k * c_{n-k},
    with a_k = 0 for k greater than the LPC order. Returns (n_frames, n_ceps).
    """
    lpc_coeffs = np.atleast_2d(np.asarray(lpc_coeffs, dtype="float64"))
    gain = np.atleast_1d(np.asarray(gain, dtype="float64"))
    order = lpc_coeffs.shape[-1] - 1
    cepstrum = np.zeros((lpc_coeffs.shape[0], n_ceps))
    cepstrum[:, 0] = np.log(np.maximum(gain, LOG_FLOOR))
    for index in range(1, n_ceps):
        value = -lpc_coeffs[:, index] if index <= order else 0.0
        for lag in range(1, min(index - 1, order) + 1):
            weight = (index - lag) / index
            value = value - (weight * lpc_coeffs[:, lag]
                             * cepstrum[:, index - lag])
        cepstrum[:, index] = value
    return cepstrum
