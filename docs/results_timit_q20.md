# TIMIT Q-20 results: MFCC, GMM posteriorgram, subDTW-LC2

First end-to-end numbers of this reimplementation. No setting was tuned to
move them towards the thesis figures. Setup: MFCC `timit_matlab` (39
dimensions, no VTLN), diagonal GMM trained on the training side without the
SA sentences (`docs/gmm_notes.md`), symmetric-KL local distance, LC2
subsequence DTW (`NSDTW_c_skel.cpp` rules). Queries are cut from train-side
audio; documents are the non-SA test-side utterances.

**Thesis targets** (MFCC, GMM, no VTLN, LC2; `Unsupervised.tex` lines
125-134, `Tab:ExpResultTIMIT`, `Tab:TIMITVTLNPerformance1`): 64 Gaussians
**34.91 / 36.71** (p@N / MAP), 128 Gaussians
**36.81 / 38.34**.

## Denominators (do not compare the raw counts)

| | Thesis | Ours, HF split | Ours, text-disjoint |
|---|---|---|---|
| Query instances | 145 (`Table:TIMITdata`, Inst. column) | 221 (251 usable train instances; 30 belong to the keywords "simple" and "youngsters", which have no relevant test document) | 145 (equal to Inst. for all 20 keywords) |
| Relevant items | 160 tokens (Occ. column) | 52 relevant document-keyword pairs | 160 relevant document-keyword pairs (equal to Occ. per keyword) |
| Searched documents | 1344 | 989 non-SA test rows | 1336 non-SA test-side rows |
| Keywords scored | 20 | 18 | 20 |

Relevance is binary per document in both setups. The thesis Occ. is a
**token** count; ours counts documents, so one document with two tokens of a
keyword counts once. Whether the thesis averages over instances or over
keywords is not stated, so both are reported.

## HF split, v2 (cycle 5 scorer)

**Labels: sentence-text overlap between queries and documents (HF split); speaker overlap present; approximate versus the thesis.** Do not read these as evidence of reproducing the
thesis, and do not call the HF split speaker-separated: its SA counts
(488/501 train, 142/129 test) are what a random row split would give, so
speaker overlap may be large.

Scorer: the thesis endpoint rule (`wr = (end - P)/N` valid in 0.5 to 2,
minimum `S/T` over valid endpoints; a document without a valid endpoint is a
non-match with distance +inf and ranks last). Nothing was tuned.

| Model | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Non-matches |
|---|---|---|---|---|---|---|
| thesis, GMM-64 | 34.91 | 36.71 | not stated | not stated | 145 | n/a |
| thesis, GMM-128 | 36.81 | 38.34 | not stated | not stated | 145 | n/a |
| ours, GMM-64 | 36.95 (25.1-49.2) | 41.25 (28.8-54.2) | 36.52 (25.7-47.8) | 41.56 (29.8-53.5) | 221 | 0 |
| ours, GMM-128 | 39.36 (28.7-50.6) | 44.21 (32.8-56.3) | 39.14 (29.6-49.0) | 44.10 (33.7-54.8) | 221 | 0 |

- Intervals: keyword-cluster bootstrap (10000 resamples, seed 0, keywords
  drawn with replacement, all instances of a keyword carried together).
  *Instance average*: every instance of the drawn keywords; *keyword
  average*: mean of per-keyword means. Which one the thesis reports is
  unknown (open question 20).
- Thesis gain 128 minus 64: +1.90 p@N, +1.63 MAP (`Unsupervised.tex` lines
  125-134, `Tab:ExpResultTIMIT`, MFCC, GMM, LC2).

Paired difference GMM-128 minus GMM-64 (same queries; paired keyword-cluster
bootstrap, 95 %):

| Average | p@N | MAP |
|---|---|---|
| instance average | 2.41 (-0.8-6.2) | 2.96 (-0.7-6.9) |
| keyword average | 2.62 (-1.0-6.4) | 2.54 (-1.6-6.8) |

Provenance:

