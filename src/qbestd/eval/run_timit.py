"""TIMIT Q-20 evaluation: MFCC-style features, GMM posteriorgram, subDTW LC2.

Usage::

    pixi run eval-timit --gmm outputs/models/mfcc_timit_matlab_gmm64.npz

Steps: (1) load or build the test feature cache (SA excluded, fingerprint
checked); (2) cut each query clip from the train audio and extract its
features; (3) posteriorgrams of queries and documents; (4) for every query
and document: symmetric-KL matrix, LC2 accumulation and the utterance
distance; (5) rank documents, then p@N and AP per query instance.

Assumptions (unverified, see ``docs/results_timit_q20.md``): every instance
is its own query; relevance is an exact token match; query features are
extracted from the clip; posteriors are floored at 1e-10 and renormalised.
Keywords with no relevant test document are left out. Results carry the
label *speaker overlap present; approximate versus the thesis*.

Writes ``per_query.tsv`` and ``summary.json`` under ``--out`` (git-ignored).
"""

import argparse
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from qbestd.alignment.manifest import read_manifest
from qbestd.data.feature_cache import (
    build_feature_cache,
    cache_path,
    feature_fingerprint,
    hf_split_id,
    load_feature_cache,
    utterance_slice,
)
from qbestd.data.timit_hf import download_timit_parquet, iter_timit_rows
from qbestd.eval.bootstrap import cluster_bootstrap
from qbestd.eval.metrics import average_precision, precision_at_n, summarise
from qbestd.eval.model_guard import check_model
from qbestd.eval.timit_queries import (
    Q20_KEYWORDS,
    build_query_examples,
    cut_clip,
    read_relevance,
)
from qbestd.features.extract import extract_features
from qbestd.features.profiles import get_profile
from qbestd.ml.gmm import gmm_content_sha256, load_gmm
from qbestd.ml.posteriorgram import (
    floor_and_renormalise,
    gaussian_posteriorgram,
)
from qbestd.search.distance import symmetric_kl_matrix
from qbestd.search.score import rank_documents
from qbestd.search.subdtw import best_utterance_distance, subdtw_lc2

PER_QUERY_HEADER = ("keyword", "row_index", "word_index", "n_relevant",
                    "p_at_n", "ap", "nonmatches")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--kind", default="mfcc",
                        choices=("mfcc", "plp", "mfcc_tmp"))
    parser.add_argument("--profile", default="timit_matlab")
    parser.add_argument("--gmm", type=Path, required=True,
                        help="model .npz from qbestd.ml.train")
    parser.add_argument("--keywords", default="q20", choices=("q20",))
    parser.add_argument("--out", type=Path, default=None,
                        help="default: outputs/eval/<model name>")
    parser.add_argument("--features-dir", type=Path,
                        default=Path("outputs/features"))
    parser.add_argument("--alignment-dir", type=Path,
                        default=Path("outputs/alignment"))
    parser.add_argument("--relevance", type=Path,
                        default=Path("outputs/eval/relevance_test.tsv"),
                        help="written by qbestd.eval.q20_counts")
    parser.add_argument("--limit-queries", type=int, default=None,
                        help="use only the first N queries (smoke tests)")
    return parser.parse_args(argv)


def utterance_distances(query_post, document_posts):
    """Utterance distance and non-match flag of one query to each document.

    ``query_post`` is (N, K); ``document_posts`` a list of (M_i, K) arrays,
    already floored and renormalised. A document with no valid end frame
    gets distance ``inf`` and ``nonmatch`` True; it never raises.
    """
    distances = np.empty(len(document_posts))
    nonmatches = np.zeros(len(document_posts), dtype=bool)
    for position, document in enumerate(document_posts):
        local = symmetric_kl_matrix(document, query_post)
        accumulated, length, start = subdtw_lc2(local)
        distance, _, _, nonmatches[position] = best_utterance_distance(
            accumulated, length, start)
        distances[position] = distance
    return distances, nonmatches


def score_query(distances, document_rows, relevant_rows):
    """``(p_at_n percent, ap)`` of one ranked document list.

    Raises:
        ValueError: if no relevant document is among ``document_rows``.
    """
    order = rank_documents(distances)
    relevant = set(relevant_rows)
    flags = [document_rows[i] in relevant for i in order]
    n_relevant = len(relevant & set(document_rows))
    return (precision_at_n(flags, n_relevant),
            average_precision(flags, n_relevant))


