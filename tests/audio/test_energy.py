import numpy as np
import pytest

from qbestd.audio.energy import (
    frame_teager_energy,
    log_energy,
    short_time_energy,
    teager_energy,
)


def test_energy_of_ones_equals_frame_length():
    assert np.array_equal(short_time_energy(np.ones((3, 200))), [200.0] * 3)


def test_log_floor_applied_to_silence():
    assert log_energy(np.zeros((2, 50)), floor=1e-10) == pytest.approx(
        [np.log(1e-10)] * 2)


def test_log_energy_matches_log_of_energy_above_floor():
    frames = np.full((1, 4), 2.0)
    assert log_energy(frames)[0] == pytest.approx(np.log(16.0))


def test_teager_energy_of_cosine_interior():
    amplitude, omega = 0.7, 0.3
    samples = amplitude * np.cos(omega * np.arange(200))
    energy = teager_energy(samples)
    expected = amplitude ** 2 * np.sin(omega) ** 2
    assert np.allclose(energy[1:-1], expected, atol=1e-9)


def test_teager_edges_replicate_neighbours():
    energy = teager_energy(np.array([1.0, 2.0, 4.0, 3.0, 5.0]))
    assert energy[0] == energy[1]
    assert energy[-1] == energy[-2]
    assert energy.shape == (5,)


def test_frame_teager_energy_is_row_mean():
    frames = np.stack([np.cos(0.3 * np.arange(100))] * 2)
    assert frame_teager_energy(frames) == pytest.approx(
        [np.sin(0.3) ** 2] * 2, abs=1e-3)


def test_teager_rejects_too_short_input():
    with pytest.raises(ValueError):
        teager_energy(np.ones(2))
