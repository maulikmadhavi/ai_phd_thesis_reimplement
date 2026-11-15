import numpy as np
import pytest

from qbestd.ml.vq import (
    assign_to_codebook,
    assign_with_distortion,
    cluster_statistics,
    kmeans_refine,
    lbg_codebook,
    split_codebook,
)

CENTERS = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]])


def blobs(n_per=200, spread=0.3, seed=0):
    rng = np.random.default_rng(seed)
    return np.concatenate([c + spread * rng.normal(size=(n_per, 2))
                           for c in CENTERS])


def nearest_distance(codebook, truth):
    return np.linalg.norm(codebook - truth, axis=1).min()


def test_four_blobs_give_four_centroids_near_truth():
    codebook, assignments, _ = lbg_codebook(blobs(), 4)
    assert codebook.shape == (4, 2)
    for center in CENTERS:
        assert nearest_distance(codebook, center) < 0.1
    assert len(np.unique(assignments)) == 4


def test_distortion_is_non_increasing_within_each_level():
    _, _, history = lbg_codebook(blobs(spread=1.0), 8)
    assert len(history) == 4  # sizes 1, 2, 4, 8
    for level in history:
        assert all(b <= a + 1e-9 for a, b in zip(level, level[1:]))


def test_more_clusters_give_lower_final_distortion():
    _, _, history = lbg_codebook(blobs(spread=1.0), 8)
    finals = [level[-1] for level in history]
    assert all(b < a for a, b in zip(finals, finals[1:]))


def test_deterministic_under_seed():
    first = lbg_codebook(blobs(), 4, seed=3)[0]
    second = lbg_codebook(blobs(), 4, seed=3)[0]
    assert np.array_equal(first, second)


@pytest.mark.parametrize("n_clusters", [0, 3, 6, -2])
def test_non_power_of_two_raises(n_clusters):
    with pytest.raises(ValueError, match="power of two"):
        lbg_codebook(blobs(), n_clusters)


def test_more_clusters_than_frames_raises():
    with pytest.raises(ValueError, match="exceeds"):
        lbg_codebook(np.zeros((4, 2)), 8)


@pytest.mark.parametrize("bad", [np.zeros(5), np.zeros((0, 2)),
                                 np.array([[np.nan, 0.0], [1.0, 1.0]])])
def test_malformed_features_raise(bad):
    with pytest.raises(ValueError):
        lbg_codebook(bad, 1)


def test_single_cluster_is_the_mean():
    data = blobs()
    codebook, assignments, _ = lbg_codebook(data, 1)
    assert np.allclose(codebook[0], data.mean(axis=0))
    assert np.all(assignments == 0)


def test_split_uses_mean_plus_minus_epsilon_sigma():
    means = np.array([[1.0, 2.0]])
    stds = np.array([[0.5, 1.0]])
    split = split_codebook(means, stds, 0.2, jitter=np.zeros((1, 2)))
    assert np.allclose(split, [[0.9, 1.8], [1.1, 2.2]])


def test_default_epsilon_is_the_thesis_value():
    import inspect
    assert inspect.signature(lbg_codebook).parameters["epsilon"].default == 0.2


def test_chunked_assignment_equals_full_assignment():
    data = blobs()
    codebook = CENTERS + 0.1
    full = assign_to_codebook(data, codebook, chunk_frames=10_000)
    chunked = assign_to_codebook(data, codebook, chunk_frames=37)
    assert np.array_equal(full, chunked)
    _, d_full = assign_with_distortion(data, codebook, 10_000)
    _, d_chunked = assign_with_distortion(data, codebook, 37)
    assert np.allclose(d_full, d_chunked)


def test_chunked_statistics_equal_full_statistics():
    data = blobs()
    labels = assign_to_codebook(data, CENTERS)
    full = cluster_statistics(data, labels, 4, chunk_frames=10_000)
    chunked = cluster_statistics(data, labels, 4, chunk_frames=41)
    for a, b in zip(full, chunked):
        assert np.allclose(a, b)


def test_empty_cluster_is_reseeded_from_the_highest_distortion_cluster():
    data = blobs(spread=0.5)
    far_away = np.array([[1000.0, 1000.0]])  # attracts no frame
    start = np.concatenate([CENTERS[:3], far_away])
    codebook, assignments, _ = kmeans_refine(data, start, 0.2, 20, 1e-4,
                                             10_000)
    assert len(np.unique(assignments)) == 4
    for center in CENTERS:
        assert nearest_distance(codebook, center) < 0.5


def test_duplicate_points_still_split_without_error():
    data = np.zeros((20, 3))
    data[10:] = 1.0
    codebook, assignments, _ = lbg_codebook(data, 4, seed=1)
    assert codebook.shape == (4, 3)
    assert np.all(np.isfinite(codebook))


def test_float32_input_is_accepted():
    codebook, _, _ = lbg_codebook(blobs().astype(np.float32), 4)
    assert codebook.dtype == np.float64
    assert codebook.shape == (4, 2)
