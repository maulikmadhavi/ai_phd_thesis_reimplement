import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from qbestd.data.feature_cache import (
    build_feature_cache,
    feature_fingerprint,
    load_feature_cache,
    warped_cache_path,
)
from qbestd.data.warped_cache import (
    build_warped_caches,
    ll_matrix_from_caches,
    select_warped_features,
)
from qbestd.features.extract import extract_features
from qbestd.features.profiles import get_profile
from qbestd.ml.gmm import DiagonalGmm, frame_log_likelihoods

RATE = 16000
WARPS = (0.9, 1.0, 1.1)
KIND, PROFILE = "mfcc", "timit_matlab"


@pytest.fixture
def parquet(tmp_path):
    rng = np.random.default_rng(0)
    lengths = [8000, 12000, 9000]
    audio = [{"array": (0.1 * rng.normal(size=n)).astype("float32").tolist(),
              "sampling_rate": RATE} for n in lengths]
    sentences = ["Combine all the ingredients.", "Chip postponed alimony.",
                 "The boy ran home."]
    path = tmp_path / "t.parquet"
    pq.write_table(pa.table({"audio": audio, "sentence": sentences}), path)
    return path


@pytest.fixture
def caches(tmp_path, parquet):
    out = tmp_path / "feat"
    paths = build_warped_caches("train", KIND, PROFILE, out, WARPS,
                                parquet_paths=[parquet])
    return out, {alpha: {"train": path} for alpha, path in paths.items()}


def tiny_gmm():
    rng = np.random.default_rng(1)
    return DiagonalGmm(np.array([0.5, 0.5]), rng.normal(size=(2, 39)),
                       np.ones((2, 39)) * 4.0)


KEYS = [("train", 0), ("train", 1), ("train", 2)]


def test_one_file_per_warp_named_by_the_warp(caches):
    out, paths = caches
    names = sorted(p["train"].name for p in paths.values())
    assert names == sorted(f"train_mfcc_timit_matlab_a{t}.npz"
                           for t in (90, 100, 110))
    assert warped_cache_path(out, "train", KIND, PROFILE, 0.88).name.endswith(
        "_a88.npz")


def test_every_warp_has_its_own_fingerprint_and_unit_warp_equals_plain(
        caches, tmp_path, parquet):
    _, paths = caches
    prints = {a: load_feature_cache(p["train"])[3]["fingerprint"]
              for a, p in paths.items()}
    assert len(set(prints.values())) == 3
    assert prints[1.0] == feature_fingerprint(KIND, PROFILE)
    plain, _ = build_feature_cache("train", KIND, PROFILE, tmp_path / "plain",
                                   parquet_paths=[parquet])
    assert np.array_equal(load_feature_cache(plain)[0],
                          load_feature_cache(paths[1.0]["train"])[0])


def test_warped_features_match_a_direct_extraction(caches, parquet):
    _, paths = caches
    features, offsets, rows, meta = load_feature_cache(paths[0.9]["train"])
    assert meta["warp_factor"] == 0.9
    rng = np.random.default_rng(0)
    first = (0.1 * rng.normal(size=8000)).astype("float32")
    direct = extract_features(first, RATE, KIND, warp_factor=0.9,
                              config=get_profile(PROFILE, KIND))
    assert np.allclose(features[offsets[0]:offsets[1]], direct, atol=1e-4)


def test_streamed_ll_matrix_equals_the_in_memory_one(caches):
    _, paths = caches
    gmm = tiny_gmm()
    matrix = ll_matrix_from_caches(paths, gmm, KEYS, KIND, PROFILE, WARPS)
    assert matrix.shape == (3, 3)
    for column, alpha in enumerate(WARPS):
        features, offsets, _, _ = load_feature_cache(paths[alpha]["train"])
        for row in range(3):
            frames = features[offsets[row]:offsets[row + 1]]
            assert matrix[row, column] == pytest.approx(
                frame_log_likelihoods(gmm, frames).sum())


def test_key_order_decides_the_row_order(caches):
    _, paths = caches
    gmm = tiny_gmm()
    forward = ll_matrix_from_caches(paths, gmm, KEYS, KIND, PROFILE, WARPS)
    backward = ll_matrix_from_caches(paths, gmm, KEYS[::-1], KIND, PROFILE,
                                     WARPS)
    assert np.allclose(forward[::-1], backward)


def test_select_warped_features_takes_each_utterance_at_its_own_warp(caches):
    _, paths = caches
    alphas = [1.1, 0.9, 1.0]
    features, offsets = select_warped_features(paths, alphas, KEYS, KIND,
                                               PROFILE)
    for row, alpha in enumerate(alphas):
        cached, cached_offsets, _, _ = load_feature_cache(
            paths[alpha]["train"])
        assert np.array_equal(features[offsets[row]:offsets[row + 1]],
                              cached[cached_offsets[row]:
                                     cached_offsets[row + 1]])
    assert offsets[0] == 0 and offsets[-1] == len(features)


def test_a_missing_row_raises(caches):
    _, paths = caches
    with pytest.raises(ValueError, match="not in"):
        ll_matrix_from_caches(paths, tiny_gmm(), [("train", 7)], KIND,
                              PROFILE, WARPS)
    with pytest.raises(ValueError, match="not in"):
        select_warped_features(paths, [1.0], [("train", 7)], KIND, PROFILE)


def test_a_cache_of_another_warp_is_refused(caches):
    _, paths = caches
    swapped = {0.9: paths[1.1], 1.0: paths[1.0], 1.1: paths[1.1]}
    with pytest.raises(ValueError, match="different settings"):
        ll_matrix_from_caches(swapped, tiny_gmm(), KEYS, KIND, PROFILE, WARPS)


def test_skip_existing_keeps_a_matching_file_and_rebuilds_a_stale_one(
        tmp_path, parquet, caches):
    out, paths = caches
    target = paths[0.9]["train"]
    before = target.stat().st_mtime_ns
    build_warped_caches("train", KIND, PROFILE, out, WARPS,
                        parquet_paths=[parquet], skip_existing=True)
    assert target.stat().st_mtime_ns == before
    target.write_bytes(paths[1.1]["train"].read_bytes())  # wrong warp
    build_warped_caches("train", KIND, PROFILE, out, WARPS,
                        parquet_paths=[parquet], skip_existing=True)
    assert load_feature_cache(target)[3]["warp_factor"] == 0.9
