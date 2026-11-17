from types import SimpleNamespace

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import qbestd.eval.s1_checks as s1
from qbestd.data.feature_cache import warped_cache_path
from qbestd.data.warped_cache import build_warped_caches
from qbestd.data.split_selection import SplitSelection

RATE = 16000
KIND, PROFILE = "mfcc", "timit_matlab"


def test_final_alphas_read_the_last_iteration(tmp_path, monkeypatch):
    trace = tmp_path / "stem_vtln5_trace"
    trace.mkdir()
    for k, ours in ((3, "0.90"), (4, "1.10")):
        (trace / f"iter{k}_alphas.tsv").write_text(
            "hf_split\trow_index\talpha_ours\talpha_thesis\n"
            f"train\t2\t{ours}\t{2 - float(ours):.2f}\n"
            f"test\t5\t1.00\t1.00\n")
    monkeypatch.setattr(s1, "MODELS", tmp_path)
    keys, ours, thesis = s1.read_final_alphas("stem")
    assert keys == [("train", 2), ("test", 5)]
    assert list(ours) == [1.10, 1.00] and list(thesis) == [0.90, 1.00]


def test_f0_is_computed_saved_and_read_back(tmp_path, monkeypatch):
    t = np.arange(RATE) / RATE
    tone = sum(np.sin(2 * np.pi * 150 * h * t) / h for h in range(1, 6))
    rows = [SimpleNamespace(row_index=i, audio=tone, sample_rate=RATE)
            for i in range(3)]
    monkeypatch.setattr(s1, "download_timit_parquet", lambda split: None)
    monkeypatch.setattr(s1, "iter_timit_rows", lambda paths, split: rows)
    keys = [("train", 0), ("train", 2)]
    first = s1.utterance_f0(keys, tmp_path / "f0.tsv")
    assert first == pytest.approx([150.0, 150.0], rel=0.03)
    monkeypatch.setattr(s1, "iter_timit_rows", lambda *a: 1 / 0)
    again = s1.utterance_f0(keys, tmp_path / "f0.tsv")  # from the file
    assert np.allclose(first, again, atol=1e-3)


def test_mean_c0_comes_from_the_unit_warp_cache(tmp_path):
    rng = np.random.default_rng(0)
    audio = [{"array": (0.1 * rng.normal(size=n)).astype("float32").tolist(),
              "sampling_rate": RATE} for n in (8000, 9000)]
    parquet = tmp_path / "t.parquet"
    pq.write_table(pa.table({"audio": audio,
                             "sentence": ["Chip postponed alimony.",
                                          "The boy ran home."]}), parquet)
    build_warped_caches("train", KIND, PROFILE, tmp_path, (0.9, 1.0, 1.1),
                        parquet_paths=[parquet])
    values = s1.mean_c0_at_unit_warp([("train", 1), ("train", 0)], KIND,
                                     PROFILE, tmp_path)
    from qbestd.data.feature_cache import feature_fingerprint, \
        load_feature_cache
    features, offsets, rows, _ = load_feature_cache(
        warped_cache_path(tmp_path, "train", KIND, PROFILE, 1.0),
        feature_fingerprint(KIND, PROFILE, warp_factor=1.0))
    assert values[0] == pytest.approx(
        features[offsets[1]:offsets[2], 0].mean())
    assert values[1] == pytest.approx(
        features[offsets[0]:offsets[1], 0].mean())


def test_order_check_counts_both_sides_and_gates_on_the_c0_offset(
        monkeypatch):
    rows = [SimpleNamespace(row_index=i, sample_rate=RATE,
                            audio=np.array([1.0, -1.0, 1.0, -1.0]) + 0.001 * i)
            for i in range(4)]
    monkeypatch.setattr(s1, "download_timit_parquet", lambda split: None)
    monkeypatch.setattr(s1, "iter_timit_rows", lambda paths, split: rows)
    selection = SplitSelection("s", {
        "train": {"train": frozenset({0, 1}), "test": frozenset()},
        "test": {"train": frozenset({3}), "test": frozenset()}})
    out = s1.order_check(selection)
    assert out["n_utterances"] == 3
    assert out["c0_offset"]["gate"] == 0.1
    assert out["c0_offset"]["gate_met"] is True
    assert out["ratio"]["max"] <= 1.0 + 1e-9


def test_order_check_fails_the_gate_for_a_large_offset(monkeypatch):
    rows = [SimpleNamespace(row_index=0, sample_rate=RATE,
                            audio=np.array([1.0, -1.0, 1.0, -1.0]) + 0.3)]
    monkeypatch.setattr(s1, "download_timit_parquet", lambda split: None)
    monkeypatch.setattr(s1, "iter_timit_rows", lambda paths, split: rows)
    selection = SplitSelection("s", {
        "train": {"train": frozenset({0}), "test": frozenset()},
        "test": {"train": frozenset(), "test": frozenset()}})
    assert s1.order_check(selection)["c0_offset"]["gate_met"] is False
