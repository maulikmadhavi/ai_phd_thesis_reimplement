import numpy as np
import pytest

from qbestd.audio.windowing import apply_window, make_window


def test_hamming_endpoints_are_0_08():
    window = make_window("hamming", 200)
    assert window[0] == pytest.approx(0.08)
    assert window[-1] == pytest.approx(0.08)
    assert window.max() == pytest.approx(1.0, abs=1e-3)


def test_hann_endpoints_are_zero():
    window = make_window("hann", 64)
    assert window[0] == pytest.approx(0.0, abs=1e-12)
    assert window[-1] == pytest.approx(0.0, abs=1e-12)


def test_rectangular_is_identity():
    frames = np.random.default_rng(0).normal(size=(5, 32))
    windowed = apply_window(frames, make_window("rectangular", 32))
    assert np.array_equal(windowed, frames)


def test_apply_window_preserves_shape():
    frames = np.ones((7, 200))
    assert apply_window(frames, make_window("hamming", 200)).shape == (7, 200)


def test_name_is_case_insensitive():
    assert np.array_equal(make_window("Hamming", 16), make_window("hamming", 16))


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        make_window("blackman", 16)


def test_length_mismatch_raises_value_error():
    with pytest.raises(ValueError):
        apply_window(np.ones((2, 10)), make_window("hamming", 8))
