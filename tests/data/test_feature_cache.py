import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from qbestd.data.feature_cache import (
    SA_SENTENCES,
    build_feature_cache,
    cache_path,
    is_sa_sentence,
    load_feature_cache,
    utterance_slice,
)
from qbestd.data.timit_hf import normalize_transcript

RATE = 16000


def make_parquet(path, sentences, lengths):
    rng = np.random.default_rng(0)
    audio = [{"array": (0.1 * rng.normal(size=n)).astype("float32").tolist(),
              "sampling_rate": RATE} for n in lengths]
    pq.write_table(pa.table({"audio": audio, "sentence": sentences}), path)
    return path


@pytest.fixture
def parquet(tmp_path):
    sentences = ["She had your dark suit in greasy wash water all year.",
                 "Combine all the ingredients.",
                 "Don't ask me to carry an oily rag like that",
                 "Chip postponed alimony."]
    return make_parquet(tmp_path / "t.parquet", sentences,
                        [8000, 12000, 8000, 6000])


def test_is_sa_sentence_matches_both_texts_only():
    for text in SA_SENTENCES:
        assert is_sa_sentence(normalize_transcript(text + "."))
    assert not is_sa_sentence(["she", "had"])
    assert not is_sa_sentence([])


def test_sa_rows_are_excluded_and_counted(tmp_path, parquet):
    path, meta = build_feature_cache("train", "mfcc", "timit_matlab",
                                     tmp_path / "out",
                                     parquet_paths=[parquet])
    features, offsets, rows, loaded = load_feature_cache(path)
    assert rows.tolist() == [1, 3]
    assert meta["excluded_sa_rows"] == 2
    assert loaded == meta
    assert features.dtype == np.float32
    assert features.shape[1] == 39


def test_offsets_index_each_utterance_correctly(tmp_path, parquet):
    path, _ = build_feature_cache("train", "mfcc", "timit_matlab", tmp_path,
                                  parquet_paths=[parquet])
    features, offsets, rows, meta = load_feature_cache(path)
    # 12000 samples -> floor(1 + (12000 - 400) / 160) = 73 frames; 6000 -> 36
    assert np.diff(offsets).tolist() == [73, 36]
    assert offsets[-1] == len(features) == meta["n_frames"] == 109
    assert utterance_slice(features, offsets, 1).shape == (36, 39)


def test_include_sa_keeps_every_row(tmp_path, parquet):
    path, meta = build_feature_cache("train", "mfcc", "timit_matlab",
                                     tmp_path, exclude_sa=False,
                                     parquet_paths=[parquet])
    assert load_feature_cache(path)[2].tolist() == [0, 1, 2, 3]
    assert meta["excluded_sa_rows"] == 0


def test_metadata_records_profile_and_revision(tmp_path, parquet):
    _, meta = build_feature_cache("train", "plp", "timit_matlab", tmp_path,
                                  parquet_paths=[parquet])
    assert meta["profile"] == "timit_matlab"
    assert meta["kind"] == "plp"
    assert meta["sample_rate"] == 16000
    assert len(meta["dataset_revision"]) == 40


def test_row_too_short_for_a_frame_is_skipped(tmp_path):
    source = make_parquet(tmp_path / "s.parquet", ["tiny one", "long enough"],
                          [100, 8000])
    path, meta = build_feature_cache("test", "mfcc", "timit_matlab", tmp_path,
                                     parquet_paths=[source])
    assert load_feature_cache(path)[2].tolist() == [1]
    assert meta["skipped_short_rows"] == 1


def test_cache_path_is_named_by_split_kind_and_profile(tmp_path):
    name = cache_path(tmp_path, "train", "mfcc", "timit_matlab").name
    assert name == "train_mfcc_timit_matlab.npz"


def test_unknown_profile_raises(tmp_path, parquet):
    with pytest.raises(ValueError):
        build_feature_cache("train", "mfcc", "nope", tmp_path,
                            parquet_paths=[parquet])
