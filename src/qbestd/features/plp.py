"""PLP cepstra following MATLAB ``Fx_PLPCC_htk.m`` (without RASTA)."""

from dataclasses import dataclass

import numpy as np

from qbestd.audio.pipeline import AudioFrontEndConfig
from qbestd.audio.spectrum import power_spectrum
from qbestd.features.cepstral import lifter_cepstra
from qbestd.features.deltas import append_deltas
from qbestd.features.filterbank import mel_filter_centers_hz, mel_filterbank
from qbestd.features.frontend import PCM_SCALE, windowed_frames
from qbestd.features.lpc import (
    autocorrelation_from_power,
    levinson_durbin,
    lpc_to_cepstrum,
)
from qbestd.features.scales import hz_to_bark, warp_frequency_piecewise

LOUDNESS_EXPONENT = 0.33


@dataclass(frozen=True)
class PlpConfig(AudioFrontEndConfig):
    """PLP settings. Front-end defaults follow ``Fx_PLPCC_htk.m``.

    That script applies no pre-emphasis and no peak normalisation (it only
    scales by 32768), so those defaults differ from ``MfccConfig``.
    """

    preemphasis: float = 0.0
    normalize_peak: bool = False
    pcm_scale: float = PCM_SCALE
    n_filters: int | None = None  # None: ceil(bark(fs/2)) + 1 as in MATLAB
    lpc_order: int = 12  # unverified default: MATLAB code 8, HTK 12
    n_ceps: int = 13
    lifter_length: int = 22  # HTK default
    deltas: bool = True
    delta_window: int = 2
    warp_factor: float = 1.0


def equal_loudness_weights(center_hz):
    """Hermansky equal-loudness curve at the given centre frequencies."""
    squared = np.asarray(center_hz, dtype="float64") ** 2
    return ((squared / (squared + 1.6e5)) ** 2
            * (squared + 1.44e6) / (squared + 9.61e6))


def default_filter_count(sample_rate):
    """MATLAB default: ceil(Bark value of Nyquist) + 1 filters."""
    return int(np.ceil(hz_to_bark(sample_rate / 2.0))) + 1


def extract_plp(samples, sample_rate, config=None):
    """Return PLP cepstra, (n_frames, 13) or (n_frames, 39) with deltas.

    Power spectrum -> mel bank over 0..fs/2 -> equal-loudness weights (at
    the warped filter centres) -> power 0.33 -> copy edge bands from their
    neighbours -> LPC (autocorrelation + Levinson) -> cepstrum -> lifter.
    """
    config = config or PlpConfig()
    frames, rate, n_fft = windowed_frames(samples, sample_rate, config)
    n_filters = config.n_filters or default_filter_count(rate)
    if n_filters < 3 or n_filters < config.lpc_order + 1:
        raise ValueError("need at least max(3, lpc_order + 1) filters")
    power = power_spectrum(frames, n_fft)
    bank = mel_filterbank(n_filters, n_fft, rate, 0.0, rate / 2.0,
                          config.warp_factor)
    centers = mel_filter_centers_hz(n_filters, 0.0, rate / 2.0)
    if config.warp_factor != 1.0:
        centers = warp_frequency_piecewise(centers, config.warp_factor, rate)
    bands = (power @ bank.T) * equal_loudness_weights(centers)
    bands = bands ** LOUDNESS_EXPONENT
    # MATLAB z([2, 2:(n-1), n-1], :): first/last bands copy their neighbours
    keep = [1] + list(range(1, n_filters - 1)) + [n_filters - 2]
    edge_copied = bands[:, keep]
    autocorr = autocorrelation_from_power(edge_copied)
    lpc_coeffs, gain = levinson_durbin(autocorr, config.lpc_order)
    ceps = lpc_to_cepstrum(lpc_coeffs, gain, config.n_ceps)
    ceps = lifter_cepstra(ceps, config.lifter_length)
    if config.deltas:
        ceps = append_deltas(ceps, config.delta_window, order=2)
    return ceps
