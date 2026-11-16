import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from qbestd.data.feature_cache import load_feature_cache
from qbestd.data.warped_cache import build_warped_caches
from qbestd.features.extract import extract_warped_bank
from qbestd.features.profiles import get_profile
from qbestd.ml.gmm import gmm_content_sha256, load_gmm, train_gmm
from qbestd.ml.vtln import WARP_FACTORS
from qbestd.ml.vtln_train import (
    estimate_clip_warp,
    estimate_test_warps,
    estimate_utterance_warps,
    peak_memory_mb,
    save_vtln_model,
    train_vtln,
    warp_histogram,
)

RATE = 16000
WARPS = (0.9, 1.0, 1.1)
KIND, PROFILE = "mfcc", "timit_matlab"
KEYS = [("train", i) for i in range(4)]


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("vtln")
    rng = np.random.default_rng(0)
    audio = [{"array": (0.1 * rng.normal(size=n)).astype("float32").tolist(),
              "sampling_rate": RATE} for n in (12000, 14000, 16000, 12000)]
    sentences = ["Combine all the ingredients.", "Chip postponed alimony.",
                 "The boy ran home.", "Wash the dishes now."]
    parquet = tmp / "t.parquet"
    pq.write_table(pa.table({"audio": audio, "sentence": sentences}), parquet)
    built = build_warped_caches("train", KIND, PROFILE, tmp / "feat", WARPS,
                                parquet_paths=[parquet])
    paths = {a: {"train": p} for a, p in built.items()}
    plain = train_gmm(np.random.default_rng(1).normal(size=(400, 39)), 2,
                      n_iter=2)[0]
    return paths, plain


def run(setup, n_iter):
    paths, plain = setup
    return train_vtln(paths, KEYS, KIND, PROFILE, plain, n_iter,
                      components=2, n_em_iter=3, warps=WARPS)


def test_warp_histogram_keeps_empty_warps():
    hist = warp_histogram([1.0, 1.0, 0.9], WARPS)
    assert hist == {"0.90": 1, "1.00": 2, "1.10": 0}
    assert len(warp_histogram([], WARP_FACTORS)) == 13


def test_utterance_warps_come_from_the_warp_list(setup):
    paths, plain = setup
    alphas, matrix = estimate_utterance_warps(paths, plain, KEYS, KIND,
                                              PROFILE, WARPS)
    assert matrix.shape == (4, 3) and set(alphas) <= set(WARPS)
    assert np.array_equal(alphas, np.array(WARPS)[matrix.argmax(axis=1)])


def test_each_iteration_leaves_one_record_and_a_new_model(setup):
    result = run(setup, 2)
    assert [r["iteration"] for r in result.iterations] == [0, 1]
    for record in result.iterations:
        assert sum(record["warp_histogram"].values()) == 4
        assert len(record["em_history"]) == 4
        assert len(record["model_content_sha256"]) == 64
    assert result.iterations[-1]["model_content_sha256"] == (
        gmm_content_sha256(result.gmm))
    assert len(result.alphas) == 4


def test_selected_warps_never_lower_the_likelihood_of_the_old_model(setup):
    paths, plain = setup
    result = run(setup, 1)
    _, matrix = estimate_utterance_warps(paths, plain, KEYS, KIND, PROFILE,
                                         WARPS)
    at_one = matrix[:, WARPS.index(1.0)].sum()
    offsets = load_feature_cache(paths[1.0]["train"])[1]
    record = result.iterations[0]
    assert record["mean_ll_init_on_selected"] * offsets[-1] >= at_one - 1e-6


def test_log_likelihood_on_the_selected_features_does_not_fall(setup):
    result = run(setup, 3)
    values = [r["mean_ll_new_on_selected"] for r in result.iterations]
    assert all(b >= a - 1e-6 for a, b in zip(values, values[1:]))


def test_model_and_log_survive_a_round_trip(setup, tmp_path):
    result = run(setup, 1)
    meta = {"kind": KIND, "profile": PROFILE, "split_id": "s", "n_vtln_iter": 1,
            "warps": list(WARPS), "feature_fingerprint": "f"}
    path = tmp_path / "m" / "vtln.npz"
    info = save_vtln_model(path, result, meta)
    gmm, loaded = load_gmm(path)
    assert loaded == info
    assert gmm_content_sha256(gmm) == gmm_content_sha256(result.gmm)
    assert path.with_suffix(".json").is_file()
    assert loaded["iterations"][0]["warp_histogram"]
    for field in meta:
        assert loaded[field] == meta[field]


def test_test_documents_get_warps_and_normalised_posteriorgrams(setup):
    paths, _ = setup
    final = run(setup, 1).gmm
    alphas, grams = estimate_test_warps(paths, final, KEYS[:3], KIND,
                                        PROFILE, WARPS)
    assert len(alphas) == len(grams) == 3
    for gram in grams:
        assert gram.shape[1] == 2
        assert np.allclose(gram.sum(axis=1), 1.0)


def test_a_clip_gets_its_own_warp(setup):
    _, plain = setup
    clip = 0.1 * np.random.default_rng(5).normal(size=6000)
    bank = extract_warped_bank(clip, RATE, KIND, WARPS,
                               config=get_profile(PROFILE, KIND))
    assert estimate_clip_warp(bank, plain) in WARPS


def test_peak_memory_is_positive_or_unknown():
    value = peak_memory_mb()
    assert value is None or value > 0


def test_the_plain_slot_refuses_a_vtln_model_and_the_metadata_names_it(
        setup, tmp_path):
    from qbestd.data.feature_cache import feature_fingerprint
    from qbestd.eval.model_guard import ModelMismatchError
    from qbestd.ml.gmm import save_gmm
    from qbestd.ml.vtln_train import load_plain_model, vtln_metadata
    _, plain = setup
    info = {"kind": KIND, "profile": PROFILE, "split_id": "s",
            "feature_fingerprint": feature_fingerprint(KIND, PROFILE),
            "n_iter": 7, "epsilon": 0.3, "var_floor_ratio": 0.02, "seed": 4}
    save_gmm(tmp_path / "plain.npz", plain, info)
    assert load_plain_model(tmp_path / "plain.npz", KIND, PROFILE, "s")
    meta = vtln_metadata(KIND, PROFILE, "s", 5, plain, info)
    assert meta["model_type"] == "vtln" and meta["n_vtln_iter"] == 5
    assert "n_iter" not in meta
    assert (meta["n_em_iter"], meta["epsilon"], meta["var_floor_ratio"],
            meta["seed"]) == (7, 0.3, 0.02, 4)
    save_gmm(tmp_path / "vtln.npz", plain, {**info, **meta})
    with pytest.raises(ModelMismatchError, match="model_type"):
        load_plain_model(tmp_path / "vtln.npz", KIND, PROFILE, "s")
