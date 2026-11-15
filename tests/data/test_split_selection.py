import numpy as np
import pytest

from qbestd.data.feature_cache import hf_split_id
from qbestd.data.split_selection import (
    SplitSelection,
    gather_utterances,
    hf_selection,
    manifest_selection,
)
from qbestd.data.text_split import (
    build_text_split,
    split_id,
    write_split_manifest,
)


def fake_cache(rows, start):
    """A cache whose row ``r`` has two frames of value ``start + r``."""
    features = np.concatenate([np.full((2, 3), start + r, np.float32)
                               for r in rows])
    offsets = np.arange(0, 2 * len(rows) + 1, 2)
    return features, offsets, np.array(rows), {}


CACHES = {"train": fake_cache([0, 1, 2, 3], 100),
          "test": fake_cache([0, 1], 200)}


def load(hf_split):
    return CACHES[hf_split]


def test_hf_selection_takes_whole_splits_in_cache_order():
    selection = hf_selection()
    assert selection.split_id == hf_split_id()
    utterances, keys = gather_utterances(selection, "train", load)
    assert keys == [("train", 0), ("train", 1), ("train", 2), ("train", 3)]
    assert [u[0, 0] for u in utterances] == [100, 101, 102, 103]
    utterances, keys = gather_utterances(selection, "test", load)
    assert keys == [("test", 0), ("test", 1)]
    assert not selection.uses("test", "train")


def test_a_manifest_selection_mixes_rows_of_both_hf_splits(tmp_path,
                                                          monkeypatch):
    monkeypatch.setattr("qbestd.data.text_split.TEST_QUOTA",
                        {"multi": 1, "single": 1})
    rows = [("train", 0, "alpha beta"), ("train", 1, "alpha beta"),
            ("train", 2, "gamma delta"), ("train", 3, "gamma delta"),
            ("test", 0, "alpha beta"), ("test", 1, "epsilon zeta")]
    manifest = build_text_split(rows, [])
    write_split_manifest(tmp_path / "m.tsv", manifest)
    selection = manifest_selection(tmp_path / "m.tsv")
    assert selection.split_id == split_id(tmp_path / "m.tsv")
    train, train_keys = gather_utterances(selection, "train", load)
    test, test_keys = gather_utterances(selection, "test", load)
    assert train_keys and test_keys
    assert set(train_keys).isdisjoint(test_keys)
    assert len(train_keys) + len(test_keys) == 6
    # utterance slices follow their own HF split's cache, not a new index
    for utterance, (hf_split, row) in zip(train + test,
                                          train_keys + test_keys):
        assert utterance[0, 0] == CACHES[hf_split][0][2 * row, 0]
    # texts do not cross: both "alpha beta" rows share a side
    sides = {key: "train" for key in train_keys}
    sides.update({key: "test" for key in test_keys})
    assert sides[("train", 0)] == sides[("train", 1)] == sides[("test", 0)]


def test_a_selected_row_missing_from_the_cache_is_an_error():
    selection = SplitSelection("x", {"train": {"train": frozenset({0, 9})},
                                     "test": {}})
    with pytest.raises(ValueError, match="not in the feature cache"):
        gather_utterances(selection, "train", load)


def test_includes_and_uses():
    selection = SplitSelection("x", {"train": {"train": frozenset({1})},
                                     "test": {"test": None}})
    assert selection.includes("train", "train", 1)
    assert not selection.includes("train", "train", 2)
    assert selection.includes("test", "test", 99)
    assert not selection.uses("train", "test")
