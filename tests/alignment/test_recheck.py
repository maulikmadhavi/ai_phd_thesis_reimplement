from qbestd.alignment.manifest import WordSegment, write_manifest
from qbestd.alignment.recheck import category_of, recheck_all, recheck_split


def seg(row, index, word, start, end):
    return WordSegment("test", row, index, word, start, end)


def test_category_of():
    assert category_of("collapsed_run: words 0..1") == "collapsed_run"
    assert category_of("non_finite: word 0") == "non_finite"
    assert category_of("word 1 'a': end <= start") == "rule"


def test_recheck_counts_each_category_and_rows():
    segments = [seg(0, 0, "she", 0.1, 0.3), seg(0, 1, "had", 0.3, 0.6),
                seg(1, 0, "a", 0.5, 0.52), seg(1, 1, "big", 0.5, 0.52),
                seg(2, 0, "x", float("nan"), 0.4)]
    rows = {0: (1.0, "She had."), 1: (1.0, "a big"), 2: (1.0, "x"),
            3: (1.0, "missing words")}
    result = recheck_split(segments, rows)
    assert result["rows"] == 4
    assert result["rows_without_segments"] == 1
    assert result["counts"]["collapsed_run"] == 1
    assert result["counts"]["non_finite"] == 1
    assert result["rows_by_category"]["collapsed_run"] == [1]
    assert result["rows_by_category"]["non_finite"] == [2]
    # row 3 has two expected tokens and no segments: a word count rule
    assert result["rows_by_category"]["rule"] == [3]


def test_clean_split_has_no_problems():
    segments = [seg(0, 0, "a", 0.1, 0.3), seg(0, 1, "b", 0.3, 0.6)]
    result = recheck_split(segments, {0: (1.0, "a b")})
    assert sum(result["counts"].values()) == 0


def test_recheck_all_writes_json(tmp_path):
    for split in ("train", "test"):
        write_manifest(tmp_path / f"timit_hf_words_{split}.tsv",
                       [seg(0, 0, "a", 0.1, 0.3)], "m", "d")
        (tmp_path / f"timit_hf_rows_{split}.tsv").write_text(
            "row_index\tduration_s\tsentence\n0\t1.0000\ta\n")
    report = recheck_all(tmp_path)
    assert set(report) == {"train", "test"}
    assert (tmp_path / "recheck.json").is_file()
