"""Diagonal-covariance Gaussian mixture model trained by EM.

Thesis (``ExpSetup.tex`` lines 229-238): the posterior of component k given
frame o_t is ``P(C_k|o_t) = pi_k N(o_t; mu_k, Sigma_k) / sum_j pi_j N(...)``;
the parameters are estimated by EM, initialised from an LBG VQ codebook, for
10 iterations (``Representation.tex`` lines 196 and 1089).

Assumptions (thesis silent; unverified): diagonal covariances, and a variance
floor of ``var_floor_ratio`` (0.01) times the global per-dimension variance
(HTK ``vFloor`` style). Sufficient statistics are accumulated chunk by chunk
so training memory stays bounded.
"""

import json
from dataclasses import dataclass

import numpy as np
from scipy.special import logsumexp

from qbestd.ml.vq import cluster_statistics, lbg_codebook

DEFAULT_CHUNK_FRAMES = 100_000
MIN_COMPONENT_MASS = 1e-8  # components with less soft count keep old values
LOG_2PI = float(np.log(2.0 * np.pi))


@dataclass(frozen=True, eq=False)
class DiagonalGmm:
    """Mixture weights (K,), means (K, D) and variances (K, D)."""

    weights: np.ndarray
    means: np.ndarray
    variances: np.ndarray

    def __post_init__(self):
        weights = np.asarray(self.weights, dtype="float64")
        means = np.asarray(self.means, dtype="float64")
        variances = np.asarray(self.variances, dtype="float64")
        if means.ndim != 2 or variances.shape != means.shape:
            raise ValueError("means and variances must both be (K, D)")
        if weights.shape != (means.shape[0],):
            raise ValueError("weights must have shape (K,)")
        if not (np.all(np.isfinite(weights)) and np.all(np.isfinite(means))
                and np.all(np.isfinite(variances))):
            raise ValueError("GMM parameters must be finite")
        if np.any(weights <= 0) or not np.isclose(weights.sum(), 1.0,
                                                  atol=1e-6):
            raise ValueError("weights must be positive and sum to 1")
        if np.any(variances <= 0):
            raise ValueError("variances must be positive")
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "means", means)
        object.__setattr__(self, "variances", variances)

    @property
    def n_components(self):
        return self.means.shape[0]

    @property
    def dim(self):
        return self.means.shape[1]


def _check_features(gmm, features):
    features = np.asarray(features)
    if features.ndim != 2 or features.shape[1] != gmm.dim:
        raise ValueError(
            f"features must be (T, {gmm.dim}), got {features.shape}")
    return features


def _weighted_log_densities(gmm, chunk):
    """(T, K) matrix of ``log pi_k + log N(x_t; mu_k, diag(var_k))``."""
    chunk = chunk.astype("float64", copy=False)
    inverse = 1.0 / gmm.variances
    quad = ((chunk ** 2) @ inverse.T
            - 2.0 * chunk @ (gmm.means * inverse).T
            + np.sum(gmm.means ** 2 * inverse, axis=1)[None, :])
    constants = (np.log(gmm.weights)
                 - 0.5 * (gmm.dim * LOG_2PI
                          + np.sum(np.log(gmm.variances), axis=1)))
    return constants[None, :] - 0.5 * quad


def frame_log_likelihoods(gmm, features, chunk_frames=DEFAULT_CHUNK_FRAMES):
    """``log sum_k pi_k N(x_t; ...)`` for every frame, shape (T,)."""
    features = _check_features(gmm, features)
    out = np.empty(len(features))
    for start in range(0, len(features), chunk_frames):
        block = _weighted_log_densities(
            gmm, features[start:start + chunk_frames])
        out[start:start + chunk_frames] = logsumexp(block, axis=1)
    return out


def component_posteriors(gmm, features, chunk_frames=DEFAULT_CHUNK_FRAMES):
    """``P(C_k | o_t)`` of shape (T, K); rows sum to 1 (log-sum-exp)."""
    features = _check_features(gmm, features)
    out = np.empty((len(features), gmm.n_components))
    for start in range(0, len(features), chunk_frames):
        block = _weighted_log_densities(
            gmm, features[start:start + chunk_frames])
        block -= logsumexp(block, axis=1, keepdims=True)
        out[start:start + chunk_frames] = np.exp(block)
    return out


