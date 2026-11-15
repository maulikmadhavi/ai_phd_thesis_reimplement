"""Chained Stage 1 front end: samples in, windowed frames out."""

from dataclasses import asdict, dataclass, fields

from qbestd.audio.framing import frame_signal
from qbestd.audio.preprocess import (
    DEFAULT_PREEMPHASIS_COEFFICIENT,
    apply_preemphasis,
    remove_dc_offset,
)
from qbestd.audio.resample import resample_audio
from qbestd.audio.windowing import DEFAULT_WINDOW_NAME, apply_window, make_window


@dataclass(frozen=True)
class AudioFrontEndConfig:
    """Settings of the audio front end.

    Every default marked unverified is an HTK-like guess that has not yet
    been checked against the MATLAB feature code (plan.md section 4).
    """

    sample_rate: int | None = 8000  # unverified default; None keeps source rate
    frame_ms: float = 25.0
    shift_ms: float = 10.0
    preemphasis: float = DEFAULT_PREEMPHASIS_COEFFICIENT  # unverified default
    window: str = DEFAULT_WINDOW_NAME  # unverified default
    n_fft: int | None = None  # unverified default; None = next power of two
    remove_dc: bool = True  # whole-utterance mean removal; PLP MATLAB: none

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        known = {field.name for field in fields(cls)}
        unknown = set(values) - known
        if unknown:
            raise ValueError(f"Unknown config keys: {sorted(unknown)}")
        return cls(**values)


def prepare_frames(samples, sample_rate, config):
    """Resample, remove DC, pre-emphasise, frame and window ``samples``.

    Returns:
        Windowed frames of shape (n_frames, frame_len).
    """
    target_rate = config.sample_rate or sample_rate
    samples = resample_audio(samples, sample_rate, target_rate)
    if config.remove_dc:
        samples = remove_dc_offset(samples)
    samples = apply_preemphasis(samples, config.preemphasis)
    frames = frame_signal(samples, target_rate, config.frame_ms, config.shift_ms)
    return apply_window(frames, make_window(config.window, frames.shape[1]))
