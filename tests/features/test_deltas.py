import numpy as np
import pytest

from qbestd.features.deltas import append_deltas, compute_deltas


def test_linear_ramp_gives_slope_in_interior():
    ramp = np.stack([0.5 * np.arange(20), -2.0 * np.arange(20)], axis=1)
    deltas = compute_deltas(ramp, window=2)
    assert np.allclose(deltas[2:-2, 0], 0.5)
    assert np.allclose(deltas[2:-2, 1], -2.0)


def test_constant_gives_zero():
    assert np.all(compute_deltas(np.full((10, 3), 4.2)) == 0)


def test_edge_replication_hand_computed():
    features = np.array([[1.0], [2.0], [4.0], [7.0]])
    # t=0 with window 1: (x[1] - x[-1 -> x[0]]) / 2 = (2 - 1) / 2
    assert compute_deltas(features, window=1)[0, 0] == pytest.approx(0.5)
    # t=3 with window 2: [1*(x[4=x3]-x[2]) + 2*(x[5=x3]-x[1])] / 10
    expected = (1 * (7 - 4) + 2 * (7 - 2)) / 10
    assert compute_deltas(features, window=2)[3, 0] == pytest.approx(expected)


def test_shapes_13_to_39():
    static = np.random.default_rng(0).normal(size=(50, 13))
    assert compute_deltas(static).shape == (50, 13)
    assert append_deltas(static).shape == (50, 39)
    assert append_deltas(static, order=1).shape == (50, 26)
    assert append_deltas(static, order=0).shape == (50, 13)


def test_appended_blocks_are_static_delta_acceleration():
    static = np.random.default_rng(1).normal(size=(30, 4))
    stacked = append_deltas(static, window=2, order=2)
    delta = compute_deltas(static, 2)
    assert np.array_equal(stacked[:, :4], static)
    assert np.allclose(stacked[:, 4:8], delta)
    assert np.allclose(stacked[:, 8:], compute_deltas(delta, 2))


def test_single_frame_does_not_crash():
    assert np.all(compute_deltas(np.ones((1, 3))) == 0)


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        compute_deltas(np.ones((5, 2)), window=0)