def global_variance_floor(features, ratio=0.01):
    """Per-dimension variance floor: ``ratio`` times the global variance."""
    return ratio * np.maximum(np.var(np.asarray(features, "float64"), axis=0),
                              1e-12)


def count_floored(gmm, var_floor):
    """Number of (component, dimension) variances sitting at the floor."""
    return int(np.sum(gmm.variances <= np.asarray(var_floor) * (1 + 1e-9)))


def init_gmm_from_codebook(features, codebook, assignments, var_floor,
                           chunk_frames=DEFAULT_CHUNK_FRAMES):
    """GMM whose components are the clusters of an LBG codebook.

    Weights are the cluster fractions (an empty cluster gets one pseudo
    frame), means are the codebook vectors and variances the cluster
    variances, floored at ``var_floor``.
    """
    codebook = np.asarray(codebook, dtype="float64")
    counts, _, stds, _ = cluster_statistics(features, assignments,
                                            len(codebook), chunk_frames)
    weights = np.maximum(counts, 1.0)
    variances = np.maximum(stds ** 2, np.asarray(var_floor, "float64"))
    return DiagonalGmm(weights / weights.sum(), codebook, variances)


def em_step(gmm, features, var_floor, chunk_frames=DEFAULT_CHUNK_FRAMES):
    """One EM iteration; returns ``(new_gmm, mean log-likelihood of gmm)``.

    The returned likelihood is that of the *input* model, measured in the
    same pass as the E step. Statistics are accumulated per chunk.
    """
    features = _check_features(gmm, features)
    var_floor = np.asarray(var_floor, dtype="float64")
    mass = np.zeros(gmm.n_components)
    first = np.zeros_like(gmm.means)
    second = np.zeros_like(gmm.means)
    total_ll = 0.0
    for start in range(0, len(features), chunk_frames):
        chunk = features[start:start + chunk_frames].astype("float64")
        block = _weighted_log_densities(gmm, chunk)
        norm = logsumexp(block, axis=1, keepdims=True)
        total_ll += float(norm.sum())
        gamma = np.exp(block - norm)
        mass += gamma.sum(axis=0)
        first += gamma.T @ chunk
        second += gamma.T @ (chunk ** 2)
    alive = mass > MIN_COMPONENT_MASS
    safe = np.where(alive, mass, 1.0)[:, None]
    means = np.where(alive[:, None], first / safe, gmm.means)
    variances = np.where(alive[:, None], second / safe - means ** 2,
                         gmm.variances)
    variances = np.maximum(variances, var_floor)
    weights = np.where(alive, mass / len(features), 1e-12)
    return (DiagonalGmm(weights / weights.sum(), means, variances),
            total_ll / len(features))


def train_gmm(features, n_components, n_iter=10, epsilon=0.2,
              var_floor_ratio=0.01, seed=0,
              chunk_frames=DEFAULT_CHUNK_FRAMES):
    """LBG initialisation followed by ``n_iter`` EM iterations.

    Returns:
        ``(gmm, log_likelihood_history)`` where the history has ``n_iter + 1``
        entries: the mean frame log-likelihood of the initial model, then of
        the model after each EM iteration (so it can be plotted as the
        convergence curve). It is non-decreasing up to flooring effects.
    """
    features = np.asarray(features)
    var_floor = global_variance_floor(features, var_floor_ratio)
    codebook, assignments, _ = lbg_codebook(
        features, n_components, epsilon=epsilon, seed=seed,
        chunk_frames=chunk_frames)
    gmm = init_gmm_from_codebook(features, codebook, assignments, var_floor,
                                 chunk_frames)
    history = []
    for _ in range(n_iter):
        gmm, likelihood = em_step(gmm, features, var_floor, chunk_frames)
        history.append(likelihood)
    history.append(float(frame_log_likelihoods(gmm, features,
                                               chunk_frames).mean()))
    return gmm, history


def save_gmm(path, gmm, metadata=None):
    """Write ``gmm`` to an ``.npz`` file with a JSON metadata string."""
    np.savez(path, weights=gmm.weights, means=gmm.means,
             variances=gmm.variances,
             metadata=np.array(json.dumps(metadata or {}, sort_keys=True)))


def load_gmm(path):
    """Read ``(gmm, metadata dict)`` written by :func:`save_gmm`."""
    with np.load(path, allow_pickle=False) as data:
        gmm = DiagonalGmm(data["weights"], data["means"], data["variances"])
        return gmm, json.loads(str(data["metadata"]))
