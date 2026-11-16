"""GMM-based VTLN: warp factor estimation (Stage 4, V1).

Thesis (``Representation.tex`` lines 100-138, Algorithm
``pseudocode_vtlnwarping`` lines 140-171): for every utterance the warp
factor ``alpha`` is the one whose warped features give the highest
likelihood under the current GMM. The warps are the 13 values 0.88, 0.90,
..., 1.12 (:data:`WARP_FACTORS`).

Likelihood is summed over frames. The frame count of an utterance does not
depend on ``alpha`` (warping only changes the filterbank), so the sum and
the mean give the same argmax.
"""

import numpy as np

from qbestd.features.scales import VTLN_WARP_FACTORS
from qbestd.ml.gmm import frame_log_likelihoods

WARP_FACTORS = VTLN_WARP_FACTORS
IDENTITY_WARP = 1.0


def utterance_log_likelihoods(features, offsets, gmm):
    """Summed frame log-likelihood of every utterance, shape ``(n_utt,)``.

    Args:
        features: ``(n_frames, dim)`` frames of all utterances in a row.
        offsets: ``(n_utt + 1,)`` frame offsets, ``offsets[0] == 0`` and
            ``offsets[-1] == n_frames`` (the cache layout). Empty utterances
            are allowed and give 0.
        gmm: a ``DiagonalGmm``.

    Raises:
        ValueError: for offsets that are not non-decreasing, do not start at
            0 or do not end at ``len(features)``.
    """
    offsets = np.asarray(offsets, dtype="int64")
    if (offsets.ndim != 1 or offsets.size < 1 or offsets[0] != 0
            or offsets[-1] != len(features)
            or np.any(np.diff(offsets) < 0)):
        raise ValueError("offsets must be non-decreasing, start at 0 and "
                         "end at the number of frames")
    frame_ll = frame_log_likelihoods(gmm, features)
    running = np.concatenate([[0.0], np.cumsum(frame_ll)])
    return running[offsets[1:]] - running[offsets[:-1]]


def _tie_priority(warps):
    """Column order in which ties are resolved: the warp closest to 1.0
    first, then the smaller warp."""
    warps = np.asarray(warps, dtype="float64")
    distance = np.round(np.abs(warps - IDENTITY_WARP), 9)
    return np.lexsort((warps, distance))


def estimate_warp_factors(ll_matrix, warps=WARP_FACTORS):
    """Warp factor with the highest log-likelihood, per utterance.

    Args:
        ll_matrix: ``(n_utt, n_warps)`` log-likelihoods, one column per
            entry of ``warps``.
        warps: the warp factor of every column.

    Returns:
        ``(n_utt,)`` array of warp factors. A tie goes to the warp closest
        to 1.0, then to the smaller one.

    Raises:
        ValueError: if the shape does not match ``warps`` or a value is not
            finite.
    """
    ll_matrix = np.asarray(ll_matrix, dtype="float64")
    warps = np.asarray(warps, dtype="float64")
    if ll_matrix.ndim != 2 or ll_matrix.shape[1] != len(warps):
        raise ValueError(f"ll_matrix must be (n_utt, {len(warps)}), got "
                         f"{ll_matrix.shape}")
    if not np.all(np.isfinite(ll_matrix)):
        raise ValueError("ll_matrix must be finite")
    order = _tie_priority(warps)
    best = np.argmax(ll_matrix[:, order], axis=1)  # first max in priority
    return warps[order[best]]
