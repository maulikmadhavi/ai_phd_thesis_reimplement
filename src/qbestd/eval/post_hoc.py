"""Post hoc paired comparisons of the Stage 4 rows (cycle 10, M2, Q1).

Not declared in advance: this script reads the ``per_query.tsv`` files of
finished evaluations and computes paired keyword-cluster intervals (10000
resamples, seed 0) for the comparisons listed in ``docs/plan.md`` section 8.
It also recomputes the per-query waveform level ratio between the ``clip``
and ``clip_lm`` query paths. Outputs go to git-ignored ``outputs/posthoc/``.

    pixi run python -m qbestd.eval.post_hoc
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np

from qbestd.alignment.manifest import read_manifest
from qbestd.data.split_selection import manifest_selection
from qbestd.data.timit_hf import download_timit_parquet, iter_timit_rows
from qbestd.eval.bootstrap import paired_keyword_bootstrap
from qbestd.eval.selection_data import selection_examples
from qbestd.eval.timit_queries import Q20_KEYWORDS, cut_clip
from qbestd.eval.vtln_eval import load_example_audio
from qbestd.provenance import finish_run, start_run

EVAL = Path("outputs/eval")
# (label, feature, "A" run (the baseline), "B" run); the difference is B - A
COMPARISONS = []
for tag in ("mfcc", "plp"):
    COMPARISONS += [
        (f"{tag.upper()} un-normalised: VTLN minus selection only", tag,
         f"cell_selection_only_{tag}_4k",
         f"vtln_{tag}_htk_described_4k_gmm64"),
        (f"{tag.upper()} un-normalised: VTLN minus model only", tag,
         f"cell_model_only_{tag}_4k", f"vtln_{tag}_htk_described_4k_gmm64"),
        (f"{tag.upper()} un-normalised: query_inherit minus VTLN", tag,
         f"vtln_{tag}_htk_described_4k_gmm64", f"cell_query_inherit_{tag}_4k"),
        (f"{tag.upper()} pn: VTLN minus selection only", tag,
         f"cell_selection_only_pn_{tag}",
         f"vtln_{tag}_htk_described_4k_pn_gmm64"),
        (f"{tag.upper()} pn: VTLN minus model only", tag,
         f"cell_model_only_pn_{tag}", f"vtln_{tag}_htk_described_4k_pn_gmm64"),
    ]


def read_per_query(path):
    """Per-query rows of a ``per_query.tsv`` with typed values."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        raw = dict(zip(header, line.split("\t")))
        rows.append({"keyword": raw["keyword"], "hf_split": raw["hf_split"],
                     "row_index": int(raw["row_index"]),
                     "word_index": int(raw["word_index"]),
                     "p_at_n": float(raw["p_at_n"]),
                     "ap": float(raw["ap"])})
    return rows


def interval_row(result, average):
    """``(p@N, MAP)`` difference of one average as signed text."""
    cells = []
    for metric in ("p_at_n", "map"):
        v = result[average][metric]
        cells.append(f"{v['estimate']:+.2f} ({v['low']:+.2f} to "
                     f"{v['high']:+.2f})")
    return cells


def excludes_zero(result, average):
    """``(p@N, MAP)`` flags: True when the 95 % interval excludes 0."""
    return [result[average][m]["low"] > 0 or result[average][m]["high"] < 0
            for m in ("p_at_n", "map")]


def paired_table(eval_dir):
    """Markdown rows and a JSON dict for every comparison in COMPARISONS."""
    records, rows = [], []
    cache = {}
    for label, _, a_name, b_name in COMPARISONS:
        for name in (a_name, b_name):
            if name not in cache:
                cache[name] = read_per_query(eval_dir / name / "per_query.tsv")
        result = paired_keyword_bootstrap(cache[a_name], cache[b_name])
        for average in ("instance_average", "keyword_average"):
            p, m = interval_row(result, average)
            ex_p, ex_m = excludes_zero(result, average)
            rows.append(f"| {label} | {average.split('_')[0]} | {p} | {m} | "
                        f"{'yes' if ex_p else 'no'} / "
                        f"{'yes' if ex_m else 'no'} |")
            records.append({"comparison": label, "average": average,
                            "A": a_name, "B": b_name, "result": {
                                k: result[average][k]
                                for k in ("p_at_n", "map")}})
    return rows, records


def level_ratios(manifest, alignment_dir, per_query_path):
    """Per query: ``max|x| / max|clip|`` (the clip path's extra gain against
    the utterance-level normalisation of ``clip_lm``) and the reading of the
    plan's formula, ``max|clip - mean| / max|x|``, both on the same clips."""
    selection = manifest_selection(manifest)
    examples, _ = selection_examples(
        selection, Q20_KEYWORDS,
        lambda split: read_manifest(
            alignment_dir / f"timit_hf_words_{split}.tsv")[0],
        lambda split: iter_timit_rows(download_timit_parquet(split), split))
    wanted = {(e["keyword"], e["hf_split"], e["row_index"], e["word_index"])
              for e in read_per_query(per_query_path)}
    examples = [e for e in examples
                if (e.keyword, e.hf_split, e.row_index, e.word_index)
                in wanted]
    audio = load_example_audio(examples)
    gain, plan_formula = [], []
    for e in examples:
        row = audio[(e.hf_split, e.row_index)]
        clip = cut_clip(row.audio, row.sample_rate, e)
        utterance_peak = np.max(np.abs(row.audio))
        clip_peak = np.max(np.abs(clip))
        if clip_peak == 0 or utterance_peak == 0:
            continue
        gain.append(utterance_peak / clip_peak)
        plan_formula.append(np.max(np.abs(clip - clip.mean()))
                            / utterance_peak)
    gain, plan_formula = np.array(gain), np.array(plan_formula)
    summary = {"n_queries": int(len(gain))}
    for name, values in (("max_utt_over_max_clip", gain),
                         ("plan_formula", plan_formula)):
        summary[name] = {"median": float(np.median(values)),
                         "p90": float(np.percentile(values, 90)),
                         "min": float(values.min()),
                         "max": float(values.max())}
    return summary


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--eval-dir", type=Path, default=EVAL)
    parser.add_argument("--split-manifest", type=Path,
                        default=Path("outputs/splits/textdisjoint_q20_v2.tsv"))
    parser.add_argument("--alignment-dir", type=Path,
                        default=Path("outputs/alignment"))
    parser.add_argument("--out", type=Path, default=Path("outputs/posthoc"))
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    provenance = start_run(args.allow_dirty)
    started = time.time()
    rows, records = paired_table(args.eval_dir)
    ratios = level_ratios(args.split_manifest, args.alignment_dir,
                          args.eval_dir / "vtln_mfcc_htk_described_4k_pn_gmm64"
                          / "per_query.tsv")
    result = {"comparisons": records, "level_ratios": ratios,
              "runtime_s": round(time.time() - started, 1),
              **finish_run(provenance)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "post_hoc.json").write_text(json.dumps(result, indent=2),
                                            encoding="utf-8")
    table = ["| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) "
             "| Excludes 0 (p@N / MAP) |", "|---|---|---|---|---|", *rows]
    (args.out / "post_hoc.md").write_text("\n".join(table) + "\n",
                                          encoding="utf-8")
    print("\n".join(table))
    print(json.dumps(ratios, indent=2))


if __name__ == "__main__":
    main()
