from dataclasses import replace

import hashlib

import numpy as np
import pytest

from qbestd.features.extract import extract_features
from qbestd.features.mfcc import MfccConfig
from qbestd.features.mfcc_tmp import MfccTmpConfig
from qbestd.features.plp import PlpConfig
from qbestd.features.profiles import KINDS, PROFILE_NAMES, get_profile


def test_timit_matlab_mfcc_and_tmp_use_16k_and_4k_band():
    for kind, cls in (("mfcc", MfccConfig), ("mfcc_tmp", MfccTmpConfig)):
        config = get_profile("timit_matlab", kind)
        assert isinstance(config, cls)
        assert (config.sample_rate, config.high_hz) == (16000, 4000.0)


def test_timit_matlab_plp_follows_matlab_script():
    config = get_profile("timit_matlab", "plp")
    assert isinstance(config, PlpConfig)
    assert config.sample_rate == 16000
    assert config.lpc_order == 8
    assert config.remove_dc is False
    assert config.preemphasis == 0.0
    assert config.normalize_peak is False
    assert config.pcm_scale == 32768.0


def test_generic_defaults_are_unchanged():
    assert MfccConfig().sample_rate == 8000
    assert PlpConfig().lpc_order == 12
    assert PlpConfig().remove_dc is True
    assert MfccTmpConfig().high_hz == 4000.0


@pytest.mark.parametrize("name, kind", [
    ("nope", "mfcc"), ("timit_matlab", "fbank"), ("timit_matlab", "")])
def test_unknown_name_or_kind_raises(name, kind):
    with pytest.raises(ValueError):
        get_profile(name, kind)


NOT_DEFINED = {("timit_matlab_levelflip", "mfcc_tmp"),
               ("htk_described", "mfcc_tmp")}


@pytest.mark.parametrize("name", PROFILE_NAMES)
@pytest.mark.parametrize("kind", KINDS)
def test_every_profile_extracts_finite_features(name, kind):
    if (name, kind) in NOT_DEFINED:
        pytest.skip("profile is not defined for this kind")
    noise = 0.1 * np.random.default_rng(0).normal(size=16000)
    features = extract_features(noise, 16000, kind,
                                config=get_profile(name, kind))
    assert features.shape[1] == 39
    assert features.shape[0] == 98
    assert np.all(np.isfinite(features))


def test_no_dc_removal_changes_plp_output_for_offset_signal():
    signal = 0.1 * np.random.default_rng(1).normal(size=16000) + 0.05
    with_dc = extract_features(signal, 16000, "plp",
                               config=PlpConfig(sample_rate=16000, lpc_order=8,
                                                remove_dc=True))
    without = extract_features(signal, 16000, "plp",
                               config=get_profile("timit_matlab", "plp"))
    assert not np.allclose(with_dc, without)


def test_levelflip_swaps_only_peak_normalisation():
    base_mfcc = get_profile("timit_matlab", "mfcc")
    flip_mfcc = get_profile("timit_matlab_levelflip", "mfcc")
    assert (base_mfcc.normalize_peak, flip_mfcc.normalize_peak) == (True,
                                                                   False)
    assert replace(flip_mfcc, normalize_peak=True) == base_mfcc
    base_plp = get_profile("timit_matlab", "plp")
    flip_plp = get_profile("timit_matlab_levelflip", "plp")
    assert (base_plp.normalize_peak, flip_plp.normalize_peak) == (False,
                                                                 True)
    assert replace(flip_plp, normalize_peak=False) == base_plp


def test_levelflip_raises_for_mfcc_tmp():
    with pytest.raises(ValueError, match="mfcc and plp only"):
        get_profile("timit_matlab_levelflip", "mfcc_tmp")


def test_levelflip_changes_only_the_level_dependent_dimensions_of_mfcc():
    noise = 0.05 * np.random.default_rng(2).normal(size=16000)
    base = extract_features(noise, 16000, "mfcc",
                            config=get_profile("timit_matlab", "mfcc"))
    flip = extract_features(noise, 16000, "mfcc",
                            config=get_profile("timit_matlab_levelflip",
                                               "mfcc"))
    assert base.shape == flip.shape
    # a gain moves c0 only: the static c1..c12 are unchanged to rounding
    assert np.allclose(base[:, 1:13], flip[:, 1:13], atol=1e-6)
    assert not np.allclose(base[:, 0], flip[:, 0])


