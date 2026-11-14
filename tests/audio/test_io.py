import numpy as np
import pytest
import soundfile as sf

from qbestd.audio.io import load_audio, save_audio


def test_round_trip_keeps_rate_and_values(tmp_path):
    samples = 0.5 * np.sin(2 * np.pi * 440 * np.arange(8000) / 8000)
    path = tmp_path / "tone.wav"
    save_audio(path, samples, 8000)
    loaded, sample_rate = load_audio(path)
    assert sample_rate == 8000
    assert loaded.shape == samples.shape
    assert np.max(np.abs(loaded - samples)) <= 1 / 32768


def test_stereo_is_downmixed_to_mono(tmp_path):
    left = np.full(100, 0.4)
    right = np.full(100, -0.2)
    path = tmp_path / "stereo.wav"
    sf.write(str(path), np.stack([left, right], axis=1), 16000, subtype="PCM_16")
    loaded, sample_rate = load_audio(path)
    assert loaded.ndim == 1
    assert sample_rate == 16000
    assert np.allclose(loaded, 0.1, atol=1 / 32768)


def test_missing_file_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="not found"):
        load_audio(tmp_path / "absent.wav")


def test_full_scale_samples_are_accepted(tmp_path):
    save_audio(tmp_path / "edge.wav", np.array([1.0, -1.0, 0.0]), 8000)
    assert (tmp_path / "edge.wav").is_file()


@pytest.mark.parametrize("bad_value", [1.0001, -1.5, np.nan, np.inf, -np.inf])
def test_invalid_samples_rejected_and_nothing_written(tmp_path, bad_value):
    path = tmp_path / "bad.wav"
    with pytest.raises(ValueError):
        save_audio(path, np.array([0.0, bad_value]), 8000)
    assert not path.exists()
