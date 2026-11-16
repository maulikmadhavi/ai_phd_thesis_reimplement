"""Named feature profiles: bundles of config values with stated sources.

**No profile is thesis-verified.** They are reading aids that group the
settings of the MATLAB scripts (``Fx_mfcc.m`` FM, ``Fx_mfcc_vtmp_cep.m`` FT,
``Fx_PLPCC_htk.m`` FP in ``research_myMATLAB_codes``). The generic config
defaults (8 kHz, unverified) are not changed by this module.
"""

from dataclasses import replace

from qbestd.features.mfcc import MfccConfig
from qbestd.features.mfcc_tmp import MfccTmpConfig
from qbestd.features.plp import PlpConfig

TIMIT_SAMPLE_RATE = 16000
PROFILE_NAMES = ("timit_matlab", "timit_matlab_levelflip",
                 "htk_described", "htk_described_4k")
KINDS = ("mfcc", "plp", "mfcc_tmp")


def _timit_matlab(kind):
    """TIMIT at its native 16 kHz with the MATLAB scripts' settings.

    Sources: MFCC and MFCC-TMP keep the thesis 0 to 4000 Hz band (FT:35-36
    uses fH 4000; FM uses fs/2, but the thesis text says 4 kHz). PLP spans
    0 to fs/2 = 8000 Hz (FP:31-32), LPC order 8 (FP:35), no DC removal and
    only the x * 32768 scaling (FP:69), so no peak normalisation either.
    """
    if kind == "mfcc":
        return MfccConfig(sample_rate=TIMIT_SAMPLE_RATE, high_hz=4000.0)
    if kind == "mfcc_tmp":
        return MfccTmpConfig(sample_rate=TIMIT_SAMPLE_RATE, high_hz=4000.0)
    return PlpConfig(sample_rate=TIMIT_SAMPLE_RATE, lpc_order=8,
                     remove_dc=False)


def _htk_described(kind):
    """The HTK configuration described by the author (user decision D2).

    Sources, per value:

    * **author-stated (2026-11-16):** ``NUMCHANS = 40`` for MFCC and PLP,
      16 kHz, band 0 to 3400 Hz. The band was stated for the HTK
      configuration and is applied to both features; the thesis text says
      0 to 4000 Hz for MFCC (``ExpSetup.tex`` 191), a conflict that is
      recorded, not resolved.
    * **thesis-stated:** 25 ms Hamming window, 10 ms shift, 13 coefficients
      plus delta and delta-delta (39 dimensions) (``Unsupervised.tex`` 113).
    * **HTK defaults, recalled and unverified:** pre-emphasis 0.97 (both
      features); cepstral lifter 22; PLP LPC order 12, compression 0.33 and
      equal-loudness weighting; c0 kept and no energy term (the thesis
      labels PLP ``PLP_D_A_0``, ``Unsupervised.tex`` 610); delta window 2;
      no DC removal and no peak normalisation (``ZMEANSOURCE`` off); MFCC on
      the magnitude spectrum, PLP on the power spectrum.

    Known approximations: HTK takes the log of the mel-weighted magnitude,
    ``log(M |X|)``, and we take ``log((M |X|)^2)``, which is twice that and
    changes every cepstrum by a constant factor 2 (the code is kept as in
    ``timit_matlab``); HTK's DCT scales c0 by ``sqrt(2/N)`` against our
    orthonormal ``sqrt(1/N)``, a factor ``sqrt(2)`` on c0 only. PLP filters
    are mel-spaced, as in ``Fx_PLPCC_htk.m``; HTK's own PLP internals are
    not reproduced.

    Raises:
        ValueError: for ``mfcc_tmp``, which stays on ``timit_matlab`` (it
            came from the MATLAB script with 26 filters).
    """
    if kind == "mfcc_tmp":
        raise ValueError("htk_described is defined for mfcc and plp only; "
                         "mfcc_tmp stays on timit_matlab")
    common = {"sample_rate": TIMIT_SAMPLE_RATE, "n_filters": 40,
              "low_hz": 0.0, "high_hz": 3400.0, "preemphasis": 0.97,
              "remove_dc": False, "normalize_peak": False,
              "lifter_length": 22, "n_ceps": 13, "deltas": True,
              "delta_window": 2}
    if kind == "mfcc":
        return MfccConfig(**common, include_c0=True,
                          spectrum_type="magnitude")
    return PlpConfig(**common, lpc_order=12)


def _htk_described_4k(kind):
    """Band comparison (cycle 7, H3): ``htk_described`` with the band
    0 to 4000 Hz, the thesis text for MFCC (``ExpSetup.tex`` 191), for both
    MFCC and PLP. Nothing else differs. A comparison profile only; the
    reference stays ``htk_described`` unless the user decides otherwise.

    Raises:
        ValueError: for ``mfcc_tmp`` (see :func:`_htk_described`).
    """
    return replace(_htk_described(kind), high_hz=4000.0)


def _timit_matlab_levelflip(kind):
    """Level-handling ablation (cycle 7, L1): ``timit_matlab`` with the
    waveform level handling of MFCC and PLP swapped.

    MFCC loses its peak normalisation (``normalize_peak=False``) and PLP
    gains it (``normalize_peak=True``); nothing else changes. A diagnostic
    only: the primary rows stay on ``timit_matlab``.

    Raises:
        ValueError: for ``mfcc_tmp``, which has no such ablation.
    """
    if kind == "mfcc_tmp":
        raise ValueError("timit_matlab_levelflip is defined for mfcc and "
                         "plp only")
    flipped = kind == "plp"
    return replace(_timit_matlab(kind), normalize_peak=flipped)


_BUILDERS = {"timit_matlab": _timit_matlab,
             "timit_matlab_levelflip": _timit_matlab_levelflip,
             "htk_described": _htk_described,
             "htk_described_4k": _htk_described_4k}


def get_profile(name, kind):
    """Config object of ``kind`` for the profile ``name``.

    Raises:
        ValueError: for an unknown profile name or feature kind.
    """
    if name not in _BUILDERS:
        raise ValueError(f"Unknown profile '{name}'; use {PROFILE_NAMES}")
    if kind not in KINDS:
        raise ValueError(f"Unknown feature kind '{kind}'; use {KINDS}")
    return _BUILDERS[name](kind)
