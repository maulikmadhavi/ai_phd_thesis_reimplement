from types import SimpleNamespace

import numpy as np
import pytest

from qbestd.eval.query_features import (
    frame_centres,
    query_features_for,
    select_frames,
)
from qbestd.eval.timit_queries import QueryExample, cut_clip
from qbestd.features.extract import extract_features
from qbestd.features.profiles import get_profile

CONFIG = SimpleNamespace(shift_ms=10.0, frame_ms=25.0)
RATE = 16000


def test_frame_centres_are_shift_times_t_plus_half_a_window():
    assert np.allclose(frame_centres(3, CONFIG), [0.0125, 0.0225, 0.0325])


@pytest.mark.parametrize("start, end, kept", [
    (0.0225, 0.0325, [1, 2]),    # both edges exactly on a centre: kept
    (0.0226, 0.0325, [2]),       # a hair after centre 1: frame 1 dropped
    (0.0225, 0.0324, [1]),       # a hair before centre 2: frame 2 dropped
    (0.0, 0.01, []),             # no centre inside
])
def test_frame_selection_at_both_interval_edges(start, end, kept):
    features = np.arange(5)[:, None] * np.ones((5, 2))
    chosen = select_frames(features, CONFIG, start, end)
    assert chosen[:, 0].astype(int).tolist() == kept


def row_and_example():
    rng = np.random.default_rng(0)
    audio = (0.1 * rng.normal(size=RATE)).astype(np.float32)
    row = SimpleNamespace(audio=audio, sample_rate=RATE)
    example = QueryExample("x", 0, 0, 0.30, 0.55, "train")
    return row, example


def test_clip_mode_is_the_features_of_the_cut_clip():
    row, example = row_and_example()
    config = get_profile("timit_matlab", "mfcc")
    got = query_features_for("clip", row, example, "mfcc", config, {})
    clip = cut_clip(row.audio, RATE, example)
    expected = extract_features(clip, RATE, "mfcc", config=config)
    assert np.array_equal(got, expected)


def test_slice_mode_keeps_whole_utterance_frames_and_caches_them():
    row, example = row_and_example()
    config = get_profile("timit_matlab", "mfcc")
    cache = {}
    got = query_features_for("slice", row, example, "mfcc", config, cache)
    full = extract_features(row.audio, RATE, "mfcc", config=config)
    assert list(cache) == [("train", 0)]
    expected = select_frames(full, config, example.start_s, example.end_s)
    assert np.array_equal(got, expected) and len(got) > 10
    clip = query_features_for("clip", row, example, "mfcc", config, cache)
    # same time span, but not the same numbers (edges, per-utterance norm)
    assert not np.allclose(got[:len(clip)], clip[:len(got)])


def test_unknown_mode_is_rejected():
    row, example = row_and_example()
    with pytest.raises(ValueError, match="unknown"):
        query_features_for("zoom", row, example, "mfcc", None, {})
