import numpy as np
import pytest

from qbestd.ml.gmm import DiagonalGmm, frame_log_likelihoods
from qbestd.ml.vtln import WARP_FACTORS
from qbestd.ml.vtln_checks import (
    bootstrap_interval,
    c0_offset,
    compare_alphas,
    drop_dimension,
    order_ratio,
    partial_spearman,
    percentile_summary,
    spearman,
)


def gmm3():
    rng = np.random.default_rng(0)
    return DiagonalGmm(np.array([0.3, 0.7]), rng.normal(size=(2, 3)),
                       rng.uniform(0.5, 2.0, size=(2, 3)))


def test_dropping_a_dimension_is_the_marginal_of_a_diagonal_gmm():
    gmm = gmm3()
    marginal = drop_dimension(gmm, 0)
    assert marginal.means.shape == (2, 2)
    assert np.array_equal(marginal.weights, gmm.weights)
    grid = np.linspace(-15, 15, 6001)
    step = grid[1] - grid[0]
    rest = np.random.default_rng(1).normal(size=(4, 2))
    for point in rest:
        frames = np.column_stack([grid, np.tile(point, (len(grid), 1))])
        integral = np.exp(frame_log_likelihoods(gmm, frames)).sum() * step
        direct = np.exp(frame_log_likelihoods(marginal, point[None, :]))[0]
        assert integral == pytest.approx(direct, rel=1e-4)


def test_dropping_a_dimension_validates():
    with pytest.raises(ValueError):
        drop_dimension(gmm3(), 3)
    one = DiagonalGmm(np.array([1.0]), np.zeros((1, 1)), np.ones((1, 1)))
    with pytest.raises(ValueError):
        drop_dimension(one, 0)


def test_compare_alphas_reports_share_changed_and_both_versions():
    warps = (0.9, 1.0, 1.1)
    out = compare_alphas([0.9, 1.0, 1.1, 1.0], [0.9, 1.1, 1.1, 1.0], warps)
    assert out["share_changed"] == 0.25 and out["n_utterances"] == 4
    assert out["full"]["histogram"] == {"1.10": 1, "1.00": 2, "0.90": 1}
    assert out["marginal"]["mean_alpha_thesis"] == pytest.approx(
        np.mean([1.1, 0.9, 0.9, 1.0]))
    with pytest.raises(ValueError):
        compare_alphas([1.0], [1.0, 1.0], warps)
    assert len(compare_alphas([1.0], [1.0])["full"]["histogram"]) == len(
        WARP_FACTORS)


def test_spearman_and_partial_spearman():
    rng = np.random.default_rng(0)
    z = rng.normal(size=500)
    x, y = z + 0.3 * rng.normal(size=500), z + 0.3 * rng.normal(size=500)
    assert spearman(x, x ** 3) == pytest.approx(1.0)
    assert spearman(x, -x) == pytest.approx(-1.0)
    assert np.isnan(spearman(x, np.ones(500)))
    assert spearman(x, y) > 0.8  # linked through z
    assert abs(partial_spearman(x, y, z)) < 0.15  # z explains the link
    assert partial_spearman(x, y, rng.normal(size=500)) > 0.8


def test_bootstrap_interval_brackets_the_estimate_and_is_seeded():
    rng = np.random.default_rng(1)
    x = rng.normal(size=300)
    y = x + rng.normal(size=300)
    first = bootstrap_interval(spearman, [x, y], n_boot=300, seed=2)
    again = bootstrap_interval(spearman, [x, y], n_boot=300, seed=2)
    assert first == again
    estimate, low, high = first
    assert low < estimate < high


def test_order_ratio_and_c0_offset():
    wave = np.array([1.0, -1.0, 1.0, -1.0])
    assert order_ratio(wave) == pytest.approx(1.0)
    shifted = wave + 0.5  # mean 0.5; peak 1.5; max|x - m| = 1.0
    assert order_ratio(shifted) == pytest.approx(1.0 / 1.5)
    assert np.isnan(order_ratio(np.zeros(5)))
    assert c0_offset(1.0) == 0.0
    assert c0_offset(0.5) == pytest.approx(np.sqrt(40) * 2 * np.log(2))
    assert c0_offset(2.0) == pytest.approx(8.77, abs=0.01)  # plan: g = 2


def test_percentile_summary_gate_and_excluded_values():
    values = np.concatenate([np.full(99, 0.01), [5.0], [np.nan]])
    out = percentile_summary(values, gate=0.1)
    assert out["n"] == 100 and out["n_excluded"] == 1
    assert out["max"] == 5.0 and out["p99"] == pytest.approx(
        np.percentile(values[:100], 99))
    assert out["gate_met"] is True
    assert percentile_summary(np.full(5, 0.5))["gate_met"] is False
    assert percentile_summary(np.full(10, 0.01))["gate_met"] is True
    with pytest.raises(ValueError):
        percentile_summary([np.nan])
