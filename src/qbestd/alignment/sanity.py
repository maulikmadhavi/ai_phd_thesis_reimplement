"""Sanity checks for the word manifests (alignment_notes.md checks 2-5).

Usage (align or core environment, after ``qbestd.alignment.run``)::

    python -m qbestd.alignment.sanity --out outputs/alignment

Writes ``sanity.json`` and ten cut WAV files to ``<out>/spot_check/`` (both
git-ignored). Check 1 (counts and rule violations) is in ``summary.json``.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from qbestd.alignment.manifest import read_manifest
from qbestd.audio.energy import log_energy
from qbestd.audio.framing import frame_signal
from qbestd.audio.io import save_audio
from qbestd.data.timit_hf import (
    download_timit_parquet,
    iter_timit_rows,
    normalize_transcript,
)

SA_SENTENCE = ("she had your dark suit in greasy wash water all year")
SA_PROBE_WORD = "dark"
SAMPLE_RATE = 16000
SPOT_PAD_S = 0.02
N_ENERGY_WORDS = 20
N_SPOT_WORDS = 10
LOW_ENERGY_PERCENTILE = 10


def read_rows_file(path):
    """``{row_index: (duration_s, sentence)}`` from ``run``'s rows file."""
    rows = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines()[1:]:
        index, duration, sentence = line.split("\t", 2)
        rows[int(index)] = (float(duration), sentence)
    return rows


def iqr_outliers(values, factor=3.0):
    """Boolean mask of values beyond ``factor`` IQRs outside the quartiles."""
    values = np.asarray(values, dtype="float64")
    q1, q3 = np.percentile(values, [25, 75])
    spread = q3 - q1
    return (values < q1 - factor * spread) | (values > q3 + factor * spread)


def relative_start_spread(segments, rows, word=SA_PROBE_WORD):
    """Spread of start/duration of ``word`` over the SA sentence rows.

    ``segments`` are one split's :class:`WordSegment` s; ``rows`` comes from
    :func:`read_rows_file`. Returns None when no row matches.
    """
    wanted = SA_SENTENCE.split()
    sa_rows = {index for index, (_, sentence) in rows.items()
               if normalize_transcript(sentence) == wanted}
    found = [(s.row_index, s.start_s / rows[s.row_index][0])
             for s in segments if s.row_index in sa_rows and s.word == word]
    if not found:
        return None
    indices = [index for index, _ in found]
    positions = np.array([position for _, position in found])
    q1, median, q3 = np.percentile(positions, [25, 50, 75])
    mask = iqr_outliers(positions)
    return {"word": word, "n_rows": len(found), "min": float(positions.min()),
            "q1": float(q1), "median": float(median), "q3": float(q3),
            "max": float(positions.max()), "std": float(positions.std()),
            "outlier_rows": [indices[i] for i in np.flatnonzero(mask)]}


def segment_energy_check(audio, segment, sample_rate=SAMPLE_RATE):
    """Compare mean frame log-energy inside a word with the quiet frames.

    Frames are 25 ms / 10 ms; a frame belongs to the word when its centre is
    inside it (the nearest frame when none is). Returns a dict whose ``ok``
    is True when the word's mean exceeds the utterance's 10th percentile.
    """
    frames = frame_signal(audio, sample_rate)
    energy = log_energy(frames)
    centres = (np.arange(len(energy)) * 0.010) + 0.0125
    inside = (centres >= segment.start_s) & (centres <= segment.end_s)
    if not inside.any():
        inside[np.argmin(np.abs(centres - (segment.start_s + segment.end_s)
                                / 2))] = True
    quiet = float(np.percentile(energy, LOW_ENERGY_PERCENTILE))
    mean_inside = float(energy[inside].mean())
    return {"mean_log_energy": mean_inside, "p10_log_energy": quiet,
            "ok": mean_inside > quiet}


def cut_segment(audio, segment, sample_rate=SAMPLE_RATE, pad_s=SPOT_PAD_S):
    """The samples of a word with ``pad_s`` seconds either side."""
    start = max(0, int(round((segment.start_s - pad_s) * sample_rate)))
    end = min(len(audio), int(round((segment.end_s + pad_s) * sample_rate)))
    return audio[start:end]


def pick_words(segments_by_split, count, seed):
    """``count`` random ``(split, WordSegment)`` pairs, reproducibly."""
    pool = [(split, s) for split, segments in sorted(segments_by_split.items())
            for s in segments]
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(pool), size=count, replace=False)
    return [pool[i] for i in sorted(chosen)]


def load_audio_rows(split, wanted):
    """``{row_index: float32 audio}`` for the ``wanted`` row indices."""
    wanted = set(wanted)
    return {row.row_index: row.audio
            for row in iter_timit_rows(download_timit_parquet(split), split)
            if row.row_index in wanted}


def run_sanity(out_dir, seed=0):
    out_dir = Path(out_dir)
    segments, rows = {}, {}
    for split in ("train", "test"):
        segments[split], _ = read_manifest(
            out_dir / f"timit_hf_words_{split}.tsv")
        rows[split] = read_rows_file(out_dir / f"timit_hf_rows_{split}.tsv")
    durations = [s.end_s - s.start_s for v in segments.values() for s in v]
    energy_words = pick_words(segments, N_ENERGY_WORDS, seed)
    spot_words = pick_words(segments, N_SPOT_WORDS, seed + 1)
    audio = {split: load_audio_rows(
        split, {s.row_index for sp, s in energy_words + spot_words
                if sp == split}) for split in segments}
    energy = []
    for split, seg in energy_words:
        result = segment_energy_check(audio[split][seg.row_index], seg)
        energy.append({"split": split, "row": seg.row_index,
                       "word": seg.word, **result})
    spot_dir = out_dir / "spot_check"
    spot_dir.mkdir(parents=True, exist_ok=True)
    spots = []
    for split, seg in spot_words:
        name = f"{split}_{seg.row_index}_{seg.word_index}_{seg.word}.wav"
        clip = cut_segment(audio[split][seg.row_index], seg)
        save_audio(spot_dir / name, np.clip(clip, -1.0, 1.0), SAMPLE_RATE)
        spots.append({"file": name, "start_s": seg.start_s,
                      "end_s": seg.end_s})
    report = {
        "median_word_duration_s": float(np.median(durations)),
        "median_in_0.15_0.5": bool(0.15 <= np.median(durations) <= 0.5),
        "sa_dark_relative_start": {
            split: relative_start_spread(segments[split], rows[split])
            for split in segments},
        "energy_check": energy,
        "energy_check_pass": sum(item["ok"] for item in energy),
        "spot_checks": spots}
    (out_dir / "sanity.json").write_text(json.dumps(report, indent=2),
                                         encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path("outputs/alignment"))
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    report = run_sanity(args.out, args.seed)
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("energy_check", "spot_checks")}, indent=2))


if __name__ == "__main__":
    main()
