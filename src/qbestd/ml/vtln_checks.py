"""Score-free checks of the Stage 4 warp factors (cycle 9, S1).

Pure functions; the runner is ``qbestd.eval.s1_checks``. Nothing here
touches retrieval:

* (a) alpha-hat with the static c0 dimension marginalised out of a diagonal
  GMM (:func:`drop_dimension`, :func:`compare_alphas`);
* (b) rank correlations of alpha-hat with F0, within F0 groups, and the
  partial correlation with the utterance mean c0 (:func:`spearman`,
  :func:`partial_spearman`, :func:`bootstrap_interval`);
* (c) the size of the waveform-order approximation (:func:`order_ratio`,
  :func:`c0_offset`, :func:`percentile_summary`).
"""

import numpy as np
from scipy.stats import rankdata

from qbestd.ml.gmm import DiagonalGmm
from qbestd.ml.vtln import (
    WARP_FACTORS,
    edge_shares,
    to_thesis_label,
    warp_histogram,
)

N_FILTERS = 40  # the htk_described filterbank (c0 offset in (c))


def drop_dimension(gmm, dim=0):
    """The GMM marginalised over feature ``dim``: for a diagonal covariance
    that is the same GMM without that column (the weights stay).

    Raises:
        ValueError: if ``dim`` is out of range or it is the only dimension.
    """
    if gmm.means.shape[1] < 2 or not 0 <= dim < gmm.means.shape[1]:
        raise ValueError("dim must index one of at least two dimensions")
    return DiagonalGmm(gmm.weights, np.delete(gmm.means, dim, axis=1),
                       np.delete(gmm.variances, dim, axis=1))


def compare_alphas(full, marginal, warps=WARP_FACTORS):
    """How alpha-hat moves when a dimension is dropped.

    Args:
        full, marginal: alpha-hat (our label) per utterance, aligned.

    Returns:
        A dict with the share of utterances whose alpha-hat differs, and the
        histogram, edge shares and mean (thesis label) of each version.
    """
    full, marginal = np.asarray(full), np.asarray(marginal)
    if full.shape != marginal.shape or full.ndim != 1:
        raise ValueError("alpha vectors must be 1-D and aligned")
    return {
        "n_utterances": int(len(full)),
        "share_changed": float(np.mean(full != marginal)),
        "full": {"histogram": warp_histogram(full, warps),
                 "edge_shares": edge_shares(full, warps),
                 "mean_alpha_thesis": float(np.mean(to_thesis_label(full)))},
        "marginal": {
            "histogram": warp_histogram(marginal, warps),
            "edge_shares": edge_shares(marginal, warps),
            "mean_alpha_thesis": float(np.mean(to_thesis_label(marginal)))}}


def spearman(x, y):
    """Spearman correlation (ranks, average for ties); ``nan`` if a side is
    constant."""
    rx, ry = rankdata(x), rankdata(y)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def _residual(y, x):
    """Residual of ``y`` after a least-squares line on ``x`` (with
    intercept)."""
    design = np.column_stack([np.ones(len(x)), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    return y - design @ coefficients


def partial_spearman(x, y, control):
    """Spearman partial correlation of ``x`` and ``y`` given ``control``:
    Pearson correlation of the residuals of the ranks of ``x`` and ``y`` on
    the ranks of ``control``."""
    rc = rankdata(control).astype("float64")
    ex = _residual(rankdata(x).astype("float64"), rc)
    ey = _residual(rankdata(y).astype("float64"), rc)
    if ex.std() == 0 or ey.std() == 0:
        return float("nan")
    return float(np.corrcoef(ex, ey)[0, 1])


def bootstrap_interval(statistic, arrays, n_boot=10000, seed=0):
    """95 % percentile interval of ``statistic(*arrays)`` over utterances
    resampled with replacement (anti-conservative without speaker IDs).

    Returns:
        ``(estimate, low, high)``.
    """
    arrays = [np.asarray(a) for a in arrays]
    rng = np.random.default_rng(seed)
    n = len(arrays[0])
    draws = []
    for _ in range(n_boot):
        pick = rng.integers(0, n, n)
        draws.append(statistic(*[a[pick] for a in arrays]))
    low, high = np.nanpercentile(draws, [2.5, 97.5])
    return float(statistic(*arrays)), float(low), float(high)


def order_ratio(samples):
    """``max|x - m| / max|x|`` of one waveform (``m`` its mean); ``nan`` for
    a silent one."""
    samples = np.asarray(samples, dtype="float64")
    peak = np.max(np.abs(samples)) if len(samples) else 0.0
    if peak == 0:
        return float("nan")
    return float(np.max(np.abs(samples - samples.mean())) / peak)


def c0_offset(ratio, n_filters=N_FILTERS):
    """MFCC c0 offset implied by a per-utterance gain ``ratio``:
    ``sqrt(n_filters) * 2 * |ln ratio|`` (a gain g adds ``2 ln g`` to each
    log channel, and the orthonormal DCT puts ``sqrt(n)`` times it in c0)."""
    return float(np.sqrt(n_filters) * 2.0 * np.abs(np.log(ratio)))


def percentile_summary(values, gate=0.1, percentile=99):
    """Min, median, the ``percentile``-th percentile and max, and whether
    the percentile is at most ``gate`` (``nan`` values are left out and
    counted)."""
    values = np.asarray(values, dtype="float64")
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        raise ValueError("no finite values")
    top = float(np.percentile(finite, percentile))
    return {"n": int(len(finite)),
            "n_excluded": int(len(values) - len(finite)),
            "min": float(finite.min()), "median": float(np.median(finite)),
            f"p{percentile}": top, "max": float(finite.max()),
            "gate": gate, "gate_met": bool(top <= gate)}
