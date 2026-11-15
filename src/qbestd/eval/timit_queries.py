"""TIMIT Q-20 queries and relevance judgements.

Thesis (``ExpSetup.tex`` lines 78-97, ``Table:TIMITdata``): 20 keywords with
their number of spoken instances (Inst.) and occurrences (Occ.). Queries come
from the train split and the searched documents from the test split; the SA
sentences are excluded (lines 73-75).

Assumptions (the thesis is silent; unverified):

* Each spoken instance is its own query.
* A test document is relevant when it contains the keyword as a token at
  least once (exact match after ``normalize_transcript``; no morphological
  variants).
* A query clip is the aligner's word interval padded by ``pad_s`` on both
  sides and clipped to the utterance. Words flagged by the alignment checks
  (under 20 ms or inside a collapsed run) are skipped.

Outputs are small TSV files under ``outputs/eval/`` (git-ignored). No audio
is stored here; :func:`cut_clip` slices samples on demand.
"""

from dataclasses import dataclass
from pathlib import Path

from qbestd.alignment.manifest import flagged_word_indices
from qbestd.data.feature_cache import is_sa_sentence
from qbestd.data.timit_hf import normalize_transcript

# (keyword, thesis Inst., thesis Occ.), ExpSetup.tex lines 78-97.
Q20_KEYWORDS = (
    ("artists", 7, 7), ("beautiful", 3, 8), ("birth", 4, 7),
    ("destroy", 9, 7), ("development", 9, 8), ("garbage", 8, 7),
    ("government", 14, 8), ("intelligence", 8, 7), ("love", 4, 16),
    ("marriage", 3, 7), ("meeting", 7, 7), ("morning", 15, 14),
    ("ocean", 7, 7), ("organizations", 7, 7), ("problems", 5, 7),
    ("shellfish", 14, 7), ("simple", 8, 8), ("surface", 3, 7),
    ("tomorrow", 3, 7), ("youngsters", 7, 7),
)
DEFAULT_PAD_S = 0.02


@dataclass(frozen=True)
class QueryExample:
    """One spoken keyword instance; times are seconds in the utterance."""

    keyword: str
    row_index: int
    word_index: int
    start_s: float
    end_s: float


@dataclass(frozen=True)
class SkippedInstance:
    keyword: str
    row_index: int
    word_index: int
    reason: str  # "flagged"


@dataclass(frozen=True)
class RelevanceScan:
    """Result of scanning the test documents for the keywords."""


    documents: tuple          # row indices of searchable documents
    relevance: dict           # keyword -> set of row indices
    occurrences: dict         # keyword -> token count over all documents


def keyword_names(keywords=Q20_KEYWORDS):
    return [entry[0] if isinstance(entry, tuple) else entry
            for entry in keywords]


def find_query_instances(train_word_manifest, train_rows, keywords,
                         pad_s=DEFAULT_PAD_S):
    """Spoken instances of ``keywords`` in the train split.

    Args:
        train_word_manifest: ``WordSegment`` list of the train split.
        train_rows: iterable of rows with ``row_index``, ``sentence``,
            ``audio`` and ``sample_rate`` (``TimitRow``); SA rows are
            ignored and their durations clip the padded intervals.
        keywords: names (or ``(name, ...)`` tuples) to look for.
        pad_s: padding added to both ends of every word.

    Returns:
        ``(examples, skipped)``: ``QueryExample`` list and the flagged
        instances left out.
    """
    wanted = set(keyword_names(keywords))
    durations = {}
    for row in train_rows:
        if not is_sa_sentence(normalize_transcript(row.sentence)):
            durations[row.row_index] = len(row.audio) / row.sample_rate
    by_row = {}
    for segment in train_word_manifest:
        if segment.row_index in durations:
            by_row.setdefault(segment.row_index, []).append(segment)
    examples, skipped = [], []
    for row_index in sorted(by_row):
        segments = sorted(by_row[row_index], key=lambda s: s.word_index)
        flagged = flagged_word_indices(segments)
        for segment in segments:
            if segment.word not in wanted:
                continue
            if segment.word_index in flagged:
                skipped.append(SkippedInstance(
                    segment.word, row_index, segment.word_index, "flagged"))
                continue
            examples.append(QueryExample(
                segment.word, row_index, segment.word_index,
                max(0.0, segment.start_s - pad_s),
                min(durations[row_index], segment.end_s + pad_s)))
    examples.sort(key=lambda e: (e.keyword, e.row_index, e.word_index))
    return examples, skipped


def build_query_examples(train_word_manifest, train_rows, keywords,
                         pad_s=DEFAULT_PAD_S):
    """The usable query instances, see :func:`find_query_instances`."""
    return find_query_instances(train_word_manifest, train_rows, keywords,
                                pad_s)[0]


def scan_test_rows(test_rows, keywords, exclude_sa=True):
    """Documents, relevance sets and token counts of the test split."""
    names = keyword_names(keywords)
    relevance = {name: set() for name in names}
    occurrences = {name: 0 for name in names}
    documents = []
    for row in test_rows:
        tokens = normalize_transcript(row.sentence)
        if exclude_sa and is_sa_sentence(tokens):
            continue
        documents.append(row.row_index)
        for name in names:
            count = tokens.count(name)
            if count:
                relevance[name].add(row.row_index)
                occurrences[name] += count
    return RelevanceScan(tuple(documents), relevance, occurrences)


def build_relevance(test_rows, keywords, exclude_sa=True):
    """``{keyword: set of test row indices containing the exact token}``."""
    return scan_test_rows(test_rows, keywords, exclude_sa).relevance


def cut_clip(audio, sample_rate, example):
    """Samples of the query interval from the full utterance ``audio``."""
    first = int(round(example.start_s * sample_rate))
    last = int(round(example.end_s * sample_rate))
    return audio[first:last]


def write_query_examples(path, examples):
    lines = ["keyword\trow_index\tword_index\tstart_s\tend_s"]
    lines += [f"{e.keyword}\t{e.row_index}\t{e.word_index}\t"
              f"{e.start_s:.3f}\t{e.end_s:.3f}" for e in examples]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_query_examples(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if lines[0].split("\t") != ["keyword", "row_index", "word_index",
                               "start_s", "end_s"]:
        raise ValueError(f"{path}: unexpected header {lines[0]!r}")
    return [QueryExample(f[0], int(f[1]), int(f[2]), float(f[3]),
                         float(f[4]))
            for f in (line.split("\t") for line in lines[1:])]


def write_relevance(path, relevance):
    lines = ["keyword\trow_indices"]
    lines += [f"{name}\t{','.join(str(r) for r in sorted(rows))}"
              for name, rows in relevance.items()]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_relevance(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if lines[0].split("\t") != ["keyword", "row_indices"]:
        raise ValueError(f"{path}: unexpected header {lines[0]!r}")
    out = {}
    for line in lines[1:]:
        name, _, rows = line.partition("\t")
        out[name] = {int(r) for r in rows.split(",") if r}
    return out
