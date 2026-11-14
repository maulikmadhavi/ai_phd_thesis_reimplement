"""MFCC-TMP: cepstra of Teager-energy subband energies.

Follows MATLAB ``Fx_mfcc_vtmp_cep.m``: each mel filter weights the complex
STFT, an inverse FFT gives a time-domain subband frame, and the Teager
energy of that frame is summed before log and DCT.
"""

from dataclasses import dataclass

import numpy as np

from qbestd.audio.pipeline import AudioFrontEndConfig
from qbestd.audio.spectrum import complex_spectrum
from qbestd.features.cepstral import dct_cepstra, lifter_cepstra, log_compress
from qbestd.features.deltas import append_deltas
from qbestd.features.filterbank import mel_filterbank
from qbestd.features.frontend import PCM_SCALE, windowed_frames

SPECTRUM_OPTIONS = ("mp", "m", "p")


@dataclass(frozen=True)
class MfccTmpConfig(AudioFrontEndConfig):
    """MFCC-TMP settings (defaults from ``Fx_mfcc_vtmp_cep.m``)."""

    n_filters: int = 26
    low_hz: float = 0.0
    high_hz: float = 4000.0
    n_ceps: int = 13
    include_c0: bool = True  # MATLAB keeps c0; the thesis formula starts at 1
    lifter_length: int = 0
    teager_lag: int = 1  # MATLAB DI
    spectrum_option: str = "mp"  # "mp" complex, "m" magnitude, "p" phase
    normalize_peak: bool = True
    pcm_scale: float = PCM_SCALE
    deltas: bool = True
    delta_window: int = 2
    warp_factor: float = 1.0


def teager_energy_lagged(frames, lag=1):
    """Teager energy x(n)^2 - x(n - lag) * x(n + lag) along the last axis.

    unverified: MATLAB ``vteo.m`` is not public; this is the standard lagged
    form. The first and last ``lag`` values replicate the nearest interior
    value so the output keeps the input length.

    Raises:
        ValueError: if lag < 1 or the input has fewer than 2 * lag + 1 samples.
    """
    frames = np.asarray(frames, dtype="float64")
    if lag < 1:
        raise ValueError("lag must be at least 1")
    if frames.shape[-1] < 2 * lag + 1:
        raise ValueError("input too short for the requested lag")
    energy = np.empty_like(frames)
    energy[..., lag:-lag] = (frames[..., lag:-lag] ** 2
                             - frames[..., 2 * lag:] * frames[..., :-2 * lag])
    energy[..., :lag] = energy[..., lag:lag + 1]
    energy[..., -lag:] = energy[..., -lag - 1:-lag]
    return energy


def symmetric_filter_weights(half_bank):
    """Mirror (n_filters, n_fft/2 + 1) weights to full length n_fft.

    MATLAB: ``[M, fliplr(M(:, 2:NFFT/2))]``.
    """
    return np.concatenate([half_bank, half_bank[:, -2:0:-1]], axis=1)


def subband_signals(spectrum, full_weights):
    """Time-domain subband frames from a complex STFT and one filter's weights.

    ``spectrum`` is (n_frames, n_fft) complex; ``full_weights`` is (n_fft,).
    Returns the real part of the inverse FFT, (n_frames, n_fft).
    """
    return np.real(np.fft.ifft(spectrum * full_weights[None, :], axis=-1))


def _apply_spectrum_option(spectrum, option):
    if option == "mp":
        return spectrum
    if option == "m":
        return np.abs(spectrum)
    return np.angle(spectrum)


def subband_teager_energies(samples, sample_rate, config=None):
    """Summed Teager energy per frame and filter, before the log.

    Returns (n_frames, n_filters). Values can be zero or negative, so the
    caller must floor them before taking a log.
    """
    config = config or MfccTmpConfig()
    if config.spectrum_option not in SPECTRUM_OPTIONS:
        raise ValueError(f"spectrum_option must be one of {SPECTRUM_OPTIONS}")
    frames, rate, n_fft = windowed_frames(samples, sample_rate, config)
    if n_fft % 2:
        raise ValueError("n_fft must be even for MFCC-TMP")
    bank = mel_filterbank(config.n_filters, n_fft, rate, config.low_hz,
                          config.high_hz, config.warp_factor)
    weights = symmetric_filter_weights(bank)
    spectrum = _apply_spectrum_option(complex_spectrum(frames, n_fft),
                                      config.spectrum_option)
    energies = np.zeros((frames.shape[0], config.n_filters))
    for filter_index in range(config.n_filters):
        subband = subband_signals(spectrum, weights[filter_index])
        energies[:, filter_index] = teager_energy_lagged(
            subband, config.teager_lag).sum(axis=1)
    return energies


def extract_mfcc_tmp(samples, sample_rate, config=None):
    """Return MFCC-TMP features, (n_frames, 13) or (n_frames, 39) with deltas.

    Non-positive subband Teager sums are floored (1e-10) before the log, so
    the output is always finite.
    """
    config = config or MfccTmpConfig()
    energies = subband_teager_energies(samples, sample_rate, config)
    ceps = dct_cepstra(log_compress(energies), config.n_ceps,
                       config.include_c0)
    ceps = lifter_cepstra(ceps, config.lifter_length,
                          first_index=0 if config.include_c0 else 1)
    if config.deltas:
        ceps = append_deltas(ceps, config.delta_window, order=2)
    return ceps
