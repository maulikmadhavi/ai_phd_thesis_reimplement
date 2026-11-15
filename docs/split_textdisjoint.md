# Text-disjoint split `textdisjoint_q20_v1`

Declared **before any score was computed on it**. The split is never redrawn;
any change becomes a new name (`..._v2`) with a written reason. v1 is kept
as declared; **v2 is declared at the end of this file** (section "v2"), with
its reason.

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


---

# v2: `textdisjoint_q20_v2`

**Reason (verbatim): "variant groups split SX texts across sides (found in
review)".** The Reviewer of cycle 5 found that v1 groups rows by exact text, so
eight SX sentences whose transcripts differ by one token (an article, "will"
against "would", "shimmered" against "simmered") had their variants on
opposite sides. Codex then asked for the cause to be removed (`ba99a8a` Q1).
v1 stays as declared and stays in the results as a historical row; v2 is a
new name. Declared **before any v2 model is trained or scored**.

**Labels (as v1):** closer to the thesis on sentence context; **not** an
official TIMIT reconstruction; speaker overlap present (amount unknown).
The post-build scan below finds no one-edit variant pair across sides, which
the label "not fully sentence-disjoint" of v1 took exception to.

| | |
|---|---|
| Rule name | `textdisjoint_q20_v2` |
| Manifest | `outputs/splits/textdisjoint_q20_v2.tsv` (git-ignored, reproducible) |
| Manifest sha256 | `0e913c50aae788f7b8dcde8926b419e39f0b74f959778d2a926bb5386cb8105d` |
| `split_id` | `textdisjoint_q20_v2-0e913c50aae7` |
| Reproduce | `pixi run python -m qbestd.data.text_split --rule v2` |
| v1 check | `--rule v1` still gives `textdisjoint_q20_v1-ee27b531237a` |

## The v2 rule

v1's rule (steps 1 to 3 above) plus one step between 1 and 2:

**1b. Merge verified variant links.** `V2_VARIANT_LINKS` in
`src/qbestd/data/text_variants.py` is an explicit, sorted tuple of
`(hash_a, hash_b)` pairs of **v1 group hashes**. Its *units* are the
connected components of those links only; there is no general one-edit rule
in the build. A unit's key is its smallest member hash. The hash prefix stays
`qbestd-textsplit-v1\n`, so the links name existing v1 hashes. Steps 2 and 3
and the manifest work on units: the tie-break, the step 3 hash order and the
manifest `group_hash` column all use the unit key, and a unit is multi-read
when it holds more than one row. Keyword tokens of a unit are counted per
transcript variant. The quotas stay at 120 multi-read and 504 single-read
test units. The build raises for a link that is not a sorted pair of known
hashes, and for a unit of more than 7 rows.

## Finding and verifying the links

Done on transcripts only, before any v2 score. `find_variant_candidates`
proposes a pair when the two token sequences differ by exactly one
substitution, insertion or deletion, at least one group is multi-read and the
combined row count is at most 7 (an SX text is read by 7 speakers). I checked
every proposed pair against the full normalised transcripts and the row
counts. The sentence text is not repeated here.

- The finder, with its two filters lifted, finds 21 one-edit
  pairs in all of the 2362 groups; it proposes 20.
  Excluded by the filters: 1 pair of two single-read groups (nothing
  says it is one sentence) and 0 over the 7-row cap.
- **Rejected after verification: none.** No group pairs with two different
  multi-read groups. One group (4 rows) has two partners (a 1-row and a
  2-row variant); together they make a 7-row unit.
- All 19 merged units hold **exactly 7 rows**, the number of
  speakers of an SX text, which is the check that each link joins variants of
  one sentence.
- 8 of the 20 links joined groups on opposite sides in v1. The
  Reviewer counted 8 crossed sentences: will/would (government), simmered
  against shimmered, a 4 + 2 pair differing by "the", and five more pairs
  described as 6 + 1 differing by "a", "the" or "at". The finder finds all of
  the crossed pairs: four 6 + 1 pairs (at, a, the, the), will/would,
  shimmered, the 4 + 2 pair and a 4 + 1 pair ("a"); the count 8 agrees. The
  Reviewer's text names five 6 + 1 pairs where the data holds four 6 + 1
  pairs plus the 4 + 1 pair; the doc records the difference rather than
  guessing which is meant. Question for the review.
