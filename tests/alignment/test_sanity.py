import numpy as np
import pytest

from qbestd.alignment.manifest import WordSegment
from qbestd.alignment.sanity import (
    SA_SENTENCE,
    cut_segment,
    iqr_outliers,
    pick_words,
    read_rows_file,
    relative_start_spread,
    segment_energy_check,
)


def seg(row, word, start, end, index=0):
    return WordSegment("train", row, index, word, start, end)


def test_read_rows_file(tmp_path):
    path = tmp_path / "rows.tsv"
    path.write_text("row_index\tduration_s\tsentence\n3\t1.5000\ta b\n")
    assert read_rows_file(path) == {3: (1.5, "a b")}


def test_iqr_outliers_flags_only_far_values():
    values = [0.30, 0.31, 0.32, 0.29, 0.30, 0.31, 0.9]
    assert iqr_outliers(values).tolist() == [False] * 6 + [True]


def test_relative_start_spread_uses_only_sa_rows():
    rows = {0: (3.0, SA_SENTENCE.capitalize() + "."), 1: (2.0, "other text"),
            2: (4.0, SA_SENTENCE)}
    segments = [seg(0, "dark", 1.5, 1.9), seg(1, "dark", 1.0, 1.2),
                seg(2, "dark", 2.0, 2.4), seg(2, "suit", 2.4, 2.8)]
    result = relative_start_spread(segments, rows)
    assert result["n_rows"] == 2
    assert result["min"] == pytest.approx(0.5)
    assert result["max"] == pytest.approx(0.5)
    assert result["outlier_rows"] == []


def test_relative_start_spread_reports_outlier_row():
    rows = {i: (2.0, SA_SENTENCE) for i in range(9)}
    segments = [seg(i, "dark", 0.60 + 0.01 * i, 0.9) for i in range(8)]
    segments.append(seg(8, "dark", 1.8, 1.95))
    assert relative_start_spread(segments, rows)["outlier_rows"] == [8]


def test_relative_start_spread_none_without_match():
    assert relative_start_spread([seg(0, "dark", 0, 1)],
                                 {0: (1.0, "x")}) is None


def tone_then_silence():
    rng = np.random.default_rng(0)
    loud = 0.3 * rng.normal(size=8000)
    hiss = 0.001 * rng.normal(size=2400)
    silence = np.zeros(5600)
    return np.concatenate([loud, hiss, silence]).astype(np.float32)


def test_energy_check_passes_on_loud_word():
    result = segment_energy_check(tone_then_silence(),
                                  seg(0, "a", 0.1, 0.4))
    assert result["ok"]


def test_energy_check_fails_on_silent_word():
    result = segment_energy_check(tone_then_silence(),
                                  seg(0, "a", 0.7, 0.95))
    assert not result["ok"]


def test_energy_check_handles_word_shorter_than_a_frame_step():
    result = segment_energy_check(tone_then_silence(),
                                  seg(0, "a", 0.101, 0.103))
    assert result["ok"]


def test_cut_segment_pads_and_clips_to_the_signal():
    audio = np.arange(16000, dtype=np.float32)
    clip = cut_segment(audio, seg(0, "a", 0.5, 0.6))
    assert len(clip) == int(round(0.14 * 16000))
    assert clip[0] == 0.48 * 16000
    edge = cut_segment(audio, seg(0, "a", 0.0, 1.0))
    assert len(edge) == 16000


def test_pick_words_is_reproducible_and_distinct():
    segments = {"train": [seg(i, "w", 0, 1) for i in range(30)],
                "test": [seg(i, "v", 0, 1) for i in range(30)]}
    first = pick_words(segments, 10, seed=1)
    assert first == pick_words(segments, 10, seed=1)
    assert len(set((s, w.row_index, w.word) for s, w in first)) == 10
