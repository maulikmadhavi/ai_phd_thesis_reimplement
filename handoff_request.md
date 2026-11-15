# Handoff Request: Reviewer → Codex

- **Cycle:** 4
- **From:** Claude Code Reviewer
- **To:** Codex. Write only `handoff_response.md` (replacing the cycle 3 response) and commit
  it. Do not touch any other file.
- **Plan under review:** `docs/plan.md` at `9f2b659`:
  - §8 Part A, fix-ups E1–E7 from your `5c5dea8` response;
  - §9 Part B, the first comparable number: T7.1, T7.2, T5.1–T5.3, T7.3–T7.5.
- **Status:** COMPLETE. 15 commits, `73ea23b..e63e723`.

## 1. Commits to review

Listed in `git log` order. E6 landed before E5, and E7 landed after T7.3. The order is
harmless.

| Commit | Task | Files | Reviewer verdict |
|---|---|---|---|
| `73ea23b` exec: drop unverified htk_like profile | E1 | `features/profiles.py`, tests | OK |
| `b844d6a` exec: fix lifter and delta thesis cells | E2 | `docs/feature_parity.md` | OK |
| `12f55dc` exec: continue kmeans after distortion increase | E3 | `ml/vq.py` (`_converged`), tests | OK |
| `06fc696` exec: fingerprint feature cache and validate on load | E4 | `data/feature_cache.py`, `ml/train.py`, tests | OK; see Q6 |
| `b9fe0b1` exec: state narrower speaker overlap finding | E6 | `docs/data_notes.md`, `docs/alignment_notes.md` | OK; superseded in part by the finding in §2 |
| `252f520` exec: add huggingface hub to core environment | E5 | `pixi.toml`, `pixi.lock`, `ml/train.py` | OK |
| `6131262` exec: add timit q20 query and relevance manifests | T7.1 | `eval/timit_queries.py`, `eval/q20_counts.py`, `docs/q20_counts.md`, tests | OK; see Q1, Q2 |
| `5f79b5a` exec: add p at n and map metrics | T7.2 | `eval/metrics.py`, tests | OK |
| `53f8ca0` exec: add symmetric kl distance matrix | T5.1 | `search/distance.py`, tests | OK |
| `3eb0eff` exec: add subdtw lc2 kernel and path selection | T5.2 | `search/subdtw.py`, tests | OK; see Q5 |
| `dac5284` exec: add score normalisation and ranking | T5.3 | `search/score.py`, tests | OK |
| `df6a7cb` exec: add timit q20 evaluation runner | T7.3 | `eval/run_timit.py`, `pixi.toml`, tests | OK |
| `9b93990` exec: correct gmm evidence and convergence notes | E7 | `ml/gmm.py`, `ml/vq.py`, `docs/gmm_notes.md` | OK |
| `fcec653` exec: add stage 5 search demo | T7.5 | `demo/stage5_search_demo.py`, `pixi.toml` | OK (its functions were smoke-tested; not opened in a browser) |
| `e63e723` exec: record first timit q20 results | T7.4 | `docs/results_timit_q20.md` | OK; see §2 |

## 2. Reviewer checks done

- **Tests:** `pixi run test` gives 457 passed and 1 skipped. The Reviewer re-ran this.
- **Limits:** the largest file is `ml/gmm.py` at 241 lines, and no line is over 79
  characters. There are no trailers on the commits.
- **Nothing derived committed:** features, models, manifests, eval outputs and audio stay
  under git-ignored `outputs/`. `docs/q20_counts.md` holds counts only.
- **E3 / E5:** `train-gmm` runs from the core environment. After a fingerprinted cache
  rebuild, GMM-64 and GMM-128 have exactly the same parameter hashes as in cycle 3, so E3
  changed nothing for them.
- **E7:** a 30-iteration GMM-64 reaches LL −31.822, against −31.986 after 10 iterations, and
  iteration 30 still adds 0.0033. This model was not evaluated.
- **Code read:** the Reviewer read `subdtw.py`, `distance.py`, `metrics.py`, the outline of
  `run_timit.py` and `timit_queries.py`, and the E3/E4 diffs.
  - **LC2 kernel:**
    - first column `S = D`, `T = 1`, `P = m`;
    - rows 0 and 1 accumulate along n;
    - predecessors `(m, n−1)`, `(m−1, n−1)` and `(m−2, n−1)`, tie order horizontal,
      diagonal, skip;
    - selection on un-normalised `D + S_pred`.

    This matches plan §9. It is tested against a loop transcription of `NSDTW_c_skel.cpp`
    on 20 random matrices, half of them tie-heavy.
  - **KL matrix:** vectorised `Σt log t − t·log qᵀ + Σq log q − log t·qᵀ`, clipped at 0.
  - **Metrics:** AP is normalised by N, so a relevant document missing from the ranking
    counts as 0. The thesis example gives 50 % and 0.775.
- **First numbers** (MFCC `timit_matlab`, LC2, 221 query instances × 989 documents,
  0 fallbacks, nothing tuned):

  | Model | p@N | MAP | Keyword-averaged p@N / MAP |
  |---|---|---|---|
  | GMM-64 | 36.89 (bootstrap 32.4–41.8) | 41.20 (36.6–46.1) | 36.49 / 41.50 |
  | GMM-128 | 39.58 | 44.23 | — |
  | Thesis, GMM-64 | 34.91 | 36.71 | — |

  - "simple" and "youngsters" have 0 relevant test documents, so 18 of the 20 keywords are
    scored.

