import numpy as np

from qbestd.audio.preprocess import apply_preemphasis, remove_dc_offset


def test_preemphasis_matches_difference_equation():
    samples = np.array([1.0, 2.0, 4.0, 3.0])
    expected = np.array([1.0, 2.0 - 0.9, 4.0 - 1.8, 3.0 - 3.6])
    assert np.allclose(apply_preemphasis(samples, 0.9), expected)


def test_zero_coefficient_is_identity():
    samples = np.random.default_rng(0).normal(size=50)
    assert np.array_equal(apply_preemphasis(samples, 0.0), samples)


def test_preemphasis_does_not_modify_input():
    samples = np.array([1.0, 2.0, 3.0])
    apply_preemphasis(samples)
    assert np.array_equal(samples, [1.0, 2.0, 3.0])


def test_dc_removal_gives_zero_mean():
    samples = np.random.default_rng(1).normal(size=100) + 3.0
    assert abs(remove_dc_offset(samples).mean()) < 1e-12
