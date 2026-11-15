"""Optional ASR audit of the word manifests (a diagnostic, not a gate).

Usage (align environment, downloads ``openai/whisper-base`` once)::

    pixi run -e align python -m qbestd.alignment.asr_audit

Samples 300 words of at least 3 letters (fixed seed), cuts each with 20 ms
padding at its aligned position and at +-0.25 s, and asks Whisper-base what
it hears. A *hit* is an exact match or a difflib ratio of at least 0.75
against any recognised word or the whole hypothesis. If the alignment is
good, true cuts should hit far more often than shifted cuts. Writes
``asr_audit.json`` next to the manifests. A low true-cut rate can also come
from Whisper-base failing on 0.3 s clips, so read it together with the
shifted rates.
"""

import argparse
import difflib
import json
import re
from dataclasses import replace
from pathlib import Path

import numpy as np

from qbestd.alignment.manifest import read_manifest
from qbestd.alignment.sanity import (
    SAMPLE_RATE,
    cut_segment,
    load_audio_rows,
    read_rows_file,
)

ASR_REPO = "openai/whisper-base"
ASR_REVISION = "e37978b90ca9030d5170a5c07aadb050351a65bb"
MIN_LETTERS = 3
N_WORDS = 300
SHIFT_S = 0.25
PAD_S = 0.02
HIT_RATIO = 0.75
BATCH_SIZE = 16
_NON_LETTER = re.compile(r"[^a-z']+")


def count_letters(word):
    return sum(char.isalpha() for char in word)


def eligible_words(segments, rows, min_letters=MIN_LETTERS,
                   shift_s=SHIFT_S):
    """Segments with enough letters whose shifted cuts stay inside the audio.

    ``rows`` is ``{row_index: (duration_s, sentence)}``. Requiring
    ``start - shift >= 0`` and ``end + shift <= duration`` keeps the three
    cuts of a word comparable (no clipped or empty cut).
    """
    return [s for s in segments
            if count_letters(s.word) >= min_letters
            and s.start_s - shift_s >= 0
            and s.end_s + shift_s <= rows[s.row_index][0]]


def shifted_segment(segment, shift_s):
    """Copy of ``segment`` moved by ``shift_s`` seconds."""
    return replace(segment, start_s=segment.start_s + shift_s,
                   end_s=segment.end_s + shift_s)


def is_hit(word, hypothesis, ratio=HIT_RATIO):
    """Exact match or difflib ratio >= ``ratio`` with any hypothesis word.

    The hypothesis is lowercased and stripped of everything but letters and
    apostrophes; the whole hypothesis (spaces removed) also counts as a
    candidate, for words that Whisper splits.
    """
    cleaned = _NON_LETTER.sub(" ", hypothesis.lower()).split()
    candidates = cleaned + ["".join(cleaned)]
    target = word.lower()
    for candidate in candidates:
        if not candidate:
            continue
        if candidate == target:
            return True
        if difflib.SequenceMatcher(None, target, candidate).ratio() >= ratio:
            return True
    return False


def hit_rate(words, hypotheses):
    """Fraction of ``words`` whose hypothesis is a hit."""
    if not words:
        return float("nan")
    return sum(is_hit(w, h) for w, h in zip(words, hypotheses)) / len(words)


def sample_words(segments_by_split, rows_by_split, n_words, seed):
    """``n_words`` eligible ``(split, segment)`` pairs, reproducibly."""
    pool = [(split, s) for split in sorted(segments_by_split)
            for s in eligible_words(segments_by_split[split],
                                    rows_by_split[split])]
    chosen = np.random.default_rng(seed).choice(
        len(pool), size=min(n_words, len(pool)), replace=False)
    return [pool[i] for i in sorted(chosen)]


def load_asr(device, dtype_name="float32"):
    """Whisper-base at the pinned revision; returns (processor, model)."""
    import torch  # lazy: align environment only
    from transformers import (
        WhisperForConditionalGeneration,
        WhisperProcessor,
    )
    processor = WhisperProcessor.from_pretrained(ASR_REPO,
                                                 revision=ASR_REVISION)
    model = WhisperForConditionalGeneration.from_pretrained(
        ASR_REPO, revision=ASR_REVISION,
        torch_dtype=getattr(torch, dtype_name)).to(device).eval()
    return processor, model


def transcribe(clips, processor, model, device):
    """Greedy English transcription of 16 kHz clips, in batches."""
    import torch
    texts = []
    for start in range(0, len(clips), BATCH_SIZE):
        batch = [np.asarray(c, dtype=np.float32)
                 for c in clips[start:start + BATCH_SIZE]]
        inputs = processor(batch, sampling_rate=SAMPLE_RATE,
                           return_tensors="pt")
        with torch.no_grad():
            ids = model.generate(inputs.input_features.to(device),
                                 language="en", task="transcribe",
                                 max_new_tokens=16)
        texts += processor.batch_decode(ids, skip_special_tokens=True)
    return texts


def run_audit(out_dir, n_words=N_WORDS, seed=0, device="cuda"):
    out_dir = Path(out_dir)
    segments, rows = {}, {}
    for split in ("train", "test"):
        segments[split], _ = read_manifest(
            out_dir / f"timit_hf_words_{split}.tsv")
        rows[split] = read_rows_file(out_dir / f"timit_hf_rows_{split}.tsv")
    picked = sample_words(segments, rows, n_words, seed)
    audio = {split: load_audio_rows(
        split, {s.row_index for sp, s in picked if sp == split})
        for split in segments}
    processor, model = load_asr(device)
    words = [s.word for _, s in picked]
    report = {"asr": ASR_REPO, "asr_revision": ASR_REVISION, "seed": seed,
              "n_words": len(words), "min_letters": MIN_LETTERS,
              "shift_s": SHIFT_S, "padding_s": PAD_S,
              "hit_rule": f"exact or difflib ratio >= {HIT_RATIO}"}
    examples = {}
    for name, shift in (("true", 0.0), ("minus", -SHIFT_S),
                        ("plus", SHIFT_S)):
        clips = [cut_segment(audio[split][s.row_index],
                             shifted_segment(s, shift), pad_s=PAD_S)
                 for split, s in picked]
        hypotheses = transcribe(clips, processor, model, device)
        report[f"hit_rate_{name}"] = hit_rate(words, hypotheses)
        examples[name] = [{"word": w, "heard": h}
                          for w, h in list(zip(words, hypotheses))[:10]]
    report["examples"] = examples
    (out_dir / "asr_audit.json").write_text(json.dumps(report, indent=2),
                                            encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path("outputs/alignment"))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--n-words", type=int, default=N_WORDS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    report = run_audit(args.out, args.n_words, args.seed, args.device)
    print({k: v for k, v in report.items() if k.startswith("hit_rate")})


if __name__ == "__main__":
    main()
