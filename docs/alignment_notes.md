# TIMIT word alignment notes

Word boundaries for the Hugging Face TIMIT copy, produced by a Whisper-based
forced aligner. They approximate the original TIMIT `.WRD` files (which we do
not have, see `docs/data_notes.md`); they are not identical to them.

## What was run

| Item | Value |
|---|---|
| Aligner | `Scicom-intl/Where-Words-Begin-and-End-Whisper-Large-V3` (Whisper large-v3 with merged LoRA, forced alignment through timestamp-token embeddings) |
| Model revision | `618763b1ed3ae17cb9a2062d6d4d0de436828c7a` |
| Model licence | **CC BY-NC 4.0** (non-commercial). Fine for this personal research; weights are never committed or redistributed |
| `align.py` SHA-256 | `8f7a3590aa3a83dbc9cc33db3d6051b1c9b94f1212c353655c96fc841c910ee0` (checked before the importlib load; verified equal at download) |
| Dataset | `Siyong/speech_timit`, revision `ef7bffd88de7065b8b1c2fdc76e8364921c30e58` |
| Files in the HF cache | model 3.09 GB (`model.safetensors`); dataset parquet 0.56 GB (train 2 files 450 MB, test 1 file 112 MB) |
| Device | RTX 5070, bf16, batch size 16, torch 2.13.0 (conda-forge, CUDA, `sm_120` listed in the arch list) |
| Command | `pixi run -e align align-timit` (`python -m qbestd.alignment.run --split all --device cuda`) |
| Runtime | train 362 s, test 88 s |
| Language flag | `"en"` for every row; transcripts passed as word lists from `normalize_transcript` |

The aligner card reports a 10.7 ms mean word-boundary error on the TIMIT test
set. We did not measure that ourselves (no reference `.WRD` files here).

## Sample rate

`iter_timit_rows` raises if any row is not 16 kHz. The run completed over all
5040 + 1260 = 6300 rows without raising, so **every row is 16 kHz**. This
replaces the earlier "train row 0 only" observation.

## Outputs (local, git-ignored, never committed)

All under `outputs/alignment/`. The manifests derive from LDC-licensed TIMIT
text through a CC BY-NC model and are reproducible from the two pinned
revisions, so they are not in the repository.

| File | SHA-256 |
|---|---|
| `timit_hf_words_train.tsv` | `d2c63f4eb7d9e2f0a5679999c4217101378848823a98257fc45d24365d030e23` |
| `timit_hf_words_test.tsv` | `4c62da3bbbf551de9e88c2e4213719654ce0e223b54ab87e4e208c6b588708de` |
| `timit_hf_rows_train.tsv` | `c442728ef4b82ead20853f4c6c25d71c3d5339cbd256a364759222fc7950a92c` |
| `timit_hf_rows_test.tsv` | `ac27a27910ea2b0c18ec43a733db9ece28dffd5155d8f5f4ad39f82cf0c4b7f8` |

Also written: `failures.tsv`, `summary.json`, `sanity.json`, `run.log`, and
`spot_check/*.wav`. The `timit_hf_rows_*.tsv` files hold each row's duration
and sentence, for the sanity checks. The hashes should repeat on a re-run with
the same environment; the GPU's bf16 arithmetic could change the last digit of
a time, so a different hash alone is not proof of a problem.

## Counts (`summary.json`)

| | train | test |
|---|---|---|
| Rows | 5040 | 1260 |
| Failed rows | 0 | 0 |
| Words | 43237 | 10961 |
| Rule violations | 11 (7 rows) | 4 (2 rows) |
| Word duration p1 / p5 / p25 (s) | 0.048 / 0.072 / 0.158 | 0.048 / 0.072 / 0.157 |
| Word duration median (s) | 0.285 | 0.283 |
| Word duration p75 / p95 / p99 (s) | 0.410 / 0.651 / 0.830 | 0.405 / 0.650 / 0.828 |
| Min / max word duration (s) | 0.010 / 1.633 | 0.010 / 1.322 |

Word-count check: every aligned row has exactly as many segments as
`normalize_transcript` has tokens (no violation of that rule).

## Sanity check results