| | GMM-64 | GMM-128 |
|---|---|---|
| `split_id` | `hf-ef7bffd88de7-nonsa` | `hf-ef7bffd88de7-nonsa` |
| Parameter SHA-256 | `80a5b016398bd7e3...` | `c0e38a61730529dd...` |
| Feature fingerprint | `2c337a2602c49699...` | `2c337a2602c49699...` |
| Non-matches | 0 | 0 |
| Runtime | 686 s | 788 s |
| Git commit | `44ec78d` | `44ec78d` |

Per keyword (v2):

| Keyword | Relevant test documents | Instances | GMM-64 p@N | GMM-64 MAP | GMM-128 p@N | GMM-128 MAP |
|---|---|---|---|---|---|---|
| artists | 1 | 13 | 7.7 | 14.9 | 30.8 | 41.5 |
| beautiful | 2 | 9 | 22.2 | 18.5 | 33.3 | 31.2 |
| birth | 2 | 9 | 5.6 | 10.9 | 11.1 | 14.2 |
| destroy | 4 | 12 | 47.9 | 52.1 | 39.6 | 48.0 |
| development | 3 | 14 | 42.9 | 54.3 | 50.0 | 54.3 |
| garbage | 2 | 13 | 26.9 | 33.8 | 30.8 | 38.8 |
| government | 5 | 17 | 30.6 | 27.8 | 31.8 | 34.5 |
| intelligence | 5 | 10 | 72.0 | 83.4 | 72.0 | 79.9 |
| love | 2 | 18 | 8.3 | 7.6 | 8.3 | 10.6 |
| marriage | 1 | 9 | 33.3 | 46.2 | 22.2 | 25.0 |
| meeting | 4 | 8 | 28.1 | 30.8 | 40.6 | 39.1 |
| morning | 8 | 21 | 42.9 | 40.9 | 41.1 | 42.1 |
| ocean | 1 | 13 | 0.0 | 2.1 | 7.7 | 9.2 |
| organizations | 4 | 10 | 67.5 | 79.1 | 67.5 | 76.5 |
| problems | 2 | 10 | 75.0 | 75.0 | 65.0 | 72.2 |
| shellfish | 3 | 18 | 83.3 | 87.8 | 83.3 | 90.6 |
| surface | 1 | 9 | 44.4 | 57.6 | 44.4 | 57.3 |
| tomorrow | 2 | 8 | 18.8 | 25.2 | 25.0 | 28.8 |

"simple" and "youngsters" have no relevant test document in this copy of
TIMIT and are left out (18 of 20 keywords are evaluated). Four keywords have
exactly one relevant document, so p@N is 0 or 100 for each of their queries.

## Text-disjoint split (`textdisjoint_q20_v1`)

**Labels: closer to the thesis on sentence context; not an official TIMIT
reconstruction; speaker overlap present (amount unknown, likely larger than on
the HF split); 8 SX sentence variants crossed sides; government affected; not
fully sentence-disjoint.** Rule, manifest hash and per-keyword thesis counts:
`docs/split_textdisjoint.md` (declared before any score was computed). Same
features, GMM recipe, LC2 scorer and clip query features as HF v2; only the
rows of the two sides differ. Nothing was tuned.

| Model | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Non-matches |
|---|---|---|---|---|---|---|
| ours, GMM-64 | 38.45 (28.2-50.0) | 40.61 (29.5-52.9) | 36.98 (27.5-47.0) | 38.44 (28.7-48.7) | 145 | 0 |
| ours, GMM-128 | 40.60 (30.3-51.1) | 43.57 (32.3-55.5) | 37.26 (28.1-46.7) | 40.37 (30.5-50.4) | 145 | 0 |

Intervals: keyword-cluster bootstrap, 10000 resamples, seed 0. Paired
difference GMM-128 minus GMM-64 (same queries, paired keyword-cluster
bootstrap, 95 %):

| Average | p@N | MAP |
|---|---|---|
| instance average | 2.15 (-1.5-5.5) | 2.95 (0.2-5.7) |
| keyword average | 0.28 (-2.9-3.5) | 1.93 (-0.3-4.4) |

