# Data notes: TIMIT on Hugging Face (`Siyong/speech_timit`)

Inspected read-only on 2026-11-14 through the public HF API and the repo's
`dataset_infos.json` (revision `ef7bffd`, last modified 2022-07-13). No data was
downloaded and the `datasets` package was not added.

## Format

| Item | Finding |
|---|---|
| Files | `data/train-00000-of-00002.parquet`, `data/train-00001-of-00002.parquet`, `data/test-00000-of-00001.parquet` |
| Columns | `audio`: struct of `array` (float32 sequence) and `sampling_rate` (int64); `sentence`: string |
| Splits | train = 5040 utterances, test = 1260 utterances |
| Sample rate | Not stated in the metadata. **Inferred 16 kHz**: the train split is 992,565,400 bytes for 5040 utterances, i.e. about 49.2k float32 samples (3.1 s) per utterance at 16 kHz. At 8 kHz that would be about 6.2 s, which is too long for TIMIT. Confirm by reading `sampling_rate` from the first parquet row group. |
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
This dataset also has 6300 (5040 + 1260), but in an 80/20 ratio. The split was
redrawn, probably at random and probably without regard to speakers.
Consequences:
- "Queries from train, documents from test" can still be followed, but speakers
  likely overlap, which makes the task easier than in the thesis.
- Keyword occurrence counts in the test split will not match the thesis tables
  (for example the Q-84 rule of 7 to 20 test occurrences).

## Implications for the plan

- **Open question 2 (sample rate), input side:** TIMIT audio is 16 kHz, so the
  8 kHz that the thesis's 0 to 4000 Hz mel filters imply needs downsampling.
  `AudioFrontEndConfig.sample_rate` already defaults to 8000 and is marked
  unverified. Whether the thesis downsampled is still open.
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
