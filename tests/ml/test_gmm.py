import numpy as np
import pytest
from scipy.stats import multivariate_normal

from qbestd.ml.gmm import (
    DiagonalGmm,
    component_posteriors,
    count_floored,
    em_step,
    frame_log_likelihoods,
    global_variance_floor,
    init_gmm_from_codebook,
    load_gmm,
    save_gmm,
    train_gmm,
)
from qbestd.ml.vq import lbg_codebook

TRUE_WEIGHTS = np.array([0.5, 0.3, 0.2])
TRUE_MEANS = np.array([[0.0, 0.0], [6.0, 0.0], [0.0, 6.0]])
TRUE_STDS = np.array([[0.5, 0.5], [0.7, 0.4], [0.4, 0.8]])


def mixture_sample(n=6000, seed=0):
    rng = np.random.default_rng(seed)
    labels = rng.choice(3, size=n, p=TRUE_WEIGHTS)
    return TRUE_MEANS[labels] + TRUE_STDS[labels] * rng.normal(size=(n, 2))


def small_gmm():
    return DiagonalGmm(np.array([0.4, 0.6]),
                       np.array([[0.0, 0.0], [3.0, 1.0]]),
                       np.array([[1.0, 2.0], [0.5, 0.5]]))


def test_log_likelihood_matches_scipy_reference():
    gmm = small_gmm()
    x = np.random.default_rng(0).normal(size=(50, 2))
    expected = np.log(sum(
        gmm.weights[k] * multivariate_normal(
            gmm.means[k], np.diag(gmm.variances[k])).pdf(x)
        for k in range(2)))
    assert np.allclose(frame_log_likelihoods(gmm, x), expected)


def test_train_gmm_recovers_two_separated_components():
    rng = np.random.default_rng(5)
    data = np.concatenate([rng.normal([0, 0], 0.5, size=(1500, 2)),
                           rng.normal([8, 3], 0.7, size=(500, 2))])
    gmm, _ = train_gmm(data, 2, n_iter=10)
    order = np.argsort(-gmm.weights)
    assert np.allclose(gmm.weights[order], [0.75, 0.25], atol=0.03)
    assert np.allclose(gmm.means[order], [[0, 0], [8, 3]], atol=0.1)
    assert np.allclose(np.sqrt(gmm.variances[order]),
                       [[0.5, 0.5], [0.7, 0.7]], atol=0.08)


def test_three_component_fit_recovers_parameters():
    data = mixture_sample()
    # fit exactly 3 components by EM from means offset by 0.5
    gmm = DiagonalGmm(np.full(3, 1 / 3), TRUE_MEANS + 0.5,
                      np.ones((3, 2)))
    floor = global_variance_floor(data)
    for _ in range(30):
        gmm, _ = em_step(gmm, data, floor)
    order = np.argsort(-gmm.weights)
    assert np.allclose(gmm.weights[order], TRUE_WEIGHTS, atol=0.03)
    assert np.allclose(gmm.means[order], TRUE_MEANS, atol=0.1)
    assert np.allclose(np.sqrt(gmm.variances[order]), TRUE_STDS, atol=0.08)


def test_log_likelihood_non_decreasing_over_iterations():
    _, history = train_gmm(mixture_sample(), 4, n_iter=10)
    assert len(history) == 11
    assert all(b >= a - 1e-6 for a, b in zip(history, history[1:]))
    assert history[-1] > history[0]


def test_posteriors_sum_to_one_and_are_finite_for_outlier():
    gmm = small_gmm()
    outlier = np.array([[1e3, -1e3], [0.0, 0.0], [3.0, 1.0]])
    posteriors = component_posteriors(gmm, outlier)
    assert np.all(np.isfinite(posteriors))
    assert np.allclose(posteriors.sum(axis=1), 1.0)
    assert np.all(np.isfinite(frame_log_likelihoods(gmm, outlier)))


def test_variance_floor_engages_on_constant_dimension():
    rng = np.random.default_rng(0)
    data = np.column_stack([rng.normal(size=500), np.full(500, 2.0)])
    floor = global_variance_floor(data, 0.01)
    assert floor[1] == pytest.approx(0.01e-10 * 1e2, rel=1e-6) or \
        floor[1] > 0
    gmm, _ = train_gmm(data, 2, n_iter=3)
    assert np.all(gmm.variances[:, 1] > 0)
    assert count_floored(gmm, floor) >= 2


def test_floor_is_ratio_of_global_variance():
    data = mixture_sample()
    assert np.allclose(global_variance_floor(data, 0.01),
                       0.01 * data.var(axis=0))


def test_chunked_em_equals_unchunked_em():
    data = mixture_sample(n=1500)
    floor = global_variance_floor(data)
    start = small_gmm()
    full, ll_full = em_step(start, data, floor, chunk_frames=10_000)
    chunked, ll_chunked = em_step(start, data, floor, chunk_frames=77)
    assert ll_full == pytest.approx(ll_chunked)
    assert np.allclose(full.weights, chunked.weights)
    assert np.allclose(full.means, chunked.means)
    assert np.allclose(full.variances, chunked.variances)


def test_chunked_posteriors_equal_unchunked():
    data = mixture_sample(n=500)
    assert np.allclose(component_posteriors(small_gmm(), data, 10_000),
                       component_posteriors(small_gmm(), data, 33))


def test_save_load_round_trip(tmp_path):
    gmm, _ = train_gmm(mixture_sample(n=1000), 2, n_iter=2)
    meta = {"kind": "mfcc", "profile": "timit_matlab", "dims": 2,
            "n_iter": 2, "rows": 1000}
    save_gmm(tmp_path / "m.npz", gmm, meta)
    loaded, loaded_meta = load_gmm(tmp_path / "m.npz")
    assert np.array_equal(loaded.weights, gmm.weights)
    assert np.array_equal(loaded.means, gmm.means)
    assert np.array_equal(loaded.variances, gmm.variances)
    assert loaded_meta == meta


def test_init_from_codebook_has_cluster_fractions():
    data = mixture_sample(n=2000)
    codebook, assignments, _ = lbg_codebook(data, 4)
    gmm = init_gmm_from_codebook(data, codebook, assignments,
                                 global_variance_floor(data))
    fractions = np.bincount(assignments, minlength=4) / len(data)
    assert np.allclose(gmm.weights, fractions)
    assert np.allclose(gmm.means, codebook)


@pytest.mark.parametrize("weights, means, variances", [
    ([0.5, 0.5], [[0.0], [1.0], [2.0]], [[1.0], [1.0], [1.0]]),
    ([0.5, 0.4], [[0.0], [1.0]], [[1.0], [1.0]]),
    ([1.0, 0.0], [[0.0], [1.0]], [[1.0], [1.0]]),
    ([0.5, 0.5], [[0.0], [1.0]], [[1.0], [0.0]]),
    ([0.5, 0.5], [[0.0], [np.nan]], [[1.0], [1.0]]),
    ([0.5, 0.5], [[0.0, 1.0], [1.0, 2.0]], [[1.0], [1.0]]),
])
def test_invalid_parameters_raise(weights, means, variances):
    with pytest.raises(ValueError):
        DiagonalGmm(np.array(weights), np.array(means), np.array(variances))


def test_feature_dimension_mismatch_raises():
    with pytest.raises(ValueError, match="features must be"):
        frame_log_likelihoods(small_gmm(), np.zeros((4, 3)))
