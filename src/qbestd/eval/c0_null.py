"""c0 null control and edge margins (cycle 10, N1; declared in
``docs/results_timit_q20_features.md``). Score-free: no retrieval score.

    pixi run python -m qbestd.eval.c0_null

For six VTLN train runs: the churn share (all-dimension alpha-hat under the
final lambda_r against the iteration-4 trace), and the margins at the two
grid edges from the saved iteration-4 log-likelihood matrix. For MFCC
0-4000 Hz (un-normalised) also the share changed by dropping each static
column c_0..c_12. Results go to git-ignored ``outputs/c0_null/``.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from qbestd.data.warped_cache import ll_matrix_from_caches
from qbestd.eval.s1_checks import MODELS, read_final_alphas
from qbestd.eval.vtln_eval import warped_paths_for
from qbestd.ml.gmm import load_gmm
from qbestd.ml.vtln import WARP_FACTORS, estimate_warp_factors
from qbestd.ml.vtln_checks import drop_dimension
from qbestd.provenance import finish_run, start_run

# name: (kind, profile, model stem); the four un-normalised, then two pn
N1_RUNS = {
    "mfcc_3400": ("mfcc", "htk_described", "mfcc_htk_described_gmm64"),
    "mfcc_4k": ("mfcc", "htk_described_4k", "mfcc_htk_described_4k_gmm64"),
    "plp_4k": ("plp", "htk_described_4k", "plp_htk_described_4k_gmm64"),
    "mfcc_tmp": ("mfcc_tmp", "timit_matlab", "mfcc_tmp_timit_matlab_gmm64"),
    "mfcc_pn": ("mfcc", "htk_described_4k_pn",
                "mfcc_htk_described_4k_pn_gmm64"),
    "plp_pn": ("plp", "htk_described_4k_pn", "plp_htk_described_4k_pn_gmm64"),
}
DIM_RUN = "mfcc_4k"
N_STATIC = 13  # c0..c12 are the first 13 columns


def share_changed(alpha, reference):
    """Share of utterances whose warp differs (tolerant to float labels)."""
    alpha, reference = np.asarray(alpha), np.asarray(reference)
    if alpha.shape != reference.shape:
        raise ValueError("alpha vectors must be aligned")
    return float(np.mean(~np.isclose(alpha, reference, atol=1e-9)))


def edge_margins(ll, alpha_ours, warps=WARP_FACTORS):
    """Margin of each grid edge over its inward neighbour, for the
    utterances whose warp is that edge.

    Thesis label 1.12 is our 0.88 (and 0.88 is our 1.12). For thesis 1.12
    the margin is LL(0.88) - LL(0.90) in our label; for thesis 0.88 it is
    LL(1.12) - LL(1.10). A margin is >= 0 when the edge is the argmax.

    Returns:
        ``{"1.12": {"n", "median", "p10", "p90"}, "0.88": {...}}``.
    """
    ll, alpha = np.asarray(ll), np.asarray(alpha_ours)
    column = {round(float(w), 2): i for i, w in enumerate(warps)}
    out = {}
    for thesis_edge, ours_edge, inward in ((1.12, 0.88, 0.90),
                                           (0.88, 1.12, 1.10)):
        chosen = np.isclose(alpha, ours_edge, atol=1e-9)
        key = f"{thesis_edge:.2f}"
        if not chosen.any():
            out[key] = {"n": 0}
            continue
        margin = (ll[chosen, column[ours_edge]]
                  - ll[chosen, column[inward]])
        p10, median, p90 = np.percentile(margin, [10, 50, 90])
        out[key] = {"n": int(chosen.sum()), "median": float(median),
                    "p10": float(p10), "p90": float(p90)}
    return out


def c0_rank(shares):
    """1-based rank of column 0 among the shares (1 = largest)."""
    shares = np.asarray(shares)
    return int(1 + np.sum(shares[1:] > shares[0]))


def run_one(name, features_dir):
    """Churn, trace agreement and edge margins of one VTLN run."""
    kind, profile, stem = N1_RUNS[name]
    gmm, _ = load_gmm(MODELS / f"{stem}_vtln5.npz")
    keys, alpha_ours, _ = read_final_alphas(stem)
    paths = warped_paths_for({split for split, _ in keys}, kind, profile,
                             features_dir)
    ll = ll_matrix_from_caches(paths, gmm, keys, kind, profile)
    full = estimate_warp_factors(ll, WARP_FACTORS)
    saved = np.load(MODELS / f"{stem}_vtln5_trace" / "iter4_ll_matrix.npy")
    return {
        "n_utterances": len(keys),
        "churn": share_changed(full, alpha_ours),
        # the trace must be the argmax of its own saved matrix
        "trace_argmax_agreement": 1.0 - share_changed(
            estimate_warp_factors(saved, WARP_FACTORS), alpha_ours),
        "edge_margins": edge_margins(saved, alpha_ours),
    }, (gmm, keys, paths, full, kind, profile)


def dimension_control(gmm, keys, paths, full, kind, profile):
    """Share changed by dropping each static column, with c0's rank."""
    shares = []
    for dim in range(N_STATIC):
        marginal = drop_dimension(gmm, dim)
        ll = ll_matrix_from_caches(paths, marginal, keys, kind, profile,
                                   drop_dim=dim)
        shares.append(share_changed(estimate_warp_factors(ll, WARP_FACTORS),
                                    full))
    return {"share_by_column": {f"c{d}": s for d, s in enumerate(shares)},
            "c0_rank_among_13": c0_rank(shares),
            "largest_other_share": float(max(shares[1:]))}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--features-dir", type=Path,
                        default=Path("outputs/features"))
    parser.add_argument("--out", type=Path, default=Path("outputs/c0_null"))
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    provenance = start_run(args.allow_dirty)
    started = time.time()
    runs, control = {}, None
    for name in N1_RUNS:
        runs[name], state = run_one(name, args.features_dir)
        if name == DIM_RUN:
            control = dimension_control(*state)
    s1 = json.loads((Path("outputs/s1") / "s1_a.json").read_text(
        encoding="utf-8"))
    s1_c0 = s1["results"]["mfcc_4k"]["share_changed"]
    result = {"runs": runs, "dimension_control": control,
              "dim_run": DIM_RUN,
              "s1_a_mfcc_4k_c0_share": s1_c0,
              "c0_share_matches_s1_a": round(
                  control["share_by_column"]["c0"], 3) == round(s1_c0, 3),
              "runtime_s": round(time.time() - started, 1),
              **finish_run(provenance)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "c0_null.json").write_text(json.dumps(result, indent=2),
                                           encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "dimension_control", "c0_share_matches_s1_a", "runtime_s")},
        indent=2))


if __name__ == "__main__":
    main()
