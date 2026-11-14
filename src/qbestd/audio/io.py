"""Reading and writing mono wav audio."""

from pathlib import Path

import numpy as np
import soundfile as sf


def load_audio(path):
    """Load an audio file as mono float64 samples in [-1, 1].

    Multi-channel files are downmixed by averaging channels.

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
    """Save mono samples in [-1, 1] as a 16-bit PCM wav file."""
    sf.write(str(path), np.asarray(samples, dtype="float64"), int(sample_rate),
             subtype="PCM_16")
