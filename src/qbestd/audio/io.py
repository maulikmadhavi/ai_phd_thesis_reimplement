"""Reading and writing mono wav audio."""

from pathlib import Path

import numpy as np
import soundfile as sf


def load_audio(path):
    """Load an audio file as mono float64 samples in [-1, 1].

    Multi-channel files are downmixed by averaging channels. Float WAV input
    is returned as stored and is not range-checked.

    Returns:
        (samples, sample_rate)

    Raises:
        FileNotFoundError: if ``path`` does not exist.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")
    samples, sample_rate = sf.read(str(path), dtype="float64", always_2d=True)
    return samples.mean(axis=1), int(sample_rate)


def save_audio(path, samples, sample_rate):
    """Save mono samples in [-1, 1] as a 16-bit PCM wav file.

    Raises:
        ValueError: if any sample is non-finite or outside [-1, 1]. Nothing
            is written in that case.
    """
    samples = np.asarray(samples, dtype="float64")
    if not np.all(np.isfinite(samples)):
        raise ValueError("samples contain NaN or infinite values")
    if samples.size and np.max(np.abs(samples)) > 1.0:
        raise ValueError("samples must lie within [-1, 1] for PCM output")
    sf.write(str(path), samples, int(sample_rate), subtype="PCM_16")
