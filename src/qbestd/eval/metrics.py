"""Ranked-retrieval metrics: p@N and average precision (AP).

Thesis (``survey.tex`` lines 40-50 and 65): for a query with ``N`` relevant
documents, p@N is the number of relevant documents among the top ``N``
returned, divided by ``N`` (reported in percent), and
``AP = (1/N) * sum_k p@k * rel(k)``, where ``p@k`` is the precision of the
top ``k`` and ``rel(k)`` is 1 when the document at rank ``k`` is relevant.
MAP is the mean AP over queries. Worked check from the plan: the ranking
``t t f f t f f t f f`` with ``N = 4`` gives p@N = 50 % and AP = 0.775.

Units: :func:`precision_at_n` returns percent, :func:`average_precision`
returns a fraction in [0, 1]; :func:`summarise` reports MAP in percent so it
is comparable with the thesis tables.
"""

import numpy as np


def _check(ranked_is_relevant, n_relevant):
    if n_relevant < 1:
        raise ValueError("a query needs at least one relevant document")
    flags = np.asarray(ranked_is_relevant, dtype=bool)
    if flags.ndim != 1:
        raise ValueError("ranked_is_relevant must be one-dimensional")
    if int(flags.sum()) > n_relevant:
        raise ValueError("more relevant documents ranked than n_relevant")
    return flags


def precision_at_n(ranked_is_relevant, n_relevant):
    """Percent of the top ``n_relevant`` ranked documents that are relevant.

    Raises:
        ValueError: if ``n_relevant < 1`` or the flags are inconsistent.
    """
    flags = _check(ranked_is_relevant, n_relevant)
    return 100.0 * float(flags[:n_relevant].sum()) / n_relevant


def average_precision(ranked_is_relevant, n_relevant):
    """Average precision as a fraction in [0, 1], normalised by ``n_relevant``.

    A relevant document missing from the ranking counts as precision 0, so
    the normalisation is always by ``n_relevant``.

    Raises:
        ValueError: if ``n_relevant < 1`` or the flags are inconsistent.
    """
    flags = _check(ranked_is_relevant, n_relevant)
    hits = np.cumsum(flags)
    ranks = np.arange(1, len(flags) + 1)
    return float(np.sum(hits[flags] / ranks[flags])) / n_relevant


def summarise(per_query):
    """Average ``(p_at_n_percent, ap_fraction)`` pairs over queries.

    Returns:
        ``{"p_at_n": mean percent, "map": mean AP in percent, "n_queries"}``.

    Raises:
        ValueError: if ``per_query`` is empty.
    """
    pairs = np.asarray(list(per_query), dtype="float64")
    if pairs.size == 0:
        raise ValueError("no queries to summarise")
    return {"p_at_n": float(pairs[:, 0].mean()),
            "map": float(100.0 * pairs[:, 1].mean()),
            "n_queries": int(len(pairs))}
