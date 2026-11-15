"""Loader for the Hugging Face ``Siyong/speech_timit`` parquet files.

The dataset is read at a pinned revision so every run sees the same rows.
Parquet files go to the Hugging Face cache, never into the repository.
Rows are read in batches with pyarrow; every row must be 16 kHz.
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

TIMIT_HF_REPO = "Siyong/speech_timit"
TIMIT_HF_REVISION = "ef7bffd88de7065b8b1c2fdc76e8364921c30e58"
EXPECTED_SAMPLE_RATE = 16000
SPLIT_FILES = {
    "train": ("data/train-00000-of-00002.parquet",
              "data/train-00001-of-00002.parquet"),
    "test": ("data/test-00000-of-00001.parquet",),
}
_EDGE_PUNCTUATION = re.compile(r"^[^\w]+|[^\w]+$")


@dataclass(frozen=True)
class TimitRow:
    """One utterance; ``row_index`` counts rows within ``split`` from 0."""

    split: str
    row_index: int
    sentence: str
    audio: np.ndarray
    sample_rate: int


def download_timit_parquet(split):
    """Download (or find in the cache) the parquet files of ``split``.

    Raises:
        ValueError: if ``split`` is not "train" or "test".
    """
    if split not in SPLIT_FILES:
        raise ValueError(f"Unknown split '{split}'; use {tuple(SPLIT_FILES)}")
    from huggingface_hub import hf_hub_download  # lazy: no network in tests
    return [Path(hf_hub_download(TIMIT_HF_REPO, name, repo_type="dataset",
                                 revision=TIMIT_HF_REVISION))
            for name in SPLIT_FILES[split]]


def iter_timit_rows(parquet_paths, split, batch_size=64):
    """Yield :class:`TimitRow` for every row of the files, in order.

    Raises:
        ValueError: if any row's sampling rate is not 16000.
    """
    import pyarrow.parquet as pq
    row_index = 0
    for path in parquet_paths:
        reader = pq.ParquetFile(path)
        for batch in reader.iter_batches(batch_size=batch_size):
            for record in batch.to_pylist():
                rate = int(record["audio"]["sampling_rate"])
                if rate != EXPECTED_SAMPLE_RATE:
                    raise ValueError(
                        f"{split} row {row_index} has sample rate {rate}, "
                        f"expected {EXPECTED_SAMPLE_RATE}")
                yield TimitRow(
                    split, row_index, record["sentence"],
                    np.asarray(record["audio"]["array"], dtype=np.float32),
                    rate)
                row_index += 1


def normalize_transcript(sentence):
    """Words of a TIMIT sentence: NFC, lowercase, edge punctuation stripped.

    Inner apostrophes are kept ("don't"); empty tokens are dropped. Stage 7
    keyword matching must use this same function.
    """
    text = unicodedata.normalize("NFC", sentence).lower()
    words = (_EDGE_PUNCTUATION.sub("", token) for token in text.split())
    return [word for word in words if word]
