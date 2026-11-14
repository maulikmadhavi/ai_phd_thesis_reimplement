import numpy as np
import pytest

from qbestd.audio.framing import count_frames, frame_signal


def test_one_second_at_8khz_gives_98_frames():
    frames = frame_signal(np.zeros(8000), 8000)
    assert frames.shape == (98, 200)


def test_frame_k_starts_at_k_times_shift():
    samples = np.arange(8000, dtype="float64")
    frames = frame_signal(samples, 8000)
    for frame_index in (0, 1, 50, 97):
        assert frames[frame_index, 0] == frame_index * 80
        assert frames[frame_index, -1] == frame_index * 80 + 199


def test_short_input_returns_zero_frames():
    assert frame_signal(np.zeros(150), 8000).shape == (0, 200)


def test_count_frames_boundaries():
    assert count_frames(199, 200, 80) == 0
    assert count_frames(200, 200, 80) == 1
    assert count_frames(279, 200, 80) == 1
    assert count_frames(280, 200, 80) == 2


def test_zero_shift_raises():
    with pytest.raises(ValueError):
        frame_signal(np.zeros(8000), 8000, shift_ms=0.0)


def test_shift_rounding_to_zero_samples_raises():
    with pytest.raises(ValueError, match="rounds to 0"):
        frame_signal(np.zeros(8000), 8000, shift_ms=0.01)


@pytest.mark.parametrize("sample_rate, frame_ms", [(-8000, 25.0), (0, 25.0),
                                                   (8000, -25.0)])
def test_nonpositive_parameters_raise(sample_rate, frame_ms):
    with pytest.raises(ValueError):
        frame_signal(np.zeros(8000), sample_rate, frame_ms=frame_ms)


def test_count_frames_rejects_nonpositive_lengths():
    with pytest.raises(ValueError):
        count_frames(1000, 0, 80)
    with pytest.raises(ValueError):
        count_frames(1000, 200, 0)
