import numpy as np
import pytest

from qbestd.features.extract import (
    FEATURE_KINDS,
    extract_features,
    extract_warped_bank,
)
from qbestd.features.mfcc import MfccConfig, extract_mfcc
from qbestd.features.plp import PlpConfig
from qbestd.features.scales import VTLN_WARP_FACTORS


def signal():
    rng = np.random.default_rng(0)
    time = np.arange(8000) / 8000
    return 0.1 * np.sin(2 * np.pi * 400 * time) + 0.01 * rng.normal(size=8000)


@pytest.mark.parametrize("kind", FEATURE_KINDS)
def test_every_kind_gives_39_dimensions(kind):
    assert extract_features(signal(), 8000, kind).shape == (98, 39)


def test_bank_has_13_keys_and_equal_frame_counts():
    bank = extract_warped_bank(signal(), 8000, "mfcc")
    assert sorted(bank) == [float(alpha) for alpha in VTLN_WARP_FACTORS]
    assert len(bank) == 13
    assert len({features.shape for features in bank.values()}) == 1


@pytest.mark.parametrize("kind", FEATURE_KINDS)
def test_alpha_one_in_bank_equals_extract_features(kind):
    bank = extract_warped_bank(signal(), 8000, kind, warp_factors=[0.94, 1.0])
    assert np.array_equal(bank[1.0], extract_features(signal(), 8000, kind))
    assert not np.allclose(bank[0.94], bank[1.0])


def test_unknown_kind_raises():
    with pytest.raises(ValueError, match="Unknown feature kind"):
        extract_features(signal(), 8000, "fbank")


def test_config_of_wrong_class_raises():
    with pytest.raises(ValueError):
        extract_features(signal(), 8000, "mfcc", config=PlpConfig())


def test_config_is_respected_and_warp_argument_wins():
    config = MfccConfig(deltas=False, warp_factor=0.9)
    features = extract_features(signal(), 8000, "mfcc", 1.12, config)
    assert features.shape == (98, 13)
    assert np.array_equal(
        features, extract_mfcc(signal(), 8000,
                               MfccConfig(deltas=False, warp_factor=1.12)))
