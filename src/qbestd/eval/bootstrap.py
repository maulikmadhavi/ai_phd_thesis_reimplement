"""Keyword-cluster bootstrap for p@N and MAP.

The instances of one keyword share the same relevant documents, so they are
not independent. The bootstrap therefore resamples **keywords** with
replacement and carries all instances of a drawn keyword together. Both
reported averages are resampled:

* *instance average*: every instance of the drawn keywords, with
  multiplicity, weighted equally;
* *keyword average*: the mean of the per-keyword means.

``per_query`` items are dicts with ``keyword``, ``row_index``,
``word_index``, ``p_at_n`` (percent) and ``ap`` (fraction; reported as MAP
in percent). An optional ``hf_split`` is part of the instance identity.
Intervals are 95 % percentile intervals from ``numpy.random.default_rng``.
"""

from collections import defaultdict

import numpy as np

METRICS = ("p_at_n", "map")


def _instance_key(item):
    return (item.get("hf_split"), item["row_index"], item["word_index"])


def _by_keyword(per_query):
    """``{keyword: [(key, p_at_n, map_percent), ...]}``, keywords sorted."""
    groups = defaultdict(list)
    for item in per_query:
        groups[item["keyword"]].append(
            (_instance_key(item), float(item["p_at_n"]),
             100.0 * float(item["ap"])))
    if not groups:
        raise ValueError("no queries to bootstrap")
    return {name: sorted(groups[name], key=repr) for name in sorted(groups)}


def _keyword_stats(groups, other=None):
    """Per keyword: instance count, sums and means of each metric.

    With ``other`` (same keywords and instances) the values are the
    differences ``other - groups``.
    """
    rows = []
    for name, items in groups.items():
        values = np.array([[p, a] for _, p, a in items])
        if other is not None:
            values = np.array([[p, a] for _, p, a in other[name]]) - values
        rows.append((len(items), values.sum(axis=0), values.mean(axis=0)))
    counts = np.array([r[0] for r in rows], dtype=float)
    return counts, np.array([r[1] for r in rows]), np.array(
        [r[2] for r in rows])


def _resample(counts, sums, means, n_boot, seed):
    rng = np.random.default_rng(seed)
    drawn = rng.integers(0, len(counts), size=(n_boot, len(counts)))
    instance = sums[drawn].sum(axis=1) / counts[drawn].sum(axis=1)[:, None]
    keyword = means[drawn].mean(axis=1)
    estimate = {"instance_average": sums.sum(axis=0) / counts.sum(),
                "keyword_average": means.mean(axis=0)}
    draws = {"instance_average": instance, "keyword_average": keyword}
    result = {"n_keywords": len(counts), "n_instances": int(counts.sum()),
              "n_boot": n_boot, "seed": seed}
    for average, sample in draws.items():
        result[average] = {}
        for column, metric in enumerate(METRICS):
            low, high = np.percentile(sample[:, column], [2.5, 97.5])
            result[average][metric] = {
                "estimate": float(estimate[average][column]),
                "low": float(low), "high": float(high)}
    return result


def cluster_bootstrap(per_query, n_boot=10000, seed=0):
    """95 % keyword-cluster bootstrap intervals of both averages.

    Returns:
        ``{"instance_average": {"p_at_n": {"estimate", "low", "high"},
        "map": {...}}, "keyword_average": {...}, "n_keywords", ...}``.
    """
    groups = _by_keyword(per_query)
    counts, sums, means = _keyword_stats(groups)
    return _resample(counts, sums, means, n_boot, seed)


def paired_keyword_bootstrap(per_query_a, per_query_b, n_boot=10000, seed=0):
    """Keyword-cluster bootstrap of the difference ``B - A``.

    The same resampling of keywords is applied to the per-keyword
    differences, so both runs must have identical keyword and instance sets.

    Raises:
        ValueError: if the keyword or instance sets differ.
    """
    a, b = _by_keyword(per_query_a), _by_keyword(per_query_b)
    if list(a) != list(b) or any(
            [k for k, _, _ in a[name]] != [k for k, _, _ in b[name]]
            for name in a):
        raise ValueError("the two runs must have the same keywords and "
                         "query instances")
    counts, sums, means = _keyword_stats(a, other=b)
    return _resample(counts, sums, means, n_boot, seed)
