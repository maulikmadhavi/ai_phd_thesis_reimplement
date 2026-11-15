import json
from pathlib import Path

import numpy as np
import pytest

from qbestd.ml.gmm import (
    gmm_content_sha256,
    load_gmm,
    train_gmm,
    train_gmm_detailed,
)
from qbestd.ml.train import (
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


def test_options():
    args = parse_args(["--kind", "plp", "--profile", "htk_like",
                       "--components", "128", "--out", "m",
                       "--rebuild-cache"])
    assert (args.kind, args.profile, args.components) == ("plp", "htk_like",
                                                          128)
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
