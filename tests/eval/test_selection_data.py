import numpy as np

from qbestd.alignment.manifest import WordSegment
from qbestd.data.split_selection import SplitSelection, hf_selection
from qbestd.data.timit_hf import TimitRow
from qbestd.eval.selection_data import selection_examples, selection_relevance

RATE = 16000


def row(hf_split, index, sentence):
    return TimitRow(hf_split, index, sentence, np.zeros(RATE, np.float32),
                    RATE)


def words(hf_split, index, text="love"):
    return WordSegment(hf_split, index, 0, text, 0.1, 0.4)


ROWS = {"train": [row("train", 0, "I love tea"),
                  row("train", 1, "love again")],
        "test": [row("test", 0, "we love food"),
                 row("test", 1, "quiet street")]}
WORDS = {"train": [words("train", 0), words("train", 1)],
         "test": [words("test", 0), words("test", 1, "street")]}


def run(selection):
    return selection_examples(selection, ["love"], lambda s: WORDS[s],
                              lambda s: iter(ROWS[s]))


def test_hf_selection_gives_train_split_queries_only():
    examples, _ = run(hf_selection())
    assert [(e.hf_split, e.row_index) for e in examples] == [("train", 0),
                                                              ("train", 1)]


def test_a_row_moved_from_hf_test_keeps_its_own_word_alignments():
    # HF test row 0 ("we love food") is on the train side; HF train row 1
    # is on the test side. The word segments come from each HF split's own
    # manifest, looked up by (hf_split, row_index), never by a new index.
    selection = SplitSelection("m", {
        "train": {"train": frozenset({0}), "test": frozenset({0})},
        "test": {"train": frozenset({1}), "test": frozenset({1})}})
    examples, _ = run(selection)
    assert [(e.hf_split, e.row_index, e.word_index)
            for e in examples] == [("test", 0, 0), ("train", 0, 0)]
    assert all(e.start_s == 0.08 for e in examples)


def test_relevance_uses_exact_tokens_of_test_side_documents():
    sentences = {"train": [r.sentence for r in ROWS["train"]],
                 "test": [r.sentence for r in ROWS["test"]]}
    keys = [("train", 1), ("test", 0), ("test", 1)]
    relevance = selection_relevance(keys, sentences, ["love", "street",
                                                      "lov"])
    assert relevance == {"love": {("train", 1), ("test", 0)},
                         "street": {("test", 1)}, "lov": set()}


def test_queries_and_documents_never_share_a_text_group(tmp_path,
                                                       monkeypatch):
    monkeypatch.setattr("qbestd.data.text_split.TEST_QUOTA",
                        {"multi": 1, "single": 1})
    from qbestd.data.split_selection import manifest_selection
    from qbestd.data.text_split import build_text_split, write_split_manifest
    sentences = [("train", i, "love tea") for i in range(3)] + [
        ("test", i, "love tea") for i in range(2)] + [
        ("train", 5, "quiet street"), ("test", 5, "we love food")]
    manifest = build_text_split(sentences, [("love", 1, 1)])
    write_split_manifest(tmp_path / "m.tsv", manifest)
    selection = manifest_selection(tmp_path / "m.tsv")
    text = {(s, i): t for s, i, t in sentences}
    query_texts = {text[(s, i)] for s in ("train", "test")
                   for i in range(6) if selection.includes("train", s, i)
                   and (s, i) in text}
    document_texts = {text[(s, i)] for s in ("train", "test")
                      for i in range(6) if selection.includes("test", s, i)
                      and (s, i) in text}
    assert query_texts and document_texts
    assert query_texts.isdisjoint(document_texts)
