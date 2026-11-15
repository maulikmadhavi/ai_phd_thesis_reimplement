import ast
import shutil
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from qbestd.data.feature_cache import (
    FEATURE_CACHE_VERSION,
    FEATURE_SOURCE_FILES,
    ROW_SELECTION_VERSION,
    ROW_SOURCE_FILES,
    SA_SENTENCES,
    CacheMismatchError,
    build_feature_cache,
    cache_path,
    feature_fingerprint,
    feature_source_digest,
    is_sa_sentence,
    load_feature_cache,
    row_source_digest,
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


def import_targets(node, name):
    """Dotted module names an import node may refer to. ``name`` is the
    importing file relative to the package (``features/extract.py``)."""
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    base = node.module.split(".") if node.module else []
    if node.level:
        package = ["qbestd"] + name.split("/")[:-1]
        base = package[:len(package) - (node.level - 1)] + base
    return [".".join(base)] + [".".join(base + [a.name]) for a in node.names]


def transitive_feature_imports(root=PACKAGE, start="features/extract.py"):
    """Files under ``audio/`` and ``features/`` of the package at ``root``
    reached from ``start`` by ``qbestd`` imports, absolute or relative,
    found by parsing the source (``__init__`` skipped). It misses dynamic
    imports and code outside those two packages."""
    seen, todo = set(), [start]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        for node in ast.walk(ast.parse((root / name).read_text("utf-8"))):
            for module in import_targets(node, name):
                parts = module.split(".")
                if parts[0] == "qbestd" and parts[1:2] and parts[1] in (
                        "audio", "features") and len(parts) > 2:
                    candidate = "/".join(parts[1:3]) + ".py"
                    if (root / candidate).exists():
                        todo.append(candidate)
    return seen


def test_source_files_are_the_transitive_feature_imports():
    assert set(FEATURE_SOURCE_FILES) == transitive_feature_imports()
    assert list(FEATURE_SOURCE_FILES) == sorted(FEATURE_SOURCE_FILES)


@pytest.mark.parametrize("import_line", [
    "from qbestd.features.newhelper import value",
    "from .newhelper import value",
    "from . import newhelper",
    "import qbestd.features.newhelper",
])
def test_closure_finds_a_new_helper_imported_by_extract(tmp_path,
                                                        import_line):
    root = tmp_path / "qbestd"
    for package in ("audio", "features"):
        shutil.copytree(PACKAGE / package, root / package,
                        ignore=shutil.ignore_patterns("__pycache__"))
    (root / "features" / "newhelper.py").write_text("value = 1\n", "utf-8")
    extract = root / "features" / "extract.py"
    extract.write_text(import_line + "\n" + extract.read_text("utf-8"),
                       "utf-8")
    missing = transitive_feature_imports(root) - set(FEATURE_SOURCE_FILES)
    assert missing == {"features/newhelper.py"}


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
                        lambda *args: "another digest")
    assert feature_fingerprint("mfcc", "timit_matlab", True) != base


def test_row_source_digest_covers_timit_hf_and_ignores_crlf(tmp_path):
    assert ROW_SOURCE_FILES == ("data/timit_hf.py",)
    target = tmp_path / "data" / "timit_hf.py"
    target.parent.mkdir()
    original = (PACKAGE / "data" / "timit_hf.py").read_bytes()
    lf = original.replace(b"\r\n", b"\n")
    target.write_bytes(lf)
    assert row_source_digest(tmp_path) == row_source_digest()
    target.write_bytes(lf.replace(b"\n", b"\r\n"))
    assert row_source_digest(tmp_path) == row_source_digest()
    target.write_bytes(lf + b"# edit\n")
    assert row_source_digest(tmp_path) != row_source_digest()


def test_fingerprint_changes_with_the_timit_hf_bytes(tmp_path, monkeypatch):
    base = feature_fingerprint("mfcc", "timit_matlab", True)
    target = tmp_path / "data" / "timit_hf.py"
    target.parent.mkdir()
    target.write_bytes((PACKAGE / "data" / "timit_hf.py").read_bytes()
                       + b"# edit\n")
    monkeypatch.setattr("qbestd.data.feature_cache.row_source_digest",
                        lambda: row_source_digest(tmp_path))
    assert feature_fingerprint("mfcc", "timit_matlab", True) != base


def test_fingerprint_changes_with_the_sa_tokens(monkeypatch):
    base = feature_fingerprint("mfcc", "timit_matlab", True)
    monkeypatch.setattr("qbestd.data.feature_cache.SA_TOKENS",
                        (("other", "text"),))
    assert feature_fingerprint("mfcc", "timit_matlab", True) != base


def test_fingerprint_changes_with_the_row_selection_version(monkeypatch):
    base = feature_fingerprint("mfcc", "timit_matlab", True)
    monkeypatch.setattr("qbestd.data.feature_cache.ROW_SELECTION_VERSION",
                        ROW_SELECTION_VERSION + 1)
    assert feature_fingerprint("mfcc", "timit_matlab", True) != base
