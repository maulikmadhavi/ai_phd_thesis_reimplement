"""Whisper-based forced word aligner (Scicom-intl, CC BY-NC 4.0).

The model repository ships its own ``align.py``. It is loaded only after its
SHA-256 matches the value reviewed for the pinned revision, and the snapshot
directory is never put on ``sys.path``. torch is imported lazily, so this
module imports in the core environment.
"""

import hashlib
import importlib.util
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from qbestd.alignment.manifest import FailedRow, WordSegment
from qbestd.data.timit_hf import normalize_transcript

LOGGER = logging.getLogger(__name__)
MODEL_REPO = "Scicom-intl/Where-Words-Begin-and-End-Whisper-Large-V3"
MODEL_REVISION = "618763b1ed3ae17cb9a2062d6d4d0de436828c7a"
ALIGN_PY_NAME = "align.py"
ALIGN_PY_SHA256 = (
    "8f7a3590aa3a83dbc9cc33db3d6051b1c9b94f1212c353655c96fc841c910ee0")
ALIGN_LANGUAGE = "en"
SAMPLE_RATE = 16000
_SNAPSHOT_PATTERNS = ["*.json", "*.safetensors", ALIGN_PY_NAME]


@dataclass(frozen=True)
class RowResult:
    """Outcome of aligning one utterance (``segments`` None means failed)."""

    split: str
    row_index: int
    duration_s: float
    n_words: int
    segments: list | None
    error: str | None = None


def sha256_of_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_align_module(snapshot_dir, expected_sha256=ALIGN_PY_SHA256):
    """Import ``align.py`` from ``snapshot_dir`` after checking its hash.

    Raises:
        ValueError: if the SHA-256 differs from ``expected_sha256``.
    """
    path = Path(snapshot_dir) / ALIGN_PY_NAME
    actual = sha256_of_file(path)
    if actual != expected_sha256:
        raise ValueError(f"{path} has SHA-256 {actual}, expected "
                         f"{expected_sha256}; refusing to load it")
    spec = importlib.util.spec_from_file_location("whisper_align", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def download_snapshot(revision=MODEL_REVISION):
    """Download the model files to the Hugging Face cache; return the path."""
    from huggingface_hub import snapshot_download  # lazy: network
    return Path(snapshot_download(MODEL_REPO, revision=revision,
                                  allow_patterns=_SNAPSHOT_PATTERNS))


def load_whisper_aligner(device="cuda", revision=MODEL_REVISION):
    """Load the pinned model: bf16 on a GPU, float32 on the CPU."""
    snapshot = download_snapshot(revision)
    module = load_align_module(snapshot)
    import torch  # lazy: only the align environment has it
    dtype = torch.float32 if device == "cpu" else torch.bfloat16
    return module.ForcedAligner(str(snapshot), device=device, dtype=dtype)


def _result(row, words, outcome):
    duration = len(row.audio) / SAMPLE_RATE
    if isinstance(outcome, Exception):
        LOGGER.warning("%s row %d failed: %s", row.split, row.row_index,
                       outcome)
        return RowResult(row.split, row.row_index, duration, len(words), None,
                         str(outcome))
    segments = [WordSegment(row.split, row.row_index, index, item["word"],
                            float(item["start"]), float(item["end"]))
                for index, item in enumerate(outcome)]
    return RowResult(row.split, row.row_index, duration, len(words), segments)


def _batches(rows, batch_size):
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def align_rows_detailed(rows, aligner, batch_size=16):
    """Align ``rows`` and yield one :class:`RowResult` per row, in order.

    Transcripts go to the aligner as word lists from
    ``normalize_transcript``, so the output words are exactly our tokens.
    An item the aligner returns as an Exception becomes a failed result.
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be positive, got {batch_size}")
    for batch in _batches(rows, batch_size):
        word_lists = [normalize_transcript(row.sentence) for row in batch]
        outcomes = aligner.align_batch(
            [row.audio for row in batch], word_lists,
            [ALIGN_LANGUAGE] * len(batch))
        for row, words, outcome in zip(batch, word_lists, outcomes):
            yield _result(row, words, outcome)


def align_rows(rows, aligner, batch_size=16, failures=None) -> Iterator:
    """Yield :class:`WordSegment` for every aligned row.

    Failed rows are logged and appended to ``failures`` (a list) as
    :class:`FailedRow`; they never raise.
    """
    for result in align_rows_detailed(rows, aligner, batch_size):
        if result.segments is None:
            if failures is not None:
                failures.append(FailedRow(result.split, result.row_index,
                                          result.error))
            continue
        yield from result.segments
