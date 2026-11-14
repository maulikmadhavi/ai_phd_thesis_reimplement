# Data notes: TIMIT on Hugging Face (`Siyong/speech_timit`)

First inspected read-only on 2026-11-14 through the public HF API, the repo's
`dataset_infos.json` (revision `ef7bffd`, last modified 2022-07-13) and one
row from the dataset-viewer rows API. Since then the parquet files were read
at the pinned revision `ef7bffd88de7065b8b1c2fdc76e8364921c30e58`, through
pyarrow and `huggingface_hub` (the `datasets` package is not used); they live
in the Hugging Face cache, not in the repository.

## Format

| Item | Finding |
|---|---|
| Files | `data/train-00000-of-00002.parquet`, `data/train-00001-of-00002.parquet`, `data/test-00000-of-00001.parquet` |
| Columns | `audio`: struct of `array` (float32 sequence) and `sampling_rate` (int64); `sentence`: string |
| Splits | train = 5040 utterances, test = 1260 utterances |
| Sample rate | **16 kHz on every row.** `iter_timit_rows` (`qbestd.data.timit_hf`) raises on any other rate, and the alignment run read all 6300 rows (5040 train, 1260 test) without raising (see `docs/alignment_notes.md`). Row 0 of train was earlier seen as 38,605 samples = 2.41 s. |
| README / license | The repo has no README and an empty license field. TIMIT itself is LDC93S1 (licensed). |

## What is missing

- **No word or phone alignments in the dataset.** Only the sentence text is
  present. Word boundaries now come from forced alignment (see D1 below).
- **No identifiers.** There is no speaker, dialect, sentence ID or file name.
  The `/sa/` sentences therefore cannot be excluded by name. Only the two fixed
  SA texts can be matched by string:
  "She had your dark suit in greasy wash water all year" and
  "Don't ask me to carry an oily rag like that".

## Split differs from official TIMIT

Official TIMIT has 4620 train and 1680 test utterances, which makes 6300.
This dataset also has 6300 (5040 + 1260), but in an 80/20 ratio, so the split
was redrawn. How it was drawn is undocumented: the repo has no README, so
nothing says whether it is random or speaker-disjoint, and the rows carry no
speaker IDs to check. Consequences:
- "Queries from train, documents from test" can still be followed, but whether
  speakers overlap is unknown.
- Keyword occurrence counts in the test split need not match the thesis tables
  (for example the Q-84 rule of 7 to 20 test occurrences).

## Implications for the plan

- **Open question 2 (sample rate), input side:** TIMIT audio is 16 kHz, so the
  8 kHz that the thesis's 0 to 4000 Hz mel filters imply needs downsampling.
  `AudioFrontEndConfig.sample_rate` already defaults to 8000 and is marked
  unverified. Whether the thesis downsampled is still open (plan.md section 4,
  question 14).
- **Document-level ground truth (p@N, MAP): derivable.** Whether a test
  utterance contains a keyword can be decided by word matching on `sentence`.
- **Q-20 and Q-84 query audio: not derivable from this dataset alone.** Query
  examples need the audio segment of a keyword, which needs word time
  boundaries. Options:
  1. Use the original LDC TIMIT `.WRD` files, if a copy is available. They
     would be matched to the HF rows by sentence text plus a waveform check,
     because the HF rows have no IDs.
  2. Forced alignment of the known text, which adds a dependency and
     alignment noise. **Chosen** (see D1 below).
- **Q-84 keyword list:** derivable from `sentence` using the thesis rule (at
  least 6 letters, 7 to 20 test occurrences), but with this split's counts.
  Verify the rule text in the thesis before implementing.

## Suggested decision for the Orchestrator (superseded)

This section recommended the original TIMIT with `.WRD`/`.PHN` files if the
user had a copy. The user chose forced alignment instead (D1 below). A
reproduction on this HF copy still differs from the thesis in the split, the
keyword counts and the segment boundaries, so absolute p@N and MAP values are
not directly comparable to the thesis tables.

## Resolved decision D1

**Resolution (2026-11-14, the user):** no licensed LDC TIMIT copy is used. Word
boundaries for Q-20 and Q-84 query cutting come from the forced aligner
`Scicom-intl/Where-Words-Begin-and-End-Whisper-Large-V3` (licence **CC BY-NC
4.0**, non-commercial, personal research only), run on both splits of this HF
copy. It replaces the MFA idea in the handoff request, Q14.

- Model revision `618763b1ed3ae17cb9a2062d6d4d0de436828c7a`; dataset revision
  `ef7bffd88de7065b8b1c2fdc76e8364921c30e58`. Both are pinned in code.
- Result: 6300 of 6300 rows aligned (54,198 words), 15 words under 20 ms in
  9 rows, all listed in `docs/alignment_notes.md` together with the sanity
  checks and 10 spot-check WAVs for the user to listen to.
- **Wording to use in any results table: "approximate against the thesis".**
  The boundaries are model output (the card reports 10.7 ms mean error on the
  official TIMIT test set; we did not measure it), the split is redrawn, and
  there are no speaker or sentence IDs.
- Manifests are written to `outputs/alignment/` and are git-ignored, because
  they derive from LDC text through a CC BY-NC model. Reproduce with
  `pixi run -e align align-timit`.
- Stage 7 must use `normalize_transcript` from `qbestd.data.timit_hf` for
  keyword matching, so words match the manifest tokens exactly.
- Stages 2 to 6 are unaffected.
