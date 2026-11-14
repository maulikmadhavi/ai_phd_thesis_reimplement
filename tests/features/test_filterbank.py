import numpy as np
import pytest

from qbestd.audio.spectrum import fft_bin_frequencies
from qbestd.features.filterbank import (
    mel_filter_centers_hz,
    mel_filterbank,
)
from qbestd.features.scales import hz_to_mel


def peak_bins(bank):
    return np.argmax(bank, axis=1)


def test_shape_and_non_negative():
    bank = mel_filterbank(26, 256, 8000)
    assert bank.shape == (26, 129)
    assert np.all(bank >= 0)
    assert bank.max() <= 1.0 + 1e-12


def test_filter_peaks_increase_strictly():
    assert np.all(np.diff(peak_bins(mel_filterbank(26, 256, 8000))) > 0)


def test_centers_equally_spaced_in_mel():
    centers = mel_filter_centers_hz(26, 0.0, 4000.0)
    assert np.allclose(np.diff(hz_to_mel(centers)),
                       np.diff(hz_to_mel(centers))[0])
    assert 0 < centers[0] < centers[-1] < 4000


def test_no_energy_outside_band_when_unwarped():
    bank = mel_filterbank(20, 512, 16000, low_hz=300.0, high_hz=3400.0)
    frequencies = fft_bin_frequencies(512, 16000)
    outside = (frequencies < 300.0) | (frequencies > 3400.0)
    assert np.all(bank[:, outside] == 0)
    assert bank[:, ~outside].sum() > 0


def test_alpha_one_equals_default():
    assert np.array_equal(mel_filterbank(26, 256, 8000, warp_factor=1.0),
                          mel_filterbank(26, 256, 8000))


def test_alpha_above_one_moves_peaks_to_higher_bins():
    # A bin at f is seen at (2 - alpha) * f < f, so a fixed triangle is
    # reached only at a higher original frequency.
    base = peak_bins(mel_filterbank(26, 512, 8000))
    warped = peak_bins(mel_filterbank(26, 512, 8000, warp_factor=1.12))
    assert np.all(warped >= base)
    assert np.sum(warped > base) > 10


def test_alpha_below_one_moves_peaks_to_lower_bins():
    base = peak_bins(mel_filterbank(26, 512, 8000))
    warped = peak_bins(mel_filterbank(26, 512, 8000, warp_factor=0.88))
    assert np.all(warped <= base)
    assert np.sum(warped < base) > 10


def test_high_hz_above_nyquist_raises():
    with pytest.raises(ValueError, match="Nyquist"):
        mel_filterbank(26, 256, 8000, high_hz=5000.0)


@pytest.mark.parametrize("kwargs", [{"n_filters": 0},
                                    {"low_hz": 3000.0, "high_hz": 1000.0}])
def test_invalid_arguments_raise(kwargs):
    with pytest.raises(ValueError):
        mel_filterbank(**kwargs)
