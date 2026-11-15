"""Score normalisation and ranking of documents for one query.

Thesis (``ExpSetup.tex`` lines 497-515): per query, the distances of all
documents are z-normalised and negated, ``s = -(d - mu_q) / sigma_q``, with
the sample standard deviation (``ddof = 1``). A higher score means a better
match. The transform is monotonic within a query, so it does not change
p@N or MAP on one query; it matters once scores of different queries are
pooled (SWS, QUESST).
"""

import numpy as np


def znorm_scores(distances):
    """``-(d - mean) / std`` with the sample standard deviation (ddof = 1).

    The mean and standard deviation use the finite distances only. A
    ``+inf`` distance (a non-match) gets the score ``-inf``.

    Raises:
        ValueError: for NaN, ``-inf``, fewer than two finite distances or a
            zero standard deviation.
    """
    values = np.asarray(distances, dtype="float64")
    if values.ndim != 1:
        raise ValueError("distances must be one-dimensional")
    if np.isnan(values).any() or np.isneginf(values).any():
        raise ValueError("distances must not be NaN or -inf")
    finite = np.isfinite(values)
    if finite.sum() < 2:
        raise ValueError("need at least two finite distances to normalise")
    spread = values[finite].std(ddof=1)
    if spread == 0.0:
        raise ValueError("all distances are equal; cannot normalise")
    scores = np.full(values.shape, -np.inf)
    scores[finite] = -(values[finite] - values[finite].mean()) / spread
    return scores


def rank_documents(distances):
    """Document indices ordered from smallest to largest distance.

    The sort is stable: equal distances keep their original order, and
    ``+inf`` (non-match) distances come last in document order.
    """
    return np.argsort(np.asarray(distances, dtype="float64"), kind="stable")
