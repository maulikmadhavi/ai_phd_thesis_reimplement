"""Align TIMIT words over the Hugging Face splits and write the manifests.

Usage (align environment)::

    pixi run -e align python -m qbestd.alignment.run --split all --device cuda

Outputs go under ``--out`` (default ``outputs/alignment/``, git-ignored):
``timit_hf_words_<split>.tsv``, ``timit_hf_rows_<split>.tsv`` (row duration
and sentence, used by the sanity checks), ``failures.tsv`` and
``summary.json``. Manifests are derived from LDC-licensed text through a
CC BY-NC model, so they are never committed.
"""

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np

from qbestd.alignment.manifest import (
    FailedRow,
    check_segments,
    write_failures,
    write_manifest,
)
from qbestd.alignment.word_aligner import (
    MODEL_REVISION,
    align_rows_detailed,
    load_whisper_aligner,
)
from qbestd.data.timit_hf import (
    TIMIT_HF_REVISION,
    download_timit_parquet,
    iter_timit_rows,
)

LOGGER = logging.getLogger(__name__)
DEFAULT_OUT = Path("outputs/alignment")
PERCENTILES = (1, 5, 25, 50, 75, 95, 99)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--split", choices=("train", "test", "all"),
                        default="all")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None,
                        help="only the first N rows of each split (testing)")
    return parser.parse_args(argv)


def summarize_split(word_durations, n_rows, n_failed, violations, seconds):
    """Counts, violations and word-duration percentiles of one split."""
    durations = np.asarray(word_durations, dtype="float64")
    percentiles = ({f"p{p}": float(np.percentile(durations, p))
                    for p in PERCENTILES} if len(durations) else {})
    return {"rows": n_rows, "failed_rows": n_failed,
            "words": int(len(durations)),
            "violations": len(violations),
            "rows_with_violations": len({row for row, _ in violations}),
            "word_duration_s": {
                **percentiles,
                "min": float(durations.min()) if len(durations) else None,
                "max": float(durations.max()) if len(durations) else None},
            "runtime_s": round(seconds, 1)}


def write_rows_file(path, infos):
    """TSV of ``(row_index, duration_s, sentence)`` for the sanity checks."""
    lines = ["row_index\tduration_s\tsentence"]
    lines += [f"{index}\t{duration:.4f}\t{' '.join(sentence.split())}"
              for index, duration, sentence in infos]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_split(rows, split, aligner, batch_size, out_dir):
    """Align ``rows`` of one split, write its files, return (summary, fails).

    ``summary["violation_list"]`` holds ``(row_index, message)`` pairs.
    """
    start = time.time()
    segments, failures, violations, infos = [], [], [], []
    sentences = {}

    def tracked(source):
        for row in source:
            sentences[row.row_index] = row.sentence
            yield row

    for count, result in enumerate(
            align_rows_detailed(tracked(rows), aligner, batch_size), 1):
        infos.append((result.row_index, result.duration_s,
                      sentences.pop(result.row_index)))
        if result.segments is None:
            failures.append(FailedRow(split, result.row_index, result.error))
        else:
            segments += result.segments
            violations += [(result.row_index, problem) for problem in
                          check_segments(result.segments, result.duration_s,
                                         result.n_words)]
        if count % 100 == 0:
            LOGGER.info("%s: %d rows, %.0f s", split, count,
                        time.time() - start)
    out_dir = Path(out_dir)
    write_manifest(out_dir / f"timit_hf_words_{split}.tsv", segments,
                   MODEL_REVISION, TIMIT_HF_REVISION)
    write_rows_file(out_dir / f"timit_hf_rows_{split}.tsv", infos)
    summary = summarize_split([s.end_s - s.start_s for s in segments],
                              len(infos), len(failures), violations,
                              time.time() - start)
    summary["violation_list"] = violations
    return summary, failures


def limited(rows, limit):
    for count, row in enumerate(rows):
        if limit is not None and count >= limit:
            return
        yield row


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    splits = ("train", "test") if args.split == "all" else (args.split,)
    aligner = load_whisper_aligner(args.device)
    summary = {"model_revision": MODEL_REVISION,
               "dataset_revision": TIMIT_HF_REVISION, "splits": {}}
    all_failures = []
    for split in splits:
        rows = iter_timit_rows(download_timit_parquet(split), split)
        result, failures = run_split(limited(rows, args.limit), split,
                                     aligner, args.batch_size, args.out)
        summary["splits"][split] = result
        all_failures += failures
    write_failures(args.out / "failures.tsv", all_failures)
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    LOGGER.info("done: %s", {k: (v["rows"], v["failed_rows"], v["violations"])
                             for k, v in summary["splits"].items()})


if __name__ == "__main__":
    main()
