import numpy as np
import pytest
from scipy.linalg import solve_toeplitz

from qbestd.features.lpc import (
    autocorrelation_from_power,
    levinson_durbin,
    lpc_to_cepstrum,
)


def test_levinson_matches_toeplitz_solution():
    rng = np.random.default_rng(0)
    signal = rng.normal(size=400)
    autocorr = np.array(
        [signal[:400 - lag] @ signal[lag:] for lag in range(11)])
    coeffs, error = levinson_durbin(autocorr, 8)
    expected = solve_toeplitz(autocorr[:8], -autocorr[1:9])
    assert coeffs.shape == (1, 9)
    assert coeffs[0, 0] == 1.0
    assert np.allclose(coeffs[0, 1:], expected)
    assert error[0] == pytest.approx(autocorr[0] + autocorr[1:9] @ expected)


def test_levinson_batch_matches_single():
    rng = np.random.default_rng(1)
    decay = np.array([1.0, .5, .2, .1, .05, 0, 0, 0, 0, 0])
    autocorr = np.abs(rng.normal(size=(3, 10))) * decay
    autocorr[:, 0] += 5.0
    batch, _ = levinson_durbin(autocorr, 4)
    for row in range(3):
        assert np.allclose(batch[row], levinson_durbin(autocorr[row], 4)[0][0])


def test_zero_energy_frame_is_safe():
    coeffs, error = levinson_durbin(np.zeros((1, 6)), 3)
    assert np.array_equal(coeffs, [[1.0, 0, 0, 0]])
    assert error[0] == 0


def test_order_larger_than_lags_raises():
    with pytest.raises(ValueError):
        levinson_durbin(np.ones(5), 5)
    with pytest.raises(ValueError):
        levinson_durbin(np.ones(5), 0)


def test_ar1_cepstrum_is_a_power_n_over_n():
    pole = 0.7
    cepstrum = lpc_to_cepstrum(np.array([[1.0, -pole]]), np.array([2.0]), 9)
    expected = np.array([pole ** n / n for n in range(1, 9)])
    assert cepstrum[0, 0] == pytest.approx(np.log(2.0))
    assert np.allclose(cepstrum[0, 1:], expected)


def test_cepstrum_longer_than_order_uses_recursion():
    coeffs = np.array([[1.0, -0.5, 0.2]])
    cepstrum = lpc_to_cepstrum(coeffs, np.array([1.0]), 6)
    # Reference: log-series of 1/A(z) via polynomial division of derivative.
    impulse = np.zeros(200)
    impulse[0] = 1
    for n in range(1, 200):
        older = impulse[n - 2] if n >= 2 else 0
        impulse[n] = 0.5 * impulse[n - 1] - 0.2 * older
    spectrum = np.fft.fft(impulse, 4096)
    reference = np.real(np.fft.ifft(np.log(spectrum)))[:6]
    assert np.allclose(cepstrum[0, 1:], reference[1:], atol=1e-6)


def test_autocorrelation_of_flat_spectrum_is_impulse():
    autocorr = autocorrelation_from_power(np.ones((2, 9)))
    assert autocorr.shape == (2, 9)
    assert np.allclose(autocorr[:, 0], 1.0)
    assert np.allclose(autocorr[:, 1:], 0.0, atol=1e-12)


def test_autocorrelation_recovers_known_lag():
    n_bands = 17
    freqs = np.pi * np.arange(n_bands) / (n_bands - 1)
    power = 1.0 + np.cos(freqs)  # r[0]=1, r[1]=0.5 for this spectrum
    autocorr = autocorrelation_from_power(power[None, :])
    assert autocorr[0, 1] / autocorr[0, 0] == pytest.approx(0.5)
