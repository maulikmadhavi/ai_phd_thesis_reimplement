import numpy as np
import pytest

from qbestd.ml.gmm import DiagonalGmm, train_gmm
from qbestd.ml.posteriorgram import (
    floor_and_renormalise,
    gaussian_posteriorgram,
    mean_posteriorgram_entropy,
    utterance_log_likelihood,
)


def gmm_at(means):
    means = np.asarray(means, dtype=float)
    k = len(means)
    return DiagonalGmm(np.full(k, 1.0 / k), means, np.ones_like(means))


def test_shape_row_sums_and_range():
    gmm = gmm_at([[0, 0], [5, 5], [-5, 5]])
    x = np.random.default_rng(0).normal(size=(40, 2)) * 3
    grid = gaussian_posteriorgram(gmm, x)
    assert grid.shape == (40, 3)
    assert np.allclose(grid.sum(axis=1), 1.0)
    assert grid.min() >= 0 and grid.max() <= 1


def test_frame_near_a_mean_is_assigned_to_it():
    gmm = gmm_at([[0, 0], [5, 5]])
    grid = gaussian_posteriorgram(gmm, np.array([[0.1, 0.0], [4.9, 5.1]]))
    assert np.argmax(grid, axis=1).tolist() == [0, 1]
    assert grid[0, 0] > 0.999


def test_floor_effect_and_row_sums():
    grid = np.array([[1.0, 0.0, 0.0], [0.5, 0.5, 0.0]])
    floored = floor_and_renormalise(grid, 1e-6)
    assert floored.min() >= 1e-6 / (1 + 3e-6)
    assert np.allclose(floored.sum(axis=1), 1.0)
    assert np.all(np.log(floored) > -np.inf)
    assert floored[0, 0] == pytest.approx(1.0, abs=1e-5)


def test_floor_leaves_a_large_entries_nearly_unchanged():
    grid = np.array([[0.25, 0.25, 0.25, 0.25]])
    assert np.allclose(floor_and_renormalise(grid), grid)


@pytest.mark.parametrize("floor", [0.0, -1e-3, 0.6])
def test_invalid_floor_raises(floor):
    with pytest.raises(ValueError):
        floor_and_renormalise(np.full((2, 2), 0.5), floor)


def test_wrong_rank_raises():
    with pytest.raises(ValueError):
        floor_and_renormalise(np.ones(4))


def test_matched_gmm_beats_mismatched_gmm():
    rng = np.random.default_rng(1)
    speech_a = rng.normal([0, 0], 1.0, size=(400, 2))
    speech_b = rng.normal([6, 6], 1.0, size=(400, 2))
    gmm_a, _ = train_gmm(speech_a, 2, n_iter=5)
    gmm_b, _ = train_gmm(speech_b, 2, n_iter=5)
    assert utterance_log_likelihood(gmm_a, speech_a) > \
        utterance_log_likelihood(gmm_b, speech_a)
    assert utterance_log_likelihood(gmm_b, speech_b) > \
        utterance_log_likelihood(gmm_a, speech_b)


def test_likelihood_is_finite_for_far_outliers_and_nan_for_empty():
    gmm = gmm_at([[0, 0], [5, 5]])
    assert np.isfinite(utterance_log_likelihood(gmm, np.array([[1e4, 1e4]])))
    assert np.isnan(utterance_log_likelihood(gmm, np.zeros((0, 2))))


def test_mean_entropy_is_zero_for_one_hot_and_log_k_for_uniform():
    one_hot = np.eye(4)
    uniform = np.full((3, 4), 0.25)
    assert mean_posteriorgram_entropy([one_hot]) == pytest.approx(0.0)
    assert mean_posteriorgram_entropy([uniform]) == pytest.approx(np.log(4))
    # pooled over frames: 4 frames of 0 and 3 frames of log 4
    assert mean_posteriorgram_entropy([one_hot, uniform]) == pytest.approx(
        3 * np.log(4) / 7)
    assert np.isnan(mean_posteriorgram_entropy([np.zeros((0, 4))]))
