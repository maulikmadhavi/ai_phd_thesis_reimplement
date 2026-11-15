import numpy as np
import pytest

from qbestd.features.filterbank import mel_filterbank
from qbestd.features.mfcc_tmp import (
    MfccTmpConfig,
    extract_mfcc_tmp,
    subband_signals,
    subband_teager_energies,
    symmetric_filter_weights,
    teager_energy_lagged,
)

FLOOR = 1e-10


def tone(frequency, sample_rate=8000, duration=1.0, amplitude=0.3):
    time = np.arange(int(sample_rate * duration)) / sample_rate
    return amplitude * np.sin(2 * np.pi * frequency * time)


def test_lag_one_teo_of_cosine_matches_formula():
    amplitude, omega = 0.8, 0.4
    signal = amplitude * np.cos(omega * np.arange(100))
    energy = teager_energy_lagged(signal, lag=1)
    assert np.allclose(energy[1:-1], amplitude ** 2 * np.sin(omega) ** 2)


def test_lag_two_teo_of_cosine():
    omega = 0.3
    signal = np.cos(omega * np.arange(100))
    energy = teager_energy_lagged(signal, lag=2)
    assert np.allclose(energy[2:-2], np.sin(2 * omega) ** 2)
    assert energy.shape == signal.shape


def test_teo_rejects_bad_lag_and_short_input():
    with pytest.raises(ValueError):
        teager_energy_lagged(np.ones(10), lag=0)
    with pytest.raises(ValueError):
        teager_energy_lagged(np.ones(4), lag=2)


def test_symmetric_weights_are_mirrored():
    bank = mel_filterbank(26, 256, 8000)
    full = symmetric_filter_weights(bank)
    assert full.shape == (26, 256)
    assert np.array_equal(full[:, 1:128], full[:, :128:-1])


def test_flat_weights_recover_the_original_frames():
    frames = np.random.default_rng(0).normal(size=(2, 256))
    recovered = subband_signals(np.fft.fft(frames, axis=-1), np.ones(256))
    assert np.allclose(recovered, frames)


def test_tone_energy_lands_in_filter_containing_it():
    config = MfccTmpConfig(n_filters=26, deltas=False)
    energies = subband_teager_energies(tone(1000.0), 8000, config)
    bank = mel_filterbank(26, 256, 8000)
    expected_filter = np.argmax(bank[:, int(round(1000 / 8000 * 256))])
    mean_energy = energies.mean(axis=0)
    winner = np.argmax(mean_energy)
    assert abs(winner - expected_filter) <= 1
    assert mean_energy[winner] > 10 * np.median(mean_energy)


def test_shapes_13_and_39():
    noise = 0.01 * np.random.default_rng(1).normal(size=8000)
    signal = tone(500.0) + noise
    assert extract_mfcc_tmp(signal, 8000).shape == (98, 39)
    shape = extract_mfcc_tmp(signal, 8000, MfccTmpConfig(deltas=False)).shape
    assert shape == (98, 13)


def test_silence_hits_floor_but_output_is_finite():
    config = MfccTmpConfig(deltas=False)
    energies = subband_teager_energies(np.zeros(8000), 8000, config)
    assert np.all(energies <= FLOOR)  # every cell hits the log floor
    assert np.all(np.isfinite(extract_mfcc_tmp(np.zeros(8000), 8000, config)))


def test_floor_hits_on_noise_are_counted_and_output_finite():
    noise = np.random.default_rng(2).normal(size=8000)
    energies = subband_teager_energies(noise, 8000)
    floor_hits = int(np.sum(energies <= FLOOR))
    print(f"floor hits on noise: {floor_hits} of {energies.size}")
    assert floor_hits < energies.size  # noise must not floor every cell
    assert np.all(np.isfinite(extract_mfcc_tmp(noise, 8000)))


@pytest.mark.parametrize("option", ["mp", "m", "p"])
def test_spectrum_options_run(option):
    config = MfccTmpConfig(spectrum_option=option, deltas=False)
    features = extract_mfcc_tmp(tone(800.0), 8000, config)
    assert features.shape == (98, 13)
    assert np.all(np.isfinite(features))


def test_unknown_spectrum_option_raises():
    with pytest.raises(ValueError):
        extract_mfcc_tmp(tone(800.0), 8000, MfccTmpConfig(spectrum_option="x"))


def test_include_c0_false_matches_shifted_coefficients():
    signal = tone(800.0) + 0.01 * np.random.default_rng(3).normal(size=8000)
    with_c0 = extract_mfcc_tmp(signal, 8000,
                               MfccTmpConfig(n_ceps=14, deltas=False))
    without = extract_mfcc_tmp(signal, 8000,
                               MfccTmpConfig(include_c0=False, deltas=False))
    assert np.allclose(without, with_c0[:, 1:])


def test_warp_changes_features():
    signal = tone(800.0) + 0.01 * np.random.default_rng(3).normal(size=8000)
    warped = extract_mfcc_tmp(signal, 8000, MfccTmpConfig(warp_factor=1.12))
    assert not np.allclose(extract_mfcc_tmp(signal, 8000), warped)


def test_config_round_trips():
    config = MfccTmpConfig(teager_lag=2, warp_factor=0.9)
    assert MfccTmpConfig.from_dict(config.to_dict()) == config
