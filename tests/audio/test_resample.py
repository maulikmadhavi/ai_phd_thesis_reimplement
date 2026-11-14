import numpy as np
import pytest

from qbestd.audio.resample import resample_audio, scale_time_axis


def make_tone(frequency, sample_rate, duration=1.0):
    time = np.arange(int(sample_rate * duration)) / sample_rate
    return np.sin(2 * np.pi * frequency * time)


def peak_frequency(samples, sample_rate):
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    return np.argmax(spectrum) * sample_rate / len(samples)


def test_downsampling_halves_length():
    resampled = resample_audio(make_tone(1000, 16000), 16000, 8000)
    assert abs(len(resampled) - 8000) <= 1


def test_tone_peak_frequency_preserved():
    resampled = resample_audio(make_tone(1000, 16000), 16000, 8000)
    assert peak_frequency(resampled, 8000) == pytest.approx(1000, abs=2)


def test_equal_rates_is_identity():
    samples = make_tone(500, 8000)
    result = resample_audio(samples, 8000, 8000)
    assert np.array_equal(result, samples)
    assert result is not samples


@pytest.mark.parametrize("warp_factor", [0.88, 1.12])
def test_scale_time_axis_moves_peak_by_factor(warp_factor):
    warped = scale_time_axis(make_tone(1000, 8000, duration=2.0), warp_factor)
    assert peak_frequency(warped, 8000) == pytest.approx(
        1000 * warp_factor, abs=2)


def test_scale_time_axis_identity_and_length():
    samples = make_tone(300, 8000)
    assert np.allclose(scale_time_axis(samples, 1.0), samples)
    assert len(scale_time_axis(samples, 2.0)) == (len(samples) - 1) // 2 + 1


def test_scale_time_axis_rejects_nonpositive_factor():
    with pytest.raises(ValueError):
        scale_time_axis(np.zeros(10), 0.0)
