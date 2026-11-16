from types import SimpleNamespace

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from qbestd.data.warped_cache import build_warped_caches
from qbestd.eval.query_features import clip_query_features
from qbestd.eval.timit_queries import QueryExample
from qbestd.eval.vtln_eval import (
    clip_warp_features,
    read_source_alphas,
    vtln_inputs,
)
from qbestd.features.extract import extract_warped_bank
from qbestd.features.profiles import get_profile
from qbestd.ml.gmm import train_gmm

RATE = 16000
WARPS = (0.9, 1.0, 1.1)
KIND, PROFILE = "mfcc", "timit_matlab"
CONFIG = get_profile(PROFILE, KIND)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("vtlneval")
    rng = np.random.default_rng(0)
    waves = [0.1 * rng.normal(size=n).astype("float32")
             for n in (12000, 14000, 16000)]
    audio = [{"array": w.tolist(), "sampling_rate": RATE} for w in waves]
    sentences = ["Combine all the ingredients.", "Chip postponed alimony.",
                 "The boy ran home."]
    parquet = tmp / "t.parquet"
    pq.write_table(pa.table({"audio": audio, "sentence": sentences}), parquet)
    built = build_warped_caches("train", KIND, PROFILE, tmp / "f", WARPS,
                                parquet_paths=[parquet])
    paths = {a: {"train": p} for a, p in built.items()}
    gmm = train_gmm(rng.normal(size=(400, 39)), 2, n_iter=2)[0]
    rows = {("train", i): SimpleNamespace(audio=waves[i].astype("float64"),
                                          sample_rate=RATE)
            for i in range(3)}
    return paths, gmm, rows


def example(row, start=0.1, end=0.5):
    return QueryExample("kw", row, 0, start, end, "train")


def test_clip_features_at_unit_warp_equal_the_plain_clip_features(world):
    _, _, rows = world
    ex = example(0)
    row = rows[("train", 0)]
    plain = clip_query_features(row.audio, RATE, ex, KIND, CONFIG)
    from qbestd.eval.timit_queries import cut_clip
    bank = extract_warped_bank(cut_clip(row.audio, RATE, ex), RATE, KIND,
                               WARPS, CONFIG)
    assert np.array_equal(bank[1.0], plain)


def test_a_clip_is_warped_from_its_own_audio(world):
    _, gmm, rows = world
    clip = rows[("train", 1)].audio[:6000]
    features, alpha = clip_warp_features(clip, RATE, KIND, CONFIG, gmm,
                                         WARPS)
    bank = extract_warped_bank(clip, RATE, KIND, WARPS, CONFIG)
    assert alpha in WARPS and np.array_equal(features, bank[alpha])


def test_a_clip_too_short_for_a_frame_raises(world):
    _, gmm, _ = world
    with pytest.raises(ValueError, match="too short"):
        clip_warp_features(np.zeros(100), RATE, KIND, CONFIG, gmm, WARPS)


def test_end_to_end_inputs_for_documents_and_queries(world, tmp_path):
    paths, gmm, rows = world
    examples = [example(0), example(1, 0.2, 0.6), example(2, 0.0, 0.00001)]
    source = {("train", 0): 1.0, ("train", 1): 0.9}
    grams, queries, info = vtln_inputs(
        gmm, [("train", 0), ("train", 2)], examples, rows, paths, KIND,
        PROFILE, CONFIG, source, WARPS)
    assert len(grams) == 2 and all(g.shape[1] == 2 for g in grams)
    assert all(np.allclose(g.sum(axis=1), 1.0) for g in grams)
    assert len(queries) == 3 and len(queries[2]) == 0  # too-short clip
    assert info["query_features"] == "clip"
    assert sum(info["test_warp_histogram"].values()) == 2
    assert sum(info["query_warp_histogram"].values()) == 2
    assert info["n_queries_with_source_alpha"] == 2
    assert 0.0 <= info["share_queries_alpha_differs_from_source"] <= 1.0


def test_source_alphas_read_back_and_a_missing_file_is_empty(tmp_path):
    path = tmp_path / "a.tsv"
    path.write_text("hf_split\trow_index\talpha_ours\talpha_thesis\n"
                    "train\t3\t0.92\t1.08\ntest\t4\t1.00\t1.00\n")
    assert read_source_alphas(path) == {("train", 3): 0.92,
                                        ("test", 4): 1.0}
    assert read_source_alphas(tmp_path / "none.tsv") == {}


@pytest.mark.parametrize("model_type, flags", [
    ("plain", ["--vtln"]), ("vtln", [])])
def test_run_timit_refuses_the_wrong_model_type(world, tmp_path, model_type,
                                                flags):
    from qbestd.data.feature_cache import feature_fingerprint, hf_split_id
    from qbestd.eval.model_guard import ModelMismatchError
    from qbestd.eval.run_timit import main
    from qbestd.ml.gmm import save_gmm
    _, gmm, _ = world
    info = {"kind": KIND, "profile": PROFILE, "split_id": hf_split_id(),
            "feature_fingerprint": feature_fingerprint(KIND, PROFILE),
            "model_type": model_type}
    save_gmm(tmp_path / "m.npz", gmm, info)
    with pytest.raises(ModelMismatchError, match="model_type"):
        main(["--gmm", str(tmp_path / "m.npz"), "--allow-dirty", *flags])
