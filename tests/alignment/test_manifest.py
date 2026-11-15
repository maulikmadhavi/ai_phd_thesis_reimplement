import pytest

from qbestd.alignment.manifest import (
    FailedRow,
    WordSegment,
    check_segments,
    read_manifest,
    write_failures,
    write_manifest,
)


def seg(index, word, start, end):
    return WordSegment("test", 3, index, word, start, end)


GOOD = [seg(0, "she", 0.10, 0.30), seg(1, "had", 0.30, 0.55)]


def test_round_trip(tmp_path):
    path = tmp_path / "out" / "m.tsv"
    write_manifest(path, GOOD, "abc", "def")
    assert path.read_text().splitlines()[0] == "# model=abc dataset=def"
    segments, provenance = read_manifest(path)
    assert segments == GOOD
    assert provenance == {"model": "abc", "dataset": "def"}


def test_read_rejects_missing_provenance(tmp_path):
    path = tmp_path / "m.tsv"
    path.write_text("split\trow_index\n")
    with pytest.raises(ValueError, match="model="):
        read_manifest(path)


def test_read_rejects_wrong_header(tmp_path):
    path = tmp_path / "m.tsv"
    path.write_text("# model=a dataset=b\nsplit\tword\n")
    with pytest.raises(ValueError, match="header"):
        read_manifest(path)


def test_write_failures_flattens_reason(tmp_path):
    path = tmp_path / "f.tsv"
    write_failures(path, [FailedRow("train", 7, "too\tlong\nfor window")])
    assert path.read_text().splitlines() == [
        "split\trow_index\treason", "train\t7\ttoo long for window"]


def test_clean_segments_pass():
    assert check_segments(GOOD, 1.0, expected_words=2) == []


@pytest.mark.parametrize("segments, duration, expected, fragment", [
    ([seg(0, "a", -0.1, 0.2)], 1.0, None, "< 0"),
    ([seg(0, "a", 0.1, 1.2)], 1.0, None, "> duration"),
    ([seg(0, "a", 0.5, 0.5)], 1.0, None, "end <= start"),
    ([seg(0, "a", 0.5, 0.4)], 1.0, None, "end <= start"),
    ([seg(0, "a", 0.2, 0.5), seg(1, "b", 0.1, 0.4)], 1.0, None,
     "earlier than previous"),
    ([seg(0, "a", 0.2, 0.21)], 1.0, None, "< 20 ms"),
    ([seg(0, "a", 0.0, 2.5)], 3.0, None, "> 2 s"),
    (GOOD, 1.0, 3, "word count 2 != transcript tokens 3"),
])
def test_each_rule_is_reported(segments, duration, expected, fragment):
    problems = check_segments(segments, duration, expected)
    assert any(fragment in problem for problem in problems), problems


def test_equal_starts_are_flagged_collapsed_run():
    segments = [seg(0, "a", 0.2, 0.4), seg(1, "b", 0.2, 0.5)]
    problems = check_segments(segments, 1.0)
    assert len(problems) == 1
    assert problems[0].startswith("collapsed_run: words 0..1")


def test_collapsed_run_of_three_is_one_warning():
    segments = [seg(0, "a", 0.2, 0.4), seg(1, "b", 0.2, 0.5),
                seg(2, "c", 0.2, 0.6), seg(3, "d", 0.7, 0.9)]
    problems = [p for p in check_segments(segments, 1.0)
                if p.startswith("collapsed_run")]
    assert len(problems) == 1
    assert "words 0..2" in problems[0]


def test_two_separate_runs_give_two_warnings():
    segments = [seg(0, "a", 0.1, 0.3), seg(1, "b", 0.1, 0.3),
                seg(2, "c", 0.5, 0.7), seg(3, "d", 0.5, 0.8)]
    assert sum(p.startswith("collapsed_run")
               for p in check_segments(segments, 1.0)) == 2


def test_distinct_starts_are_not_collapsed():
    assert not any(p.startswith("collapsed_run")
                   for p in check_segments(GOOD, 1.0))


@pytest.mark.parametrize("start, end", [
    (float("nan"), 0.4), (0.2, float("inf")), (float("-inf"), 0.4),
    (0.2, float("nan"))])
def test_non_finite_times_are_flagged(start, end):
    problems = check_segments([seg(0, "a", start, end)], 1.0)
    assert any(p.startswith("non_finite") for p in problems)


def test_non_finite_word_does_not_hide_other_problems():
    segments = [seg(0, "a", float("nan"), 0.4), seg(1, "b", 0.5, 0.5)]
    problems = check_segments(segments, 1.0)
    assert any("non_finite" in p for p in problems)
    assert any("end <= start" in p for p in problems)


def test_exactly_20_ms_and_2_s_are_allowed():
    segments = [seg(0, "a", 0.0, 0.02), seg(1, "b", 0.5, 2.5)]
    assert check_segments(segments, 3.0) == []
