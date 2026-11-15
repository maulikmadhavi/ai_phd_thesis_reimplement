"""Linde-Buzo-Gray (LBG) vector quantiser used to initialise the GMM.

Thesis (``Algorithm_LC.tex``, Fig. VQ; ``ExpSetup.tex`` line 238): K-means VQ
with splitting constant epsilon = 0.2. Every split uses the per-dimension
mean mu and standard deviation sigma of the cluster ("data uncorrelated
assumption"), so a centroid becomes the pair ``mu - eps * sigma`` and
``mu + eps * sigma``. The codebook doubles until ``n_clusters`` is reached.

Assumptions (the thesis is silent; all unverified): k-means refinement
inside each level stops at a relative distortion decrease in ``[0, tol)``
(``tol = 1e-3`` is our choice, not a thesis value) or after
``max_kmeans_iter`` iterations, and an empty cluster is re-seeded by
splitting the cluster with the highest distortion. All statistics are
accumulated in chunks so memory stays bounded.
"""

import numpy as np

DEFAULT_EPSILON = 0.2  # thesis value
DEFAULT_CHUNK_FRAMES = 100_000
JITTER_RATIO = 1e-6  # unverified: breaks ties when a cluster has sigma = 0


def _check_features(features):
    features = np.asarray(features)
    if features.ndim != 2 or features.shape[0] == 0:
        raise ValueError("features must be a non-empty (T, D) array")
    if not np.all(np.isfinite(features)):
        raise ValueError("features contain nan or inf")
    return features


def _squared_distances(chunk, codebook, codebook_norms):
    """(len(chunk), K) squared Euclidean distances."""
    chunk = chunk.astype("float64", copy=False)
    distances = (np.sum(chunk ** 2, axis=1)[:, None]
                 - 2.0 * chunk @ codebook.T + codebook_norms[None, :])
    return np.maximum(distances, 0.0)


def assign_with_distortion(features, codebook,
                           chunk_frames=DEFAULT_CHUNK_FRAMES):
    """Nearest codeword per frame and its squared distance, chunk by chunk."""
    features = _check_features(features)
    codebook = np.asarray(codebook, dtype="float64")
    norms = np.sum(codebook ** 2, axis=1)
    assignments = np.empty(len(features), dtype=np.int64)
    distances = np.empty(len(features), dtype="float64")
    for start in range(0, len(features), chunk_frames):
        block = _squared_distances(features[start:start + chunk_frames],
                                   codebook, norms)
        index = np.argmin(block, axis=1)
        assignments[start:start + chunk_frames] = index
        distances[start:start + chunk_frames] = block[
            np.arange(len(index)), index]
    return assignments, distances


def assign_to_codebook(features, codebook, chunk_frames=DEFAULT_CHUNK_FRAMES):
    """Index of the nearest codeword for every frame (chunked)."""
    return assign_with_distortion(features, codebook, chunk_frames)[0]


def cluster_statistics(features, assignments, n_clusters,
                       chunk_frames=DEFAULT_CHUNK_FRAMES):
    """Per-cluster counts, means, per-dimension std and total distortion.

    Returns ``(counts, means, stds, distortions)``; the means and stds of an
    empty cluster are zero. Distortion is the summed squared error to the
    cluster mean.
    """
    features = _check_features(features)
    dim = features.shape[1]
    counts = np.zeros(n_clusters)
    sums = np.zeros((n_clusters, dim))
    squares = np.zeros((n_clusters, dim))
    for start in range(0, len(features), chunk_frames):
        block = features[start:start + chunk_frames].astype("float64")
        labels = assignments[start:start + chunk_frames]
        counts += np.bincount(labels, minlength=n_clusters)
        for d in range(dim):
            sums[:, d] += np.bincount(labels, block[:, d],
                                      minlength=n_clusters)
            squares[:, d] += np.bincount(labels, block[:, d] ** 2,
                                         minlength=n_clusters)
    safe = np.maximum(counts, 1.0)[:, None]
    means = sums / safe
    variances = np.maximum(squares / safe - means ** 2, 0.0)
    distortions = np.sum(squares - counts[:, None] * means ** 2, axis=1)
    return counts, means, np.sqrt(variances), np.maximum(distortions, 0.0)


def split_codebook(means, stds, epsilon, jitter):
    """Double the codebook: ``mu - eps*sigma`` and ``mu + eps*sigma``.

    ``jitter`` (same shape as ``means``) is added to ``sigma`` so a
    zero-spread cluster still splits into two distinct points.
    """
    offset = epsilon * (stds + jitter)
    return np.concatenate([means - offset, means + offset])


