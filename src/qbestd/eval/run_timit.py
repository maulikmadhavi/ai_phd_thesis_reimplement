"""TIMIT Q-20 evaluation: MFCC-style features, GMM posteriorgram, subDTW LC2.

Usage::

    pixi run eval-timit --gmm outputs/models/mfcc_timit_matlab_gmm64.npz
    pixi run eval-timit --gmm <model> --split-manifest <manifest.tsv>

Without ``--split-manifest`` the Hugging Face split is used (train rows give
queries, test rows give documents). With it, the train side of the manifest
(rows of either HF split, each with its own word alignments) gives queries
and the test side gives documents and relevance; the model must have been
trained on the same split (``split_id`` is checked).

Steps: (1) load or build the feature caches (SA excluded, fingerprint
checked) and select the test-side documents; (2) cut each query clip from its
audio and extract its features; (3) posteriorgrams of queries and
documents; (4) for every query and document: symmetric-KL matrix, LC2
accumulation and the utterance distance; (5) rank documents, then p@N
and AP per query instance.

Assumptions (unverified, see ``docs/results_timit_q20.md``): every instance
is its own query; relevance is an exact token match; query features are
extracted from the clip; posteriors are floored at 1e-10 and renormalised.
Keywords with no relevant test document are left out. Results carry the
label *speaker overlap present; approximate versus the thesis*.

Writes ``per_query.tsv`` and ``summary.json`` under ``--out`` (git-ignored).
"""

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from qbestd.alignment.manifest import read_manifest
from qbestd.data.feature_cache import (
    build_feature_cache,
    cache_path,
    feature_fingerprint,
    load_feature_cache,
)
from qbestd.data.split_selection import (
    HF_SPLITS,
    gather_utterances,
    hf_selection,
    manifest_selection,
)
from qbestd.data.timit_hf import (
    download_timit_parquet,
    iter_timit_rows,
    read_sentences,
)
from qbestd.eval.bootstrap import cluster_bootstrap
from qbestd.eval.metrics import average_precision, precision_at_n, summarise
from qbestd.eval.model_guard import check_model
from qbestd.eval.selection_data import (
    selection_examples,
    selection_relevance,
)
from qbestd.eval.query_features import MODES, query_features_for
from qbestd.eval.timit_queries import Q20_KEYWORDS
from qbestd.eval.vtln_eval import CELL_MODEL_TYPE, expected_model_type
from qbestd.features.profiles import get_profile
from qbestd.ml.gmm import gmm_content_sha256, load_gmm
from qbestd.ml.posteriorgram import (
    floor_and_renormalise,
    gaussian_posteriorgram,
    mean_posteriorgram_entropy,
)
from qbestd.provenance import finish_run, start_run
from qbestd.search.distance import symmetric_kl_matrix
from qbestd.search.score import rank_documents
from qbestd.search.subdtw import best_utterance_distance, subdtw_lc2

PER_QUERY_HEADER = ("keyword", "hf_split", "row_index", "word_index",
                    "n_relevant", "p_at_n", "ap", "nonmatches")


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
    parser.add_argument("--query-features", default="clip", choices=MODES,
                        help="clip (primary): features of the cut clip; "
                        "slice (sensitivity): frames of the whole "
                        "utterance inside the interval")
    parser.add_argument("--split-manifest", type=Path, default=None,
                        help="text-disjoint manifest (default: HF split)")
    parser.add_argument("--limit-queries", type=int, default=None,
                        help="use only the first N queries (smoke tests)")
    parser.add_argument("--vtln", action="store_true",
                        help="the model is a GMM-VTLN model (train-vtln); "
                        "documents and query clips are warped")
    parser.add_argument("--vtln-cell", choices=tuple(CELL_MODEL_TYPE),
                        default=None,
                        help="gain-split cell: model_only (VTLN model, "
                        "plain inputs), selection_only (plain model, "
                        "alpha-hat inputs) or query_inherit (VTLN model, "
                        "queries at their source utterance's alpha-hat)")
    parser.add_argument("--allow-dirty", action="store_true",
                        help="run on uncommitted changes (recorded)")
    args = parser.parse_args(argv)
    if args.vtln and args.vtln_cell:
        parser.error("--vtln and --vtln-cell are exclusive")
    return args


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


def load_split_cache(args, hf_split):
    """Feature cache of one HF split, built on demand, fingerprint checked."""
    path = cache_path(args.features_dir, hf_split, args.kind, args.profile)
    if not path.is_file():
        build_feature_cache(hf_split, args.kind, args.profile,
                            args.features_dir)
    expected = feature_fingerprint(args.kind, args.profile, exclude_sa=True)
    return load_feature_cache(path, expected)


def query_features(args, examples):
    """Features of every query clip (extracted from the cut audio)."""
    wanted = {(e.hf_split, e.row_index) for e in examples}
    config = get_profile(args.profile, args.kind)
    audio = {}
    for hf_split in sorted({split for split, _ in wanted}):
        for row in iter_timit_rows(download_timit_parquet(hf_split),
                                   hf_split):
            if (hf_split, row.row_index) in wanted:
                audio[(hf_split, row.row_index)] = row
    full_cache = {}
    return [query_features_for(
        args.query_features, audio[(e.hf_split, e.row_index)], e, args.kind,
        config, full_cache) for e in examples]


