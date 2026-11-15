"""Subsequence DTW with the thesis local constraint LC2.

Reference kernel: ``research_qbestd/matlab/NSDTW_c_skel.cpp`` (NOT
``Fx_do_SDTW.m``, which is segmental DTW). ``D`` has one row per test frame
(M) and one column per query frame (N); the path may start at any test frame.

* First column (n = 0): ``S = D``, ``T = 1``, start ``P = m``.
* First two test rows (m = 0, 1): accumulate along n,
  ``S(m, n) = S(m, n-1) + D(m, n)``, ``T = n + 1``, ``P = m``.
* Otherwise the predecessors are ``(m, n-1)``, ``(m-1, n-1)`` and
  ``(m-2, n-1)``; ``S = D + S_pred`` of the cheapest, ``T = T_pred + 1`` and
  ``P = P_pred``. Ties go to ``(m, n-1)`` first, then ``(m-1, n-1)``, then
  ``(m-2, n-1)`` (``min_fun_ind`` in the C++).

Selection compares the un-normalised sums ``D + S_pred`` exactly as the C++
does. Every predecessor lies in column n-1, so a whole column is computed at
once, vectorised over m. ``P`` is 0-based here (the C++ stores m + 1).

The C++ takes the end frame with the smallest ``S`` in the last column and
reports ``S/T`` there. The thesis (``ExpSetup.tex`` line 442) reports
``S(i, N)/T(i, N)``; the path-validity interval below is the plan's reading
of the thesis (open question 23) and the choice of ``min S/T`` over valid end
frames is likewise a documented assumption, not the C++ behaviour.
"""

import numpy as np


def subdtw_lc2(local_distance):
    """Accumulate ``D`` with LC2; returns ``(S, T, P)``, each (M, N).

    ``S`` is the accumulated cost of the best path ending at ``(m, n)``,
    ``T`` its length in steps (query frames consumed) and ``P`` the 0-based
    test frame where that path started.

    Raises:
        ValueError: if ``local_distance`` is not a non-empty 2-D array.
    """
    distance = np.asarray(local_distance, dtype="float64")
    if distance.ndim != 2 or distance.size == 0:
        raise ValueError("local distance must be a non-empty (M, N) array")
    rows, cols = distance.shape
    accumulated = np.empty_like(distance)
    length = np.empty_like(distance)
    start = np.empty(distance.shape, dtype=np.int64)
    accumulated[:, 0] = distance[:, 0]
    length[:, 0] = 1.0
    start[:, 0] = np.arange(rows)
    for n in range(1, cols):
        _advance_column(distance, accumulated, length, start, n)
    return accumulated, length, start


def _advance_column(distance, accumulated, length, start, n):
    """Fill column ``n`` from column ``n - 1`` (all rows at once)."""
    rows = distance.shape[0]
    column = distance[:, n]
    previous = accumulated[:, n - 1]
    # Rows 0 and 1: accumulate along the query axis only.
    top = min(rows, 2)
    accumulated[:top, n] = previous[:top] + column[:top]
    length[:top, n] = n + 1
    start[:top, n] = np.arange(top)
    if rows < 3:
        return
    horizontal = column[2:] + previous[2:]
    diagonal = column[2:] + previous[1:-1]
    skip = column[2:] + previous[:-2]
    # Tie order: horizontal, then diagonal, then skip.
    use_h = (horizontal <= skip) & (horizontal <= diagonal)
    use_d = ~use_h & (diagonal <= skip) & (diagonal <= horizontal)
    source = np.arange(2, rows) - np.where(use_h, 0, np.where(use_d, 1, 2))
    accumulated[2:, n] = np.where(use_h, horizontal,
                                  np.where(use_d, diagonal, skip))
    length[2:, n] = length[source, n - 1] + 1
    start[2:, n] = start[source, n - 1]


def best_utterance_distance(accumulated, length, start, min_ratio=0.5,
                            max_ratio=2.0):
    """Utterance distance: the minimum ``S/T`` over valid end frames.

    An end frame ``i`` of the last query column is valid when the matched
    test interval ``i - P + 1`` is between ``min_ratio`` and ``max_ratio``
    times the query length N.

    Returns:
        ``(distance, start_frame, end_frame, used_fallback)``. If no end
        frame is valid the minimum over all of them is used and
        ``used_fallback`` is True.
    """
    cols = accumulated.shape[1]
    ends = np.arange(accumulated.shape[0])
    normalised = accumulated[:, -1] / length[:, -1]
    ratio = (ends - start[:, -1] + 1) / cols
    valid = (ratio >= min_ratio) & (ratio <= max_ratio)
    used_fallback = not valid.any()
    candidates = normalised if used_fallback else np.where(valid, normalised,
                                                           np.inf)
    end = int(np.argmin(candidates))
    return (float(normalised[end]), int(start[end, -1]), end, used_fallback)


def backtrace_path(local_distance, accumulated, end_frame):
    """Best path ending at test frame ``end_frame`` in the last column.

    Re-derives each predecessor with the kernel's rules and tie order, so it
    agrees with :func:`subdtw_lc2`. Returns a list of ``(test_frame,
    query_frame)`` pairs from query frame 0 to N - 1 (used by the demo).
    """
    distance = np.asarray(local_distance, dtype="float64")
    path = [(int(end_frame), distance.shape[1] - 1)]
    m = int(end_frame)
    for n in range(distance.shape[1] - 1, 0, -1):
        if m >= 2:
            here = distance[m, n]
            horizontal = here + accumulated[m, n - 1]
            diagonal = here + accumulated[m - 1, n - 1]
            skip = here + accumulated[m - 2, n - 1]
            if horizontal <= skip and horizontal <= diagonal:
                step = 0
            elif diagonal <= skip and diagonal <= horizontal:
                step = 1
            else:
                step = 2
            m -= step
        path.append((m, n - 1))
    return path[::-1]
