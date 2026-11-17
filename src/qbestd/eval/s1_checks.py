"""Runner of the score-free Stage 4 checks (cycle 9, S1; declared in
``docs/results_timit_q20_features.md``). No retrieval score is computed.

    pixi run python -m qbestd.eval.s1_checks a|b|c --split-manifest <tsv>

Parts: ``a`` c0-marginalised alpha-hat, ``b`` F0 and c0 against alpha-hat,
``c`` the order-approximation gate. Results are written as JSON under
``outputs/s1/`` (git-ignored) with the provenance of the run.
"""

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

from qbestd.audio.pitch import median_f0
from qbestd.data.feature_cache import (
    feature_fingerprint,
    load_feature_cache,
    warped_cache_path,
)
from qbestd.data.split_selection import HF_SPLITS, manifest_selection
from qbestd.data.timit_hf import download_timit_parquet, iter_timit_rows
from qbestd.data.warped_cache import ll_matrix_from_caches
from qbestd.eval.vtln_eval import warped_paths_for
from qbestd.features.profiles import get_profile
from qbestd.ml.gmm import load_gmm
from qbestd.ml.vtln import WARP_FACTORS, estimate_warp_factors
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
from qbestd.provenance import finish_run, start_run

LOGGER = logging.getLogger(__name__)
MODELS = Path("outputs/models/stage4")
F0_SPLIT_HZ = 165.0
# name: (kind, profile, model stem)
RUNS = {
    "mfcc_4k": ("mfcc", "htk_described_4k", "mfcc_htk_described_4k_gmm64"),
    "mfcc_3400": ("mfcc", "htk_described", "mfcc_htk_described_gmm64"),
    "plp_4k": ("plp", "htk_described_4k", "plp_htk_described_4k_gmm64"),
    "mfcc_tmp": ("mfcc_tmp", "timit_matlab", "mfcc_tmp_timit_matlab_gmm64"),
}
D5_RUNS = ("mfcc_4k", "plp_4k", "mfcc_tmp")


def read_final_alphas(stem, n_iter=5):
    """``(keys, alpha_ours, alpha_thesis)`` of the last iteration's trace."""
    path = (MODELS / f"{stem}_vtln{n_iter}_trace"
            / f"iter{n_iter - 1}_alphas.tsv")
    rows = [line.split("\t") for line in
            path.read_text(encoding="utf-8").splitlines()[1:]]
    keys = [(r[0], int(r[1])) for r in rows]
    return (keys, np.array([float(r[2]) for r in rows]),
            np.array([float(r[3]) for r in rows]))


def c0_marginal_check(name, features_dir, n_iter=5):
    """Part (a) for one run."""
    kind, profile, stem = RUNS[name]
    # PLP always keeps c0 (log gain, column 0); MFCC kinds have a switch
    if not getattr(get_profile(profile, kind), "include_c0", True):
        raise ValueError("the static c0 is column 0 only when include_c0")
    gmm, _ = load_gmm(MODELS / f"{stem}_vtln{n_iter}.npz")
    keys, _, _ = read_final_alphas(stem, n_iter)
    paths = warped_paths_for({split for split, _ in keys}, kind, profile,
                             features_dir)
    full = ll_matrix_from_caches(paths, gmm, keys, kind, profile)
    marginal = ll_matrix_from_caches(paths, drop_dimension(gmm, 0), keys,
                                     kind, profile, drop_dim=0)
    return compare_alphas(estimate_warp_factors(full, WARP_FACTORS),
                          estimate_warp_factors(marginal, WARP_FACTORS))


