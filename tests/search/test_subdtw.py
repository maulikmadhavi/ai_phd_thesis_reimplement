import numpy as np
import pytest

from qbestd.search.distance import symmetric_kl_matrix
from qbestd.search.subdtw import (
    backtrace_path,
    best_utterance_distance,
    subdtw_lc2,
)


def cpp_transcription(D):
    """Plain loops following NSDTW_c_skel.cpp (0-based P)."""
    M, N = D.shape
    S = np.zeros((M, N))
    T = np.zeros((M, N))
    P = np.zeros((M, N), dtype=int)
    for m in range(M):
        P[m, 0], S[m, 0], T[m, 0] = m, D[m, 0], 1
    for m in range(min(M, 2)):
        for n in range(1, N):
            P[m, n], S[m, n], T[m, n] = m, S[m, n - 1] + D[m, n], n + 1
    for m in range(2, M):
        for n in range(1, N):
            e1 = D[m, n] + S[m - 2, n - 1]
            d1 = D[m, n] + S[m - 1, n - 1]
            s1 = D[m, n] + S[m, n - 1]
            if s1 <= e1 and s1 <= d1:      # min_fun_ind: z first
                src, S[m, n] = m, s1
            elif d1 <= e1 and d1 <= s1:    # then y
                src, S[m, n] = m - 1, d1
            else:                          # then x
                src, S[m, n] = m - 2, e1
            T[m, n] = T[src, n - 1] + 1
            P[m, n] = P[src, n - 1]
    return S, T, P


@pytest.mark.parametrize("seed", range(20))
def test_matches_cpp_transcription_on_random_matrices(seed):
    rng = np.random.default_rng(seed)
    shape = (int(rng.integers(3, 40)), int(rng.integers(1, 15)))
    if seed % 2:
        D = rng.integers(0, 3, size=shape).astype(float)  # tie-heavy
    else:
        D = rng.random(shape)
    expected = cpp_transcription(D)
    for got, want in zip(subdtw_lc2(D), expected):
        assert np.array_equal(got, want)


def test_tie_order_prefers_horizontal_then_diagonal():
    D = np.zeros((4, 3))
    S, T, P = subdtw_lc2(D)
    # all predecessors tie: horizontal wins, so the path stays on its row
    assert np.array_equal(P[:, 2], np.arange(4))
    assert np.array_equal(T[:, 2], np.full(4, 3.0))
    # make the diagonal strictly cheaper than horizontal and skip
    D = np.ones((4, 2))
    D[1, 0] = 0.0
    S, T, P = subdtw_lc2(D)
    assert P[2, 1] == 1  # came from (1, 0) by the diagonal move


def test_first_two_rows_only_accumulate_along_query():
    D = np.arange(12, dtype=float).reshape(3, 4)
    S, T, P = subdtw_lc2(D)
    assert np.allclose(S[0], np.cumsum(D[0]))
    assert np.allclose(S[1], np.cumsum(D[1]))
    assert np.array_equal(T[0], [1, 2, 3, 4])
    assert np.array_equal(P[1], [1, 1, 1, 1])


def test_edge_cases_few_test_frames_and_single_query_frame():
    for rows in (1, 2):
        D = np.random.default_rng(0).random((rows, 5))
        S, T, P = subdtw_lc2(D)
        assert np.allclose(S, np.cumsum(D, axis=1))
    D = np.random.default_rng(1).random((6, 1))
    S, T, P = subdtw_lc2(D)
    assert np.array_equal(S, D) and np.all(T == 1)
    assert np.array_equal(P[:, 0], np.arange(6))


def test_empty_or_one_dimensional_input_raises():
    for bad in (np.zeros(5), np.zeros((0, 3)), np.zeros((3, 0))):
        with pytest.raises(ValueError):
            subdtw_lc2(bad)


def planted_case(seed=0, k=6, query_len=12, before=15, after=20):
    rng = np.random.default_rng(seed)

    def peaked(rows):
        raw = rng.gamma(0.3, size=(rows, k)) + 1e-3
        return raw / raw.sum(axis=1, keepdims=True)

    query = peaked(query_len)
    document = np.concatenate([peaked(before), query, peaked(after)])
    return query, document, before, before + query_len - 1


