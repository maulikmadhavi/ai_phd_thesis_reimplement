"""Named feature profiles: bundles of config values with stated sources.

**No profile is thesis-verified.** They are reading aids that group the
settings of the MATLAB scripts (``Fx_mfcc.m`` FM, ``Fx_mfcc_vtmp_cep.m`` FT,
``Fx_PLPCC_htk.m`` FP in ``research_myMATLAB_codes``) or the HTK defaults.
The generic config defaults (8 kHz, unverified) are not changed by this
module.
"""

from qbestd.features.mfcc import MfccConfig
from qbestd.features.mfcc_tmp import MfccTmpConfig
from qbestd.features.plp import PlpConfig

TIMIT_SAMPLE_RATE = 16000
PROFILE_NAMES = ("timit_matlab", "htk_like")
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


def _htk_like(kind):
    """As ``timit_matlab`` but PLP follows HTK: LPC order 12, DC removed.

    The HTK values are recalled from the HTK Book, not checked here.
    """
    if kind == "plp":
        return PlpConfig(sample_rate=TIMIT_SAMPLE_RATE, lpc_order=12,
                         remove_dc=True)
    return _timit_matlab(kind)


_BUILDERS = {"timit_matlab": _timit_matlab, "htk_like": _htk_like}


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