def aggregate(per_query):
    """Instance-averaged and keyword-averaged p@N and MAP.

    ``per_query`` is a list of dicts with ``keyword``, ``p_at_n`` (percent)
    and ``ap`` (fraction).
    """
    by_keyword = defaultdict(list)
    for item in per_query:
        by_keyword[item["keyword"]].append((item["p_at_n"], item["ap"]))
    instance = summarise([(q["p_at_n"], q["ap"]) for q in per_query])
    keyword = summarise([tuple(np.mean(pairs, axis=0))
                         for pairs in by_keyword.values()])
    return {"instance_average": instance,
            "keyword_average": {**keyword, "n_keywords": len(by_keyword)},
            "per_keyword": {name: {
                "n_instances": len(pairs),
                "p_at_n": float(np.mean([p for p, _ in pairs])),
                "map": float(100 * np.mean([a for _, a in pairs]))}
                for name, pairs in sorted(by_keyword.items())}}


def write_per_query(path, per_query):
    lines = ["\t".join(PER_QUERY_HEADER)]
    for q in per_query:
        lines.append("\t".join(str(q[name]) if name not in ("p_at_n", "ap")
                               else f"{q[name]:.4f}"
                               for name in PER_QUERY_HEADER))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], text=True,
                              capture_output=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def load_documents(args):
    """Posterior-ready test features: ``(feature list, row indices, meta)``."""
    path = cache_path(args.features_dir, "test", args.kind, args.profile)
    if not path.is_file():
        build_feature_cache("test", args.kind, args.profile,
                            args.features_dir)
    expected = feature_fingerprint(args.kind, args.profile, exclude_sa=True)
    features, offsets, rows, meta = load_feature_cache(path, expected)
    utterances = [utterance_slice(features, offsets, i)
                  for i in range(len(rows))]
    return utterances, [int(r) for r in rows], meta


def query_features(args, examples):
    """Features of every query clip (extracted from the cut audio)."""
    wanted = {e.row_index for e in examples}
    config = get_profile(args.profile, args.kind)
    audio = {row.row_index: row for row in iter_timit_rows(
        download_timit_parquet("train"), "train") if row.row_index in wanted}
    out = []
    for example in examples:
        row = audio[example.row_index]
        clip = cut_clip(row.audio, row.sample_rate, example)
        out.append(extract_features(clip, row.sample_rate, args.kind,
                                    config=config))
    return out


def main(argv=None):
    args = parse_args(argv)
    started = time.time()
    gmm, info = load_gmm(args.gmm)
    split_id = hf_split_id()
    check_model(info, args.kind, args.profile, split_id,
                feature_fingerprint(args.kind, args.profile, exclude_sa=True))
    out = args.out or Path("outputs/eval") / args.gmm.stem
    utterances, doc_rows, doc_meta = load_documents(args)
    relevance = read_relevance(args.relevance)
    words, _ = read_manifest(args.alignment_dir / "timit_hf_words_train.tsv")
    rows = iter_timit_rows(download_timit_parquet("train"), "train")
    examples = [e for e in build_query_examples(words, rows, Q20_KEYWORDS)
                if relevance.get(e.keyword) and
                set(relevance[e.keyword]) & set(doc_rows)]
    if args.limit_queries:
        examples = examples[:args.limit_queries]
    clips = query_features(args, examples)
    document_posts = [floor_and_renormalise(gaussian_posteriorgram(gmm, u))
                      for u in utterances]
    per_query, skipped_short = [], 0
    for count, (example, features) in enumerate(zip(examples, clips), 1):
        if count % 20 == 0:
            print(f"query {count}/{len(examples)} "
                  f"({time.time() - started:.0f} s)", flush=True)
        if len(features) == 0:
            skipped_short += 1
            continue
        query_post = floor_and_renormalise(
            gaussian_posteriorgram(gmm, features))
        distances, nonmatches = utterance_distances(
            query_post, document_posts)
        p_at_n, ap = score_query(distances, doc_rows,
                                 relevance[example.keyword])
        per_query.append({
            "keyword": example.keyword, "row_index": example.row_index,
            "word_index": example.word_index,
            "n_relevant": len(set(relevance[example.keyword])
                              & set(doc_rows)),
            "p_at_n": p_at_n, "ap": ap,
            "nonmatches": int(nonmatches.sum())})
    write_per_query(out / "per_query.tsv", per_query)
    summary = {
        **aggregate(per_query), "bootstrap": cluster_bootstrap(per_query),
        "model": args.gmm.name,
        "model_content_sha256": gmm_content_sha256(gmm),
        "model_info": info, "split_id": split_id,
        "feature_fingerprint": doc_meta["fingerprint"],
        "n_documents": len(doc_rows), "n_queries": len(per_query),
        "queries_without_frames": skipped_short,
        "total_nonmatches": int(sum(q["nonmatches"] for q in per_query)),
        "runtime_s": round(time.time() - started, 1),
        "git_commit": git_commit(),
        "label": "speaker overlap present; approximate versus the thesis"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2),
                                      encoding="utf-8")
    print(json.dumps({k: summary[k] for k in
                      ("instance_average", "keyword_average", "n_queries",
                       "total_nonmatches", "runtime_s")}, indent=2))


if __name__ == "__main__":
    main()
