"""Re-run the manifest checks on existing manifests (no re-alignment).

Usage::

    python -m qbestd.alignment.recheck --out outputs/alignment

Reads ``timit_hf_words_<split>.tsv`` and ``timit_hf_rows_<split>.tsv`` from
``--out`` and writes ``recheck.json``. Needs only the core environment.
"""

import argparse
import json
from itertools import groupby
from pathlib import Path

from qbestd.alignment.manifest import check_segments, read_manifest
from qbestd.alignment.sanity import read_rows_file
from qbestd.data.timit_hf import normalize_transcript

CATEGORIES = ("collapsed_run", "non_finite")


def category_of(problem):
    """``collapsed_run``, ``non_finite`` or ``rule`` (the older rules)."""
    for name in CATEGORIES:
        if problem.startswith(name):
            return name
    return "rule"


def recheck_split(segments, rows):
    """Check every row of one split.

    ``segments`` come from :func:`read_manifest`; ``rows`` from
    :func:`read_rows_file`. Returns counts per category, the rows involved
    and the number of rows that have no segments at all.
    """
    by_row = {index: list(group) for index, group in
              groupby(segments, key=lambda s: s.row_index)}
    counts = {name: 0 for name in (*CATEGORIES, "rule")}
    row_lists = {name: [] for name in counts}
    for index, (duration, sentence) in rows.items():
        expected = len(normalize_transcript(sentence))
        problems = check_segments(by_row.get(index, []), duration, expected)
        for name in counts:
            hits = [p for p in problems if category_of(p) == name]
            counts[name] += len(hits)
            if hits:
                row_lists[name].append(index)
    return {"rows": len(rows), "rows_without_segments":
            sum(1 for index in rows if index not in by_row),
            "counts": counts, "rows_by_category": row_lists}


def recheck_all(out_dir):
    out_dir = Path(out_dir)
    report = {}
    for split in ("train", "test"):
        segments, _ = read_manifest(out_dir / f"timit_hf_words_{split}.tsv")
        rows = read_rows_file(out_dir / f"timit_hf_rows_{split}.tsv")
        report[split] = recheck_split(segments, rows)
    (out_dir / "recheck.json").write_text(json.dumps(report, indent=2),
                                          encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path("outputs/alignment"))
    args = parser.parse_args(argv)
    report = recheck_all(args.out)
    for split, result in report.items():
        print(split, result["rows"], result["counts"])


if __name__ == "__main__":
    main()
