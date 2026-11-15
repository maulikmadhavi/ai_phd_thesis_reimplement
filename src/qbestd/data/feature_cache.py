"""On-disk cache of acoustic features for the TIMIT training split.

One ``.npz`` per (split, kind, profile) holds the concatenated frame
features (float32), the utterance ``offsets`` into it, the dataset
``row_indices`` and a JSON metadata string. Files go to
``outputs/features/`` (git-ignored) and are never committed.

The two SA sentences, which every TIMIT speaker reads, are excluded by
default, as the thesis excluded them from GMM training (3696 utterances).
"""

import hashlib
import json
from dataclasses import asdict
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
# Cache FORMAT schema version: bump it only when the layout of the ``.npz``
# or its metadata changes. Changes to the feature maths are caught by the
# source digest in the fingerprint, not by this number.
FEATURE_CACHE_VERSION = 1
# The modules that compute features: the transitive ``qbestd.audio`` and
# ``qbestd.features`` imports of ``qbestd.features.extract`` (a test checks
# this). Paths are relative to the ``qbestd`` package, sorted. Docs, tests
# and other packages are deliberately not listed.
FEATURE_SOURCE_FILES = (
    "audio/framing.py",
    "audio/pipeline.py",
    "audio/preprocess.py",
    "audio/resample.py",
    "audio/spectrum.py",
    "audio/windowing.py",
    "features/cepstral.py",
    "features/deltas.py",
    "features/extract.py",
    "features/filterbank.py",
    "features/frontend.py",
    "features/lpc.py",
    "features/mfcc.py",
    "features/mfcc_tmp.py",
    "features/plp.py",
    "features/scales.py",
)


class CacheMismatchError(ValueError):
    """A cache file was built with different settings than requested."""


def feature_source_digest(root=None, files=FEATURE_SOURCE_FILES):
    """SHA-256 over the feature source files: each relative path, then its
    bytes with CRLF turned into LF (so git autocrlf does not change it)."""
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for name in files:
        digest.update(name.encode("utf-8") + b"\0")
        data = (root / name).read_bytes().replace(b"\r\n", b"\n")
        digest.update(data + b"\0")
    return digest.hexdigest()


def feature_fingerprint(kind, profile, exclude_sa=True,
                        dataset_revision=TIMIT_HF_REVISION):
    """SHA-256 over everything that decides what the cached features are:
    the profile config values, feature kind, dataset revision, SA exclusion,
    the feature source digest and ``FEATURE_CACHE_VERSION`` (the cache
    format version)."""
    payload = {"config": asdict(get_profile(profile, kind)), "kind": kind,
               "dataset_revision": dataset_revision,
               "exclude_sa": bool(exclude_sa),
               "source_digest": feature_source_digest(),
               "version": FEATURE_CACHE_VERSION}
    text = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
            "fingerprint": feature_fingerprint(kind, profile, exclude_sa),
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


def load_feature_cache(path, expected=None):
    """Read ``(features, offsets, row_indices, meta)`` from a cache file.

    Args:
        expected: a :func:`feature_fingerprint`; when given, the file must
            carry the same one.

    Raises:
        CacheMismatchError: if ``expected`` is given and the fingerprint of
            the file differs or is missing (an older cache).
    """
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data["metadata"]))
        if expected is not None and meta.get("fingerprint") != expected:
            raise CacheMismatchError(
                f"{path} was built with different settings (or before "
                "fingerprints existed)")
        return (data["features"], data["offsets"], data["row_indices"], meta)


def utterance_slice(features, offsets, position):
    """Frames of the ``position``-th cached utterance."""
    return features[offsets[position]:offsets[position + 1]]
