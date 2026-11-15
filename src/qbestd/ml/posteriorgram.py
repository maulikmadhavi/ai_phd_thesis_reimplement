"""Gaussian posteriorgram: per-frame component posteriors of a GMM.

Thesis (``ExpSetup.tex`` lines 229-237): the representation of frame o_t is
the vector ``P(C_k | o_t) = pi_k N(o_t; mu_k, Sigma_k) / sum_j pi_j N(...)``.
Stage 5 compares posteriorgrams with a (symmetric) KL distance, which needs
strictly positive entries; Stage 4 VTLN picks the warp factor that maximises
:func:`utterance_log_likelihood`.
"""

import numpy as np

from qbestd.ml.gmm import component_posteriors, frame_log_likelihoods

DEFAULT_FLOOR = 1e-10


def gaussian_posteriorgram(gmm, features):
    """(T, K) posteriors of every frame; rows sum to 1."""
    return component_posteriors(gmm, features)


def floor_and_renormalise(posteriorgram, floor=DEFAULT_FLOOR):
    """Clip entries at ``floor`` and renormalise each row to sum to 1.

    Raises:
        ValueError: if ``floor`` is not in (0, 1 / K].
    """
    posteriorgram = np.asarray(posteriorgram, dtype="float64")
    if posteriorgram.ndim != 2:
        raise ValueError("posteriorgram must be a (T, K) array")
    if not 0 < floor <= 1.0 / posteriorgram.shape[1]:
        raise ValueError(f"floor must be in (0, 1/K], got {floor}")
    floored = np.maximum(posteriorgram, floor)
    return floored / floored.sum(axis=1, keepdims=True)


def utterance_log_likelihood(gmm, features):
    """Mean frame log-likelihood of an utterance under ``gmm``.

    Finite for any finite input (computed with log-sum-exp); an empty
    utterance returns ``nan``.
    """
    if len(features) == 0:
        return float("nan")
    return float(frame_log_likelihoods(gmm, features).mean())
