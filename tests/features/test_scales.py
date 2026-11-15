import numpy as np
import pytest

from qbestd.features.scales import (
    VTLN_WARP_FACTORS,
    bark_to_hz,
    hz_to_bark,
    hz_to_mel,
    mel_to_hz,
    vtln_cutoff_frequency,
    warp_frequency_piecewise,
    warp_mel_scale,
)

FREQUENCIES = np.linspace(0, 8000, 161)


def test_warp_factor_grid_has_13_values():
    assert len(VTLN_WARP_FACTORS) == 13
    assert VTLN_WARP_FACTORS[0] == 0.88
    assert VTLN_WARP_FACTORS[-1] == 1.12
    assert np.allclose(np.diff(VTLN_WARP_FACTORS), 0.02)


def test_mel_round_trip_and_reference_value():
    assert np.allclose(mel_to_hz(hz_to_mel(FREQUENCIES)), FREQUENCIES, atol=1e-9)
    assert hz_to_mel(1000.0) == pytest.approx(1000.0, abs=0.1)


def test_bark_round_trip():
    assert np.allclose(bark_to_hz(hz_to_bark(FREQUENCIES)), FREQUENCIES, atol=1e-9)
    assert hz_to_bark(4000.0) == pytest.approx(6 * np.arcsinh(4000 / 600))


def test_alpha_one_is_identity():
    assert np.allclose(warp_frequency_piecewise(FREQUENCIES, 1.0, 16000),
                       FREQUENCIES)


def test_cutoff_and_slope_at_alpha_088_8khz():
    assert vtln_cutoff_frequency(0.88, 8000) == pytest.approx(3500.0)
    below = warp_frequency_piecewise(np.array([1000.0]), 0.88, 8000)[0]
    assert below == pytest.approx(1120.0)  # slope 2 - 0.88 = 1.12


@pytest.mark.parametrize("warp_factor", VTLN_WARP_FACTORS)
def test_warp_is_continuous_monotonic_and_fixes_nyquist(warp_factor):
    sample_rate = 8000
    warped = warp_frequency_piecewise(np.linspace(0, 4000, 801), warp_factor,
                                      sample_rate)
    assert np.all(np.diff(warped) > 0)
    assert warped[0] == 0
    assert warped[-1] == pytest.approx(4000.0)
    cutoff = vtln_cutoff_frequency(warp_factor, sample_rate)
    left, right = warp_frequency_piecewise(
        np.array([cutoff - 1e-9, cutoff + 1e-9]), warp_factor, sample_rate)
    assert right - left == pytest.approx(0.0, abs=1e-6)


def test_cutoff_backs_off_for_extreme_warp():
    # alpha = 0.8: slope 1.2 -> 1.2 * 0.875 >= 1, so ratio drops to 0.825.
    assert vtln_cutoff_frequency(0.8, 8000) == pytest.approx(0.825 * 4000)


def test_cutoff_impossible_raises():
    with pytest.raises(ValueError):
        vtln_cutoff_frequency(-100.0, 8000)


def test_warp_mel_scale_matches_formula_and_identity():
    assert np.allclose(warp_mel_scale(FREQUENCIES, 1.0), hz_to_mel(FREQUENCIES))
    assert warp_mel_scale(1000.0, 1.1) == pytest.approx(
        2595 * np.log10(1 + 1000 / (700 * 1.1)))
    with pytest.raises(ValueError):
        warp_mel_scale(100.0, 0.0)


def test_upper_anchor_gives_3500_hz_cutoff_for_4khz_band():
    assert vtln_cutoff_frequency(0.88, 16000, upper_hz=4000.0) \
        == pytest.approx(3500.0)
    assert vtln_cutoff_frequency(0.88, 16000) == pytest.approx(7000.0)


@pytest.mark.parametrize("warp_factor", VTLN_WARP_FACTORS)
def test_upper_anchor_maps_to_itself_and_is_monotonic(warp_factor):
    frequencies = np.linspace(0, 8000, 1601)
    warped = warp_frequency_piecewise(frequencies, warp_factor, 16000,
                                      upper_hz=4000.0)
    assert np.all(np.diff(warped) > 0)
    index = int(np.argmin(np.abs(frequencies - 4000.0)))
    assert warped[index] == pytest.approx(4000.0)


def test_default_anchor_is_nyquist():
    frequencies = np.linspace(0, 8000, 101)
    assert np.array_equal(
        warp_frequency_piecewise(frequencies, 0.92, 16000),
        warp_frequency_piecewise(frequencies, 0.92, 16000, upper_hz=8000.0))
