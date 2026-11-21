import numpy as np
import pytest

from qbestd.eval.c0_null import c0_rank, edge_margins, share_changed
from qbestd.ml.vtln import WARP_FACTORS


def test_share_changed_tolerates_float_labels():
    alpha = np.array([0.88, 1.0, 1.12])
    assert share_changed(alpha, [0.8800000001, 1.0, 1.02]) == pytest.approx(
        1 / 3)


def test_share_changed_needs_aligned_vectors():
    with pytest.raises(ValueError):
        share_changed([1.0, 1.0], [1.0])


def test_edge_margins_take_the_edge_against_its_inward_neighbour():
    n = len(WARP_FACTORS)
    ll = np.zeros((4, n))
    col = {round(w, 2): i for i, w in enumerate(WARP_FACTORS)}
    # two utterances at our 0.88 edge (thesis 1.12), two at our 1.12
    alpha = np.array([0.88, 0.88, 1.12, 1.12])
    ll[0, col[0.88]], ll[0, col[0.90]] = 5.0, 3.0   # margin 2
    ll[1, col[0.88]], ll[1, col[0.90]] = 4.0, 3.5   # margin 0.5
    ll[2, col[1.12]], ll[2, col[1.10]] = 9.0, 7.0   # margin 2
    ll[3, col[1.12]], ll[3, col[1.10]] = 1.0, 1.0   # margin 0
    margins = edge_margins(ll, alpha)
    assert margins["1.12"]["n"] == 2
    assert margins["1.12"]["median"] == pytest.approx(1.25)
    assert margins["0.88"]["median"] == pytest.approx(1.0)


def test_edge_margins_report_an_empty_edge_without_error():
    ll = np.zeros((2, len(WARP_FACTORS)))
    margins = edge_margins(ll, np.array([1.0, 1.0]))
    assert margins["1.12"] == {"n": 0}


@pytest.mark.parametrize("shares, rank", [
    ([0.2, 0.1, 0.05], 1),        # c0 largest
    ([0.1, 0.2, 0.05], 2),        # one column above c0
    ([0.0, 0.0, 0.0], 1),         # ties do not count as above
])
def test_c0_rank_counts_columns_above_c0(shares, rank):
    assert c0_rank(shares) == rank
