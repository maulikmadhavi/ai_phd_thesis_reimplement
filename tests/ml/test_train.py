import json
from pathlib import Path

import numpy as np
import pytest

from qbestd.data.feature_cache import build_feature_cache, hf_split_id
from qbestd.ml.gmm import (
    gmm_content_sha256,
    load_gmm,
    train_gmm,
    train_gmm_detailed,
)
from qbestd.ml.train import (
    get_features,
    model_name,
    parse_args,
    train_from_features,
)


def test_defaults():
    args = parse_args([])
    assert args.kind == "mfcc"
    assert args.profile == "timit_matlab"
    assert args.components == 64
    assert args.n_iter == 10
    assert args.var_floor_ratio == 0.01
    assert args.epsilon == 0.2
    assert args.out == Path("outputs/models")
    assert args.features_dir == Path("outputs/features")
    assert args.rebuild_cache is False
    assert args.split_id == hf_split_id()


def test_options():
    args = parse_args(["--kind", "plp", "--profile", "timit_matlab",
                       "--components", "128", "--out", "m",
                       "--rebuild-cache"])
    assert (args.kind, args.profile) == ("plp", "timit_matlab")
    assert args.components == 128
    assert args.rebuild_cache is True


def test_unknown_kind_is_rejected():
    with pytest.raises(SystemExit):
        parse_args(["--kind", "fbank"])


def test_model_name():
    assert model_name("mfcc", "timit_matlab", 64) == \
        "mfcc_timit_matlab_gmm64"


def small_features():
    rng = np.random.default_rng(0)
    return np.concatenate([rng.normal(0, 1, size=(300, 3)),
                           rng.normal(5, 1, size=(300, 3))]).astype(
                               np.float32)


def test_train_from_features_writes_model_and_log(tmp_path):
    args = parse_args(["--components", "2", "--n-iter", "4",
                       "--out", str(tmp_path)])
    meta = {"n_rows": 12, "dataset_revision": "d" * 40,
            "excluded_sa_rows": 3}
    log = train_from_features(small_features(), meta, args)
    gmm, info = load_gmm(tmp_path / "mfcc_timit_matlab_gmm2.npz")
    assert gmm.n_components == 2
    assert info["training_rows"] == 12
    assert info["split_id"] == hf_split_id()
    assert info["training_frames"] == 600
    on_disk = json.loads(
        (tmp_path / "mfcc_timit_matlab_gmm2.json").read_text())
    assert on_disk["content_sha256"] == gmm_content_sha256(gmm)
    assert len(log["file_sha256"]) == 64
    assert len(log["ll_history"]) == 5
    assert log["ll_history"][-1] > log["ll_history"][0]
    assert [len(level) for level in log["lbg_distortion_history"]][0] == 1
    assert log["excluded_sa_rows"] == 3
    assert 0 < log["smallest_weight"] <= 0.5


def test_detailed_training_matches_train_gmm():
    data = small_features()
    gmm, history = train_gmm(data, 2, n_iter=3)
    result = train_gmm_detailed(data, 2, n_iter=3)
    assert result.log_likelihood_history == history
    assert np.array_equal(result.gmm.means, gmm.means)
    assert len(result.lbg_distortion_history) == 2  # sizes 1 and 2


def test_content_hash_is_deterministic_and_parameter_sensitive():
    data = small_features()
    first = train_gmm(data, 2, n_iter=2)[0]
    second = train_gmm(data, 2, n_iter=2)[0]
    assert gmm_content_sha256(first) == gmm_content_sha256(second)
    other = train_gmm(data, 2, n_iter=0)[0]
    assert gmm_content_sha256(first) != gmm_content_sha256(other)


def make_cache(tmp_path, exclude_sa):
    import pyarrow as pa
    import pyarrow.parquet as pq
    rng = np.random.default_rng(0)
    audio = [{"array": (0.1 * rng.normal(size=8000)).astype("float32")
              .tolist(), "sampling_rate": 16000}]
    source = tmp_path / "t.parquet"
    pq.write_table(pa.table({"audio": audio,
                             "sentence": ["Combine all."]}), source)
    return build_feature_cache("train", "mfcc", "timit_matlab", tmp_path,
                               exclude_sa=exclude_sa,
                               parquet_paths=[source])


def test_get_features_accepts_a_matching_cache(tmp_path):
    make_cache(tmp_path, exclude_sa=True)
    args = parse_args(["--features-dir", str(tmp_path)])
    assert get_features(args)[0].shape[1] == 39


def test_get_features_refuses_a_mismatched_cache(tmp_path):
    make_cache(tmp_path, exclude_sa=False)
    args = parse_args(["--features-dir", str(tmp_path)])
    with pytest.raises(SystemExit, match="--rebuild-cache"):
        get_features(args)


def test_rebuild_cache_replaces_a_mismatched_cache(tmp_path, monkeypatch):
    make_cache(tmp_path, exclude_sa=False)
    calls = []

    def fake_build(split, kind, profile, out_dir):
        calls.append(split)
        return make_cache(tmp_path, exclude_sa=True)

    monkeypatch.setattr("qbestd.ml.train.build_feature_cache", fake_build)
    args = parse_args(["--features-dir", str(tmp_path), "--rebuild-cache"])
    assert get_features(args)[0].shape[1] == 39
    assert calls == ["train"]


def test_manifest_training_uses_rows_of_both_hf_splits(tmp_path,
                                                       monkeypatch):
    monkeypatch.setattr("qbestd.data.text_split.TEST_QUOTA",
                        {"multi": 1, "single": 1})
    import qbestd.ml.train as train
    from qbestd.data.text_split import (
        build_text_split,
        split_id,
        write_split_manifest,
    )
    rows = [("train", 0, "alpha beta"), ("train", 1, "gamma delta"),
            ("test", 0, "alpha beta"), ("test", 1, "epsilon zeta")]
    write_split_manifest(tmp_path / "m.tsv", build_text_split(rows, []))
    caches = {}
    for hf_split, value in (("train", 1.0), ("test", 5.0)):
        features = np.full((4, 3), value, np.float32)
        meta = {"dataset_revision": "d" * 40, "excluded_sa_rows": 1}
        caches[hf_split] = (features, np.array([0, 2, 4]), np.array([0, 1]),
                            meta)
    monkeypatch.setattr(train, "load_split_cache",
                        lambda args, hf_split: caches[hf_split])
    args = parse_args(["--split-manifest", str(tmp_path / "m.tsv")])
    features, _, keys, meta = train.get_manifest_features(args)
    assert meta["n_rows"] == len(keys) and len(keys) >= 1
    assert meta["excluded_sa_rows"] >= 1
    assert features.shape == (2 * len(keys), 3)
    assert {k[0] for k in keys} <= {"train", "test"}
    assert split_id(tmp_path / "m.tsv").startswith("textdisjoint_q20_v1-")


def test_split_id_option_is_stored_in_the_model(tmp_path):
    args = parse_args(["--components", "2", "--n-iter", "1", "--split-id",
                       "textdisjoint_q20_v1-abc", "--out", str(tmp_path)])
    meta = {"n_rows": 1, "dataset_revision": "d" * 40,
            "excluded_sa_rows": 0}
    train_from_features(small_features(), meta, args)
    info = load_gmm(tmp_path / "mfcc_timit_matlab_gmm2.npz")[1]
    assert info["split_id"] == "textdisjoint_q20_v1-abc"


def test_hf_split_id_uses_twelve_hex_of_the_revision():
    assert hf_split_id("0123456789abcdef" * 2 + "01234567") ==         "hf-0123456789ab-nonsa"