- The other 12 links were both on the train side in v1 (or both on the
  test side) and are linked for the same reason (Q27: every verified pair).

### Link evidence (20 links, 19 units)

Hashes are the first 12 hex of the v1 group hash. "Edit" is relative to the
first hash; the token is the differing token only.

| # | Hash a | Hash b | Rows | Edit | Token | Keyword | v1 sides | Crossed in v1 |
|---|---|---|---|---|---|---|---|---|
| 1 | `0164a42a7486` | `40b189a45527` | 6 + 1 | substitution | this/the | - | test / test | no |
| 2 | `0609435b34ca` | `a3b42edc22f2` | 6 + 1 | deletion | at | - | test / train | yes |
| 3 | `0984b6229f40` | `cf064136a3b7` | 6 + 1 | insertion | a | - | test / train | yes |
| 4 | `09e46dbdc06b` | `55b771c503e3` | 6 + 1 | deletion | the | - | test / train | yes |
| 5 | `24181c08ebc9` | `cb69f3017232` | 6 + 1 | deletion | the | - | test / train | yes |
| 6 | `24a69ee84725` | `4f59ccc36397` | 1 + 6 | substitution | would/will | government | test / train | yes |
| 7 | `31820500b0cc` | `88de70720b33` | 1 + 6 | substitution | simmered/shimmered | - | test / train | yes |
| 8 | `3b70f551e889` | `f07866806318` | 4 + 1 | deletion | a | - | test / train | yes |
| 9 | `3b70f551e889` | `f43bec409d4a` | 4 + 2 | deletion | the | - | test / train | yes |
| 10 | `4566ad641f69` | `a4946f5c51ed` | 5 + 2 | deletion | a | - | train / train | no |
| 11 | `45c072ef7c8f` | `6f0ab47a079f` | 6 + 1 | deletion | a | - | train / train | no |
| 12 | `5302e3537839` | `5979ddfeda1d` | 6 + 1 | deletion | a | - | train / train | no |
| 13 | `5f6365c9433a` | `f84e16c77e75` | 1 + 6 | substitution | used/use | - | train / train | no |
| 14 | `62b22fe30ad9` | `f281b1ceff7c` | 6 + 1 | insertion | her | - | train / train | no |
| 15 | `845b65478f45` | `ff100ae27314` | 1 + 6 | substitution | remain/remained | - | train / train | no |
| 16 | `a0435d4e8896` | `e69015b9d66a` | 2 + 5 | substitution | cleaned/cleans | shellfish | train / train | no |
| 17 | `ca48eb2f5435` | `fe03851b0532` | 6 + 1 | deletion | the | - | train / train | no |
| 18 | `caccbb974bed` | `e44f9c30a8b6` | 6 + 1 | deletion | the | - | train / train | no |
| 19 | `cc396d7f8b83` | `f33def961554` | 1 + 6 | substitution | had/ate | - | train / train | no |
| 20 | `ee0def7dd934` | `f80fe9ac2666` | 1 + 6 | insertion | a | - | train / train | no |

## Result of the v2 rule

| | Train side | Test side |
|---|---|---|
| Rows | 3696 | 1344 |
| Multi-read units | 330 | 120 |
| Single-read units | 1388 | 504 |

2342 units from 2362 v1 groups: the 20 links join 39 groups into
19 units (one unit has three variants), 20 groups fewer. The rows per side
are now **3696 and 1344, the thesis counts** (v1: 3704 and 1336). That follows from
the quotas being exact in units and every unit of variants holding 7 rows; it
is not a target that was tuned.

Placement by step 2: 19 of 120 multi-read and 6 of 504 single-read
test units; step 3 added 101 multi-read and 498 single-read
units. No quota was exceeded or short.

### Rows relative to the HF split and to v1

| HF split -> side | Rows |
|---|---|
| train -> train | 2945 |
| train -> test | 1106 |
| test -> train | 751 |
| test -> test | 238 |

1857 of 5040 non-SA rows (36.8 %) change side
relative to the HF split (v1: 1851). **36 rows change side relative
to v1.**

## Per component: cost and minimum-cost assignments

`n_min` is the number of assignments of the component's units that reach the
minimum cost (one count per connected component). The winner is picked by the
unchanged tie-break, so a count above 1 means the choice among equal-cost
assignments rests on the hash order alone. v1 and v2 are side by side.

