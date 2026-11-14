import numpy as np
import pytest

from qbestd.features.mfcc import MfccConfig, extract_mfcc


def speech_like(sample_rate, duration=1.0, seed=0):
    rng = np.random.default_rng(seed)
    time = np.arange(int(sample_rate * duration)) / sample_rate
    tone = np.sin(2 * np.pi * 300 * time) + 0.5 * np.sin(2 * np.pi * 1700 * time)
    return 0.1 * tone + 0.01 * rng.normal(size=len(time))


def test_shapes_at_8k_and_16k():
    assert extract_mfcc(speech_like(8000), 8000).shape == (98, 39)
    assert extract_mfcc(speech_like(16000), 16000).shape == (98, 39)
    no_deltas = MfccConfig(deltas=False)
    assert extract_mfcc(speech_like(8000), 8000, no_deltas).shape == (98, 13)


def test_deterministic():
    samples = speech_like(8000)
    assert np.array_equal(extract_mfcc(samples, 8000), extract_mfcc(samples, 8000))


def test_finite_on_silence_and_short_input():
    assert np.all(np.isfinite(extract_mfcc(np.zeros(8000), 8000)))
    assert extract_mfcc(np.zeros(50), 8000).shape == (0, 39)


def test_c0_rises_with_amplitude_when_not_normalised():
    config = MfccConfig(normalize_peak=False, deltas=False)
    quiet = extract_mfcc(speech_like(8000), 8000, config)[:, 0].mean()
    loud = extract_mfcc(10 * speech_like(8000), 8000, config)[:, 0].mean()
    assert loud > quiet


def test_peak_normalisation_removes_amplitude_dependence():
    config = MfccConfig(deltas=False)
    samples = speech_like(8000)
    assert np.allclose(extract_mfcc(samples, 8000, config),
                       extract_mfcc(5 * samples, 8000, config))


def test_warp_factor_one_equals_default():
    samples = speech_like(8000)
    assert np.array_equal(extract_mfcc(samples, 8000, MfccConfig(warp_factor=1.0)),
                          extract_mfcc(samples, 8000))


def test_warping_changes_features():
    samples = speech_like(8000)
    assert not np.allclose(extract_mfcc(samples, 8000),
                           extract_mfcc(samples, 8000, MfccConfig(warp_factor=1.12)))


def test_power_spectrum_option_and_include_c0_false():
    samples = speech_like(8000)
    power = extract_mfcc(samples, 8000, MfccConfig(spectrum_type="power",
                                                   deltas=False))
    assert power.shape == (98, 13) and np.all(np.isfinite(power))
    no_c0 = extract_mfcc(samples, 8000, MfccConfig(include_c0=False, deltas=False))
    with_c0 = extract_mfcc(samples, 8000, MfccConfig(n_ceps=14, deltas=False))
    assert np.allclose(no_c0, with_c0[:, 1:])


def test_lifter_scales_coefficients():
    samples = speech_like(8000)
    plain = extract_mfcc(samples, 8000, MfccConfig(deltas=False))
    lifted = extract_mfcc(samples, 8000, MfccConfig(deltas=False, lifter_length=22))
    assert np.allclose(lifted[:, 0], plain[:, 0])
    assert not np.allclose(lifted[:, 5], plain[:, 5])


def test_unknown_spectrum_type_raises():
    with pytest.raises(ValueError):
        extract_mfcc(speech_like(8000), 8000, MfccConfig(spectrum_type="bogus"))


def test_config_round_trips_through_dict():
    config = MfccConfig(n_filters=23, lifter_length=22, warp_factor=0.94)
    assert MfccConfig.from_dict(config.to_dict()) == config
