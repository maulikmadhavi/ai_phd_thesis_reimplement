"""Level-matched query mode ``clip_lm`` (cycle 10, M1, D7 b)."""

from types import SimpleNamespace

import numpy as np
import pytest

from qbestd.audio.preprocess import remove_dc_offset
from qbestd.eval.query_features import (
    level_matched_clip,
    level_matched_config,
    query_features_for,
)
from qbestd.eval.timit_queries import QueryExample, cut_clip
from qbestd.features.extract import extract_features
from qbestd.features.frontend import PCM_SCALE, scale_waveform
from qbestd.features.profiles import get_profile

RATE = 16000
# profiles that normalise: remove_dc and normalize_peak both true
NORMALISING = [("htk_described_4k_pn", "mfcc"), ("htk_described_4k_pn", "plp"),
               ("timit_matlab", "mfcc"), ("timit_matlab", "mfcc_tmp")]


def utterance(seed=0, n=RATE):
    rng = np.random.default_rng(seed)
    return (0.1 * rng.normal(size=n) + 0.03).astype(np.float64)


def full_span(audio):
    return QueryExample("x", 0, 0, 0.0, len(audio) / RATE, "train")


def partial(start=0.30, end=0.55):
    return QueryExample("x", 0, 0, start, end, "train")


@pytest.mark.parametrize("profile, kind", NORMALISING)
def test_identity_full_span_clip_lm_is_the_document_features(profile, kind):
    """STOP gate: a clip spanning the whole utterance reproduces the document
    features of that utterance (plain)."""
    config = get_profile(profile, kind)
    row = SimpleNamespace(audio=utterance(), sample_rate=RATE)
    got = query_features_for("clip_lm", row, full_span(row.audio), kind,
                             config, {})
    expected = extract_features(row.audio, RATE, kind, config=config)
    assert got.shape == expected.shape
    assert np.allclose(got, expected, atol=1e-8)


@pytest.mark.parametrize("profile, kind", NORMALISING)
def test_identity_full_span_clip_lm_is_the_document_features_warped(profile,
                                                                   kind):
    """STOP gate, warped: the same at a non-unit VTLN warp."""
    config = get_profile(profile, kind)
    audio = utterance(seed=1)
    lm = level_matched_clip(audio, RATE, full_span(audio), config)
    got = extract_features(lm, RATE, kind, 0.94, level_matched_config(config))
    expected = extract_features(audio, RATE, kind, 0.94, config)
    assert np.allclose(got, expected, atol=1e-8)


@pytest.mark.parametrize("gain", [0.5, 2.0])
def test_clip_lm_is_invariant_to_a_gain_on_the_source(gain):
    config = get_profile("htk_described_4k_pn", "mfcc")
    audio = utterance(seed=2)
    example = partial()
    base = query_features_for(
        "clip_lm", SimpleNamespace(audio=audio, sample_rate=RATE), example,
        "mfcc", config, {})
    scaled = query_features_for(
        "clip_lm", SimpleNamespace(audio=gain * audio, sample_rate=RATE),
        example, "mfcc", config, {})
    assert np.allclose(scaled, base, atol=1e-8)


def test_clip_lm_waveform_is_the_clip_waveform_times_the_level_ratio():
    """``clip`` normalises the clip by its own peak, ``clip_lm`` by the
    utterance peak. Before framing the two waveforms differ by the ratio
    ``max|clip| / max|utterance|`` and by a constant (the DC term)."""
    config = get_profile("htk_described_4k_pn", "mfcc")
    audio = utterance(seed=3)
    example = partial()
    raw = cut_clip(audio, RATE, example)
    clip_path = remove_dc_offset(scale_waveform(raw, True, PCM_SCALE))
    lm_path = scale_waveform(level_matched_clip(audio, RATE, example, config),
                             False, PCM_SCALE)
    ratio = np.max(np.abs(raw)) / np.max(np.abs(audio))
    residual = lm_path - ratio * clip_path
    assert np.ptp(residual) < 1e-6 * np.max(np.abs(lm_path))


@pytest.mark.parametrize("profile, kind", [("htk_described", "mfcc"),
                                           ("timit_matlab", "plp")])
def test_profiles_without_normalisation_are_refused(profile, kind):
    config = get_profile(profile, kind)
    row = SimpleNamespace(audio=utterance(), sample_rate=RATE)
    with pytest.raises(ValueError, match="clip_lm needs"):
        query_features_for("clip_lm", row, partial(), kind, config, {})


def test_vtln_inputs_refuse_an_unknown_query_mode():
    from qbestd.eval.vtln_eval import vtln_inputs
    config = get_profile("htk_described_4k_pn", "mfcc")
    with pytest.raises(ValueError, match="clip or clip_lm"):
        vtln_inputs(None, [], [], {}, {}, "mfcc", "htk_described_4k_pn",
                    config, query_mode="slice")
