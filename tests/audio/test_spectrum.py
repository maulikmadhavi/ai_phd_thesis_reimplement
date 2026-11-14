import numpy as np
import pytest

from qbestd.audio.spectrum import (
    complex_spectrum,
    fft_bin_frequencies,
    magnitude_spectrum,
    next_power_of_two,
    power_spectrum,
)


def test_next_power_of_two():
    assert [next_power_of_two(n) for n in (1, 2, 3, 200, 256, 257)] == [
        1, 2, 4, 256, 256, 512]
    with pytest.raises(ValueError):
        next_power_of_two(0)


def test_200_sample_frame_uses_256_fft():
    spectrum = power_spectrum(np.zeros((3, 200)))
    assert spectrum.shape == (3, 129)


def test_tone_peaks_at_expected_bin():
    sample_rate, n_fft = 8000, 256
    bin_index = 32  # 1000 Hz exactly
    time = np.arange(n_fft) / sample_rate
    frame = np.sin(2 * np.pi * fft_bin_frequencies(n_fft, sample_rate)[bin_index]
                   * time)
    spectrum = power_spectrum(frame[None, :], n_fft)[0]
    assert np.argmax(spectrum) == bin_index


def test_parseval_relation():
    frames = np.random.default_rng(0).normal(size=(4, 256))
    spectrum = power_spectrum(frames, 256)
    full_sum = (spectrum[:, 0] + spectrum[:, -1]
                + 2 * spectrum[:, 1:-1].sum(axis=1))
    assert np.allclose(full_sum / 256, (frames ** 2).sum(axis=1))


def test_power_is_magnitude_squared():
    frames = np.random.default_rng(1).normal(size=(2, 64))
    assert np.allclose(power_spectrum(frames), magnitude_spectrum(frames) ** 2)


def test_bin_frequencies_span_zero_to_nyquist():
    frequencies = fft_bin_frequencies(256, 8000)
    assert frequencies[0] == 0
    assert frequencies[-1] == 4000
    assert len(frequencies) == 129


def test_n_fft_shorter_than_frame_raises():
    with pytest.raises(ValueError, match="shorter than the frame"):
        power_spectrum(np.zeros((2, 200)), n_fft=128)


@pytest.mark.parametrize("bad_n_fft", [255.5, 0, -256])
def test_invalid_n_fft_raises(bad_n_fft):
    with pytest.raises(ValueError):
        power_spectrum(np.zeros((2, 200)), n_fft=bad_n_fft)


def test_n_fft_equal_to_frame_length_is_allowed():
    assert power_spectrum(np.zeros((2, 200)), n_fft=200).shape == (2, 101)


def test_complex_spectrum_is_two_sided_and_consistent():
    frames = np.random.default_rng(2).normal(size=(3, 200))
    full = complex_spectrum(frames)
    assert full.shape == (3, 256)
    assert np.allclose(np.abs(full[:, :129]), magnitude_spectrum(frames))
    assert np.allclose(full[:, 1:128], np.conj(full[:, :128:-1]))


def test_complex_spectrum_validates_n_fft():
    with pytest.raises(ValueError):
        complex_spectrum(np.zeros((1, 200)), n_fft=100)
