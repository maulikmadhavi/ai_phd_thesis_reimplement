import ast
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from qbestd.data.feature_cache import (
    FEATURE_CACHE_VERSION,
    FEATURE_SOURCE_FILES,
    SA_SENTENCES,
    CacheMismatchError,
    build_feature_cache,
    cache_path,
    feature_fingerprint,
    feature_source_digest,
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


def test_fingerprint_is_stored_and_accepted_on_load(tmp_path, parquet):
    path, meta = build_feature_cache("train", "mfcc", "timit_matlab",
                                     tmp_path, parquet_paths=[parquet])
    expected = feature_fingerprint("mfcc", "timit_matlab", True)
    assert meta["fingerprint"] == expected
    assert load_feature_cache(path, expected=expected)[3] == meta
    assert load_feature_cache(path)[3] == meta  # no check requested


def test_fingerprint_changes_with_every_ingredient(monkeypatch):
    base = feature_fingerprint("mfcc", "timit_matlab", True)
    assert feature_fingerprint("plp", "timit_matlab", True) != base
    assert feature_fingerprint("mfcc", "timit_matlab", False) != base
    assert feature_fingerprint("mfcc", "timit_matlab", True,
                               dataset_revision="x" * 40) != base
    monkeypatch.setattr("qbestd.data.feature_cache.FEATURE_CACHE_VERSION",
                        FEATURE_CACHE_VERSION + 1)
    assert feature_fingerprint("mfcc", "timit_matlab", True) != base


def test_fingerprint_changes_with_the_profile_config(monkeypatch):
    from qbestd.features.mfcc import MfccConfig
    base = feature_fingerprint("mfcc", "timit_matlab", True)
    monkeypatch.setattr(
        "qbestd.data.feature_cache.get_profile",
        lambda name, kind: MfccConfig(sample_rate=16000, high_hz=3000.0))
    assert feature_fingerprint("mfcc", "timit_matlab", True) != base


def test_cache_with_other_settings_is_never_silently_reused(tmp_path,
                                                            parquet):
    path, _ = build_feature_cache("train", "mfcc", "timit_matlab", tmp_path,
                                  exclude_sa=False, parquet_paths=[parquet])
    wanted = feature_fingerprint("mfcc", "timit_matlab", True)
    with pytest.raises(CacheMismatchError):
        load_feature_cache(path, expected=wanted)


def test_cache_without_fingerprint_is_rejected(tmp_path):
    path = tmp_path / "old.npz"
    np.savez(path, features=np.zeros((1, 39), np.float32),
             offsets=np.array([0, 1]), row_indices=np.array([0]),
             metadata=np.array("{}"))
    with pytest.raises(CacheMismatchError):
        load_feature_cache(path, expected="abc")


PACKAGE = Path(__file__).resolve().parents[2] / "src" / "qbestd"


def transitive_feature_imports(start="features/extract.py"):
    """Files under ``audio/`` and ``features/`` reached from ``start`` by
    ``qbestd`` imports, found by parsing the source (``__init__`` skipped)."""
    seen, todo = set(), [start]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        for node in ast.walk(ast.parse((PACKAGE / name).read_text("utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
                modules += [f"{node.module}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            else:
                continue
            for module in modules:
                parts = module.split(".")
                if parts[0] == "qbestd" and parts[1:2] and parts[1] in (
                        "audio", "features") and len(parts) > 2:
                    candidate = "/".join(parts[1:3]) + ".py"
                    if (PACKAGE / candidate).exists():
                        todo.append(candidate)
    return seen


def test_source_files_are_the_transitive_feature_imports():
    assert set(FEATURE_SOURCE_FILES) == transitive_feature_imports()
    assert list(FEATURE_SOURCE_FILES) == sorted(FEATURE_SOURCE_FILES)


def copy_sources(target):
    for name in FEATURE_SOURCE_FILES:
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        (target / name).write_bytes((PACKAGE / name).read_bytes())
    return target


def test_digest_matches_a_copy_and_changes_with_one_file(tmp_path):
    root = copy_sources(tmp_path)
    assert feature_source_digest(root) == feature_source_digest()
    edited = root / "features/deltas.py"
    edited.write_bytes(edited.read_bytes() + b"# edit\n")
    assert feature_source_digest(root) != feature_source_digest()


def test_digest_ignores_crlf_line_endings(tmp_path):
    root = copy_sources(tmp_path)
    changed = root / "features/mfcc.py"
    text = changed.read_bytes().replace(b"\r\n", b"\n")
    changed.write_bytes(text.replace(b"\n", b"\r\n"))
    assert changed.read_bytes() != text
    assert feature_source_digest(root) == feature_source_digest()


def test_fingerprint_changes_with_the_source_digest(monkeypatch):
    base = feature_fingerprint("mfcc", "timit_matlab", True)
    monkeypatch.setattr("qbestd.data.feature_cache.feature_source_digest",
                        lambda: "another digest")
    assert feature_fingerprint("mfcc", "timit_matlab", True) != base
