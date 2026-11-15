import numpy as np
import pytest

from qbestd.search.distance import symmetric_kl_matrix


def random_posteriors(rows, k, seed):
    rng = np.random.default_rng(seed)
    raw = rng.gamma(0.5, size=(rows, k)) + 1e-6
    return raw / raw.sum(axis=1, keepdims=True)


def loop_reference(test, query, floor=1e-10):
    out = np.zeros((len(test), len(query)))
    for i, t in enumerate(test):
        for j, q in enumerate(query):
            t_c, q_c = np.maximum(t, floor), np.maximum(q, floor)
            out[i, j] = (np.sum(t_c * np.log(t_c / q_c))
                         + np.sum(q_c * np.log(q_c / t_c)))
    return out


def test_identical_rows_give_zero():
    post = random_posteriors(6, 5, 0)
    matrix = symmetric_kl_matrix(post, post)
    assert np.allclose(np.diag(matrix), 0.0, atol=1e-12)


def test_swapping_inputs_transposes_the_result():
    test, query = random_posteriors(7, 4, 1), random_posteriors(5, 4, 2)
    forward = symmetric_kl_matrix(test, query)
    assert forward.shape == (7, 5)
    assert np.allclose(forward, symmetric_kl_matrix(query, test).T)


def test_result_is_non_negative():
    test, query = random_posteriors(30, 8, 3), random_posteriors(20, 8, 4)
    assert symmetric_kl_matrix(test, query).min() >= 0.0


def test_matches_double_loop_reference():
    test, query = random_posteriors(9, 6, 5), random_posteriors(4, 6, 6)
    assert np.allclose(symmetric_kl_matrix(test, query),
                       loop_reference(test, query))


def test_zeros_stay_finite_through_the_floor():
    test = np.array([[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]])
    query = np.array([[0.0, 1.0, 0.0]])
    matrix = symmetric_kl_matrix(test, query)
    assert np.all(np.isfinite(matrix))
    assert np.allclose(matrix, loop_reference(test, query))
    assert matrix[0, 0] > 10  # very different distributions


def test_known_value():
    test, query = np.array([[0.5, 0.5]]), np.array([[0.25, 0.75]])
    expected = (0.5 - 0.25) * np.log(0.5 / 0.25) + (0.5 - 0.75) * np.log(
        0.5 / 0.75)
    assert symmetric_kl_matrix(test, query)[0, 0] == pytest.approx(expected)


def test_component_mismatch_raises():
    with pytest.raises(ValueError):
        symmetric_kl_matrix(np.ones((2, 3)) / 3, np.ones((2, 4)) / 4)


def test_one_dimensional_input_raises():
    with pytest.raises(ValueError):
        symmetric_kl_matrix(np.ones(3) / 3, np.ones((2, 3)) / 3)
