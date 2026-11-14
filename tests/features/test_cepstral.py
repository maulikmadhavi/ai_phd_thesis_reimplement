import numpy as np
import pytest

from qbestd.features.cepstral import (
    dct_cepstra,
    lifter_cepstra,
    lifter_weights,
    log_compress,
)


def explicit_dct_matrix(n_rows, n_filters):
    index = np.arange(n_filters)
    matrix = np.stack([
        np.sqrt(2.0 / n_filters)
        * np.cos(row * (2 * index + 1) * np.pi / (2 * n_filters))
        for row in range(n_rows)])
    matrix[0] /= np.sqrt(2.0)
    return matrix


def test_dct_matches_explicit_cosine_matrix():
    log_energies = np.random.default_rng(0).normal(size=(5, 26))
    expected = log_energies @ explicit_dct_matrix(13, 26).T
    assert np.allclose(dct_cepstra(log_energies, 13), expected)


def test_include_c0_false_takes_c1_onwards():
    log_energies = np.random.default_rng(1).normal(size=(3, 26))
    with_c0 = dct_cepstra(log_energies, 14, include_c0=True)
    without_c0 = dct_cepstra(log_energies, 13, include_c0=False)
    assert without_c0.shape == (3, 13)
    assert np.allclose(without_c0, with_c0[:, 1:14])


def test_too_many_coefficients_raises():
    with pytest.raises(ValueError):
        dct_cepstra(np.zeros((2, 13)), 13, include_c0=False)


def test_lifter_zero_is_identity():
    ceps = np.random.default_rng(2).normal(size=(4, 13))
    assert np.array_equal(lifter_cepstra(ceps, 0), ceps)


def test_lifter_22_matches_htk_formula():
    weights = lifter_weights(13, 22)
    expected = 1 + 11 * np.sin(np.pi * np.arange(13) / 22)
    assert np.allclose(weights, expected)
    assert weights[0] == 1.0
    ceps = np.ones((2, 13))
    assert np.allclose(lifter_cepstra(ceps, 22), np.tile(expected, (2, 1)))


def test_lifter_first_index_shifts_weights():
    assert np.allclose(lifter_weights(3, 22, first_index=1),
                       lifter_weights(4, 22)[1:])


def test_log_floor_prevents_minus_infinity():
    result = log_compress(np.array([0.0, -1.0, 1.0]))
    assert np.all(np.isfinite(result))
    assert result[0] == pytest.approx(np.log(1e-10))
    assert result[2] == 0.0