Provenance:

| | GMM-64 | GMM-128 |
|---|---|---|
| `split_id` | `textdisjoint_q20_v1-ee27b531237a` | `textdisjoint_q20_v1-ee27b531237a` |
| Parameter SHA-256 | `c78c19859f4b9081...` | `ba421ceff32cc6c1...` |
| Documents / queries | 1336 / 145 | 1336 / 145 |
| Non-matches | 0 | 0 |
| Runtime | 669 s | 726 s |
| Git commit | `78361a7` | `78361a7` |

Query instances and relevant documents per keyword, against the thesis table
(thesis Occ. is a token count, ours counts documents; instances are usable
aligned instances after flagged ones are dropped):

| Keyword | Thesis Inst. | Our instances | Thesis Occ. | Our relevant documents | GMM-64 p@N | GMM-64 MAP | GMM-128 p@N | GMM-128 MAP |
|---|---|---|---|---|---|---|---|---|
| artists | 7 | 7 | 7 | 7 | 26.5 | 23.6 | 18.4 | 22.9 |
| beautiful | 3 | 3 | 8 | 8 | 50.0 | 53.5 | 45.8 | 53.1 |
| birth | 4 | 4 | 7 | 7 | 14.3 | 18.9 | 7.1 | 13.0 |
| destroy | 9 | 9 | 7 | 7 | 25.4 | 30.1 | 31.7 | 32.9 |
| development | 9 | 9 | 8 | 8 | 45.8 | 54.8 | 55.6 | 59.3 |
| garbage | 8 | 8 | 7 | 7 | 26.8 | 23.8 | 37.5 | 40.5 |
| government | 14 | 14 | 8 | 8 | 16.1 | 18.6 | 20.5 | 20.5 |
| intelligence | 8 | 8 | 7 | 7 | 76.8 | 78.9 | 80.4 | 83.1 |
| love | 4 | 4 | 16 | 16 | 4.7 | 3.4 | 9.4 | 7.4 |
| marriage | 3 | 3 | 7 | 7 | 42.9 | 44.1 | 33.3 | 43.5 |
| meeting | 7 | 7 | 7 | 7 | 32.7 | 34.7 | 28.6 | 28.9 |
| morning | 15 | 15 | 14 | 14 | 28.6 | 30.5 | 43.3 | 42.7 |
| ocean | 7 | 7 | 7 | 7 | 12.2 | 12.7 | 12.2 | 14.0 |
| organizations | 7 | 7 | 7 | 7 | 75.5 | 78.8 | 69.4 | 74.7 |
| problems | 5 | 5 | 7 | 7 | 40.0 | 41.0 | 45.7 | 49.2 |
| shellfish | 14 | 14 | 7 | 7 | 75.5 | 82.2 | 74.5 | 84.1 |
| simple | 8 | 8 | 8 | 8 | 39.1 | 39.2 | 34.4 | 36.3 |
| surface | 3 | 3 | 7 | 7 | 61.9 | 51.7 | 47.6 | 48.2 |
| tomorrow | 3 | 3 | 7 | 7 | 0.0 | 1.9 | 4.8 | 3.3 |
| youngsters | 7 | 7 | 7 | 7 | 44.9 | 46.4 | 44.9 | 49.5 |

### Three-row comparison: thesis, HF split v2, text-disjoint

*Instance* columns average every query instance; *keyword* columns average
per keyword first. Labels as above; the HF rows carry sentence-text overlap
between queries and documents and speaker overlap, the text-disjoint rows
carry speaker overlap only. The thesis uses 145 query instances (ours: HF 221,
text-disjoint 145) and 160 Occ. tokens (ours: relevant document
pairs).