def utterance_f0(keys, path):
    """Median F0 per key, read from ``path`` or computed and saved there."""
    path = Path(path)
    if path.is_file():
        table = {}
        for line in path.read_text(encoding="utf-8").splitlines()[1:]:
            split, row, value = line.split("\t")
            table[(split, int(row))] = float(value)
        if all(key in table for key in keys):
            return np.array([table[key] for key in keys])
    wanted = set(keys)
    table = {}
    for split in sorted({split for split, _ in keys}):
        for row in iter_timit_rows(download_timit_parquet(split), split):
            if (split, row.row_index) in wanted:
                table[(split, row.row_index)] = median_f0(row.audio,
                                                          row.sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["hf_split\trow_index\tmedian_f0_hz"] + [
        f"{s}\t{r}\t{table[(s, r)]:.4f}" for s, r in keys]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return np.array([table[key] for key in keys])


def mean_c0_at_unit_warp(keys, kind, profile, features_dir):
    """Mean static c0 (column 0) over the frames of each key at alpha = 1."""
    out = {}
    for split in sorted({split for split, _ in keys}):
        path = warped_cache_path(features_dir, split, kind, profile, 1.0)
        features, offsets, rows, _ = load_feature_cache(
            path, feature_fingerprint(kind, profile, warp_factor=1.0))
        for position, row in enumerate(rows):
            frames = features[offsets[position]:offsets[position + 1], 0]
            out[(split, int(row))] = (float(frames.mean()) if len(frames)
                                      else float("nan"))
    return np.array([out[key] for key in keys])


def f0_check(name, f0, features_dir, n_boot=10000, n_iter=5):
    """Part (b) for one run, given the F0 of its train keys."""
    kind, profile, stem = RUNS[name]
    keys, _, alpha = read_final_alphas(stem, n_iter)
    c0 = mean_c0_at_unit_warp(keys, kind, profile, features_dir)
    ok = np.isfinite(f0) & np.isfinite(c0)
    f0, alpha, c0 = f0[ok], alpha[ok], c0[ok]

    def interval(statistic, *arrays):
        est, low, high = bootstrap_interval(statistic, arrays, n_boot)
        return {"estimate": est, "low": low, "high": high}

    low_f0 = f0 < F0_SPLIT_HZ
    return {
        "n_utterances": int(len(ok)), "n_without_f0_or_c0": int((~ok).sum()),
        "rho_f0_alpha_thesis": interval(spearman, f0, alpha),
        "rho_f0_alpha_thesis_below_165": {
            "n": int(low_f0.sum()),
            **interval(spearman, f0[low_f0], alpha[low_f0])},
        "rho_f0_alpha_thesis_from_165": {
            "n": int((~low_f0).sum()),
            **interval(spearman, f0[~low_f0], alpha[~low_f0])},
        "rho_c0_alpha_thesis": interval(spearman, c0, alpha),
        "partial_rho_c0_alpha_thesis_given_f0": interval(
            partial_spearman, c0, alpha, f0)}


def order_check(selection):
    """Part (c): the order-approximation ratio over every utterance of both
    sides of the split."""
    ratios = []
    for split in HF_SPLITS:
        sides = [selection.wanted(side, split) for side in ("train", "test")]
        everything = any(rows is None for rows in sides)
        wanted = set().union(*[rows for rows in sides if rows is not None])
        if not everything and not wanted:
            continue
        for row in iter_timit_rows(download_timit_parquet(split), split):
            if everything or row.row_index in wanted:
                ratios.append(order_ratio(row.audio))
    ratios = np.array(ratios)
    offsets = np.array([c0_offset(r) if np.isfinite(r) else np.nan
                        for r in ratios])
    return {"n_utterances": int(len(ratios)),
            "ratio": percentile_summary(ratios, gate=float("inf")),
            "c0_offset": percentile_summary(offsets, gate=0.1)}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("part", choices=("a", "b", "c"))
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--features-dir", type=Path,
                        default=Path("outputs/features"))
    parser.add_argument("--out", type=Path, default=Path("outputs/s1"))
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    provenance = start_run(args.allow_dirty)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    started = time.time()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.part == "a":
        result = {name: c0_marginal_check(name, args.features_dir)
                  for name in RUNS}
    elif args.part == "b":
        keys, _, _ = read_final_alphas(RUNS["mfcc_4k"][2])
        f0 = utterance_f0(keys, args.out / "f0_train.tsv")
        result = {}
        for name in D5_RUNS:
            run_keys, _, _ = read_final_alphas(RUNS[name][2])
            if run_keys != keys:
                raise ValueError("runs must share their utterance keys")
            result[name] = f0_check(name, f0, args.features_dir)
    else:
        result = order_check(manifest_selection(args.split_manifest))
    result = {"part": args.part, "results": result,
              "runtime_s": round(time.time() - started, 1),
              **finish_run(provenance)}
    path = args.out / f"s1_{args.part}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    LOGGER.info("wrote %s", path)


if __name__ == "__main__":
    main()
