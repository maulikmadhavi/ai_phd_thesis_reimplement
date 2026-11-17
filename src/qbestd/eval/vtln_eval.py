"""GMM-VTLN inputs for the TIMIT evaluation (Stage 4, W2).

With ``run_timit --vtln`` documents and queries are warped by the final
lambda_r of a VTLN model:

* **documents:** alpha-hat per test document from the per-warp caches, then
  the posteriorgram of its features at that warp (``estimate_test_warps``);
* **query clips:** each clip is cut from the audio and its features are
  extracted at all 13 warps **from the clip itself**; alpha-hat is estimated
  on those. The utterance warp caches are never sliced for queries, so a
  VTLN row stays comparable with the clip-mode no-VTLN rows
  (``query_features: "clip"``).

Histograms and edge shares are in the thesis label (``2 - alpha_ours``).
"""

from pathlib import Path

import numpy as np

from qbestd.data.timit_hf import download_timit_parquet, iter_timit_rows
from qbestd.data.warped_cache import build_warped_caches
from qbestd.eval.timit_queries import cut_clip
from qbestd.features.extract import extract_warped_bank
from qbestd.ml.vtln import (
    WARP_FACTORS,
    edge_shares,
    estimate_warp_factors,
    utterance_log_likelihoods,
    warp_histogram,
)
from qbestd.ml.vtln_train import estimate_test_warps


def warped_paths_for(hf_splits, kind, profile, features_dir,
                     warps=WARP_FACTORS):
    """``{alpha: {hf_split: path}}``, building missing warp caches."""
    paths = {float(a): {} for a in warps}
    for hf_split in sorted(hf_splits):
        built = build_warped_caches(hf_split, kind, profile, features_dir,
                                    warps, skip_existing=True)
        for alpha, path in built.items():
            paths[alpha][hf_split] = path
    return paths


def clip_warp_features(clip, sample_rate, kind, config, gmm,
                       warps=WARP_FACTORS):
    """``(features at alpha-hat, alpha-hat)`` of one query clip.

    Features at every warp come from the clip audio. Raises ``ValueError``
    for a clip too short to give a frame (no warp can be estimated); the
    length is checked before any feature is computed, and an empty bank is
    a second guard.
    """
    if len(clip) < round(config.frame_ms * sample_rate / 1000.0):
        raise ValueError("clip too short for a frame")
    bank = extract_warped_bank(clip, sample_rate, kind, warps, config)
    if any(len(features) == 0 for features in bank.values()):
        raise ValueError("clip too short for a frame")
    row = np.array([[utterance_log_likelihoods(
        bank[float(w)], [0, len(bank[float(w)])], gmm)[0] for w in warps]])
    alpha = float(estimate_warp_factors(row, warps)[0])
    return bank[alpha], alpha


def load_example_audio(examples):
    """``{(hf_split, row_index): TimitRow}`` for the rows of ``examples``."""
    wanted = {(e.hf_split, e.row_index) for e in examples}
    audio = {}
    for hf_split in sorted({split for split, _ in wanted}):
        for row in iter_timit_rows(download_timit_parquet(hf_split),
                                   hf_split):
            if (hf_split, row.row_index) in wanted:
                audio[(hf_split, row.row_index)] = row
    return audio


def read_source_alphas(path):
    """``{(hf_split, row_index): alpha_ours}`` from a trace ``alphas.tsv``;
    empty when the file is missing."""
    path = Path(path)
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        split, row, ours, _ = line.split("\t")
        out[(split, int(row))] = float(ours)
    return out


def vtln_inputs(gmm, doc_keys, examples, audio, paths, kind, profile,
                config, source_alphas=None, warps=WARP_FACTORS):
    """Warped document posteriorgrams, query features and a summary dict.

    Args:
        doc_keys: ``(hf_split, row_index)`` per test document.
        examples: the query examples (clip interval fields).
        audio: ``load_example_audio(examples)``.
        paths: ``warped_paths_for(...)`` covering the documents' HF splits.
        source_alphas: final train alpha-hat of the source utterances, for
            the share of queries whose alpha-hat differs from it.

    Returns:
        ``(posteriorgrams, query_features, info)``; a query whose clip is too
        short gets an empty feature array (and no alpha-hat).
    """
    doc_alphas, grams = estimate_test_warps(paths, gmm, doc_keys, kind,
                                            profile, warps)
    queries, alphas, differs = [], [], []
    for example in examples:
        row = audio[(example.hf_split, example.row_index)]
        clip = cut_clip(row.audio, row.sample_rate, example)
        try:
            features, alpha = clip_warp_features(
                clip, row.sample_rate, kind, config, gmm, warps)
        except ValueError:
            queries.append(np.zeros((0, gmm.dim)))
            continue
        queries.append(features)
        alphas.append(alpha)
        source = (source_alphas or {}).get((example.hf_split,
                                            example.row_index))
        if source is not None:
            differs.append(alpha != source)
    info = {"query_features": "clip",
            "test_warp_histogram": warp_histogram(doc_alphas, warps),
            "test_edge_shares": edge_shares(doc_alphas, warps),
            "query_warp_histogram": warp_histogram(alphas, warps),
            "query_edge_shares": edge_shares(alphas, warps),
            "share_queries_alpha_differs_from_source": (
                float(np.mean(differs)) if differs else None),
            "n_queries_with_source_alpha": len(differs)}
    return grams, queries, info
