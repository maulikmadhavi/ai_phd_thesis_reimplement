"""Stage 5 demo: query-by-example search with subsequence DTW (LC2).

Usage:  pixi run -e demo demo-stage5
Two modes:

* **Two clips**: upload a query clip and a document clip. The page shows both
  Gaussian posteriorgrams, the symmetric-KL matrix D, the accumulated cost S
  with the best path overlaid, and the utterance distance.
* **Q-20 keyword**: pick a keyword and a spoken instance (from
  ``outputs/eval/queries_train.tsv``, built by ``python -m
  qbestd.eval.q20_counts``). The query is cut from the TIMIT train audio and
  searched against the cached test documents; the page lists the 10 best
  documents with relevance marks and the query p@N and AP.

A GMM from ``outputs/models/*.npz`` is required (``pixi run train-gmm``).
Features use the ``timit_matlab`` MFCC profile. Results are labelled
*speaker overlap present; approximate versus the thesis*. All processing
comes from ``qbestd``.
"""

from functools import lru_cache
from pathlib import Path

import gradio as gr
from matplotlib.figure import Figure

from qbestd.audio.io import load_audio
from qbestd.data.feature_cache import (
    cache_path,
    feature_fingerprint,
    load_feature_cache,
    utterance_slice,
)
from qbestd.data.timit_hf import download_timit_parquet, iter_timit_rows
from qbestd.eval.metrics import average_precision, precision_at_n
from qbestd.eval.run_timit import utterance_distances
from qbestd.eval.timit_queries import (
    cut_clip,
    read_query_examples,
    read_relevance,
)
from qbestd.features.extract import extract_features
from qbestd.features.profiles import get_profile
from qbestd.ml.gmm import load_gmm
from qbestd.ml.posteriorgram import (
    floor_and_renormalise,
    gaussian_posteriorgram,
)
from qbestd.search.distance import symmetric_kl_matrix
from qbestd.search.score import rank_documents
from qbestd.search.subdtw import (
    backtrace_path,
    best_utterance_distance,
    subdtw_lc2,
)

KIND, PROFILE = "mfcc", "timit_matlab"
MODELS_DIR = Path("outputs/models")
EVAL_DIR = Path("outputs/eval")
FEATURES_DIR = Path("outputs/features")
SHIFT_S = 0.010
LABEL = "speaker overlap present; approximate versus the thesis"


def list_models():
    return sorted(path.name for path in MODELS_DIR.glob("*.npz"))


def posteriors(gmm, samples, rate):
    features = extract_features(samples, rate, KIND,
                                config=get_profile(PROFILE, KIND))
    if len(features) == 0:
        raise gr.Error("A clip is shorter than one frame.")
    return floor_and_renormalise(gaussian_posteriorgram(gmm, features))


def heatmap(matrix, title, path=None, ylabel="test frame",
            xlabel="query frame"):
    figure = Figure(figsize=(5, 4))
    axis = figure.subplots()
    image = axis.imshow(matrix, origin="lower", aspect="auto")
    if path:
        axis.plot([n for _, n in path], [m for m, _ in path], color="white",
                  linewidth=1.5)
    axis.set(title=title, xlabel=xlabel, ylabel=ylabel)
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    return figure


def posteriorgram_plot(grid, title):
    figure = Figure(figsize=(5, 3))
    axis = figure.subplots()
    image = axis.imshow(grid.T, origin="lower", aspect="auto",
                        extent=[0, len(grid) * SHIFT_S, 0, grid.shape[1]])
    axis.set(title=title, xlabel="time (s)", ylabel="component")
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    return figure


def align_pair(query_post, document_post):
    """D, S, the best path and the utterance distance of one pair."""
    local = symmetric_kl_matrix(document_post, query_post)
    accumulated, length, start = subdtw_lc2(local)
    distance, first, last, nonmatch = best_utterance_distance(
        accumulated, length, start)
    path = None if nonmatch else backtrace_path(local, accumulated, last)
    return local, accumulated, path, distance, (first, last, nonmatch)


def search_two_clips(model_name, query_audio, document_audio):
    if not (model_name and query_audio and document_audio):
        raise gr.Error("Pick a model and upload both clips.")
    gmm, _ = load_gmm(MODELS_DIR / model_name)
    query = posteriors(gmm, *load_audio(query_audio))
    document = posteriors(gmm, *load_audio(document_audio))
    local, accumulated, path, distance, (first, last, nonmatch) = (
        align_pair(query, document))
    note = ("**non-match**: no end frame has a test-frame displacement of "
            "0.5 to 2 times the query length, so the distance is infinite"
            if nonmatch else
            f"utterance distance **{distance:.3f}**; best match at test "
            f"frames {first}-{last} ({first * SHIFT_S:.2f}-"
            f"{(last + 1) * SHIFT_S:.2f} s)")
    return (posteriorgram_plot(query, "Query posteriorgram"),
            posteriorgram_plot(document, "Document posteriorgram"),
            heatmap(local, "Local distance D (symmetric KL)"),
            heatmap(accumulated, "Accumulated S with best path", path),
            note, None)


