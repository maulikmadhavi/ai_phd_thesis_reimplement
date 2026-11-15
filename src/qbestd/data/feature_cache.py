"""On-disk cache of acoustic features for the TIMIT training split.

One ``.npz`` per (split, kind, profile) holds the concatenated frame
features (float32), the utterance ``offsets`` into it, the dataset
``row_indices`` and a JSON metadata string. Files go to
``outputs/features/`` (git-ignored) and are never committed.

The two SA sentences, which every TIMIT speaker reads, are excluded by
default, as the thesis excluded them from GMM training (3696 utterances).
"""

import json
from pathlib import Path

import numpy as np

from qbestd.data.timit_hf import (
    TIMIT_HF_REVISION,
    download_timit_parquet,
    iter_timit_rows,
    normalize_transcript,
)
from qbestd.features.extract import extract_features
from qbestd.features.profiles import get_profile

SA_SENTENCES = ("She had your dark suit in greasy wash water all year",
                "Don't ask me to carry an oily rag like that")
SA_TOKENS = tuple(tuple(normalize_transcript(text)) for text in SA_SENTENCES)
FEATURE_DIM = 39


def is_sa_sentence(tokens):
    """True when ``tokens`` (from ``normalize_transcript``) are an SA text."""
    return tuple(tokens) in SA_TOKENS


def cache_path(out_dir, split, kind, profile):
    return Path(out_dir) / f"{split}_{kind}_{profile}.npz"


def build_feature_cache(split, kind, profile, out_dir, exclude_sa=True,
                        parquet_paths=None):
    """Extract features for every row of ``split`` and save one ``.npz``.

    Rows are optionally skipped when they are SA sentences; a row too short
    to give a frame is skipped and counted. ``parquet_paths`` overrides the
    download (used by the tests).

    Returns:
        ``(path, meta)`` of the written file.

    Raises:
        ValueError: if the features do not have 39 dimensions.
    """
    config = get_profile(profile, kind)
    paths = parquet_paths or download_timit_parquet(split)
    blocks, lengths, row_indices = [], [], []
    skipped_sa = skipped_short = 0
    for row in iter_timit_rows(paths, split):
        if exclude_sa and is_sa_sentence(normalize_transcript(row.sentence)):
            skipped_sa += 1
            continue
        features = extract_features(row.audio, row.sample_rate, kind,
                                    config=config)
        if features.shape[1] != FEATURE_DIM:
            raise ValueError(f"expected {FEATURE_DIM} dims, got "
                             f"{features.shape[1]}")
        if len(features) == 0:
            skipped_short += 1
            continue
        blocks.append(features.astype(np.float32))
        lengths.append(len(features))
        row_indices.append(row.row_index)
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    meta = {"split": split, "kind": kind, "profile": profile,
            "dataset_revision": TIMIT_HF_REVISION, "dims": FEATURE_DIM,
            "sample_rate": config.sample_rate, "exclude_sa": exclude_sa,
            "excluded_sa_rows": skipped_sa,
            "skipped_short_rows": skipped_short,
            "n_rows": len(lengths), "n_frames": int(offsets[-1])}
    path = cache_path(out_dir, split, kind, profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    stacked = (np.concatenate(blocks) if blocks
               else np.zeros((0, FEATURE_DIM), np.float32))
    np.savez(path, features=stacked, offsets=offsets,
             row_indices=np.asarray(row_indices, dtype=np.int64),
             metadata=np.array(json.dumps(meta, sort_keys=True)))
    return path, meta


def load_feature_cache(path):
    """Read ``(features, offsets, row_indices, meta)`` from a cache file."""
    with np.load(path, allow_pickle=False) as data:
        return (data["features"], data["offsets"], data["row_indices"],
                json.loads(str(data["metadata"])))


def utterance_slice(features, offsets, position):
    """Frames of the ``position``-th cached utterance."""
    return features[offsets[position]:offsets[position + 1]]
