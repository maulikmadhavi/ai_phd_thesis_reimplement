import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from qbestd.data import timit_hf
from qbestd.data.timit_hf import (
    TimitRow,
    download_timit_parquet,
    iter_timit_rows,
    normalize_transcript,
)


def write_parquet(path, rates=(16000, 16000)):
    audio = [{"array": [0.0, 0.5, -0.5][: 2 + index], "sampling_rate": rate}
             for index, rate in enumerate(rates)]
    sentences = ["She had your dark suit. ", "Don't ask me"][: len(rates)]
    table = pa.table({"audio": audio, "sentence": sentences})
    pq.write_table(table, path)
    return path


def test_rows_come_back_in_order_with_float32_audio(tmp_path):
    path = write_parquet(tmp_path / "a.parquet")
    rows = list(iter_timit_rows([path], "test", batch_size=1))
    assert [row.row_index for row in rows] == [0, 1]
    assert isinstance(rows[0], TimitRow)
    assert rows[0].split == "test"
    assert rows[0].audio.dtype == np.float32
    assert rows[0].audio.tolist() == [0.0, 0.5]
    assert rows[1].sentence == "Don't ask me"
    assert rows[1].sample_rate == 16000


def test_row_index_continues_across_files(tmp_path):
    first = write_parquet(tmp_path / "a.parquet")
    second = write_parquet(tmp_path / "b.parquet")
    rows = list(iter_timit_rows([first, second], "train"))
    assert [row.row_index for row in rows] == [0, 1, 2, 3]


def test_wrong_sample_rate_raises(tmp_path):
    path = write_parquet(tmp_path / "a.parquet", rates=(16000, 8000))
    with pytest.raises(ValueError, match="row 1.*8000"):
        list(iter_timit_rows([path], "test"))


@pytest.mark.parametrize("sentence, expected", [
    ("She had your dark suit.", ["she", "had", "your", "dark", "suit"]),
    ("Don't  ask\tme ", ["don't", "ask", "me"]),
    ('"Hello," she said!', ["hello", "she", "said"]),
    ("  ...  ", []),
    ("", []),
    ("Rock-n-roll's fun", ["rock-n-roll's", "fun"]),
])
def test_normalize_transcript(sentence, expected):
    assert normalize_transcript(sentence) == expected


def test_unknown_split_raises():
    with pytest.raises(ValueError, match="Unknown split"):
        download_timit_parquet("dev")


def test_pinned_revision_is_a_full_sha():
    assert len(timit_hf.TIMIT_HF_REVISION) == 40
    assert timit_hf.SPLIT_FILES["test"] == ("data/test-00000-of-00001.parquet",)
