"""Per-warp feature caches for GMM-based VTLN (Stage 4, V2).

One cache file per warp factor and HF split,
``<split>_<kind>_<profile>_a<alpha x 100>.npz``, built by
``build_feature_cache`` (same row selection, own fingerprint). Everything
here reads **one warp's file at a time**, so memory never holds more than one
warp of a whole split.

Rows are ``(hf_split, row_index)`` keys, as in ``split_selection``: a
manifest split mixes rows of both HF splits.
"""

import numpy as np

from qbestd.data.feature_cache import (
    build_feature_cache,
    feature_fingerprint,
    load_feature_cache,
    warped_cache_path,
)
from qbestd.ml.vtln import WARP_FACTORS, utterance_log_likelihoods


def build_warped_caches(split, kind, profile, out_dir, warps=WARP_FACTORS,
                        parquet_paths=None, skip_existing=False):
    """Build one cache per warp of the HF ``split``; returns ``{alpha: path}``.

    With ``skip_existing`` a file whose fingerprint matches is kept.
    """
    paths = {}
    for alpha in warps:
        path = warped_cache_path(out_dir, split, kind, profile, alpha)
        if skip_existing and path.is_file():
            try:
                load_feature_cache(path, feature_fingerprint(
                    kind, profile, warp_factor=alpha))
                paths[float(alpha)] = path
                continue
            except ValueError:
                pass  # stale file: rebuild it
        paths[float(alpha)], _ = build_feature_cache(
            split, kind, profile, out_dir, parquet_paths=parquet_paths,
            warp_factor=alpha)
    return paths


def _read(path, kind, profile, alpha):
    return load_feature_cache(path, expected=feature_fingerprint(
        kind, profile, warp_factor=alpha))


def _positions(row_indices):
    return {int(row): position for position, row in enumerate(row_indices)}


def ll_matrix_from_caches(paths, gmm, keys, kind, profile,
                          warps=WARP_FACTORS):
    """Log-likelihood of every utterance at every warp, ``(n_utt, n_warps)``.

    Args:
        paths: ``{alpha: {hf_split: cache path}}``.
        keys: ``(hf_split, row_index)`` per utterance, in output order.
        kind, profile: checked against each file's fingerprint.

    Streams one warp, and one HF split of it, at a time.

    Raises:
        ValueError: if a key is missing from its cache or a fingerprint
            differs.
    """
    matrix = np.empty((len(keys), len(warps)))
    features = None
    for column, alpha in enumerate(warps):
        for hf_split, path in paths[float(alpha)].items():
            features, offsets, rows, _ = _read(path, kind, profile, alpha)
            per_row = utterance_log_likelihoods(features, offsets, gmm)
            where = _positions(rows)
            for index, (split, row) in enumerate(keys):
                if split != hf_split:
                    continue
                if row not in where:
                    raise ValueError(f"row {row} of {split} is not in {path}")
                matrix[index, column] = per_row[where[row]]
        del features
    return matrix


def select_warped_features(paths, alphas, keys, kind, profile):
    """Features ``X^alpha_hat``: each utterance at its own warp.

    Args:
        paths: ``{alpha: {hf_split: cache path}}``.
        alphas: warp factor per utterance, aligned with ``keys``.

    Returns:
        ``(features, offsets)`` with the utterances in ``keys`` order.
        Opens one warp file at a time.

    Raises:
        ValueError: if a key is missing from its cache.
    """
    pieces = [None] * len(keys)
    features = None
    alphas = np.asarray(alphas, dtype="float64")
    for alpha in sorted(set(alphas.tolist())):
        for hf_split, path in paths[float(alpha)].items():
            features, offsets, rows, _ = _read(path, kind, profile, alpha)
            where = _positions(rows)
            for index, (split, row) in enumerate(keys):
                if split != hf_split or alphas[index] != alpha:
                    continue
                if row not in where:
                    raise ValueError(f"row {row} of {split} is not in {path}")
                position = where[row]
                pieces[index] = np.array(
                    features[offsets[position]:offsets[position + 1]])
        del features
    if any(piece is None for piece in pieces):
        raise ValueError("an utterance has no warped features")
    lengths = [len(piece) for piece in pieces]
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    dim = pieces[0].shape[1] if pieces else 0
    stacked = np.concatenate(pieces) if pieces else np.zeros((0, dim))
    return stacked, offsets
