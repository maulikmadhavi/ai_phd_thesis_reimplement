from pathlib import Path

import numpy as np
import pytest

from qbestd.alignment.manifest import read_manifest
from qbestd.alignment.run import (
    limited,
    parse_args,
    run_split,
    summarize_split,
    write_rows_file,
)
from qbestd.data.timit_hf import TimitRow


class FakeAligner:
    """Words of 0.2 s each; the 2-word rows end past the audio length."""

    def align_batch(self, audios, transcripts, languages=None):
        out = []
        for audio, words in zip(audios, transcripts):
            if not words:
                out.append(ValueError("empty transcript"))
                continue
            out.append([{"word": word, "start": 0.2 * i, "end": 0.2 * i + 0.2}
                        for i, word in enumerate(words)])
        return out


def make_row(index, sentence, seconds):
    audio = np.zeros(int(16000 * seconds), dtype=np.float32)
    return TimitRow("test", index, sentence, audio, 16000)


def test_defaults():
    args = parse_args([])
    assert args.split == "all"
    assert args.device == "cuda"
    assert args.batch_size == 16
    assert args.out == Path("outputs/alignment")
    assert args.limit is None


def test_options():
    args = parse_args(["--split", "test", "--device", "cpu",
                       "--batch-size", "4", "--out", "x", "--limit", "3"])
    assert (args.split, args.device, args.batch_size, args.limit) == (
        "test", "cpu", 4, 3)


def test_bad_split_is_rejected():
    with pytest.raises(SystemExit):
        parse_args(["--split", "dev"])


def test_limited_stops_early():
    assert list(limited(iter(range(10)), 3)) == [0, 1, 2]
    assert list(limited(iter(range(3)), None)) == [0, 1, 2]


def test_summarize_counts_and_percentiles():
    summary = summarize_split([0.1, 0.2, 0.3], 2, 1, [(0, "a"), (0, "b"),
                                                       (1, "c")], 12.34)
    assert summary["rows"] == 2
    assert summary["failed_rows"] == 1
    assert summary["words"] == 3
    assert summary["violations"] == 3
    assert summary["rows_with_violations"] == 2
    assert summary["word_duration_s"]["p50"] == pytest.approx(0.2)
    assert summary["word_duration_s"]["min"] == pytest.approx(0.1)
    assert summary["runtime_s"] == 12.3


def test_summarize_empty_split():
    summary = summarize_split([], 0, 0, [], 0.0)
    assert summary["words"] == 0
    assert summary["word_duration_s"] == {"min": None, "max": None}


def test_write_rows_file_flattens_whitespace(tmp_path):
    path = tmp_path / "rows.tsv"
    write_rows_file(path, [(0, 1.23456, "a  b\tc")])
    assert path.read_text().splitlines() == [
        "row_index\tduration_s\tsentence", "0\t1.2346\ta b c"]


def test_run_split_writes_files_and_reports_violations(tmp_path):
    rows = [make_row(0, "she had", 1.0),
            make_row(1, "one two three", 0.5),   # last word ends at 0.6 > 0.5
            make_row(2, " . ", 1.0)]             # empty transcript: failed
    summary, failures = run_split(iter(rows), "test", FakeAligner(), 2,
                                  tmp_path)
    assert summary["rows"] == 3
    assert summary["failed_rows"] == 1
    assert [f.row_index for f in failures] == [2]
    assert summary["words"] == 5
    assert [row for row, _ in summary["violation_list"]] == [1]
    segments, provenance = read_manifest(tmp_path / "timit_hf_words_test.tsv")
    assert len(segments) == 5
    assert set(provenance) == {"model", "dataset"}
    lines = (tmp_path / "timit_hf_rows_test.tsv").read_text().splitlines()
    assert lines[1] == "0\t1.0000\tshe had"
    assert len(lines) == 4