| Component | Groups v1 | Units v2 | Cost v1 | Cost v2 | n_min v1 | n_min v2 |
|---|---|---|---|---|---|---|
| artists | 2 | 2 | 0 | 0 | 2 | 2 |
| beautiful | 5 | 5 | 0 | 0 | 4 | 4 |
| birth, organizations | 6 | 6 | 0 | 0 | 1 | 1 |
| destroy | 4 | 4 | 0 | 0 | 2 | 2 |
| development | 5 | 5 | 0 | 0 | 6 | 6 |
| garbage | 3 | 3 | 0 | 0 | 2 | 2 |
| government | 5 | 4 | 0 | 0 | 5 | 3 |
| intelligence | 3 | 3 | 0 | 0 | 2 | 2 |
| love, youngsters | 9 | 9 | 0 | 0 | 15 | 15 |
| marriage | 4 | 4 | 0 | 0 | 1 | 1 |
| meeting, tomorrow | 5 | 5 | 0 | 0 | 1 | 1 |
| morning | 5 | 5 | 0 | 0 | 6 | 6 |
| ocean | 2 | 2 | 0 | 0 | 2 | 2 |
| problems | 6 | 6 | 0 | 0 | 1 | 1 |
| shellfish | 4 | 3 | 0 | 0 | 3 | 3 |
| simple | 4 | 4 | 0 | 0 | 4 | 4 |
| surface | 4 | 4 | 0 | 0 | 1 | 1 |

Every component has cost 0 in v2, as in v1. Components with a count of 1 are
fully determined by the thesis counts. "love, youngsters" has the largest
count (15 of 2^9 = 512 assignments); no component is undetermined in the
sense of a cost difference, only in which equal-cost assignment was taken
(Q28). The components "government" and "shellfish" lost one unit each to
a link; their counts are 3 (was 5) and 3 (unchanged).

## Keywords against the thesis (v2)

| Keyword | Train tokens | Thesis Inst. | Test tokens | Thesis Occ. | Cost | Changed from v1 |
|---|---|---|---|---|---|---|
| artists | 7 | 7 | 7 | 7 | 0 | no |
| beautiful | 3 | 3 | 8 | 8 | 0 | no |
| birth | 4 | 4 | 7 | 7 | 0 | no |
| destroy | 9 | 9 | 7 | 7 | 0 | no |
| development | 9 | 9 | 8 | 8 | 0 | no |
| garbage | 8 | 8 | 7 | 7 | 0 | no |
| government | 14 | 14 | 8 | 8 | 0 | no |
| intelligence | 8 | 8 | 7 | 7 | 0 | no |
| love | 4 | 4 | 16 | 16 | 0 | no |
| marriage | 3 | 3 | 7 | 7 | 0 | no |
| meeting | 7 | 7 | 7 | 7 | 0 | no |
| morning | 15 | 15 | 14 | 14 | 0 | no |
| ocean | 7 | 7 | 7 | 7 | 0 | no |
| organizations | 7 | 7 | 7 | 7 | 0 | no |
| problems | 5 | 5 | 7 | 7 | 0 | no |
| shellfish | 14 | 14 | 7 | 7 | 0 | no |
| simple | 8 | 8 | 8 | 8 | 0 | no |
| surface | 3 | 3 | 7 | 7 | 0 | no |
| tomorrow | 3 | 3 | 7 | 7 | 0 | no |
| youngsters | 7 | 7 | 7 | 7 | 0 | no |

No keyword count changed from v1 and no cost is nonzero, so no keyword lost
its coverage: each of the 20 keywords has its thesis Inst. on the train side
and Occ. on the test side.

## Post-build scan

The finder was run on the final v2 manifest (groups by exact text, side from
the manifest, same filters). **0 one-edit candidate pairs cross sides**
(v1: 8). 0 exact texts occur on both sides.
The scan only sees pairs that pass the finder's filters (at least one
multi-read group, at most 7 rows together); a variant pair of two single-read
groups would not be seen (1 such one-edit pair exists, and it is not linked).

## What v2 does not do

Everything v1 does not do (above) still holds: not the official TIMIT split,
speakers not separated, only the Q-20 counts and the text constraint used.
One-token variants beyond the 20 verified links, for example a
variant of two or more tokens, are not merged; the scan only covers one-token
variants.
