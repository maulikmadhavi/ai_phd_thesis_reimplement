"""Unified entry points for MFCC, PLP and MFCC-TMP, with VTLN warping."""

from dataclasses import replace

from qbestd.features.mfcc import MfccConfig, extract_mfcc
from qbestd.features.mfcc_tmp import MfccTmpConfig, extract_mfcc_tmp
from qbestd.features.plp import PlpConfig, extract_plp
from qbestd.features.scales import VTLN_WARP_FACTORS

_EXTRACTORS = {
    "mfcc": (MfccConfig, extract_mfcc),
    "plp": (PlpConfig, extract_plp),
    "mfcc_tmp": (MfccTmpConfig, extract_mfcc_tmp),
}
FEATURE_KINDS = tuple(_EXTRACTORS)


def extract_features(samples, sample_rate, kind, warp_factor=None,
                     config=None):
    """Extract features of the given ``kind`` at one VTLN warp factor.

    Args:
        kind: one of "mfcc", "plp", "mfcc_tmp".
        warp_factor: VTLN factor alpha. None (default) uses the value stored
            in ``config``; an explicit value overrides it (1.0 = no warping).
        config: the config class matching ``kind``; None uses its defaults.

    Raises:
        ValueError: for an unknown kind or a config of the wrong class.
    """
    if kind not in _EXTRACTORS:
        raise ValueError(f"Unknown feature kind '{kind}'; use {FEATURE_KINDS}")
    config_class, extractor = _EXTRACTORS[kind]
    if config is None:
        config = config_class()
    elif not isinstance(config, config_class):
        raise ValueError(
            f"kind '{kind}' needs a {config_class.__name__}, "
            f"got {type(config).__name__}")
    if warp_factor is not None:
        config = replace(config, warp_factor=warp_factor)
    return extractor(samples, sample_rate, config)


def extract_warped_bank(samples, sample_rate, kind,
                        warp_factors=VTLN_WARP_FACTORS, config=None):
    """Features for every warp factor: ``{alpha: (n_frames, n_dims)}``.

    This is the input of GMM-based VTLN (Stage 4). Frame counts are the same
    for all alphas because warping only changes the filterbank.
    """
    return {float(alpha): extract_features(samples, sample_rate, kind, alpha,
                                           config)
            for alpha in warp_factors}
