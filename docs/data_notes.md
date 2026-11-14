# Data notes: TIMIT on Hugging Face (`Siyong/speech_timit`)

Inspected read-only on 2026-11-14 through the public HF API, the repo's
`dataset_infos.json` (revision `ef7bffd`, last modified 2022-07-13) and one
row from the dataset-viewer rows API. No parquet file was downloaded and the
`datasets` package was not added.

## Format

| Item | Finding |
|---|---|
| Files | `data/train-00000-of-00002.parquet`, `data/train-00001-of-00002.parquet`, `data/test-00000-of-00001.parquet` |
| Columns | `audio`: struct of `array` (float32 sequence) and `sampling_rate` (int64); `sentence`: string |
| Splits | train = 5040 utterances, test = 1260 utterances |
| Sample rate | **Observed 16 kHz** on train row 0 (`audio.sampling_rate = 16000`, 38,605 samples = 2.41 s, sentence "combine all the ingredients in a large bowl"). Read from the `sampling_rate` field of the rows API JSON, which returns the array inline, so no WAV header was involved. Only row 0 was checked; the size estimate (about 49.2k float32 samples per utterance, 3.1 s mean at 16 kHz) is consistent with the rest of train being 16 kHz but does not prove it. |
| README / license | The repo has no README and an empty license field. TIMIT itself is LDC93S1 (licensed). |

## What is missing

- **No word or phone alignments.** Only the sentence text is present.
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
     alignment noise.
- **Q-84 keyword list:** derivable from `sentence` using the thesis rule (at
  least 6 letters, 7 to 20 test occurrences), but with this split's counts.
  Verify the rule text in the thesis before implementing.

## Suggested decision for the Orchestrator

Prefer option 1 (original TIMIT with `.WRD`/`.PHN`) if the user holds a copy.
Otherwise a reproduction on this HF copy will differ from the thesis in the
split, the keyword counts and the segment boundaries, so absolute p@N and MAP
values are not directly comparable to the thesis tables.

## Pending user decision D1

**Is a licensed LDC TIMIT copy with `.WRD`/`.PHN` files available?** (plan.md
section 4, D1.) Status: open, waiting for the user. Without it, Q-20 and Q-84
query audio would have to be cut by forced alignment on the HF copy, and that
experiment must be labelled approximate. Stages 2 to 6 do not depend on the
answer; Stage 7 does.