| Row | p@N, instance | MAP, instance | p@N, keyword | MAP, keyword | Queries |
|---|---|---|---|---|---|
| thesis, GMM-64 | 34.91 | 36.71 | not stated | not stated | 145 |
| HF split v2, GMM-64 | 36.95 (25.1-49.2) | 41.25 (28.8-54.2) | 36.52 (25.7-47.8) | 41.56 (29.8-53.5) | 221 |
| text-disjoint v1, GMM-64 | 38.45 (28.2-50.0) | 40.61 (29.5-52.9) | 36.98 (27.5-47.0) | 38.44 (28.7-48.7) | 145 |
| thesis, GMM-128 | 36.81 | 38.34 | not stated | not stated | 145 |
| HF split v2, GMM-128 | 39.36 (28.7-50.6) | 44.21 (32.8-56.3) | 39.14 (29.6-49.0) | 44.10 (33.7-54.8) | 221 |
| text-disjoint v1, GMM-128 | 40.60 (30.3-51.1) | 43.57 (32.3-55.5) | 37.26 (28.1-46.7) | 40.37 (30.5-50.4) | 145 |

## Sensitivity: query features, clip vs slice (GMM-64, text-disjoint)

*Sensitivity, not a thesis-mandated correction.* Same GMM-64, alignments,
relevance and documents on `textdisjoint_q20_v1`; only the query features
differ. `clip` (primary) extracts features from the cut clip. `slice`
extracts them on the whole utterance and keeps the frames whose centre lies in
the padded query interval. `slice` changes the delta and delta-delta values at
the edges **and** the per-utterance waveform normalisation (DC removal), which
shifts c0.

| Mode | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Queries without frames |
|---|---|---|---|---|---|---|
| clip (primary) | 38.45 (28.2-50.0) | 40.61 (29.5-52.9) | 36.98 (27.5-47.0) | 38.44 (28.7-48.7) | 145 | 0 |
| slice | 37.12 (27.2-47.6) | 40.06 (29.0-52.0) | 35.10 (26.3-43.9) | 37.78 (28.2-47.6) | 145 | 0 |

Paired difference slice minus clip (same queries, paired keyword-cluster bootstrap, 95 %):

| Average | p@N | MAP |
|---|---|---|
| instance average | -1.34 (-4.2-1.3) | -0.55 (-2.4-1.3) |
| keyword average | -1.88 (-5.2-1.0) | -0.65 (-2.7-1.3) |

## How to read the gap

The numbers sit above the thesis targets for both GMM sizes on both splits (the keyword-cluster intervals contain the thesis figures). Evidence that
bears on the comparison, none of it tested by changing a setting:

- **Sentence-text overlap.** 42 of the 52 relevant test documents (81 %) have
  the same sentence text as a train row, and 330 test texts covering 599 of
  the 989 test rows also occur in train (Reviewer count, cycle 4). In the
  official TIMIT split no non-SA text crosses between train and test. A query
  cut from a train utterance can therefore have a document with the *same
  sentence* in the search set. The text-disjoint v1 split removes most of
  this (8 SX sentence variants still crossed sides). Its scores are given
  above for description only: GMM-64 p@N 38.45 against 36.95 on the HF
  split, MAP 40.61 against 41.25. The two runs differ in queries, documents,
  relevance and GMM training rows, so the comparison is unpaired and no test
  is made. It does not show that removing sentence overlap raised, lowered
  or failed to explain the scores. Speaker overlap on v1 is probably larger.
- **Speaker overlap.** The HF split is per utterance, not per speaker
  (`docs/data_notes.md`). The amount of overlap is unknown.
- **Different setups.** On the HF split the keyword counts, query set and
  document set all differ from the thesis (see the denominators). The
  text-disjoint split was built to match the thesis Inst. and Occ. per
  keyword, and does (145 queries, 160 relevant pairs, 20 keywords), but its
  documents and queries are still not the thesis ones.
- **Coarse metric.** With 1 to 8 relevant documents per keyword (HF split; 7 to 16 on the text-disjoint split), one document
  moving in the ranking changes a keyword's p@N by 12 to 100 points. The
  keyword-cluster intervals are about 24 points wide and contain the thesis
  figures, so this data cannot separate our numbers from the thesis ones.
  For GMM-128 minus GMM-64 on v1 (fixed experiment, section above), the
  instance-averaged MAP difference is +2.95, 95 % keyword-cluster interval
  0.2 to 5.7: positive, in the thesis's direction (thesis +1.63 MAP). The
  p@N interval (-1.5 to 5.5) and the keyword-averaged MAP interval (-0.3
  to 4.4) include 0. On the HF split the paired intervals all include 0.
  This is not a claim of numerical parity.
