from pathlib import Path

import numpy as np
import pytest

from qbestd.search.score import rank_documents
from qbestd.eval.run_timit import (
    PER_QUERY_HEADER,
    aggregate,
    parse_args,
    score_query,
    utterance_distances,
    write_per_query,
)


def peaked(rows, k, rng):
    raw = rng.gamma(0.3, size=(rows, k)) + 1e-3
    return raw / raw.sum(axis=1, keepdims=True)


def test_defaults_and_required_model():
    args = parse_args(["--gmm", "m.npz"])
    assert (args.kind, args.profile, args.keywords) == (
        "mfcc", "timit_matlab", "q20")
    assert args.gmm == Path("m.npz")
    assert args.out is None and args.limit_queries is None
    assert args.split_manifest is None


def test_model_is_required():
    with pytest.raises(SystemExit):
        parse_args([])


def test_planted_query_ranks_its_document_first():
    rng = np.random.default_rng(0)
    query = peaked(10, 6, rng)
    documents = [peaked(40, 6, rng) for _ in range(5)]
    documents[3] = np.concatenate([peaked(8, 6, rng), query,
                                   peaked(12, 6, rng)])
    distances, nonmatches = utterance_distances(query, documents)
    assert int(np.argmin(distances)) == 3
    assert distances[3] == pytest.approx(0.0, abs=1e-9)
    assert nonmatches.dtype == bool and nonmatches.shape == (5,)
    assert not nonmatches.any()


def test_short_document_is_a_nonmatch_and_ranks_last_without_raising():
    rng = np.random.default_rng(1)
    query = peaked(20, 6, rng)
    documents = [peaked(5, 6, rng), np.concatenate([peaked(4, 6, rng), query])]
    distances, nonmatches = utterance_distances(query, documents)
    assert nonmatches.tolist() == [True, False]
    assert distances[0] == np.inf
    assert rank_documents(distances).tolist() == [1, 0]


def test_score_query_perfect_and_worst_ranking():
    rows = [10, 11, 12, 13]
    assert score_query([0.1, 0.2, 0.9, 0.8], rows, {10, 11}) == (
        pytest.approx(100.0), pytest.approx(1.0))
    p_at_n, ap = score_query([0.9, 0.8, 0.1, 0.2], rows, {10, 11})
    assert p_at_n == 0.0
    assert ap == pytest.approx((1 / 3 + 2 / 4) / 2)


def test_score_query_ignores_relevant_rows_outside_the_documents():
    # row 99 is relevant but not a document, so N = 1
    assert score_query([0.1, 0.5], [10, 11], {10, 99})[0] == 100.0


def test_score_query_without_relevant_document_raises():
    with pytest.raises(ValueError):
        score_query([0.1, 0.5], [10, 11], {99})


def test_aggregate_instance_and_keyword_averages_differ():
    per_query = [
        {"keyword": "a", "p_at_n": 100.0, "ap": 1.0},
        {"keyword": "a", "p_at_n": 100.0, "ap": 1.0},
        {"keyword": "a", "p_at_n": 100.0, "ap": 1.0},
        {"keyword": "b", "p_at_n": 0.0, "ap": 0.0}]
    result = aggregate(per_query)
    assert result["instance_average"]["p_at_n"] == pytest.approx(75.0)
    assert result["keyword_average"]["p_at_n"] == pytest.approx(50.0)
    assert result["keyword_average"]["map"] == pytest.approx(50.0)
    assert result["keyword_average"]["n_keywords"] == 2
    assert result["per_keyword"]["a"]["n_instances"] == 3


def test_write_per_query_has_the_documented_columns(tmp_path):
    rows = [{"keyword": "love", "hf_split": "train", "row_index": 3,
             "word_index": 1,
             "n_relevant": 2, "p_at_n": 50.0, "ap": 0.75, "nonmatches": 4}]
    write_per_query(tmp_path / "sub" / "per_query.tsv", rows)
    lines = (tmp_path / "sub" / "per_query.tsv").read_text().splitlines()
    assert lines[0].split("\t") == list(PER_QUERY_HEADER)
    assert lines[1].split("\t") == ["love", "train", "3", "1", "2",
                                    "50.0000", "0.7500", "4"]
