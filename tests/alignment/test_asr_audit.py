import math

import pytest

from qbestd.alignment.asr_audit import (
    count_letters,
    eligible_words,
    hit_rate,
    is_hit,
    sample_words,
    shifted_segment,
)
from qbestd.alignment.manifest import WordSegment


def seg(row, index, word, start, end):
    return WordSegment("test", row, index, word, start, end)


def test_count_letters_ignores_apostrophes_and_digits():
    assert count_letters("don't") == 4
    assert count_letters("a1") == 1


def test_eligible_words_filters_letters_and_edges():
    rows = {0: (3.0, "x")}
    segments = [seg(0, 0, "is", 1.0, 1.2),        # too few letters
                seg(0, 1, "dark", 0.1, 0.4),      # shifted cut before 0
                seg(0, 2, "suit", 1.0, 1.4),      # fine
                seg(0, 3, "wash", 2.6, 2.9)]      # shifted cut past the end
    kept = eligible_words(segments, rows)
    assert [s.word for s in kept] == ["suit"]


def test_shifted_segment_moves_both_ends_only():
    moved = shifted_segment(seg(0, 1, "dark", 1.0, 1.5), -0.25)
    assert (moved.start_s, moved.end_s) == (0.75, 1.25)
    assert (moved.word, moved.row_index) == ("dark", 0)


@pytest.mark.parametrize("word, heard, expected", [
    ("dark", "Dark.", True),
    ("dark", " dark suit", True),
    ("water", "Walter", True),         # ratio 0.833
    ("water", "wash", False),
    ("greasy", "grease he", True),     # whole-hypothesis candidate
    ("suit", "", False),
    ("suit", "...", False),
    ("year", "there", False),
])
def test_is_hit(word, heard, expected):
    assert is_hit(word, heard) is expected


def test_hit_rate_and_empty_case():
    assert hit_rate(["dark", "wash"], ["dark", "xyz"]) == 0.5
    assert math.isnan(hit_rate([], []))


def test_sample_words_is_reproducible_and_capped():
    rows = {i: (5.0, "x") for i in range(40)}
    segments = {"train": [seg(i, 0, "dark", 1.0, 1.4) for i in range(40)],
                "test": [seg(i, 0, "suit", 1.0, 1.4) for i in range(5)]}
    rows_by_split = {"train": rows, "test": rows}
    first = sample_words(segments, rows_by_split, 10, seed=3)
    assert first == sample_words(segments, rows_by_split, 10, seed=3)
    assert len(first) == 10
    assert len(sample_words(segments, rows_by_split, 500, seed=3)) == 45
