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

| | Thesis | Ours, HF split |
|---|---|---|
| Query instances | 145 (`Table:TIMITdata`, Inst. column) | 221 (251 usable train instances; 30 belong to the keywords "simple" and "youngsters", which have no relevant test document) |
| Relevant items | 160 tokens (Occ. column) | 52 relevant document-keyword pairs |
| Searched documents | 1344 | 989 non-SA test rows |
| Keywords scored | 20 | 18 |

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

## How to read the gap (HF split)

The numbers sit above the thesis targets for both GMM sizes. Evidence that
bears on the comparison, none of it tested by changing a setting:

- **Sentence-text overlap.** 42 of the 52 relevant test documents (81 %) have
  the same sentence text as a train row, and 330 test texts covering 599 of
  the 989 test rows also occur in train (Reviewer count, cycle 4). In the
  official TIMIT split no non-SA text crosses between train and test. A query
  cut from a train utterance can therefore have a document with the *same
  sentence* in the search set. The text-disjoint split below removes this.
- **Speaker overlap.** The HF split is per utterance, not per speaker
  (`docs/data_notes.md`). The amount of overlap is unknown.
- **Different setups.** The keyword counts, query set and document set all
  differ from the thesis (see the denominators).
- **Coarse metric.** With 1 to 8 relevant documents per keyword, one document
  moving in the ranking changes a keyword's p@N by 12 to 100 points. The
  keyword-cluster intervals are about 24 points wide and contain the thesis
  figures, and the paired 128 minus 64 intervals contain 0: this data cannot
  separate our numbers from the thesis ones, nor the two model sizes.
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
```

Outputs (`per_query.tsv`, `summary.json`) go to git-ignored `outputs/eval/`;
only this summary is committed.
