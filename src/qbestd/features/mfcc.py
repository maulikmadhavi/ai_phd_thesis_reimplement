"""MFCC extraction following MATLAB ``Fx_mfcc.m`` (+ optional VTLN warp)."""

from dataclasses import dataclass

import numpy as np

from qbestd.audio.pipeline import AudioFrontEndConfig
from qbestd.audio.spectrum import power_spectrum
from qbestd.features.cepstral import dct_cepstra, lifter_cepstra, log_compress
from qbestd.features.deltas import append_deltas
from qbestd.features.filterbank import mel_filterbank
from qbestd.features.frontend import PCM_SCALE, windowed_frames

SPECTRUM_TYPES = ("magnitude", "power")


@dataclass(frozen=True)
class MfccConfig(AudioFrontEndConfig):
    """MFCC settings; front-end fields are inherited from the audio config."""

    n_filters: int = 26
    low_hz: float = 0.0
    high_hz: float = 4000.0
    n_ceps: int = 13
    include_c0: bool = True
    lifter_length: int = 0  # Fx_mfcc.m applies none; HTK default would be 22
    # unverified default: MATLAB computes log((M * |X|)^2)
    spectrum_type: str = "magnitude"
    normalize_peak: bool = True  # MATLAB x / max|x|
    pcm_scale: float = PCM_SCALE
    deltas: bool = True
    delta_window: int = 2
    warp_factor: float = 1.0


def extract_mfcc(samples, sample_rate, config=None):
    """Return MFCCs of shape (n_frames, 13) or (n_frames, 39) with deltas.

    Pipeline: scale -> resample -> DC removal -> pre-emphasis -> frame ->
    window -> spectrum -> mel filterbank (VTLN-warped if warp_factor != 1) ->
    log -> DCT -> lifter -> deltas. For ``spectrum_type="magnitude"`` the
    filtered value is squared before the log, like ``log((M*|X|)^2)``.

    Raises:
        ValueError: for an unknown spectrum_type.
    """
    config = config or MfccConfig()
    if config.spectrum_type not in SPECTRUM_TYPES:
        raise ValueError(f"spectrum_type must be one of {SPECTRUM_TYPES}")
    frames, rate, n_fft = windowed_frames(samples, sample_rate, config)
    power = power_spectrum(frames, n_fft)
    bank = mel_filterbank(config.n_filters, n_fft, rate, config.low_hz,
                          config.high_hz, config.warp_factor)
    if config.spectrum_type == "magnitude":
        band_energy = (np.sqrt(power) @ bank.T) ** 2
    else:
        band_energy = power @ bank.T
    ceps = dct_cepstra(log_compress(band_energy), config.n_ceps,
                       config.include_c0)
    ceps = lifter_cepstra(ceps, config.lifter_length,
                          first_index=0 if config.include_c0 else 1)
    if config.deltas:
        ceps = append_deltas(ceps, config.delta_window, order=2)
    return ceps
