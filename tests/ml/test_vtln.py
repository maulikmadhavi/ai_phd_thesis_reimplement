import numpy as np
import pytest

from qbestd.ml.gmm import DiagonalGmm, frame_log_likelihoods
from qbestd.ml.vtln import (
    WARP_FACTORS,
    estimate_warp_factors,
    utterance_log_likelihoods,
)


def tiny_gmm(dim=3):
    return DiagonalGmm(np.array([0.5, 0.5]),
                       np.array([np.zeros(dim), np.ones(dim)]),
                       np.ones((2, dim)))


def test_the_thirteen_warps_run_from_088_to_112():
    assert len(WARP_FACTORS) == 13
    assert WARP_FACTORS[0] == 0.88 and WARP_FACTORS[-1] == 1.12
    assert 1.0 in WARP_FACTORS


def test_utterance_sums_match_the_frame_log_likelihoods():
    rng = np.random.default_rng(0)
    features = rng.normal(size=(10, 3))
    gmm = tiny_gmm()
    offsets = [0, 4, 4, 10]  # the middle utterance is empty
    got = utterance_log_likelihoods(features, offsets, gmm)
    frames = frame_log_likelihoods(gmm, features)
    assert got.shape == (3,)
    assert got[0] == pytest.approx(frames[:4].sum())
    assert got[1] == 0.0
    assert got[2] == pytest.approx(frames[4:].sum())


@pytest.mark.parametrize("offsets", [[1, 5, 10], [0, 5, 9], [0, 6, 5, 10],
                                     [[0, 10]]])
def test_bad_offsets_are_refused(offsets):
    with pytest.raises(ValueError, match="offsets"):
        utterance_log_likelihoods(np.zeros((10, 3)), offsets, tiny_gmm())


def test_a_planted_warp_is_found_for_every_utterance():
    rng = np.random.default_rng(1)
    planted = rng.choice(WARP_FACTORS, size=40)
    ll = rng.normal(size=(40, 13)) - 5.0
    for row, alpha in enumerate(planted):
        ll[row, WARP_FACTORS.index(alpha)] = 10.0
    assert np.array_equal(estimate_warp_factors(ll), planted)


def test_ties_go_to_the_warp_closest_to_one_then_the_smaller():
    ll = np.zeros((3, 13))
    assert estimate_warp_factors(ll).tolist() == [1.0, 1.0, 1.0]
    only = np.full((1, 13), -1.0)
    only[0, WARP_FACTORS.index(0.98)] = 0.0
    only[0, WARP_FACTORS.index(1.02)] = 0.0
    assert estimate_warp_factors(only)[0] == 0.98  # equally close: smaller
    only[0, WARP_FACTORS.index(0.96)] = 0.0
    assert estimate_warp_factors(only)[0] == 0.98  # closer to 1.0 than 0.96
    far = np.full((1, 13), -1.0)
    far[0, WARP_FACTORS.index(0.88)] = 0.0
    far[0, WARP_FACTORS.index(1.12)] = 0.0
    assert estimate_warp_factors(far)[0] == 0.88


def test_sum_and_mean_log_likelihood_give_the_same_warp():
    rng = np.random.default_rng(2)
    ll = rng.normal(size=(5, 13))
    frames = np.array([100, 80, 120, 60, 90])[:, None]
    assert np.array_equal(estimate_warp_factors(ll),
                          estimate_warp_factors(ll * frames))


@pytest.mark.parametrize("matrix", [np.zeros(13), np.zeros((4, 12)),
                                    np.zeros((4, 13, 1))])
def test_wrong_shapes_are_refused(matrix):
    with pytest.raises(ValueError, match="ll_matrix must be"):
        estimate_warp_factors(matrix)


def test_non_finite_log_likelihoods_are_refused():
    ll = np.zeros((2, 13))
    ll[1, 3] = np.nan
    with pytest.raises(ValueError, match="finite"):
        estimate_warp_factors(ll)


def test_a_custom_warp_list_is_honoured():
    ll = np.array([[0.0, 1.0, 0.5]])
    assert estimate_warp_factors(ll, warps=(0.9, 1.1, 1.0))[0] == 1.1


def test_the_label_map_is_a_mirror_and_the_grid_maps_onto_itself():
    from qbestd.ml.vtln import to_thesis_label
    assert float(to_thesis_label(0.88)) == 1.12
    assert float(to_thesis_label(1.0)) == 1.0
    labels = to_thesis_label(np.array(WARP_FACTORS))
    assert sorted(labels.tolist()) == sorted(WARP_FACTORS)
    assert np.array_equal(to_thesis_label(labels), np.array(WARP_FACTORS))


def test_histogram_counts_sum_to_the_utterances_and_refuse_off_grid_warps():
    from qbestd.ml.vtln import warp_histogram
    alphas = [0.88, 0.88, 1.0, 1.12]
    hist = warp_histogram(alphas)
    assert sum(hist.values()) == 4 and hist["1.12"] == 2 and hist["0.88"] == 1
    with pytest.raises(ValueError, match="grid"):
        warp_histogram([0.93])


def test_edge_shares_are_in_the_thesis_label():
    from qbestd.ml.vtln import edge_shares
    shares = edge_shares([0.88, 0.88, 1.0, 1.12])
    assert shares == {"0.88": 0.25, "1.12": 0.5}  # ours 0.88 -> thesis 1.12


def test_changed_share_counts_differing_utterances():
    from qbestd.ml.vtln import changed_share
    assert changed_share([1.0, 1.0, 0.9, 0.9], [1.0, 0.9, 0.9, 1.1]) == 0.5
    with pytest.raises(ValueError, match="same shape"):
        changed_share([1.0], [1.0, 1.0])