- **Unverified choices** between the thesis and this run (list below). The
  10-iteration GMM is an experimental choice.

## HF split, v1 (cycle 4 scorer), exploratory

*Exploratory: instance bootstrap, `(end-start+1)/N` endpoint, fallback
scorer.* Kept as it was reported in cycle 4; superseded by v2 above. The
intervals resample the instances and ignore that the instances of a keyword
share their relevant documents, so they understate the uncertainty. Labels as
for v2.

| Model | p@N, instance avg (95% bootstrap) | MAP, instance avg (95% bootstrap) | p@N, keyword avg | MAP, keyword avg | Queries | Fallbacks |
|---|---|---|---|---|---|---|
| GMM-64 | 36.89 (32.4-41.8) | 41.20 (36.6-46.1) | 36.49 | 41.50 | 221 | 0 |
| GMM-128 | 39.58 (35.1-44.3) | 44.23 (39.8-48.8) | 39.36 | 44.12 | 221 | 0 |

## Assumptions (thesis silent or unverified)

1. Each spoken instance is its own query (open question 20).
2. Relevance is an exact token match against `normalize_transcript`, at least
   once per document; no morphological variants (open question 21).
3. Query features are extracted from the cut clip (aligner interval +/- 20
   ms, clipped), not sliced from full-utterance features (open question 22);
   a sensitivity run is in the sensitivity section when present.
4. The endpoint rule is the thesis one (`ExpSetup.tex` lines 442-448,
   467-469), read with zero-based frames: `wr = (end - P[end]) / N`.
5. Posteriors are floored at 1e-10 and renormalised.
6. The forced aligner's boundaries (about 20-50 ms accurate) define the
   queries; the 10.7 ms figure of the model card is not ours.
7. GMM: diagonal, variance floor 0.01 x global variance, LBG epsilon 0.2,
   k-means tolerance 1e-3, c0 kept, 10 EM iterations, all frames used (no
   speech detection); see `docs/gmm_notes.md`.
8. Two queries were skipped for flagged alignments (`meeting`).

## Reproduce

```
pixi run python -m qbestd.eval.q20_counts
pixi run train-gmm --components 64
pixi run train-gmm --components 128
pixi run eval-timit --gmm outputs/models/mfcc_timit_matlab_gmm64.npz --out outputs/eval/hf_v2_gmm64
pixi run eval-timit --gmm outputs/models/mfcc_timit_matlab_gmm128.npz --out outputs/eval/hf_v2_gmm128
pixi run python -m qbestd.data.text_split
pixi run train-gmm --components 64 --split-manifest outputs/splits/textdisjoint_q20_v1.tsv
pixi run train-gmm --components 128 --split-manifest outputs/splits/textdisjoint_q20_v1.tsv
pixi run eval-timit --gmm outputs/models/textdisjoint_q20_v1/mfcc_timit_matlab_gmm64.npz --split-manifest outputs/splits/textdisjoint_q20_v1.tsv --out outputs/eval/td_gmm64
pixi run eval-timit --gmm outputs/models/textdisjoint_q20_v1/mfcc_timit_matlab_gmm128.npz --split-manifest outputs/splits/textdisjoint_q20_v1.tsv --out outputs/eval/td_gmm128
pixi run eval-timit --gmm outputs/models/textdisjoint_q20_v1/mfcc_timit_matlab_gmm64.npz --split-manifest outputs/splits/textdisjoint_q20_v1.tsv --query-features slice --out outputs/eval/td_gmm64_slice
```

Outputs (`per_query.tsv`, `summary.json`) go to git-ignored `outputs/eval/`;
only this summary is committed.