def vtln_run_inputs(args, gmm, info, doc_rows, examples):
    """Warped documents and query clips of a VTLN model (see vtln_eval)."""
    from qbestd.eval.vtln_eval import (
        load_example_audio,
        read_source_alphas,
        vtln_inputs,
        warped_paths_for,
    )
    paths = warped_paths_for({split for split, _ in doc_rows}, args.kind,
                             args.profile, args.features_dir)
    sources = {}
    if "n_vtln_iter" in info:  # a plain model has no trace
        last = info["n_vtln_iter"] - 1
        trace = (args.gmm.with_name(args.gmm.stem + "_trace")
                 / f"iter{last}_alphas.tsv")
        sources = read_source_alphas(trace)
    return vtln_inputs(
        gmm, doc_rows, examples, load_example_audio(examples), paths,
        args.kind, args.profile, get_profile(args.profile, args.kind),
        sources, inherit=args.vtln_cell == "query_inherit")


def load_inputs(args, selection):
    """``(documents, document keys, relevance, examples)`` of a selection."""
    utterances, keys = gather_utterances(
        selection, "test", lambda split: load_split_cache(args, split))
    sentences = {split: read_sentences(download_timit_parquet(split))
                 for split in HF_SPLITS if selection.uses("test", split)}
    relevance = selection_relevance(keys, sentences, Q20_KEYWORDS)
    examples, _ = selection_examples(
        selection, Q20_KEYWORDS,
        lambda split: read_manifest(
            args.alignment_dir / f"timit_hf_words_{split}.tsv")[0],
        lambda split: iter_timit_rows(download_timit_parquet(split), split))
    return (utterances, keys, relevance,
            [e for e in examples if relevance[e.keyword]])


def main(argv=None):
    args = parse_args(argv)
    provenance = start_run(args.allow_dirty)
    started = time.time()
    gmm, info = load_gmm(args.gmm)
    selection = (manifest_selection(args.split_manifest)
                 if args.split_manifest else hf_selection())
    split_id = selection.split_id
    fingerprint = feature_fingerprint(args.kind, args.profile,
                                      exclude_sa=True)
    model_type = expected_model_type(args.vtln, args.vtln_cell)
    check_model(info, args.kind, args.profile, split_id, fingerprint,
                model_type=model_type)
    out = args.out or Path("outputs/eval") / args.gmm.stem
    utterances, doc_rows, relevance, examples = load_inputs(args, selection)
    if args.limit_queries:
        examples = examples[:args.limit_queries]
    vtln_info = {}
    warped = args.vtln or args.vtln_cell in ("selection_only",
                                             "query_inherit")
    if warped:
        grams, clips, vtln_info = vtln_run_inputs(args, gmm, info, doc_rows,
                                                  examples)
        document_posts = [floor_and_renormalise(g) for g in grams]
    else:
        clips = query_features(args, examples)
        document_posts = [
            floor_and_renormalise(gaussian_posteriorgram(gmm, u))
            for u in utterances]
    query_posts, per_query, skipped_short = [], [], 0
    for count, (example, features) in enumerate(zip(examples, clips), 1):
        if count % 20 == 0:
            print(f"query {count}/{len(examples)} "
                  f"({time.time() - started:.0f} s)", flush=True)
        if len(features) == 0:
            skipped_short += 1
            continue
        query_post = floor_and_renormalise(
            gaussian_posteriorgram(gmm, features))
        query_posts.append(query_post)
        distances, nonmatches = utterance_distances(
            query_post, document_posts)
        p_at_n, ap = score_query(distances, doc_rows,
                                 relevance[example.keyword])
        per_query.append({
            "keyword": example.keyword, "hf_split": example.hf_split,
            "row_index": example.row_index,
            "word_index": example.word_index,
            "n_relevant": len(relevance[example.keyword]),
            "p_at_n": p_at_n, "ap": ap,
            "nonmatches": int(nonmatches.sum())})
    write_per_query(out / "per_query.tsv", per_query)
    summary = {
        **aggregate(per_query), "bootstrap": cluster_bootstrap(per_query),
        "model": args.gmm.name,
        "model_content_sha256": gmm_content_sha256(gmm),
        "model_info": info, "split_id": split_id,
        "feature_fingerprint": fingerprint,
        "query_features": "clip" if warped else args.query_features,
        "model_type": model_type, "vtln_cell": args.vtln_cell,
        "mean_entropy_documents": mean_posteriorgram_entropy(document_posts),
        "mean_entropy_queries": mean_posteriorgram_entropy(query_posts),
        **({"vtln": vtln_info} if warped else {}),
        "split_manifest": (str(args.split_manifest)
                           if args.split_manifest else None),
        "n_documents": len(doc_rows), "n_queries": len(per_query),
        "queries_without_frames": skipped_short,
        "total_nonmatches": int(sum(q["nonmatches"] for q in per_query)),
        "runtime_s": round(time.time() - started, 1),
        "git_commit": provenance["git_commit_start"],
        **finish_run(provenance),
        "label": ("closer to the thesis on sentence context; not an "
                  "official TIMIT reconstruction; speaker overlap present"
                  if args.split_manifest else
                  "sentence-text overlap between queries and documents "
                  "(HF split); speaker overlap present; approximate "
                  "versus the thesis")}
    (out / "summary.json").write_text(json.dumps(summary, indent=2),
                                      encoding="utf-8")
    print(json.dumps({k: summary[k] for k in
                      ("instance_average", "keyword_average", "n_queries",
                       "total_nonmatches", "runtime_s")}, indent=2))


if __name__ == "__main__":
    main()
