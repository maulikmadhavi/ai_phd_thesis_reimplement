import os
import sys

import numpy as np
import pytest

from qbestd.alignment import word_aligner
from qbestd.alignment.manifest import FailedRow
from qbestd.alignment.word_aligner import (
    align_rows,
    align_rows_detailed,
    load_align_module,
    load_whisper_aligner,
    sha256_of_file,
)
from qbestd.data.timit_hf import TimitRow


class FakeAligner:
    """Records its calls; a word list longer than 3 returns an Exception."""

    def __init__(self):
        self.calls = []

    def align_batch(self, audios, transcripts, languages=None):
        self.calls.append((audios, transcripts, languages))
        out = []
        for words in transcripts:
            if len(words) > 3:
                out.append(ValueError("does not fit one window"))
            else:
                out.append([{"word": word, "start": 0.1 * i,
                             "end": 0.1 * i + 0.1}
                            for i, word in enumerate(words)])
        return out


def make_row(index, sentence, seconds=1.0):
    audio = np.zeros(int(16000 * seconds), dtype=np.float32)
    return TimitRow("test", index, sentence, audio, 16000)


def test_word_lists_not_strings_reach_the_aligner():
    aligner = FakeAligner()
    rows = [make_row(0, "She had. "), make_row(1, "Don't go")]
    list(align_rows(rows, aligner, batch_size=8))
    _, transcripts, languages = aligner.calls[0]
    assert transcripts == [["she", "had"], ["don't", "go"]]
    assert languages == ["en", "en"]


def test_segments_carry_indices_and_times():
    segments = list(align_rows([make_row(5, "a b")], FakeAligner()))
    assert [(s.row_index, s.word_index, s.word) for s in segments] == [
        (5, 0, "a"), (5, 1, "b")]
    assert segments[1].start_s == pytest.approx(0.1)


def test_batches_are_split_by_batch_size():
    aligner = FakeAligner()
    rows = [make_row(i, "a b") for i in range(5)]
    list(align_rows(rows, aligner, batch_size=2))
    assert [len(call[0]) for call in aligner.calls] == [2, 2, 1]


def test_exception_item_is_recorded_not_raised():
    failures = []
    rows = [make_row(0, "a b"), make_row(1, "a b c d e"), make_row(2, "c")]
    segments = list(align_rows(rows, FakeAligner(), 8, failures))
    assert {s.row_index for s in segments} == {0, 2}
    assert failures == [FailedRow("test", 1, "does not fit one window")]


def test_detailed_results_have_duration_and_word_count():
    results = list(align_rows_detailed([make_row(0, "a b", 2.0)],
                                       FakeAligner()))
    assert results[0].duration_s == pytest.approx(2.0)
    assert results[0].n_words == 2
    assert results[0].error is None


def test_empty_transcript_is_passed_through_as_empty_list():
    aligner = FakeAligner()
    results = list(align_rows_detailed([make_row(0, " . ")], aligner))
    assert aligner.calls[0][1] == [[]]
    assert results[0].n_words == 0


def test_batch_size_must_be_positive():
    with pytest.raises(ValueError):
        list(align_rows([make_row(0, "a")], FakeAligner(), batch_size=0))


def write_module(directory, body="VALUE = 41\n"):
    (directory / "align.py").write_text(body)
    return sha256_of_file(directory / "align.py")


def test_matching_hash_loads_module_without_touching_sys_path(tmp_path):
    digest = write_module(tmp_path)
    before = list(sys.path)
    module = load_align_module(tmp_path, expected_sha256=digest)
    assert module.VALUE == 41
    assert sys.path == before


def test_hash_mismatch_raises_and_does_not_execute(tmp_path):
    write_module(tmp_path, "raise SystemExit('executed')\n")
    with pytest.raises(ValueError, match="refusing to load"):
        load_align_module(tmp_path)


def test_loader_checks_hash_before_importing_torch(tmp_path, monkeypatch):
    write_module(tmp_path)
    monkeypatch.setattr(word_aligner, "download_snapshot",
                        lambda revision: tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        load_whisper_aligner("cpu")


def test_pinned_values():
    assert len(word_aligner.MODEL_REVISION) == 40
    assert len(word_aligner.ALIGN_PY_SHA256) == 64


@pytest.mark.skipif(os.environ.get("QBESTD_RUN_ALIGNER") != "1",
                    reason="set QBESTD_RUN_ALIGNER=1 (align env, downloads)")
def test_real_model_smoke():
    aligner = load_whisper_aligner(os.environ.get("QBESTD_DEVICE", "cuda"))
    row = make_row(0, "she had", seconds=2.0)
    segments = list(align_rows([row], aligner, batch_size=1))
    assert [s.word for s in segments] == ["she", "had"]
