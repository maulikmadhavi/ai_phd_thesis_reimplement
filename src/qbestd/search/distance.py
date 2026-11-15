"""Symmetric KL local distance between posteriorgram frames.

Thesis (``ExpSetup.tex`` line 304): the local distance of a test frame ``t``
and a query frame ``q`` is ``sum_k t_k log(t_k / q_k) + sum_k q_k log(q_k /
t_k)``. Each term ``(t_k - q_k) log(t_k / q_k)`` is non-negative, so the
distance is non-negative for any positive vectors, normalised or not.

Zeros would give infinities, so entries are clipped at ``floor`` first. The
caller normally passes rows already floored and renormalised with
``qbestd.ml.posteriorgram.floor_and_renormalise``; clipping here is only a
guard and does not renormalise.
"""

import numpy as np

DEFAULT_FLOOR = 1e-10


def _clipped(posteriorgram, floor):
    array = np.asarray(posteriorgram, dtype="float64")
    if array.ndim != 2:
        raise ValueError("posteriorgram must be a (frames, K) array")
    if floor <= 0:
        raise ValueError("floor must be positive")
    return np.maximum(array, floor)


def symmetric_kl_matrix(test_post, query_post, floor=DEFAULT_FLOOR):
    """Local distance matrix ``D`` of shape (M test frames, N query frames).

    Computed as
    ``sum(t log t) - t @ log(q).T + sum(q log q) - log(t) @ q.T``
    with two matrix products instead of a double loop over frames.

    Raises:
        ValueError: if the inputs are not 2-D with the same number of
            components, or ``floor`` is not positive.
    """
    test = _clipped(test_post, floor)
    query = _clipped(query_post, floor)
    if test.shape[1] != query.shape[1]:
        raise ValueError(
            f"component counts differ: {test.shape[1]} vs {query.shape[1]}")
    log_test, log_query = np.log(test), np.log(query)
    self_test = np.sum(test * log_test, axis=1)
    self_query = np.sum(query * log_query, axis=1)
    cross = test @ log_query.T + log_test @ query.T
    distance = self_test[:, None] + self_query[None, :] - cross
    return np.maximum(distance, 0.0)  # rounding can give -1e-16