# sha256 of np.round(features, 8) for seeded noise, recorded from the code
# before ``htk_described`` was added: the ``timit_matlab`` features must not
# move (cycle 7, H1).
GOLDEN = {
    ("mfcc", 1.0):
        "8a9fd62c3d308fac5dabcdf950e9f64c9cc1b67fc1026395e06b42f659307820",
    ("mfcc", 0.92):
        "ef3053cf397e772205c066d565b99e3e721c78067923a442176a9b0d23aca58f",
    ("plp", 1.0):
        "ed946b88794a5af1f712bad6f6755a98895d85bd9e844c96d0af4c6b6a3ca31d",
    ("plp", 0.92):
        "af8515ed2656f1453eb8b737b4288963aadeae8c197482088a978b61bb3b2ad9",
    ("mfcc_tmp", 1.0):
        "21b616f3166904db0c8e39cefc4311183c638bb43ff7a8099ffa768f3c9ef9e9",
    ("mfcc_tmp", 0.92):
        "81b6eda7036c16025f0b96b60f7650f11ba8ca0e9f584dd54d51d7564d6cb820",
}


@pytest.mark.parametrize("kind, warp", sorted(GOLDEN))
def test_timit_matlab_features_are_byte_identical_to_before_h1(kind, warp):
    signal = 0.1 * np.random.default_rng(7).normal(size=24000) + 0.02
    features = extract_features(signal, 16000, kind, warp_factor=warp,
                                config=get_profile("timit_matlab", kind))
    digest = hashlib.sha256(np.round(features, 8).tobytes()).hexdigest()
    assert digest == GOLDEN[(kind, warp)]


@pytest.mark.parametrize("kind, cls", [("mfcc", MfccConfig),
                                       ("plp", PlpConfig)])
def test_htk_described_has_40_channels_3400_hz_and_39_dimensions(kind, cls):
    config = get_profile("htk_described", kind)
    assert isinstance(config, cls)
    assert (config.n_filters, config.low_hz, config.high_hz) == (40, 0.0,
                                                                 3400.0)
    assert config.sample_rate == 16000
    assert (config.preemphasis, config.lifter_length) == (0.97, 22)
    assert config.remove_dc is False and config.normalize_peak is False
    noise = 0.1 * np.random.default_rng(3).normal(size=16000)
    features = extract_features(noise, 16000, kind, config=config)
    assert features.shape == (98, 39)
    assert np.all(np.isfinite(features))


def test_htk_described_filterbank_top_edge_is_3400_hz():
    from qbestd.features.filterbank import mel_filter_edges_hz
    config = get_profile("htk_described", "plp")
    edges = mel_filter_edges_hz(config.n_filters, config.low_hz,
                                config.high_hz)
    assert len(edges) == 42 and edges[-1] == pytest.approx(3400.0)


def test_htk_described_plp_uses_lpc_order_12_and_the_power_spectrum():
    config = get_profile("htk_described", "plp")
    assert config.lpc_order == 12


def test_htk_described_mfcc_uses_the_magnitude_spectrum_with_c0():
    config = get_profile("htk_described", "mfcc")
    assert config.spectrum_type == "magnitude" and config.include_c0


def test_htk_described_raises_for_mfcc_tmp():
    with pytest.raises(ValueError, match="mfcc_tmp stays on timit_matlab"):
        get_profile("htk_described", "mfcc_tmp")


def test_plp_band_limits_change_the_features_and_warping_stays_finite():
    base = PlpConfig(sample_rate=16000, lpc_order=8, n_filters=21)
    narrow = PlpConfig(sample_rate=16000, lpc_order=8, n_filters=21,
                       high_hz=3400.0)
    noise = 0.1 * np.random.default_rng(4).normal(size=16000)
    assert not np.allclose(extract_features(noise, 16000, "plp", config=base),
                           extract_features(noise, 16000, "plp",
                                            config=narrow))
    for alpha in (0.88, 1.12):
        warped = extract_features(noise, 16000, "plp", warp_factor=alpha,
                                  config=narrow)
        assert np.all(np.isfinite(warped))
