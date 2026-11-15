import numpy as np
import pytest

from qbestd.alignment.manifest import WordSegment
from qbestd.data.feature_cache import SA_SENTENCES
from qbestd.data.timit_hf import TimitRow
from qbestd.eval.timit_queries import (
    Q20_KEYWORDS,
    QueryExample,
    build_query_examples,
    build_relevance,
    cut_clip,
    find_query_instances,
    read_query_examples,
    read_relevance,
    scan_test_rows,
    write_query_examples,
    write_relevance,
)

RATE = 16000


def row(index, sentence, seconds=2.0, split="train"):
    return TimitRow(split, index, sentence,
                    np.zeros(int(seconds * RATE), np.float32), RATE)


def word(row_index, index, text, start, end):
    return WordSegment("train", row_index, index, text, start, end)


def test_q20_list_matches_the_thesis_table():
    assert len(Q20_KEYWORDS) == 20
    table = {name: (inst, occ) for name, inst, occ in Q20_KEYWORDS}
    assert table["love"] == (4, 16)
    assert table["morning"] == (15, 14)
    assert table["government"] == (14, 8)
    assert sum(inst for _, inst, _ in Q20_KEYWORDS) == 145


def test_sa_rows_are_excluded_from_queries():
    rows = [row(0, SA_SENTENCES[0] + "."), row(1, "I love music.")]
    manifest = [word(0, 0, "love", 0.2, 0.5), word(1, 0, "love", 0.2, 0.5)]
    examples = build_query_examples(manifest, rows, ["love"])
    assert [e.row_index for e in examples] == [1]


def test_padding_is_added_and_clipped_to_the_utterance():
    rows = [row(0, "love it", seconds=1.0), row(1, "so love", seconds=1.0)]
    manifest = [word(0, 0, "love", 0.01, 0.50),   # start clipped at 0
                word(1, 1, "love", 0.50, 0.99)]   # end clipped at 1.0
    first, second = build_query_examples(manifest, rows, ["love"], pad_s=0.02)
    assert (first.start_s, first.end_s) == (0.0, pytest.approx(0.52))
    assert (second.start_s, second.end_s) == (pytest.approx(0.48), 1.0)


def test_flagged_segments_are_skipped_and_reported():
    rows = [row(0, "love it all")]
    manifest = [word(0, 0, "love", 0.30, 0.31),     # under 20 ms
                word(0, 1, "it", 0.31, 0.50),
                word(0, 2, "all", 0.50, 0.80)]
    examples, skipped = find_query_instances(manifest, rows, ["love"])
    assert examples == []
    assert [(s.keyword, s.reason) for s in skipped] == [("love", "flagged")]


def test_collapsed_run_member_is_skipped():
    rows = [row(0, "so love it")]
    manifest = [word(0, 0, "so", 0.10, 0.30), word(0, 1, "love", 0.30, 0.60),
                word(0, 2, "it", 0.30, 0.90)]
    examples, skipped = find_query_instances(manifest, rows, ["love"])
    assert examples == [] and len(skipped) == 1


def test_only_requested_keywords_become_queries():
    rows = [row(0, "love beautiful day")]
    manifest = [word(0, 0, "love", 0.1, 0.4), word(0, 1, "beautiful", 0.4,
                                                   0.9),
                word(0, 2, "day", 0.9, 1.3)]
    examples = build_query_examples(manifest, rows, ["beautiful"])
    assert [e.keyword for e in examples] == ["beautiful"]


def test_relevance_uses_exact_token_match_not_substrings():
    rows = [row(10, "I love you.", split="test"),
            row(11, "A lovely day.", split="test"),
            row(12, "Love, love, love!", split="test"),
            row(13, "Nothing here.", split="test")]
    relevance = build_relevance(rows, ["love"])
    assert relevance == {"love": {10, 12}}
    scan = scan_test_rows(rows, ["love"])
    assert scan.occurrences == {"love": 4}      # tokens, not documents
    assert scan.documents == (10, 11, 12, 13)


def test_sa_rows_are_excluded_from_documents_and_relevance():
    rows = [row(0, SA_SENTENCES[1] + ".", split="test"),
            row(1, "She said love.", split="test")]
    scan = scan_test_rows(rows, ["love"])
    assert scan.documents == (1,)
    scan_all = scan_test_rows(rows, ["love"], exclude_sa=False)
    assert scan_all.documents == (0, 1)


def test_cut_clip_slices_the_requested_interval():
    audio = np.arange(RATE, dtype=np.float32)
    clip = cut_clip(audio, RATE, QueryExample("x", 0, 0, 0.25, 0.5))
    assert len(clip) == RATE // 4
    assert clip[0] == RATE // 4


def test_tsv_round_trips(tmp_path):
    examples = [QueryExample("love", 3, 2, 0.12, 0.58),
                QueryExample("ocean", 9, 0, 0.0, 0.7)]
    write_query_examples(tmp_path / "q.tsv", examples)
    assert read_query_examples(tmp_path / "q.tsv") == examples
    relevance = {"love": {5, 1, 9}, "ocean": set()}
    write_relevance(tmp_path / "r.tsv", relevance)
    assert read_relevance(tmp_path / "r.tsv") == relevance


def test_read_rejects_wrong_header(tmp_path):
    (tmp_path / "bad.tsv").write_text("nope\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_query_examples(tmp_path / "bad.tsv")
    with pytest.raises(ValueError):
        read_relevance(tmp_path / "bad.tsv")


def test_counts_table_and_summary_text():
    from qbestd.eval.q20_counts import counts_table, summary_text
    keywords = (("love", 4, 16), ("ocean", 7, 7))
    rows = [row(0, "I love you", split="test"),
            row(1, "Love and love", split="test")]
    scan = scan_test_rows(rows, keywords)
    examples = [QueryExample("love", 1, 0, 0.1, 0.4)]
    table = counts_table(keywords, examples, [], scan)
    assert "| love | 4 | 16 | 1 | 0 | 2 | 3 |" in table
    assert "| ocean | 7 | 7 | 0 | 0 | 0 | 0 |" in table
    assert "| **total** | **11** | **23** |" in table
    text = summary_text(examples, [], scan, keywords)
    assert "**2** documents" in text
    assert "speaker overlap present; approximate versus the thesis" in text
