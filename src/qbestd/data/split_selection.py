"""Which rows are train and which are test: the HF split or a manifest split.

The feature caches stay per Hugging Face split (each holds every non-SA row
of that split). A *selection* is a layer over them, keyed by
``(hf_split, row_index)``:

* :func:`hf_selection`: train side = all rows of the HF train split, test
  side = all rows of the HF test split (the baseline);
* :func:`manifest_selection`: the sides of a text-disjoint manifest, which
  mixes rows of both HF splits.

Keys are always ``(hf_split, row_index)`` pairs so that a row that moved
across the split is still looked up in its own HF split (cache, word
alignments, audio).
"""

from dataclasses import dataclass

from qbestd.data.feature_cache import hf_split_id, utterance_slice
from qbestd.data.text_split import read_split_manifest
from qbestd.data.text_split import split_id as manifest_split_id

HF_SPLITS = ("train", "test")
SIDES = ("train", "test")


@dataclass(frozen=True)
class SplitSelection:
    """``rows[side][hf_split]`` is ``None`` (every row) or a frozenset."""

    split_id: str
    rows: dict

    def wanted(self, side, hf_split):
        """``None`` for all rows, otherwise the selected row indices."""
        return self.rows[side].get(hf_split, frozenset())

    def uses(self, side, hf_split):
        wanted = self.wanted(side, hf_split)
        return wanted is None or len(wanted) > 0

    def includes(self, side, hf_split, row_index):
        wanted = self.wanted(side, hf_split)
        return wanted is None or row_index in wanted


def hf_selection():
    """The Hugging Face split: train rows to train, test rows to test."""
    return SplitSelection(hf_split_id(), {"train": {"train": None},
                                          "test": {"test": None}})


def manifest_selection(path):
    """The sides of the manifest file at ``path``; ``split_id`` is from it."""
    manifest = read_split_manifest(path)
    rows = {side: {hf_split: frozenset(manifest.side_rows(hf_split, side))
                   for hf_split in HF_SPLITS} for side in SIDES}
    return SplitSelection(manifest_split_id(path), rows)


def gather_utterances(selection, side, load_cache):
    """Features of the selected rows of ``side``.

    Args:
        load_cache: ``hf_split -> (features, offsets, row_indices, meta)``,
            the result of ``load_feature_cache``.

    Returns:
        ``(utterances, keys)``: one feature array and one
        ``(hf_split, row_index)`` per row, ordered by HF split (train
        first) and cache order.

    Raises:
        ValueError: if a selected row is missing from its cache.
    """
    utterances, keys = [], []
    for hf_split in HF_SPLITS:
        if not selection.uses(side, hf_split):
            continue
        features, offsets, rows, _ = load_cache(hf_split)
        wanted = selection.wanted(side, hf_split)
        found = set()
        for position, row in enumerate(int(r) for r in rows):
            if wanted is None or row in wanted:
                utterances.append(utterance_slice(features, offsets,
                                                  position))
                keys.append((hf_split, row))
                found.add(row)
        if wanted is not None and wanted != found:
            raise ValueError(
                f"{len(wanted - found)} selected {hf_split} rows are not "
                "in the feature cache")
    return utterances, keys
