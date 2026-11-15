# Text-disjoint split `textdisjoint_q20_v1`

Declared **before any score was computed on it**. The split is never redrawn;
any change becomes a new name (`..._v2`) with a written reason.

**Labels:** closer to the thesis on sentence context; **not** an official
TIMIT reconstruction; speaker overlap present (amount unknown, likely larger
than on the HF split, because each speaker's sentences are now spread across
both sides). It is reported next to the HF baseline, never in place of it.

| | |
|---|---|
| Rule name | `textdisjoint_q20_v1` |
| Manifest | `outputs/splits/textdisjoint_q20_v1.tsv` (git-ignored, reproducible) |
| Manifest sha256 | `ee27b531237a6e197e136880a7e7632c300ac9288c587f8083cc3705a65a839a` |
| `split_id` | `textdisjoint_q20_v1-ee27b531237a` |
| Reproduce | `pixi run python -m qbestd.data.text_split` |
| Inputs | transcripts of both HF splits (revision `ef7bffd88de7`), the thesis `Table:TIMITdata` counts and the official quotas. No audio, no scores, no RNG |

The manifest holds `hf_split, row_index, side, group_hash` only. No sentence
text, features or audio are stored in it.

## The rule

1. **Universe.** Every non-SA row of both HF splits, keyed by the original
   `(hf_split, row_index)`. Rows are grouped by the normalised text
   (`normalize_transcript`, joined by spaces). The group hash is
   `sha256("qbestd-textsplit-v1\n" + text)`.
2. **Keyword constraints.** Keywords that share a group form a connected
   component; components are processed in table order of their first
   keyword. For a component every assignment of all its groups is
   enumerated; the cost is the sum over its keywords of
   `|test tokens - Occ.| + |train tokens - Inst.|`, counting tokens in the
   transcripts before any aligner flag. The minimum cost wins; ties go to the
   lexicographically smallest sorted tuple of the test-side hashes over the
   component's groups.
3. **Quotas.** The test side holds 120 multi-read and 504 single-read groups
   (the official counts of non-SA test sentences: 168 speakers x 8). The
   remaining test groups are the untouched groups in ascending hash order
   within each stratum; every other group is train. If step 2 had exceeded a
   quota, nothing would be moved and the excess reported (it did not).

### Why step 2 is joint (change before declaration)

The first draft decided one keyword at a time, in table order. That left
"tomorrow" at **cost 8** (train 7 vs Inst. 3, test 3 vs Occ. 7): its 7-read
group ("if carol comes tomorrow ... meeting at two") also contains "meeting",
and "meeting" decided that shared group first, by hash tie-break, in the wrong
direction for "tomorrow". Solving each connected component jointly reaches
cost 0 for all 20 keywords. The change uses only transcripts and the thesis
table, and no score existed on this split when it was made.

Components with more than one keyword (3):
- birth, organizations
- love, youngsters
- meeting, tomorrow

All other keywords are components of their own. The summed cost of every
component is 0.

## Result of the rule

| | Train side | Test side |
|---|---|---|
| Rows | 3704 | 1336 |
| Multi-read groups | 333 | 120 |
| Single-read groups | 1405 | 504 |

Groups in total: 2362. Thesis: 3696 train utterances
(`Representation.tex` line 174) and 1344 test documents (`Unsupervised.tex`
line 74). Multi-read groups hold 2 to 7 rows (the odd sizes are probably SX
texts split by transcript variants), so the row totals differ slightly from
3696 and 1344 while the group quotas are exact.

Placement by step 2: 19 of 120
multi-read and 6 of 504
single-read test groups; step 3 added 101 multi-read and
498 single-read groups. No quota was exceeded or short.

### Rows relative to the HF split

| HF split -> side | Rows |
|---|---|
| train -> train | 2952 |
| train -> test | 1099 |
| test -> train | 752 |
| test -> test | 237 |

1851 of 5040 non-SA rows (36.7 %) change side.
Row indices stay the original `(hf_split, row_index)`; word alignments are
looked up by that key in the per-HF-split manifests.

## Keywords against the thesis

| Keyword | Train tokens | Thesis Inst. | Test tokens | Thesis Occ. | Cost |
|---|---|---|---|---|---|
| artists | 7 | 7 | 7 | 7 | 0 |
| beautiful | 3 | 3 | 8 | 8 | 0 |
| birth | 4 | 4 | 7 | 7 | 0 |
| destroy | 9 | 9 | 7 | 7 | 0 |
| development | 9 | 9 | 8 | 8 | 0 |
| garbage | 8 | 8 | 7 | 7 | 0 |
| government | 14 | 14 | 8 | 8 | 0 |
| intelligence | 8 | 8 | 7 | 7 | 0 |
| love | 4 | 4 | 16 | 16 | 0 |
| marriage | 3 | 3 | 7 | 7 | 0 |
| meeting | 7 | 7 | 7 | 7 | 0 |
| morning | 15 | 15 | 14 | 14 | 0 |
| ocean | 7 | 7 | 7 | 7 | 0 |
| organizations | 7 | 7 | 7 | 7 | 0 |
| problems | 5 | 5 | 7 | 7 | 0 |
| shellfish | 14 | 14 | 7 | 7 | 0 |
| simple | 8 | 8 | 8 | 8 | 0 |
| surface | 3 | 3 | 7 | 7 | 0 |
| tomorrow | 3 | 3 | 7 | 7 | 0 |
| youngsters | 7 | 7 | 7 | 7 | 0 |

Tokens are exact matches after `normalize_transcript`; "Occ." in the thesis
is read as a token count here (open question 21). Query instances later lost
to aligner flags are counted in `docs/results_timit_q20.md`.

## What this split does not do

- It is not the official TIMIT train/test split (core test set, dialect
  balance and speaker disjointness are not reproduced).
- Speakers are not separated: utterances of one speaker may be on both sides,
  and likely more often than on the HF split. The size of the effect is not
  measured.
- Only the Q-20 keyword counts and the sentence-text constraint were used to
  build it. Nothing here was tuned towards a retrieval score.
