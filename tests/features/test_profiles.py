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


@pytest.mark.parametrize("name", PROFILE_NAMES)
@pytest.mark.parametrize("kind", KINDS)
def test_every_profile_extracts_finite_features(name, kind):
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
