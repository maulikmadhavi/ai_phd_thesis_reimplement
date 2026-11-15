"""Train a baseline GMM on cached TIMIT features and log how it went.

Usage (core environment, which includes ``huggingface_hub`` for the
dataset download)::

    pixi run train-gmm --kind mfcc --profile timit_matlab --components 64
    pixi run train-gmm --components 64 --split-manifest <manifest.tsv>

Builds (or reuses) the feature cache of the HF train split without the two SA
sentences in ``outputs/features/``, runs LBG + 10 EM iterations and writes
``<out>/<kind>_<profile>_gmm<K>.npz`` plus a ``.json`` training log. Models
and features are git-ignored and never committed.

With ``--split-manifest`` the training rows are the train side of the
manifest, taken from the caches of both HF splits; ``split_id`` comes from
the manifest and the model goes to ``<out>/<rule name>/`` unless ``--out``
is given.
"""

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

from qbestd.data.feature_cache import (
    CacheMismatchError,
    build_feature_cache,
    cache_path,
    feature_fingerprint,
    hf_split_id,
    load_feature_cache,
)
from qbestd.data.split_selection import gather_utterances, manifest_selection
from qbestd.data.text_split import read_split_manifest
from qbestd.ml.gmm import (
    count_floored,
    gmm_content_sha256,
    save_gmm,
    train_gmm_detailed,
)

LOGGER = logging.getLogger(__name__)
DEFAULT_MODELS_DIR = Path("outputs/models")
DEFAULT_FEATURES_DIR = Path("outputs/features")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--kind", default="mfcc",
                        choices=("mfcc", "plp", "mfcc_tmp"))
    parser.add_argument("--profile", default="timit_matlab")
    parser.add_argument("--components", type=int, default=64)
    parser.add_argument("--n-iter", type=int, default=10)
    parser.add_argument("--var-floor-ratio", type=float, default=0.01)
    parser.add_argument("--epsilon", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--split", default="train")
    parser.add_argument("--split-manifest", type=Path, default=None,
                        help="train on the train side of this manifest")
    parser.add_argument("--split-id", default=hf_split_id(),
                        help="identity of the training rows, stored in the "
                        "model (default: the HF split without SA)")
    parser.add_argument("--out", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--features-dir", type=Path,
                        default=DEFAULT_FEATURES_DIR)
    parser.add_argument("--rebuild-cache", action="store_true",
                        help="ignore an existing feature cache")
    return parser.parse_args(argv)


def model_name(kind, profile, components):
    return f"{kind}_{profile}_gmm{components}"


def file_sha256(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_split_cache(args, hf_split):
    """Cache of one HF split (built on demand), fingerprint checked.

    A missing cache is built; one whose fingerprint does not match the
    requested settings is only replaced with ``--rebuild-cache``.
    """
    path = cache_path(args.features_dir, hf_split, args.kind, args.profile)
    if args.rebuild_cache or not path.is_file():
        LOGGER.info("building feature cache %s", path)
        path, _ = build_feature_cache(hf_split, args.kind, args.profile,
                                      args.features_dir)
    expected = feature_fingerprint(args.kind, args.profile, exclude_sa=True)
    try:
        return load_feature_cache(path, expected=expected)
    except CacheMismatchError as error:
        raise SystemExit(f"{error}; rerun with --rebuild-cache") from error


def get_features(args):
    """Features of the training split, from the cache (built on demand)."""
    return load_split_cache(args, args.split)


def get_manifest_features(args):
    """``(features, None, keys, meta)`` of the manifest's train side.

    Rows come from the caches of both HF splits; ``keys`` are the
    ``(hf_split, row_index)`` pairs in training order.
    """
    selection = manifest_selection(args.split_manifest)
    caches = {}

    def load(hf_split):
        if hf_split not in caches:
            caches[hf_split] = load_split_cache(args, hf_split)
        return caches[hf_split]

    utterances, keys = gather_utterances(selection, "train", load)
    meta = {"n_rows": len(keys),
            "dataset_revision": next(iter(caches.values()))[3][
                "dataset_revision"],
            "excluded_sa_rows": sum(c[3]["excluded_sa_rows"]
                                    for c in caches.values()),
            "fingerprint": feature_fingerprint(args.kind, args.profile,
                                               exclude_sa=True)}
    return np.concatenate(utterances), None, keys, meta


def train_from_features(features, meta, args):
    """Train, save and describe a model; returns the log dictionary."""
    start = time.time()
    result = train_gmm_detailed(features, args.components, args.n_iter,
                                args.epsilon, args.var_floor_ratio,
                                args.seed)
    seconds = time.time() - start
    name = model_name(args.kind, args.profile, args.components)
    npz_path = Path(args.out) / f"{name}.npz"
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    info = {"kind": args.kind, "profile": args.profile,
            "split_id": args.split_id, "dims": int(features.shape[1]),
            "n_iter": args.n_iter,
            "components": args.components, "epsilon": args.epsilon,
            "var_floor_ratio": args.var_floor_ratio, "seed": args.seed,
            "training_rows": meta["n_rows"],
            "training_frames": int(len(features)),
            "dataset_revision": meta["dataset_revision"],
            "feature_fingerprint": meta.get("fingerprint")}
    save_gmm(npz_path, result.gmm, info)
    log = {**info, "name": name,
           "ll_history": result.log_likelihood_history,
           "lbg_distortion_history": result.lbg_distortion_history,
           "smallest_weight": float(result.gmm.weights.min()),
           "largest_weight": float(result.gmm.weights.max()),
           "floored_variances": count_floored(result.gmm, result.var_floor),
           "total_variances": int(result.gmm.variances.size),
           "wall_time_s": round(seconds, 1),
           "file_sha256": file_sha256(npz_path),
           "content_sha256": gmm_content_sha256(result.gmm),
           "excluded_sa_rows": meta["excluded_sa_rows"]}
    (Path(args.out) / f"{name}.json").write_text(
        json.dumps(log, indent=2), encoding="utf-8")
    return log


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    if args.split_manifest:
        args.split_id = manifest_selection(args.split_manifest).split_id
        if args.out == DEFAULT_MODELS_DIR:
            args.out = DEFAULT_MODELS_DIR / read_split_manifest(
                args.split_manifest).rule
        features, _, _, meta = get_manifest_features(args)
    else:
        features, _, _, meta = get_features(args)
    log = train_from_features(np.asarray(features), meta, args)
    LOGGER.info("%s: LL %.3f -> %.3f in %.0f s, sha256 %s", log["name"],
                log["ll_history"][0], log["ll_history"][-1],
                log["wall_time_s"], log["file_sha256"][:16])


if __name__ == "__main__":
    main()
