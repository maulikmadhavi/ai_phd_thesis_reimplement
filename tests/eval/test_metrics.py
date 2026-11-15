import pytest

from qbestd.eval.metrics import (
    average_precision,
    precision_at_n,
    summarise,
)

THESIS_EXAMPLE = [True, True, False, False, True, False, False, True,
                  False, False]


def test_thesis_example_gives_50_percent_and_0_775():
    assert precision_at_n(THESIS_EXAMPLE, 4) == pytest.approx(50.0)
    assert average_precision(THESIS_EXAMPLE, 4) == pytest.approx(0.775)


def test_perfect_ranking_gives_100_percent_and_ap_one():
    ranking = [True] * 3 + [False] * 7
    assert precision_at_n(ranking, 3) == pytest.approx(100.0)
    assert average_precision(ranking, 3) == pytest.approx(1.0)


def test_no_relevant_document_in_ranking_gives_zero():
    assert precision_at_n([False] * 5, 2) == 0.0
    assert average_precision([False] * 5, 2) == 0.0


def test_relevant_documents_missing_from_ranking_lower_ap():
    # one of two relevant documents is not ranked at all
    assert average_precision([True, False], 2) == pytest.approx(0.5)


def test_ranking_shorter_than_n_is_allowed():
    assert precision_at_n([True], 4) == pytest.approx(25.0)


def test_worst_rank_for_single_relevant_document():
    ranking = [False] * 9 + [True]
    assert average_precision(ranking, 1) == pytest.approx(0.1)
    assert precision_at_n(ranking, 1) == 0.0


@pytest.mark.parametrize("function", [precision_at_n, average_precision])
def test_zero_relevant_raises(function):
    with pytest.raises(ValueError):
        function([False, False], 0)


@pytest.mark.parametrize("function", [precision_at_n, average_precision])
def test_more_flags_than_relevant_raises(function):
    with pytest.raises(ValueError):
        function([True, True], 1)


def test_summarise_averages_over_queries():
    result = summarise([(50.0, 0.775), (100.0, 1.0)])
    assert result["p_at_n"] == pytest.approx(75.0)
    assert result["map"] == pytest.approx(88.75)
    assert result["n_queries"] == 2


def test_summarise_empty_raises():
    with pytest.raises(ValueError):
        summarise([])
