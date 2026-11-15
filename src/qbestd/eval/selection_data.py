"""Queries, documents and relevance for one split selection.

Queries are the Q-20 keyword instances of the **train-side** rows of either
HF split (each with its own HF word alignments); documents and relevance
come from the **test-side** rows. Every key is ``(hf_split, row_index)``.
For the HF baseline this reproduces the cycle 4 and cycle 5 inputs exactly.
"""

from dataclasses import replace

from qbestd.data.split_selection import HF_SPLITS
from qbestd.data.timit_hf import normalize_transcript
from qbestd.eval.timit_queries import (
    find_query_instances,
    keyword_names,
)


def selection_examples(selection, keywords, read_words, iter_rows):
    """Usable query instances of the train side.

    Args:
        read_words: ``hf_split -> list of WordSegment``.
        iter_rows: ``hf_split -> iterable of TimitRow``.

    Returns:
        ``(examples, skipped)`` with ``QueryExample.hf_split`` set, sorted
        by keyword, HF split, row and word.
    """
    examples, skipped = [], []
    for hf_split in HF_SPLITS:
        if not selection.uses("train", hf_split):
            continue
        rows = (row for row in iter_rows(hf_split)
                if selection.includes("train", hf_split, row.row_index))
        found, left_out = find_query_instances(read_words(hf_split), rows,
                                               keywords)
        examples += [replace(e, hf_split=hf_split) for e in found]
        skipped += [replace(s, hf_split=hf_split) for s in left_out]
    order = {name: i for i, name in enumerate(keyword_names(keywords))}
    examples.sort(key=lambda e: (order[e.keyword], e.hf_split, e.row_index,
                                 e.word_index))
    return examples, skipped


def selection_relevance(document_keys, sentences, keywords):
    """``{keyword: set of (hf_split, row)}`` of the documents with the token.

    ``sentences`` maps ``hf_split`` to its list of sentences (by row index).
    A document is relevant when the exact keyword is among its tokens.
    """
    relevance = {name: set() for name in keyword_names(keywords)}
    for hf_split, row in document_keys:
        tokens = set(normalize_transcript(sentences[hf_split][row]))
        for name in relevance:
            if name in tokens:
                relevance[name].add((hf_split, row))
    return relevance
