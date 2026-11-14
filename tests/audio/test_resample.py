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


@pytest.mark.parametrize("bad_rate", [0, -8000, 8000.5])
def test_invalid_rates_raise(bad_rate):
    with pytest.raises(ValueError):
        resample_audio(np.zeros(10), bad_rate, 8000)
    with pytest.raises(ValueError):
        resample_audio(np.zeros(10), 8000, bad_rate)


def test_scale_time_axis_empty_and_single_sample():
    assert scale_time_axis(np.array([]), 1.1).shape == (0,)
    single = np.array([0.5])
    result = scale_time_axis(single, 1.1)
    assert np.array_equal(result, single)
    assert result is not single


def test_antialias_attenuates_tone_that_would_fold():
    tone = make_tone(3900, 8000, duration=1.0)
    folded = scale_time_axis(tone, 1.12, antialias=False)
    filtered = scale_time_axis(tone, 1.12)
    rms = lambda signal: np.sqrt(np.mean(signal[200:-200] ** 2))
    attenuation_db = 20 * np.log10(rms(folded) / rms(filtered))
    assert attenuation_db >= 20


def test_antialias_not_applied_for_slowdown():
    tone = make_tone(1000, 8000)
    assert np.allclose(scale_time_axis(tone, 0.9),
                       scale_time_axis(tone, 0.9, antialias=False))


def test_antialias_handles_short_signals():
    assert len(scale_time_axis(np.ones(20), 1.12)) > 0