def test_planted_query_is_found_at_the_right_place():
    query, document, first, last = planted_case()
    D = symmetric_kl_matrix(document, query)
    S, T, P = subdtw_lc2(D)
    distance, start, end, nonmatch = best_utterance_distance(S, T, P)
    assert (start, end) == (first, last)
    assert distance == pytest.approx(0.0, abs=1e-9)
    assert not nonmatch


def last_column(costs, starts, cols=4):
    """(S, T, P) whose last column holds ``costs`` and ``starts``."""
    S = np.zeros((len(costs), cols))
    S[:, -1] = costs
    P = np.zeros((len(costs), cols), dtype=int)
    P[:, -1] = starts
    return S, np.ones_like(S), P


def test_validity_uses_the_zero_based_displacement_without_plus_one():
    # N = 4, so wr = (end - P) / 4. Displacements 1, 2, 3, 4, 8, 9.
    S, T, P = last_column([1.0, 9.0, 9.0, 8.0, 4.0, 3.0], [0] * 6)
    P[:, -1] = [0, 0, 0, 0, -4, -4]
    ends = np.arange(6)
    wr = (ends - P[:, -1]) / 4
    assert wr.tolist() == [0.0, 0.25, 0.5, 0.75, 2.0, 2.25]
    dist, start, end, nonmatch = best_utterance_distance(S, T, P)
    # valid ends are 2, 3, 4 (wr 0.5, 0.75, 2.0); the cheapest is end 4
    assert (dist, start, end, nonmatch) == (4.0, -4, 4, False)


@pytest.mark.parametrize("displacement, valid", [
    (1, False), (2, True), (3, True), (8, True), (9, False)])
def test_wr_bounds_are_inclusive_at_half_and_double(displacement, valid):
    # N = 4: wr = displacement / 4, so 2 -> 0.5 and 8 -> 2.0 exactly.
    S, T, P = last_column([5.0], [0])
    P[0, -1] = -displacement  # end 0, so end - P = displacement
    dist, _, _, nonmatch = best_utterance_distance(S, T, P)
    assert nonmatch is (not valid)
    assert (dist == 5.0) if valid else (dist == float("inf"))


def test_no_valid_end_frame_is_a_nonmatch_not_an_error():
    S = np.array([[5.0, 6.0], [4.0, 3.0]])
    T = np.ones((2, 2))
    P = np.array([[0, 0], [1, 1]])  # displacement 0 < 0.5 * N everywhere
    result = best_utterance_distance(S, T, P)
    assert result == (float("inf"), -1, -1, True)


def test_document_shorter_than_half_the_query_is_a_nonmatch():
    rng = np.random.default_rng(0)
    D = rng.random((3, 20))  # 3 test frames, N = 20, needs wr >= 0.5
    S, T, P = subdtw_lc2(D)
    assert best_utterance_distance(S, T, P)[3] is True


def test_normalisation_by_path_length_is_used():
    S = np.array([[4.0], [6.0]])
    T = np.array([[2.0], [6.0]])
    P = np.array([[0], [1]])
    dist, _, end, _ = best_utterance_distance(S, T, P, 0.0, 2.0)
    assert (dist, end) == (1.0, 1)


@pytest.mark.parametrize("seed", range(5))
def test_backtrace_is_consistent_with_the_accumulation(seed):
    rng = np.random.default_rng(seed)
    D = rng.integers(0, 4, size=(25, 6)).astype(float)  # tie-heavy
    S, T, P = subdtw_lc2(D)
    for end in (5, 12, 24):
        path = backtrace_path(D, S, end)
        assert [n for _, n in path] == list(range(6))
        assert path[-1] == (end, 5)
        assert path[0][0] == P[end, 5]
        steps = np.diff([m for m, _ in path])
        assert set(steps) <= {0, 1, 2}
        assert sum(D[m, n] for m, n in path) == pytest.approx(S[end, 5])
        assert len(path) == T[end, 5]
