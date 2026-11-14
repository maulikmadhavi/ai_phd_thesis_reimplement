import numpy as np
import pytest

from qbestd.features.cepstral import lifter_weights
from qbestd.features.plp import (
    PlpConfig,
    default_filter_count,
    equal_loudness_weights,
    extract_plp,
)


def speech_like(sample_rate, duration=1.0, seed=0):
    rng = np.random.default_rng(seed)
    time = np.arange(int(sample_rate * duration)) / sample_rate
    tone = np.sin(2 * np.pi * 300 * time) + 0.5 * np.sin(2 * np.pi * 1700 * time)
    return 0.1 * tone + 0.01 * rng.normal(size=len(time))


def test_shapes_with_and_without_deltas():
    samples = speech_like(8000)
    assert extract_plp(samples, 8000).shape == (98, 39)
    assert extract_plp(samples, 8000, PlpConfig(deltas=False)).shape == (98, 13)
    assert extract_plp(speech_like(16000), 16000,
                       PlpConfig(deltas=False)).shape == (98, 13)


def test_finite_on_silence_and_noise():
    assert np.all(np.isfinite(extract_plp(np.zeros(8000), 8000)))
    noise = np.random.default_rng(3).normal(size=8000)
    assert np.all(np.isfinite(extract_plp(noise, 8000)))


def test_equal_loudness_matches_formula_at_1khz():
    f2 = 1000.0 ** 2
    expected = (f2 / (f2 + 1.6e5)) ** 2 * ((f2 + 1.44e6) / (f2 + 9.61e6))
    assert equal_loudness_weights(1000.0) == pytest.approx(expected)
    assert equal_loudness_weights(1000.0) == pytest.approx(0.1709, abs=1e-3)


def test_default_filter_count_from_bark_span():
    assert default_filter_count(8000) == 17
    assert default_filter_count(16000) == 21


def test_lifter_is_applied():
    samples = speech_like(8000)
    plain = extract_plp(samples, 8000, PlpConfig(deltas=False, lifter_length=0))
    lifted = extract_plp(samples, 8000, PlpConfig(deltas=False, lifter_length=22))
    assert np.allclose(lifted, plain * lifter_weights(13, 22))


def test_warp_changes_output_and_alpha_one_matches_default():
    samples = speech_like(8000)
    base = extract_plp(samples, 8000)
    assert np.array_equal(base, extract_plp(samples, 8000, PlpConfig(warp_factor=1.0)))
    assert not np.allclose(base, extract_plp(samples, 8000,
                                             PlpConfig(warp_factor=1.12)))


def test_too_few_filters_for_order_raises():
    with pytest.raises(ValueError):
        extract_plp(speech_like(8000), 8000, PlpConfig(n_filters=10, lpc_order=12))


def test_config_round_trips_and_has_matlab_front_end_defaults():
    config = PlpConfig(lpc_order=8, warp_factor=0.9)
    assert PlpConfig.from_dict(config.to_dict()) == config
    assert PlpConfig().preemphasis == 0.0
    assert PlpConfig().normalize_peak is False