def _reseed_empty(codebook, counts, means, stds, distortions, epsilon):
    """Replace empty centroids by splitting the highest-distortion cluster."""
    for empty in np.flatnonzero(counts == 0):
        donor = int(np.argmax(np.where(counts > 1, distortions, -1.0)))
        if counts[donor] <= 1 or distortions[donor] <= 0:
            continue
        offset = epsilon * stds[donor]
        codebook[empty] = means[donor] + offset
        codebook[donor] = means[donor] - offset
        counts = counts.copy()
        counts[empty], counts[donor] = 1, counts[donor] - 1
        distortions = distortions.copy()
        distortions[donor] /= 2.0
    return codebook


def _converged(previous, current, tol):
    """True when the relative decrease is in ``[0, tol)``.

    A distortion *increase* (for example after an empty-cluster re-seed) is
    not convergence: refinement carries on until it recovers or runs out of
    iterations.
    """
    decrease = previous - current
    return 0.0 <= decrease < tol * max(previous, 1e-300)


def kmeans_refine(features, codebook, epsilon, max_iter, tol, chunk_frames):
    """Lloyd iterations; returns (codebook, assignments, distortion list).

    Each list entry is the mean squared distance per frame before that
    iteration's update; refinement stops when it *decreases* by less than
    ``tol`` (relative, unverified default) or after ``max_iter`` iterations.
    An increase does not stop it.
    """
    codebook = np.array(codebook, dtype="float64")
    n_clusters = len(codebook)
    history = []
    for _ in range(max_iter):
        assignments, distances = assign_with_distortion(features, codebook,
                                                        chunk_frames)
        history.append(float(distances.mean()))
        counts, means, stds, distortions = cluster_statistics(
            features, assignments, n_clusters, chunk_frames)
        codebook = np.where(counts[:, None] > 0, means, codebook)
        codebook = _reseed_empty(codebook, counts, means, stds, distortions,
                                 epsilon)
        if len(history) > 1 and _converged(history[-2], history[-1], tol):
            break
    assignments, distances = assign_with_distortion(features, codebook,
                                                    chunk_frames)
    history.append(float(distances.mean()))
    return codebook, assignments, history


def lbg_codebook(features, n_clusters, epsilon=DEFAULT_EPSILON,
                 max_kmeans_iter=20, tol=1e-3, seed=0,
                 chunk_frames=DEFAULT_CHUNK_FRAMES):
    """Train an LBG codebook by repeated splitting and k-means refinement.

    Args:
        features: (T, D) array.
        n_clusters: a power of two (1, 2, 4, ...).
        epsilon: splitting constant (thesis: 0.2).
        seed: seeds the tiny jitter used only for zero-spread clusters.

    Returns:
        ``(codebook (K, D) float64, assignments (T,), distortion_history)``,
        where ``distortion_history`` is a list with one list of mean squared
        distances per codebook size (1, 2, 4, ... K). Within a level the
        values do not increase unless an empty cluster was re-seeded.

    Raises:
        ValueError: if ``n_clusters`` is not a power of two, exceeds the
            number of frames, or ``features`` is malformed.
    """
    features = _check_features(features)
    if n_clusters < 1 or n_clusters & (n_clusters - 1):
        raise ValueError(
            f"n_clusters must be a power of two, got {n_clusters}")
    if n_clusters > len(features):
        raise ValueError("n_clusters exceeds the number of frames")
    rng = np.random.default_rng(seed)
    scale = features.std(axis=0).astype("float64") * JITTER_RATIO
    assignments = np.zeros(len(features), dtype=np.int64)
    counts, means, stds, _ = cluster_statistics(features, assignments, 1,
                                                chunk_frames)
    codebook = means.copy()
    distortion_history = [[float(
        assign_with_distortion(features, codebook, chunk_frames)[1].mean())]]
    while len(codebook) < n_clusters:
        jitter = scale * rng.uniform(0.5, 1.5, size=(len(codebook),
                                                     features.shape[1]))
        codebook = split_codebook(means, stds, epsilon, jitter)
        codebook, assignments, history = kmeans_refine(
            features, codebook, epsilon, max_kmeans_iter, tol, chunk_frames)
        distortion_history.append(history)
        counts, means, stds, _ = cluster_statistics(
            features, assignments, len(codebook), chunk_frames)
        means = np.where(counts[:, None] > 0, means, codebook)
    return codebook, assignments, distortion_history
