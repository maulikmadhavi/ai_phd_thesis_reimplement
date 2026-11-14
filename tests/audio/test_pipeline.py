import numpy as np
import pytest

from qbestd.audio.pipeline import AudioFrontEndConfig, prepare_frames


def test_one_second_at_16k_resampled_to_8k_shape():
    samples = np.random.default_rng(0).normal(size=16000)
    frames = prepare_frames(samples, 16000, AudioFrontEndConfig(sample_rate=8000))
    assert frames.shape == (98, 200)


def test_none_sample_rate_keeps_source_rate():
    frames = prepare_frames(np.zeros(16000), 16000,
                            AudioFrontEndConfig(sample_rate=None))
    assert frames.shape == (98, 400)


def test_window_is_applied_to_frame_edges():
    config = AudioFrontEndConfig(sample_rate=8000, preemphasis=0.0)
    time = np.arange(8000) / 8000
    frames = prepare_frames(np.sin(2 * np.pi * 440 * time), 8000, config)
    assert np.all(np.abs(frames[:, 0]) <= 0.08 + 1e-6)


def test_config_round_trips_through_dict():
    config = AudioFrontEndConfig(sample_rate=16000, frame_ms=20.0,
                                 window="hann", n_fft=512)
    assert AudioFrontEndConfig.from_dict(config.to_dict()) == config


def test_unknown_config_key_rejected():
    with pytest.raises(ValueError, match="bogus"):
        AudioFrontEndConfig.from_dict({"bogus": 1})
