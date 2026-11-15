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

    Raises:
        ValueError: for fewer than two distances, non-finite values or a
            zero standard deviation.
    """
    values = np.asarray(distances, dtype="float64")
    if values.ndim != 1 or len(values) < 2:
        raise ValueError("need at least two distances to normalise")
    if not np.all(np.isfinite(values)):
        raise ValueError("distances must be finite")
    spread = values.std(ddof=1)
    if spread == 0.0:
        raise ValueError("all distances are equal; cannot normalise")
    return -(values - values.mean()) / spread


def rank_documents(distances):
    """Document indices ordered from smallest to largest distance.

    The sort is stable: equal distances keep their original order.
    """
    return np.argsort(np.asarray(distances, dtype="float64"), kind="stable")
