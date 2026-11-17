import warnings

import numpy as np
import pytest

from qbestd.audio.pitch import frame_f0, median_f0

RATE = 16000


def tone(freq, seconds=0.6, harmonics=1):
    t = np.arange(int(RATE * seconds)) / RATE
    return sum(np.sin(2 * np.pi * freq * k * t) / k
               for k in range(1, harmonics + 1))


@pytest.mark.parametrize("freq", [80, 120, 200, 310, 390])
def test_a_pure_tone_is_found_within_two_percent(freq):
    assert median_f0(tone(freq), RATE) == pytest.approx(freq, rel=0.02)


@pytest.mark.parametrize("freq", [100, 150, 250])
def test_a_harmonic_tone_gives_its_fundamental(freq):
    assert median_f0(tone(freq, harmonics=6), RATE) == pytest.approx(
        freq, rel=0.03)


def test_noise_and_silence_have_no_pitch():
    noise = np.random.default_rng(0).normal(size=RATE)
    assert np.isnan(median_f0(noise, RATE))
    assert np.isnan(median_f0(np.zeros(RATE), RATE))


def test_a_tone_outside_the_range_is_not_reported():
    assert np.isnan(median_f0(tone(30, seconds=1.0), RATE))


def test_a_signal_shorter_than_one_frame_gives_nan_and_no_frames():
    assert len(frame_f0(np.zeros(100), RATE)) == 0
    assert np.isnan(median_f0(np.zeros(100), RATE))


def test_silent_frames_are_unvoiced_inside_a_voiced_signal():
    signal = np.concatenate([tone(150, 0.4), np.zeros(RATE // 2)])
    f0 = frame_f0(signal, RATE)
    assert np.isfinite(f0[:20]).all() and np.isnan(f0[-10:]).all()


def test_a_dc_offset_does_not_change_the_estimate():
    assert median_f0(tone(180) + 0.5, RATE) == pytest.approx(
        median_f0(tone(180), RATE), rel=0.01)


def test_a_frame_without_any_peak_is_unvoiced_without_a_warning():
    ramp = np.linspace(-1.0, 1.0, RATE // 4)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        f0 = frame_f0(ramp, RATE)
    assert len(f0) > 0 and np.isnan(f0).all()
