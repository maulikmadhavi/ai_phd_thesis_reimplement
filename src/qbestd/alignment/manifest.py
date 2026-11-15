"""Word-boundary manifest: records, TSV files and sanity checks.

A manifest is a TSV file whose first line is a comment
``# model=<sha> dataset=<sha>``, followed by a header and one row per word.
"""

from dataclasses import dataclass
from pathlib import Path

HEADER = ("split", "row_index", "word_index", "word", "start_s", "end_s")
FAILURE_HEADER = ("split", "row_index", "reason")
MIN_WORD_S = 0.02
MAX_WORD_S = 2.0


@dataclass(frozen=True)
class WordSegment:
    """One aligned word; times are seconds from the start of the utterance."""

    split: str
    row_index: int
    word_index: int
    word: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class FailedRow:
    """An utterance the aligner could not process."""

    split: str
    row_index: int
    reason: str


def write_manifest(path, segments, model_revision, dataset_revision):
    """Write ``segments`` to ``path`` as TSV with a provenance comment."""
    lines = [f"# model={model_revision} dataset={dataset_revision}",
             "\t".join(HEADER)]
    lines += [f"{s.split}\t{s.row_index}\t{s.word_index}\t{s.word}\t"
              f"{s.start_s:.3f}\t{s.end_s:.3f}" for s in segments]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_manifest(path):
    """Return ``(segments, provenance)``; provenance is ``{"model": .., ..}``.

    Raises:
        ValueError: if the provenance comment or the header is missing.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if len(lines) < 2 or not lines[0].startswith("# "):
        raise ValueError(f"{path}: missing '# model=... dataset=...' line")
    provenance = dict(item.split("=", 1) for item in lines[0][2:].split())
    if tuple(lines[1].split("\t")) != HEADER:
        raise ValueError(f"{path}: unexpected header {lines[1]!r}")
    segments = []
    for line in lines[2:]:
        split, row, index, word, start, end = line.split("\t")
        segments.append(WordSegment(split, int(row), int(index), word,
                                    float(start), float(end)))
    return segments, provenance


def write_failures(path, failures):
    """Write failed rows as TSV (tabs and newlines in reasons are replaced)."""
    lines = ["\t".join(FAILURE_HEADER)]
    for failure in failures:
        reason = " ".join(failure.reason.split())
        lines.append(f"{failure.split}\t{failure.row_index}\t{reason}")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_segments(segments, duration_s, expected_words=None):
    """List the rule violations of one utterance's segments (empty = fine).

    Rules: start < 0; end > duration; end <= start; starts not
    non-decreasing; duration below 20 ms or above 2 s; word count differing
    from ``expected_words`` (the transcript token count, when given).
    """
    problems = []
    if expected_words is not None and len(segments) != expected_words:
        problems.append(
            f"word count {len(segments)} != transcript tokens "
            f"{expected_words}")
    previous_start = None
    for segment in segments:
        label = f"word {segment.word_index} '{segment.word}'"
        length = segment.end_s - segment.start_s
        if segment.start_s < 0:
            problems.append(f"{label}: start {segment.start_s:.3f} < 0")
        if segment.end_s > duration_s:
            problems.append(f"{label}: end {segment.end_s:.3f} > duration "
                            f"{duration_s:.3f}")
        if segment.end_s <= segment.start_s:
            problems.append(f"{label}: end <= start")
        elif length < MIN_WORD_S:
            problems.append(
                f"{label}: duration {length * 1000:.0f} ms < 20 ms")
        elif length > MAX_WORD_S:
            problems.append(f"{label}: duration {length:.2f} s > 2 s")
        if previous_start is not None and segment.start_s < previous_start:
            problems.append(f"{label}: start earlier than previous word")
        previous_start = segment.start_s
    return problems
