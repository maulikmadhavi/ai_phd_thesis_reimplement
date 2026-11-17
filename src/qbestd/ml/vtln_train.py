"""Iterative GMM-VTLN training (Stage 4, V3).

Thesis: ``Representation.tex`` lines 100-138 and Algorithm
``pseudocode_vtlnwarping`` (lines 140-171), with ``k < N_iter`` (plan
section 5, erratum). Starting from the plain GMM (alpha = 1 for every
utterance)::

    for k in 0 .. N_iter - 1:
        alpha_hat  = argmax over the 13 warps of log P(X^alpha | lambda_init)
        lambda_r   = a new GMM trained on X^alpha_hat   (same LBG + EM)
        lambda_init = lambda_r

Assumption (recorded for the review): the thesis says "build" lambda_r, so
every iteration starts from a fresh LBG initialisation instead of the old
model. Memory: only one warp's cache of one HF split is read at a time.

Usage (the warped caches come from ``qbestd.data.warped_cache``)::

    pixi run train-vtln --gmm <plain.npz> --split-manifest <manifest.tsv> \
        --n-iter 1
"""

import argparse
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from qbestd.data.feature_cache import feature_fingerprint
from qbestd.data.split_selection import manifest_selection
from qbestd.data.warped_cache import (
    build_warped_caches,
    ll_matrix_from_caches,
    select_warped_features,
)
from qbestd.eval.model_guard import check_model
from qbestd.ml.gmm import (
    gmm_content_sha256,
    load_gmm,
    save_gmm,
    train_gmm_detailed,
)
from qbestd.ml.posteriorgram import gaussian_posteriorgram
from qbestd.ml.vtln import (
    WARP_FACTORS,
    changed_share,
    edge_shares,
    estimate_warp_factors,
    to_thesis_label,
    utterance_log_likelihoods,
    warp_histogram,
)
from qbestd.provenance import finish_run, start_run

LOGGER = logging.getLogger(__name__)
SELECTION_TOLERANCE = 1e-9  # per frame
DEFAULT_N_ITER = 5  # Representation.tex line 229: gains saturate at 4-5


@dataclass(frozen=True, eq=False)
class VtlnResult:
    """The final model, the final warps and one record per iteration."""

    gmm: object
    alphas: np.ndarray
    iterations: list


def estimate_utterance_warps(paths, gmm, keys, kind, profile,
                             warps=WARP_FACTORS):
    """alpha_hat per utterance of ``keys`` under ``gmm`` (train or test
    side alike), streaming one warp at a time."""
    matrix = ll_matrix_from_caches(paths, gmm, keys, kind, profile, warps)
    return estimate_warp_factors(matrix, warps), matrix


def estimate_test_warps(paths, gmm, keys, kind, profile,
                        warps=WARP_FACTORS):
    """Warp factor of each test document and its Gaussian posteriorgram.

    ``gmm`` is the final lambda_r. Returns ``(alphas, posteriorgrams)``, one
    ``(T, K)`` array per document, from the document's features at its own
    alpha_hat. **Not wired into the retrieval run this cycle.**
    """
    alphas, _ = estimate_utterance_warps(paths, gmm, keys, kind, profile,
                                         warps)
    features, offsets = select_warped_features(paths, alphas, keys, kind,
                                               profile)
    grams = [gaussian_posteriorgram(gmm, features[offsets[i]:offsets[i + 1]])
             for i in range(len(keys))]
    return alphas, grams


def estimate_clip_warp(features_by_warp, gmm):
    """alpha_hat of one clip from ``{alpha: (T, D) features}`` (the output
    of ``extract_warped_bank``). Assumption: a query clip gets its own
    estimate, as a separate file would (open question 33)."""
    warps = sorted(features_by_warp)
    if len({len(features_by_warp[w]) for w in warps}) != 1:
        raise ValueError("every warp must give the same number of frames")
    row = np.array([[utterance_log_likelihoods(
        features_by_warp[w], [0, len(features_by_warp[w])], gmm)[0]
        for w in warps]])
    return float(estimate_warp_factors(row, warps)[0])


def selection_step_ok(ll_init, previous_ll_new, tolerance=SELECTION_TOLERANCE):
    """Selection-step check of one iteration (K1).

    The previous model, scored on the features at the new alpha-hat
    (``ll_init``), must not score below its own log-likelihood on the
    previous alpha-hat features (``previous_ll_new``): alpha-hat maximises the
    per-utterance likelihood under that model. ``None`` when there is no
    previous iteration. A ``False`` would be a bug, not a model property.
    """
    if previous_ll_new is None:
        return None
    return bool(ll_init >= previous_ll_new - tolerance)