1. **Every row aligned, violations explained.** 6300 of 6300 rows aligned and
   none failed. All 15 violations are the same rule, word duration under 20 ms
   (no negative starts, no end past the audio, no `end <= start`, no
   decreasing starts, no word over 2 s). Row indices below are 0-based within
   the split:

   | Split | Row | Words under 20 ms |
   |---|---|---|
   | train | 908 | `a`, `meeting` (10 ms each) |
   | train | 1241 | `the` (14 ms) |
   | train | 2090 | `meeting` (10 ms) |
   | train | 3213 | `a`, `result`, `of` (10 ms each) |
   | train | 3505 | `universe`, `is` (10, 11 ms) |
   | train | 4300 | `a` (17 ms) |
   | train | 4769 | `a` (19 ms) |
   | test | 885 | `a` (18 ms) |
   | test | 1151 | `sailboat`, `may`, `have` (10 ms each) |

   **Explanation: the aligner collapses a short run of words onto one
   instant.** In rows 908, 3213, 3505 and test 1151 two to four neighbouring
   words (a content word such as `meeting` or `sailboat` among them) get the
   same start, with the 10 ms floor the model applies (`end >= start + 0.01`).
   Those are alignment errors; real 10 ms words do not exist. The single-word
   cases of 14 to 19 ms (`a`, `the`) are borderline and may be legitimate
   reduced function words. **Stage 7 should drop any keyword whose segment is
   shorter than 20 ms** (or whose row appears above), which loses at most a
   handful of occurrences. 38 train and 8 test words are 30 ms or shorter,
   503 and 137 are 50 ms or shorter; those are not violations but are short.

2. **Median word duration 0.285 s**, inside the 0.15 to 0.5 s band. Pass.

3. **SA sentence ("she had your dark suit in greasy wash water all year").**
   630 rows (488 train, 142 test) contain it. The relative start
   (`start / duration`) of `dark`:

   | | n | min | Q1 | median | Q3 | max | std |
   |---|---|---|---|---|---|---|---|
   | train | 488 | 0.144 | 0.196 | 0.209 | 0.222 | 0.400 | 0.028 |
   | test | 142 | 0.175 | 0.199 | 0.210 | 0.224 | 0.307 | 0.025 |

   Beyond 3 IQR there are 10 train rows (466, 1092, 1627, 2095, 3364, 3386,
   3451, 3802, 4229, 4543) and 2 test rows (1088, 1105), 12 of 630. Looking at
   their segments, eleven are explained by a long leading pause (`she` starts
   at 0.5 to 0.9 s) or a slow speaker, with sensible word durations. Train
   row 3802 is different: `she` starts at 0.14 s but the first three words
   take 0.26, 0.35 and 0.34 s, which may be a hesitation or a misalignment.
   It is worth listening to if a Stage 7 result looks odd for that row.

4. **Energy inside words.** For 20 random words (seed 0, from both splits)
   the mean frame log-energy inside the segment was above the utterance's
   10th-percentile frame energy in 20 of 20 cases. The check is weak (a
   10th percentile is a low bar) but catches words placed on silence. Details
   in `outputs/alignment/sanity.json`.

5. **Spot-check WAVs.** Ten cut words (20 ms padding each side) are in
   `outputs/alignment/spot_check/`, named `<split>_<row>_<word index>_<word>.wav`:
   `test_214_9_worried`, `test_893_3_you`, `train_1703_4_survive`,
   `train_1949_8_cost`, `train_295_4_suit`, `train_3496_1_leather`,
   `train_3925_1_hats`, `train_4710_4_carry`, `train_4721_1_process`,
   `train_692_6_competitors`. **The user should listen to these**; no one has.

## Other observations

- Neighbouring words overlap: 12732 of 38197 adjacent pairs in train (3254 of
  9701 in test) have the next start before the previous end, 261 (59) by more
  than 20 ms, at most 0.23 s (0.27 s). Treat boundaries as roughly 20 to 50 ms
  accurate, not exact, and pad cuts rather than trusting a tight start.
- Gaps over 0.5 s between words: 25 train, 7 test (pauses).
- Rows have no speaker or sentence-id metadata in the parquet files, so we
  cannot separate SA, SX and SI sentences or speakers, and the train/test
  split method is whatever the dataset author chose.

## Reproduce

```
pixi run -e align align-timit            # about 8 minutes on an RTX 5070
pixi run -e align python -m qbestd.alignment.sanity --out outputs/alignment
```

Core-environment tests use a fake aligner. To run the real model once:
`QBESTD_RUN_ALIGNER=1 pixi run -e align pytest -q tests/alignment -k real_model`.
