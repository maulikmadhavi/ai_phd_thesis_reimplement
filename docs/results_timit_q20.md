# First TIMIT Q-20 results: MFCC, GMM posteriorgram, subDTW-LC2

**Label: speaker overlap present; approximate versus the thesis.** These are
the first end-to-end numbers of this reimplementation. No setting was tuned to
move them towards the thesis figure.

Setup: MFCC `timit_matlab` (39 dimensions, no VTLN), diagonal GMM trained on
the Hugging Face TIMIT train split without the SA sentences (see
`docs/gmm_notes.md`), 10 EM iterations, symmetric-KL local distance, LC2
subsequence DTW (`NSDTW_c_skel.cpp` rules), utterance distance = minimum `S/T`
over end frames with a matched length of 0.5 to 2 times the query. Queries are
cut from train audio, documents are the 989 non-SA test
utterances. Commit `fcec653`; model parameter hashes are in
each `summary.json` (`80a5b016398b...` for GMM-64).

## Results against the thesis

Thesis target (MFCC, 64 mixtures, no VTLN, `Tab:TIMITVTLNPerformance1`):
p@N **34.91**, MAP **36.71**. No GMM-128 figure is recorded in our
plan, so GMM-128 has no target here.

| Model | p@N, instance average (95% bootstrap) | MAP, instance average (95% bootstrap) | p@N, keyword average | MAP, keyword average | Queries | Fallbacks | Runtime |
|---|---|---|---|---|---|---|---|
| thesis, GMM-64 | 34.91 | 36.71 | not stated | not stated | not stated | n/a | n/a |
| GMM-64 | 36.89 (32.4-41.8) | 41.20 (36.6-46.1) | 36.49 | 41.50 | 221 | 0 | 325 s |
| GMM-128 | 39.58 (35.1-44.3) | 44.23 (39.8-48.8) | 39.36 | 44.12 | 221 | 0 | 356 s |

- *Instance average*: every spoken instance is a query and all are averaged.
  *Keyword average*: instances are averaged per keyword first, then over the
  18 keywords. Which one the thesis used is
  open question 20.
- The bootstrap resamples the 221 query instances (2000
  resamples, seed 0). It ignores that instances of one keyword share the same
  relevant documents, so it understates the real uncertainty.
- Fallbacks: the number of query-document pairs for which no end frame passed
  the length check. It is 0 for both models.
- Runtime: 325 s for GMM-64 and
  356 s for GMM-128 (CPU, features cached,
  including loading), for 221 x 989 pairs.

## Per keyword

| Keyword | Relevant test documents | Instances | GMM-64 p@N | GMM-64 MAP | GMM-128 p@N | GMM-128 MAP |
|---|---|---|---|---|---|---|
| artists | 1 | 13 | 7.7 | 14.6 | 30.8 | 41.5 |
| beautiful | 2 | 9 | 22.2 | 18.5 | 33.3 | 31.1 |
| birth | 2 | 9 | 5.6 | 10.9 | 11.1 | 14.2 |
| destroy | 4 | 12 | 47.9 | 52.1 | 39.6 | 48.0 |
| development | 3 | 14 | 42.9 | 54.3 | 50.0 | 54.3 |
| garbage | 2 | 13 | 26.9 | 33.9 | 34.6 | 39.4 |
| government | 5 | 17 | 30.6 | 27.8 | 31.8 | 34.4 |
| intelligence | 5 | 10 | 72.0 | 83.4 | 72.0 | 79.9 |
| love | 2 | 18 | 8.3 | 7.6 | 8.3 | 10.7 |
| marriage | 1 | 9 | 33.3 | 46.1 | 22.2 | 25.0 |
| meeting | 4 | 8 | 28.1 | 30.6 | 40.6 | 38.9 |
| morning | 8 | 21 | 42.3 | 40.6 | 41.1 | 42.1 |
| ocean | 1 | 13 | 0.0 | 2.1 | 7.7 | 9.2 |
| organizations | 4 | 10 | 67.5 | 79.1 | 67.5 | 76.5 |
| problems | 2 | 10 | 75.0 | 75.0 | 65.0 | 72.2 |
| shellfish | 3 | 18 | 83.3 | 87.8 | 83.3 | 90.6 |
| surface | 1 | 9 | 44.4 | 57.6 | 44.4 | 57.3 |
| tomorrow | 2 | 8 | 18.8 | 25.0 | 25.0 | 28.7 |

"simple" and "youngsters" have **no** relevant test document in this copy of
TIMIT, so they cannot be scored and are left out (18 of the 20 keywords are
evaluated). Four keywords have exactly one relevant document, for which p@N is
0 or 100 per query.

## How to read the gap

Our GMM-64 numbers are +2.0
(p@N) and +4.5 (MAP) away from the
thesis figures. This is **not** evidence of reproducing the thesis. Evidence
that bears on the comparison, none of it tested by changing a setting:

- **The setups differ.** Our test split holds 989 non-SA
  documents and 52 relevant document-keyword pairs in total (1 to 8 per
  keyword, `docs/q20_counts.md`), against thesis Occ. of 7 to 16 per keyword.
  The train split has 251 usable instances against the thesis 145. So the
  keyword set, the relevant sets and the number of queries are all different.
- **Speaker overlap.** The split is not strictly speaker-independent
  (`docs/data_notes.md`), which can raise both numbers.
- **The metric is coarse and noisy here.** With 1 to 8 relevant documents per
  keyword, one document moving in the ranking changes p@N by 12 to 100 points
  for that keyword; the bootstrap interval of the instance average spans about
  9 p@N points.
- **Many unverified choices** sit between the thesis and this run (list
  below). The 10-iteration GMM is an experimental choice, and the 30-iteration
  model was not evaluated.
- GMM-128 scores higher than GMM-64 on both metrics, in the direction expected
  from the thesis, but the difference is within the bootstrap interval.

## Assumptions (thesis silent or unverified)

1. Each spoken instance is its own query (open question 20).
2. Relevance is an exact token match against `normalize_transcript`, at least
   once per document; no morphological variants (open question 21).
3. Query features are extracted from the cut clip (aligner interval +/- 20 ms,
   clipped), not sliced from full-utterance features (open question 22).
4. A path is valid when its matched test length is 0.5 to 2 times the query
   length, measured in test frames from the start `P` (open question 23);
   the utterance distance is the minimum `S/T` over valid end frames.
5. Posteriors are floored at 1e-10 and renormalised.
6. The forced aligner's boundaries (about 20-50 ms accurate) define the
   queries; the 10.7 ms figure of the model card is not ours.
7. GMM: diagonal, variance floor 0.01 x global variance, LBG epsilon 0.2,
   k-means tolerance 1e-3, c0 kept, all frames used (no speech detection).
8. Two queries were skipped for flagged alignments (`meeting`); no query clip
   was too short to give a frame (0 such).

## Reproduce

```
pixi run python -m qbestd.eval.q20_counts
pixi run eval-timit --gmm outputs/models/mfcc_timit_matlab_gmm64.npz
pixi run eval-timit --gmm outputs/models/mfcc_timit_matlab_gmm128.npz
```

Outputs (`per_query.tsv`, `summary.json`) go to git-ignored `outputs/eval/`;
only this summary is committed.