def write_trace(trace_dir, iteration, keys, alphas, matrix):
    """Per-utterance warps of one iteration and the LL matrix, next to the
    model. ``alpha_ours`` is the cache-file label, ``alpha_thesis`` is
    ``2 - alpha_ours`` (D3 c). The matrix columns follow ``WARP_FACTORS``
    (our label)."""
    trace_dir = Path(trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)
    lines = ["hf_split\trow_index\talpha_ours\talpha_thesis"]
    labels = to_thesis_label(alphas)
    for (split, row), ours, thesis in zip(keys, alphas, labels):
        lines.append(f"{split}\t{row}\t{ours:.2f}\t{thesis:.2f}")
    (trace_dir / f"iter{iteration}_alphas.tsv").write_text(
        ("\n").join(lines) + "\n", encoding="utf-8")
    np.save(trace_dir / f"iter{iteration}_ll_matrix.npy", matrix)


def write_flags(trace_dir, iteration, record):
    """``ll_decreased`` and ``selection_step_ok`` of one iteration, next to
    the trace files."""
    flags = {key: record[key] for key in ("ll_decreased",
                                          "selection_step_ok")}
    (Path(trace_dir) / f"iter{iteration}_flags.json").write_text(
        json.dumps(flags), encoding="utf-8")


def train_vtln(paths, keys, kind, profile, plain_gmm, n_iter,
               components, n_em_iter=10, epsilon=0.2, var_floor_ratio=0.01,
               seed=0, warps=WARP_FACTORS, trace_dir=None):
    """Run the iterations; returns a :class:`VtlnResult`.

    Each record holds the warp histogram (thesis label), the share at each
    edge, the share of utterances whose warp changed since the previous
    iteration (iteration 0: since alpha = 1), the mean frame log-likelihood
    of lambda_init on X^alpha_hat, the mean log-likelihood of the new model
    on the same features, ``ll_decreased``, the EM history and the model
    hash. With ``trace_dir`` the per-utterance warps and LL matrix are saved
    for every iteration.

    Raises:
        ValueError: if ``n_iter < 1``.
    """
    if n_iter < 1:
        raise ValueError("n_iter must be at least 1")
    gmm, records = plain_gmm, []
    previous_ll_new = None
    previous = np.ones(len(keys))
    for k in range(n_iter):
        start = time.time()
        alphas, matrix = estimate_utterance_warps(paths, gmm, keys, kind,
                                                  profile, warps)
        features, offsets = select_warped_features(paths, alphas, keys,
                                                   kind, profile)
        chosen = matrix[np.arange(len(keys)),
                        [list(map(float, warps)).index(a) for a in alphas]]
        trained = train_gmm_detailed(features, components, n_em_iter,
                                     epsilon, var_floor_ratio, seed)
        ll_init = float(chosen.sum() / len(features))
        ll_new = trained.log_likelihood_history[-1]
        if trace_dir is not None:
            write_trace(trace_dir, k, keys, alphas, matrix)
        records.append({
            "iteration": k, "warp_histogram": warp_histogram(alphas, warps),
            "edge_shares": edge_shares(alphas, warps),
            "changed_share": changed_share(previous, alphas),
            "mean_ll_init_on_selected": ll_init,
            "mean_ll_new_on_selected": ll_new,
            "ll_decreased": bool(ll_new < ll_init),
            "selection_step_ok": selection_step_ok(ll_init, previous_ll_new),
            "em_history": trained.log_likelihood_history,
            "model_content_sha256": gmm_content_sha256(trained.gmm),
            "seconds": round(time.time() - start, 1)})
        if records[-1]["ll_decreased"]:
            LOGGER.warning("iteration %d: log-likelihood fell from %.4f to "
                           "%.4f on the selected features", k, ll_init,
                           ll_new)
        LOGGER.info("iteration %d: LL init %.4f, new %.4f, edges %s, "
                    "changed %.3f, %s", k, ll_init, ll_new,
                    records[-1]["edge_shares"],
                    records[-1]["changed_share"],
                    records[-1]["warp_histogram"])
        if records[-1]["selection_step_ok"] is False:
            LOGGER.warning("iteration %d: selection step check FAILED (LL "
                           "%.6f below the previous model's %.6f): a bug",
                           k, ll_init, previous_ll_new)
        if trace_dir is not None:
            write_flags(trace_dir, k, records[-1])
        previous_ll_new = ll_new
        previous = alphas
        gmm = trained.gmm
        del features
    return VtlnResult(gmm, alphas, records)


