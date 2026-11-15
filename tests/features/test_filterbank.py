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


@pytest.mark.parametrize("warp_factor", [0.88, 1.12])
def test_band_limited_support_stays_below_high_hz_when_warped(warp_factor):
    bank = mel_filterbank(26, 512, 16000, 0.0, 4000.0, warp_factor)
    frequencies = fft_bin_frequencies(512, 16000)
    assert np.all(bank[:, frequencies > 4000.0] == 0)
    assert bank[:, frequencies <= 4000.0].sum() > 0


def test_band_limited_warp_differs_from_nyquist_anchored_warp():
    # With the old fs/2 anchor the last filters reach beyond 4 kHz for 1.12
    # or stop short of it for 0.88; the band-edge anchor keeps them at 4 kHz.
    bank = mel_filterbank(26, 512, 16000, 0.0, 4000.0, 0.88)
    frequencies = fft_bin_frequencies(512, 16000)
    assert frequencies[np.flatnonzero(bank[-1])[-1]] >= 3900.0


def test_alpha_one_band_limited_is_unchanged():
    assert np.array_equal(
        mel_filterbank(26, 512, 16000, 0.0, 4000.0, 1.0),
        mel_filterbank(26, 512, 16000, 0.0, 4000.0))


def test_full_band_warp_is_nyquist_anchored():
    from qbestd.features.filterbank import mel_filter_edges_hz
    from qbestd.features.scales import warp_frequency_piecewise
    bank = mel_filterbank(26, 512, 16000, 0.0, 8000.0, 0.92)
    warped = warp_frequency_piecewise(fft_bin_frequencies(512, 16000), 0.92,
                                      16000, upper_hz=8000.0)
    edges = mel_filter_edges_hz(26, 0.0, 8000.0)
    low, mid, high = edges[:-2, None], edges[1:-1, None], edges[2:, None]
    expected = np.maximum(0.0, np.minimum((warped - low) / (mid - low),
                                          (high - warped) / (high - mid)))
    assert np.allclose(bank, expected)