### Reviewer finding: queries and documents share sentence texts

The Reviewer counted texts with the normalised transcripts of the non-SA rows (a scratch
script; nothing committed):

| | Rows | Distinct texts |
|---|---|---|
| train (non-SA) | 4051 | 1972 |
| test (non-SA) | 989 | 720 |

- Of the test texts, **330** also occur in train, and they cover **599 of the 989** test
  rows.
- Across both splits, 429 texts are read 7 times and 1909 once. This matches TIMIT's design:
  450 SX texts × 7 speakers, and 1890 SI texts read once each. A few SI texts look duplicated
  because of normalisation.
- **42 of the 52 relevant Q-20 documents (81%) have the same sentence text as at least one
  train row.** Every keyword with relevant documents except "marriage" has one. So the
  matching query instances probably come from the same SX sentence, read by another speaker,
  in the same word context.

In the official TIMIT split, SX/SI texts do not cross between train and test (only SA is
shared). Thesis Occ. ≈ 7 per keyword is consistent with one SX text read by the 7 test
speakers. So the thesis queries and documents never shared a sentence context, and ours
mostly do. With 20 ms padding, the query clip carries neighbouring-word coarticulation that
often recurs verbatim in the relevant document. This is likely a bigger optimistic bias than
speaker overlap, and it means the +2.0 / +4.5 gap shouldn't be read as parity.

It also gives a way to rebuild a split that is *closer to official*:
- group rows by sentence text and assign whole SX text groups to one side, i.e. a
  text-disjoint split;
- or keep the HF split but drop query instances whose sentence text appears in the test set.

See Q3.

### Minor notes

- `run_timit` checks the test-feature fingerprint, but not that the chosen GMM was trained
  on the same `kind`/`profile`. A dimension mismatch would raise, but an MFCC GMM paired
  with 39-dimensional MFCC-TMP features would run silently.
- `FEATURE_CACHE_VERSION` is bumped by hand, as planned, so a forgotten bump after a
  front-end change is still a silent reuse.
- The query clips are only about 25–60 frames long, so Δ/ΔΔ edge effects make up a larger
  share of each clip than they do of a document (Q4).

## 3. Questions for Codex

1. **Plan Q20: instances.** How did the thesis combine a keyword's several spoken instances
   (Inst. 3–15)? Was each instance its own query (current, instance-averaged), or were scores
   fused or averaged per keyword?
2. **Plan Q21: Occ.** Is "Occ." in `Table:TIMITdata` a document count or a token count? Did
   relevance include morphological variants? In our copy the test side has only 1–8 relevant
   documents per keyword (52 in total, against thesis Occ. 160), so p@N is very coarse.
3. **Text overlap (new finding above).** 81% of relevant documents share their sentence text
   with a train query source, which the official TIMIT split never allows. Choose one:
   - (a) rebuild a text-disjoint query/document split from the 6300 HF rows, grouping by
     normalised sentence text so SX groups stay whole; queries and documents still come from
     disjoint text sets;
   - (b) keep the HF split and drop query instances (or relevant documents) whose text
     occurs on the other side;
   - (c) keep everything and only label it.

   The Reviewer leans towards (a), reported next to the current numbers. Under (a), thesis
   Occ. ≈ 7 becomes attainable, and the relevant-set size problem in Q2 largely goes away.
   Is (a) defensible as "closer to the thesis protocol", given speaker overlap remains?
4. **Plan Q22: query features.** Should they come from the cut clip (current), or be sliced
   from the full-utterance features (no edge effects in Δ/ΔΔ, but context leaks in)? Should
   the Executor run both on GMM-64 as a sensitivity check?
5. **Plan Q23: path validity.** Is the interval measured in test frames from `P` (current) or
   as the path length `T`? The C++ also differs from the plan:
   - the C++ takes the end frame with `argmin S` and reports `S/T` there;
   - we take `min S/T` over valid end frames.

   Which is the thesis behaviour (`ExpSetup.tex` line 442)?
6. **Cache and model consistency.** Should `run_timit` refuse a GMM whose metadata
   `kind`/`profile` differs from the evaluation features (minor note above)? Should
   `FEATURE_CACHE_VERSION` be derived automatically, for example from a hash of the feature
   module sources, rather than bumped by hand?
7. **Uncertainty.** The bootstrap resamples instances and ignores that a keyword's instances
   share one relevant set. Should it resample keywords, i.e. a cluster bootstrap, instead?
8. **GMM-128 vs GMM-64.** GMM-128 is higher on both metrics but inside the GMM-64 interval.
   Is any thesis GMM-128 TIMIT figure available to add as a second target?
9. Any other correctness, PEP 8, security or test-coverage issues in E1–E7, T7.1–T7.5 or
   T5.1–T5.3?

## 4. Response format requested

Write `handoff_response.md` with one section per question number. Mark each as
**agree / change requested / unknown**. For a requested change, give the file and the
concrete change. Commit it as `handoff_resp: cycle 4 review`.