def peak_memory_mb():
    """Peak working set of this process in MB (Windows or POSIX); ``None``
    when it cannot be read."""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except ImportError:
        pass
    try:
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount",
                        wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage")]
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(handle), ctypes.byref(counters), counters.cb)
        return counters.PeakWorkingSetSize / 2 ** 20 if ok else None
    except (AttributeError, OSError):
        return None


def save_vtln_model(path, result, metadata):
    """Write the final model and a JSON log next to it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    info = {**metadata, "iterations": result.iterations,
            "content_sha256": gmm_content_sha256(result.gmm)}
    save_gmm(path, result.gmm, info)
    path.with_suffix(".json").write_text(json.dumps(info, indent=2),
                                         encoding="utf-8")
    return info


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--gmm", type=Path, required=True,
                        help="the plain GMM (lambda_init)")
    parser.add_argument("--kind", default="mfcc",
                        choices=("mfcc", "plp", "mfcc_tmp"))
    parser.add_argument("--profile", default="htk_described")
    parser.add_argument("--n-iter", type=int, default=DEFAULT_N_ITER)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--features-dir", type=Path,
                        default=Path("outputs/features"))
    parser.add_argument("--out", type=Path, default=Path("outputs/models"))
    parser.add_argument("--allow-dirty", action="store_true",
                        help="run on uncommitted changes (recorded)")
    return parser.parse_args(argv)


def load_plain_model(path, kind, profile, split_id):
    """The plain GMM lambda_init; a VTLN model (or one for other features
    or another split) is refused."""
    gmm, info = load_gmm(path)
    check_model(info, kind, profile, split_id,
                feature_fingerprint(kind, profile), model_type="plain")
    return gmm, info


def vtln_metadata(kind, profile, split_id, n_vtln_iter, plain, info):
    """Metadata of a VTLN model; EM settings are those of lambda_init."""
    return {"model_type": "vtln", "kind": kind, "profile": profile,
            "split_id": split_id, "n_vtln_iter": n_vtln_iter,
            "n_em_iter": info.get("n_iter", 10),
            "epsilon": info.get("epsilon", 0.2),
            "var_floor_ratio": info.get("var_floor_ratio", 0.01),
            "seed": info.get("seed", 0), "components": plain.n_components,
            "warps": [float(w) for w in WARP_FACTORS],
            "feature_fingerprint": feature_fingerprint(kind, profile),
            "plain_model_sha256": gmm_content_sha256(plain),
            "fresh_lbg_each_iteration": True}


def main(argv=None):
    args = parse_args(argv)
    provenance = start_run(args.allow_dirty)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    started = time.time()
    selection = manifest_selection(args.split_manifest)
    plain, info = load_plain_model(args.gmm, args.kind, args.profile,
                                   selection.split_id)
    keys = [(split, row) for split in ("train", "test")
            for row in sorted(selection.wanted("train", split) or ())]
    paths = {float(a): {} for a in WARP_FACTORS}
    for hf_split in ("train", "test"):
        if not selection.uses("train", hf_split):
            continue
        built = build_warped_caches(hf_split, args.kind, args.profile,
                                    args.features_dir, skip_existing=True)
        for alpha, path in built.items():
            paths[alpha][hf_split] = path
    name = (f"{args.kind}_{args.profile}_gmm{plain.n_components}"
            f"_vtln{args.n_iter}")
    result = train_vtln(paths, keys, args.kind, args.profile, plain,
                        args.n_iter, plain.n_components,
                        n_em_iter=info.get("n_iter", 10),
                        epsilon=info.get("epsilon", 0.2),
                        var_floor_ratio=info.get("var_floor_ratio", 0.01),
                        seed=info.get("seed", 0),
                        trace_dir=args.out / f"{name}_trace")
    metadata = vtln_metadata(args.kind, args.profile, selection.split_id,
                             args.n_iter, plain, info)
    metadata.update(finish_run(provenance))
    metadata["runtime_s"] = round(time.time() - started, 1)
    metadata["peak_memory_mb"] = peak_memory_mb()
    out = args.out / f"{name}.npz"
    save_vtln_model(out, result, metadata)
    LOGGER.info("wrote %s in %.0f s, peak memory %s MB", out,
                time.time() - started, metadata["peak_memory_mb"])


if __name__ == "__main__":
    main()
