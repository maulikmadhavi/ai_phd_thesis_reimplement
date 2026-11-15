"""Build the Q-20 query and relevance files and compare counts to the thesis.

Usage::

    pixi run python -m qbestd.eval.q20_counts

Reads the train and test word manifests (``outputs/alignment/``), writes
``outputs/eval/queries_train.tsv`` and ``outputs/eval/relevance_test.tsv``
(git-ignored) and the small committed summary ``docs/q20_counts.md``. The
summary holds counts only: no audio, no transcripts.
"""

import argparse
from pathlib import Path

from qbestd.alignment.manifest import read_manifest
from qbestd.data.timit_hf import download_timit_parquet, iter_timit_rows
from qbestd.eval.timit_queries import (
    Q20_KEYWORDS,
    find_query_instances,
    scan_test_rows,
    write_query_examples,
    write_relevance,
)

ALIGNMENT_DIR = Path("outputs/alignment")
EVAL_DIR = Path("outputs/eval")
DOC_PATH = Path("docs/q20_counts.md")


def counts_table(keywords, examples, skipped, scan):
    """Markdown table: thesis Inst/Occ against our counts per keyword."""
    lines = ["| Keyword | Thesis Inst. | Thesis Occ. | Our train instances "
             "| Our flagged (skipped) | Our test documents "
             "| Our test token occurrences |",
             "|---|---|---|---|---|---|---|"]
    totals = [0] * 6
    for name, inst, occ in keywords:
        ours = sum(1 for e in examples if e.keyword == name)
        flagged = sum(1 for s in skipped if s.keyword == name)
        documents = len(scan.relevance[name])
        tokens = scan.occurrences[name]
        row = [inst, occ, ours, flagged, documents, tokens]
        totals = [a + b for a, b in zip(totals, row)]
        lines.append(f"| {name} | " + " | ".join(str(v) for v in row)
                     + " |")
    lines.append("| **total** | " + " | ".join(f"**{v}**" for v in totals)
                 + " |")
    return "\n".join(lines)


def summary_text(examples, skipped, scan, keywords=Q20_KEYWORDS):
    empty = ", ".join(name for name, _, _ in keywords
                      if not scan.relevance[name])
    return f"""# Q-20 counts: thesis against this reimplementation

Thesis table: `ExpSetup.tex` lines 78-97 (`Table:TIMITdata`). Ours: the
Hugging Face TIMIT copy. Label:
*speaker overlap present; approximate versus the thesis*.
Counts only; nothing here is audio or transcript text.

- Search documents: test split without the two SA sentences,
  **{len(scan.documents)}** documents (1260 test rows minus the SA rows).
- Query instances: train split without SA rows, exact token match on the
  aligned word, padded by 20 ms and clipped. **{len(examples)}** usable
  instances; **{len(skipped)}** more were skipped because their segment was
  flagged (under 20 ms or inside a collapsed run).
- "Test documents" counts documents containing the token at least once;
  "test token occurrences" counts every token.
- Keywords with no test document cannot be scored (p@N needs at least one
  relevant document) and are left out of the evaluation:
  {empty if empty else "none"}.
- Thesis Inst. is the number of spoken instances; whether thesis Occ. is a
  document or a token count is open question 21.

{counts_table(keywords, examples, skipped, scan)}
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--alignment-dir", type=Path, default=ALIGNMENT_DIR)
    parser.add_argument("--out", type=Path, default=EVAL_DIR)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    args = parser.parse_args(argv)
    train_words, _ = read_manifest(
        args.alignment_dir / "timit_hf_words_train.tsv")
    train_rows = iter_timit_rows(download_timit_parquet("train"), "train")
    examples, skipped = find_query_instances(train_words, train_rows,
                                             Q20_KEYWORDS)
    test_rows = iter_timit_rows(download_timit_parquet("test"), "test")
    scan = scan_test_rows(test_rows, Q20_KEYWORDS)
    write_query_examples(args.out / "queries_train.tsv", examples)
    write_relevance(args.out / "relevance_test.tsv", scan.relevance)
    args.doc.write_text(summary_text(examples, skipped, scan),
                        encoding="utf-8")
    print(f"{len(examples)} queries, {len(skipped)} skipped, "
          f"{len(scan.documents)} documents")


if __name__ == "__main__":
    main()