@lru_cache(maxsize=1)
def query_table():
    return read_query_examples(EVAL_DIR / "queries_train.tsv")


@lru_cache(maxsize=1)
def test_documents():
    path = cache_path(FEATURES_DIR, "test", KIND, PROFILE)
    features, offsets, rows, _ = load_feature_cache(
        path, feature_fingerprint(KIND, PROFILE, exclude_sa=True))
    return ([utterance_slice(features, offsets, i) for i in range(len(rows))],
            [int(r) for r in rows])


def instances_of(keyword):
    return [f"{i}: row {e.row_index}, word {e.word_index}"
            for i, e in enumerate(e for e in query_table()
                                  if e.keyword == keyword)]


def search_keyword(model_name, keyword, instance):
    if not (model_name and keyword and instance):
        raise gr.Error("Pick a model, a keyword and an instance.")
    gmm, _ = load_gmm(MODELS_DIR / model_name)
    example = [e for e in query_table() if e.keyword == keyword][
        int(instance.split(":")[0])]
    row = next(r for r in iter_timit_rows(download_timit_parquet("train"),
                                          "train")
               if r.row_index == example.row_index)
    query = posteriors(gmm, cut_clip(row.audio, row.sample_rate, example),
                       row.sample_rate)
    utterances, doc_rows = test_documents()
    document_posts = [floor_and_renormalise(gaussian_posteriorgram(gmm, u))
                      for u in utterances]
    distances, _ = utterance_distances(query, document_posts)
    relevant = set(read_relevance(EVAL_DIR / "relevance_test.tsv")[keyword])
    n_relevant = len(relevant & set(doc_rows))
    order = rank_documents(distances)
    flags = [doc_rows[i] in relevant for i in order]
    best = int(order[0])
    local, accumulated, path, distance, _ = align_pair(query,
                                                       document_posts[best])
    table = "| Rank | Test row | Distance | Relevant |\n|---|---|---|---|\n"
    table += "\n".join(
        f"| {rank + 1} | {doc_rows[i]} | {distances[i]:.3f} | "
        f"{'yes' if flags[rank] else 'no'} |"
        for rank, i in enumerate(order[:10]))
    note = (f"{keyword}: {n_relevant} relevant of {len(doc_rows)} documents; "
            f"p@N **{precision_at_n(flags, n_relevant):.1f}%**, "
            f"AP **{average_precision(flags, n_relevant):.3f}**. "
            f"*{LABEL}*")
    return (posteriorgram_plot(query, "Query posteriorgram"),
            posteriorgram_plot(document_posts[best],
                               f"Top document (row {doc_rows[best]})"),
            heatmap(local, "Local distance D (top document)"),
            heatmap(accumulated, "Accumulated S, best path", path),
            note, table)


def build_demo():
    from qbestd.eval.timit_queries import keyword_names
    with gr.Blocks(title="Stage 5: subDTW search") as demo:
        gr.Markdown(__doc__)
        models = list_models()
        model = gr.Dropdown(models, value=models[0] if models else None,
                            label="GMM")
        with gr.Tab("Two clips"):
            query_audio = gr.Audio(type="filepath", label="Query clip",
                                   sources=["upload", "microphone"])
            document_audio = gr.Audio(type="filepath", label="Document clip",
                                      sources=["upload", "microphone"])
            clips_button = gr.Button("Search")
        with gr.Tab("Q-20 keyword"):
            keyword = gr.Dropdown(keyword_names(), value="love",
                                  label="keyword")
            instance = gr.Dropdown([], label="spoken instance")
            keyword_button = gr.Button("Search test documents")
        note = gr.Markdown()
        outputs_ = [gr.Plot(label=name) for name in
                    ("Query", "Document", "D", "S + path")]
        table = gr.Markdown()
        results = outputs_ + [note, table]
        keyword.change(lambda k: gr.update(choices=instances_of(k)),
                       keyword, instance)
        clips_button.click(search_two_clips,
                           [model, query_audio, document_audio], results)
        keyword_button.click(search_keyword, [model, keyword, instance],
                             results)
    return demo


if __name__ == "__main__":
    build_demo().launch()
