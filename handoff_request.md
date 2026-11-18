# Handoff Request: Reviewer → Handoff_feedback

- **Cycle:** 9
- **From:** Claude Code Reviewer
- **To:** Handoff_feedback, the independent reviewer (`requirements.md`, "Agentic handoff").
  Write only `handoff_response.md` (replacing the cycle 8 response) and commit it as
  `handoff_resp: ...`. Do not create or modify any other file, and do not take plan decisions
  in place of the Orchestrator. Mark anything that needs the user as **user decision**.
- **Plan under review:** `docs/plan.md` at `ffa064d`:
  - §8 Part A, K1–K5 (fix-ups and diagnostic code, from Handoff_feedback `5fd6ef0`);
  - §9 Part B: S1 score-free checks, S2 2×2 gain split (un-normalised rows), S3 normalised
    reference `htk_described_4k_pn` (D6).
- **User decisions already taken, not to be re-opened:** D4 (fresh LBG each VTLN
  iteration; `ll_decreased` recorded, not a stop), D5 (0–4000 Hz band only), D6 (the thesis
  HTK pipeline subtracted the mean and scaled to ±1; `htk_described_4k_pn` is the MFCC/PLP
  reference whatever it scores).
- **Status:** COMPLETE. 13 exec commits, `a399230..9785a28`. No STOP gate fired: the S1 (c)
  order gate was met, `selection_step_ok` held in every iteration, and no feature-digest file
  was edited. `ll_decreased` fired (recorded, D4).
- **Sources:** the thesis is at `D:\Storage\career_phd_daiict_work\Thesis`. The old MATLAB
  code is at `D:\Storage\research_code_qbe_std`.

## 1. Commits to review

In plan order: K1–K5, then S1, S2 and S3, each declared before its run.

| # | Commit | Task | Reviewer verdict |
|---|---|---|---|
| 1 | `a399230` | K1 `selection_step_ok` (vtln_train.py, per-iteration flags file, test) | OK |
| 2 | `fb9fc3a` | K2 clip length check, `frame_f0` no-peak, import order | OK |
| 3 | `a1d582b` | K3 `--vtln-cell` (model_only, selection_only, query_inherit), entropy | OK |
| 4 | `a986d63` | K4 profile `htk_described_4k_pn` and tests | OK |
| 5 | `5cc8ba4` | K5 docs (Q1, Q3–Q7, relabel) | OK |
| 6 | `df8ed4a` | S1 declared | OK |
| 7 | `fa01e4d` | S1 code (`ml/vtln_checks.py`, `eval/s1_checks.py`, `drop_dim`) | OK |
| 8 | `cc086de` | S1 guard fix: PLP has no `include_c0` switch | OK (before any result) |
| 9 | `5c301b9` | S1 report | OK; nit: also edits a test (§2) |
| 10 | `d4422af` | S2 declared | OK |
| 11 | `946e1ff` | S2 report | OK; Q39 wording (§3) |
| 12 | `84e26bc` | S3 declared | OK |
| 13 | `9785a28` | S3 report | OK; Q41/Q42 wording (§3) |

## 2. Reviewer checks done

- **Tests:** `pixi run test` re-run by the Reviewer: 700 passed, 5 skipped (matches the
  Executor). Code modules are all under 400 lines (largest `vtln_train.py` 339,
  `run_timit.py` 333), and no code line in the cycle 9 diff exceeds 79 characters.
- **Digest:** no file in `FEATURE_SOURCE_FILES` changed between `ffa064d` and `9785a28`.
  `profiles.py`, `pitch.py`, `vtln_eval.py` and `warped_cache.py` are outside it.
- **Code read:**
  - K1: `ll_init[k]` (λ_{k−1} on X^α̂_k) ≥ `ll_new[k−1]` (λ_{k−1} on X^α̂_{k−1}) holds by
    construction, because α̂_k maximises each utterance's summed LL under λ_{k−1}. Checking
    it is still worthwhile as a bug guard.
  - K3:
    - model_only scores plain documents and plain clips under λ_r.
    - selection_only takes a plain model, so there is no trace and `sources = {}`; α̂ comes
      from λ_init.
    - query_inherit uses the same warped documents as the VTLN row, and raises if a source
      α̂ is missing.
    - Each cell checks its own `model_type`, and `--vtln` with `--vtln-cell` is rejected.
  - K4: the profile is `htk_described_4k` with `remove_dc` and `normalize_peak` set and
    nothing else. The gain-invariance tests cover MFCC and PLP at ×0.5 and ×2, plus a
    negative control on the un-normalised profile. DC removal is whole-utterance
    (`remove_dc_offset`).
  - S1: the c0 marginal is the diagonal GMM with column 0 dropped and the weights kept. The
    partial correlation is Pearson on rank residuals.
- **`query_inherit` consistency (Reviewer):** the documents are identical to the VTLN row
  (identical document entropy). Per-query rows that are byte-identical to the VTLN row:
  49 of 145 for MFCC and 63 of 145 for PLP. Queries whose own α̂ equals the source's should
  be identical: 145 × (1 − 0.717) = 41 and 145 × (1 − 0.586) = 60. The counts are at least
  that, so the single-warp path (`extract_features(clip, sr, kind, α, config)`) agrees with
  `extract_warped_bank`.
- **Paired numbers recomputed** by the Reviewer from `per_query.tsv` with
  `paired_keyword_bootstrap` (10000 resamples, seed 0): every S2 and S3 paired difference
  in the doc matches to the printed precision. That covers the cells, VTLN − no-VTLN,
  `pn` − un-normalised, MFCC-TMP − MFCC and PLP − MFCC.
- **Provenance:** every summary is `git_dirty: false` with start equal to end commit, and
  the runs never overlap.

  | Step | Start commit | Run window (2026-11-18/19) | Next commit |
  |---|---|---|---|
  | S1 (c) | `fa01e4d` | 06:21:39–06:21:54 | `cc086de` 06:25:25 |
  | S1 (a), (b) | `cc086de` | 06:25:30–06:33:36 | `5c301b9` 06:34:39 |
  | S2: 6 cells + 4 re-evaluations | `d4422af` | 06:35:02–07:32:57 | `946e1ff` 07:34:02 |
  | S3 MFCC caches, GMM, no-VTLN, 26 warp caches | `84e26bc` | 07:34:30–07:55:00 | (shutdown) |
  | S3 MFCC train-vtln (re-run), VTLN eval, cells | `84e26bc` | 23:23–00:12:48 | none |
  | S3 PLP: all 7 steps | `84e26bc` | 00:13–01:31:57 | `9785a28` 01:33:00 |

  - The killed MFCC train-vtln left no stale trace: every `iter*` file is dated
    23:26–23:41, inside the re-run.
  - PLP `iter0` is dated 00:41:44, after its warp caches (00:36–00:38). That fits a
    single process.
  - Model hashes: the S2 cells use `1c0742a` and `03f7143` (W3 VTLN) and `324ebb5` and
    `751a0f9` (W3 plain), the same models as cycle 8. The `pn` models are `e692f68` and
    `573fe04` (plain) and `b1f4340` and `c36b1d1` (VTLN).
  - The four W3 re-evaluations reproduce the W3 per-query rows.
- **Nits:**
  - `5c301b9` (a report commit) also edits `tests/eval/test_s1_checks.py`, a cosmetic
    refactor made after the run. It is harmless, but report commits should touch only docs.
  - In the D6 table, the **thesis** rows are labelled "normalised (`htk_described_4k_pn`)".
    That is our profile name, not the thesis's configuration. Label them "thesis".

### Results (instance p@N / MAP; thesis `Tab:TIMITPerformance` GMM-64 and `Tab:TIMITVTLNPerformance1`)

| Row | No VTLN | VTLN | Paired gain (95 % CI) | Thesis gain |
|---|---|---|---|---|
| MFCC `pn` | 37.04 / 38.75 | 45.10 / 48.10 | +8.07 (+3.7, +12.0) / +9.35 (+4.9, +13.1) | +1.35 / +2.91 |
| PLP `pn` | 36.88 / 37.83 | 45.85 / 49.03 | +8.97 (+6.1, +12.2) / +11.20 (+8.4, +14.3) | +1.98 / +2.37 |
| MFCC un-normalised (W3) | 37.48 / 40.50 | 48.17 / 50.58 | +10.69 / +10.08 | +1.35 / +2.91 |
| PLP un-normalised (W3) | 38.59 / 39.75 | 45.37 / 48.99 | +6.78 / +9.24 | +1.98 / +2.37 |
| Thesis MFCC / PLP | 34.91 / 36.71, 35.50 / 37.58 | 36.26 / 39.62, 37.48 / 39.95 | | |

2×2 cells, paired cell minus no-VTLN, instance (p@N / MAP). ✱ marks an interval that excludes 0:

| Feature | Model only | Selection only | Both (VTLN row) | Model + selection |
|---|---|---|---|---|
| MFCC un-norm. | +1.98 / +1.42 | +3.77✱ / +4.07✱ | +10.69✱ / +10.08✱ | +5.75 / +5.49 |
| PLP un-norm. | −1.53 / −0.12 | +5.52✱ / +6.89✱ | +6.78✱ / +9.24✱ | +3.99 / +6.77 |
| MFCC `pn` | +0.92 / +1.98 | +2.14 / +2.79 | +8.07✱ / +9.35✱ | +3.06 / +4.77 |
| PLP `pn` | −0.98 / +1.10 | +4.48✱ / +5.71✱ | +8.97✱ / +11.20✱ | +3.50 / +6.81 |

Mean document posteriorgram entropy (nats): no-VTLN, model-only and selection-only are
all 0.434–0.449. Only the VTLN rows are lower, at 0.416–0.424.

### Reviewer checks (scratch, not committed, no new retrieval run)

These are post hoc and undeclared, computed from existing outputs or score-free. They are
not results.

1. **The cycle 8 level hypothesis does not explain the excess VTLN gain.**
   - Gain test on the `pn` VTLN models: 100 train utterances, seed 1, waveform ×0.5 / ×1 /
     ×2. α̂ changes for **0 %** of utterances, for both MFCC and PLP. This confirms K4 on real
     utterances under λ_r.
   - Yet the `pn` paired gains stay at +8 to +11, every `pn` − un-normalised interval
     includes 0, and the final 1.12 edge share is unchanged: MFCC 0.128 against 0.129, PLP
     0.197 against 0.200.
   - The level mechanism found in cycle 8 is real for un-normalised MFCC, but it is not
     what makes our VTLN gain larger than the thesis's. The edge pile-up is not level-driven
     either.
2. **`pn` creates a level mismatch between queries and documents.**
   - Query clips are peak-normalised on their own (clip mode extracts features from the cut
     clip). Documents and training utterances are normalised per utterance.
   - Over the 145 queries, the ratio of utterance peak to clip peak has median 1.44, p90
     2.70 and max 4.96, and 79 % of queries have a ratio above 1.01. The implied MFCC c0
     offset of queries against documents (√40 · 2 ln r) has median 4.6, p90 12.5 and max
     20.3. The c0 spread across utterances is about 5.3.
   - The un-normalised profile has no such mismatch, because clip and utterance share the
     raw level. MFCC-TMP and `timit_matlab` MFCC (both peak-normalised) have always had it.
   - The only measurement so far is cycle 5's slice − clip on `timit_matlab` MFCC GMM-64
     (split v1, no VTLN): −1.34 (−4.2, +1.3) / −0.55 (−2.4, +1.3). That run also changes the
     deltas at clip edges, and nothing has been measured under VTLN or on `pn`.
   - No cause is claimed. The `pn` − un-normalised MFCC no-VTLN MAP of −1.76 (−3.36, +0.03)
     is borderline and is not evidence of one.
3. **Paired comparisons the doc reads from marginal intervals.**
   - `query_inherit` − VTLN row: MFCC +0.49 (−1.07, +2.28) / +0.77 (−0.26, +1.91); PLP
     **+1.98 (+0.54, +3.48) / +1.87 (+0.54, +3.18)**, which excludes 0.
   - VTLN row − selection only (un-normalised): MFCC **+6.92 (+3.76, +10.19) / +6.01
     (+3.20, +8.86)**; PLP +1.26 (−1.99, +4.95) / +2.34 (−0.11, +5.19).
4. **Q41 nuance.** Every thesis row, with and without VTLN, lies inside our marginal
   cluster intervals. For example, MFCC `pn` VTLN is 45.10 (35.1–55.5) against 36.26, near
   the low edge. Only the **paired** gain is inconsistent with the thesis.
5. **Q42 nuance.** MFCC-TMP − MFCC `pn` without VTLN:
   - p@N +2.14 (−0.07, +4.19): the thesis's +5.12 lies above the interval;
   - MAP +2.40 (−0.58, +4.93): the thesis's +4.79 lies **inside** it;
   - with VTLN, −1.03 / −0.73: the thesis's +6.62 / +5.90 lie above.

   The doc's "not reproduced" holds under VTLN. Without VTLN it is true for p@N only.

## 3. Questions for Handoff_feedback

1. **Plan Q39: where the un-normalised gain shows up.**
   - Model only never excludes 0. Selection only excludes 0 on the instance average for
     both features, and on the keyword average for PLP only.
   - In all four 2×2 sets (un-normalised and `pn`), the full VTLN row exceeds the sum of the
     two halves. On p@N the full row is 1.7 to 2.6 times the sum; on MAP it is 1.4 to 2.0
     times. Document entropy drops only in the full row.
   - Descriptively, then, the gain mostly appears only when model and selection change
     together. Is that wording supportable under the declared reading rule ("no mechanism;
     halves need not add up")? Or does even "mostly together" overstep it?
   - The doc says `query_inherit` is "within about 0.5–2 points… overlapping intervals".
     Should it give the paired difference instead? Under the paired difference, PLP
     `query_inherit` is above its VTLN row with an interval that excludes 0 (§2 check 3), so
     noisy clip α̂ (59–72 % disagree with the source) slightly *lowers* PLP's VTLN row.
   - Should the Reviewer-computed paired numbers (check 3) go into the doc, labelled post
     hoc?
2. **Plan Q40: S1.**
   - (a) Dropping c0 changes α̂ for 12–14 % of MFCC utterances and 6.4 % of PLP, and the
     mean moves by less than 0.001. There is no null: when the LL is nearly flat across
     warps, dropping any one dimension might flip a similar share. Is a control (drop one
     non-c0 static cepstral dimension, same code) needed before reading "c0 drives part of
     the individual choices"?
   - Also, the (a) baseline is α̂ under λ_r, not the iteration-4 trace α̂. The doc says so;
     is that enough?
   - (b) ρ(F0, α̂_thesis) is −0.69 to −0.75 overall and stays clearly negative within the
     F0 groups (−0.18 to −0.34 below 165 Hz, −0.42 to −0.44 at or above). Does this support
     "α̂ tracks the speaker within gender"?
   - The partial ρ(c0, α̂ | F0) is as large for PLP (+0.206) as for MFCC (+0.235), although
     PLP's α̂ barely responds to gain (cycle 8: 8–9 %). So the partial correlation is not
     evidence of the level mechanism. Should the doc say that?
   - The intervals are over utterances ("no speaker IDs"). `TimitRow` holds only split,
     row, sentence, audio and rate. Does the HF TIMIT copy carry a speaker or dialect column
     (TIMIT speaker IDs start with M/F)? If it does, a speaker-cluster bootstrap and a true
     gender split would replace the 165 Hz proxy. Is that worth a small task?
3. **Plan Q41: normalised reference.**
   - The `pn` paired gains, +8.07 / +9.35 (MFCC) and +8.97 / +11.20 (PLP), stay far above
     the thesis's, which lie below our intervals.
   - The no-VTLN rows stay above the thesis's (MFCC +2.13 / +2.04, PLP +1.38 / +0.25), but
     every thesis row lies inside our marginal intervals (§2 check 4).
   - Every `pn` − un-normalised interval includes 0.
   - Two questions:
     - Is "level handling does not explain the excess VTLN gain" (§2 check 1) a supportable
       sentence for the doc?
     - Must the `pn` − un-normalised comparisons carry the caveat that `pn` changes two
       things at once: the normalisation and a new query/document level mismatch (§2
       check 2)?
4. **New: the query level under `pn` (§2 check 2).**
   - Did the thesis normalise each cut query file, or extract query features from the
     normalised utterance? The answer decides whether clip mode under `pn` matches the
     thesis. Asking the author is likely a **user decision**.
   - Pending that, is a declared, untuned `--query-features slice` sensitivity run worth
     doing for `pn` MFCC and PLP, no-VTLN and VTLN? The slice path already applies
     utterance-level normalisation to queries. The VTLN slice path would also need
     query α̂ from the sliced warped features, or the inherited α̂, which is a design
     choice to settle first.
   - Or is reporting the ratio table enough?
5. **Plan Q42: MFCC-TMP − MFCC with level handling matched.** Without VTLN, +2.14 / +2.40
   (intervals include 0). With VTLN, −1.03 / −0.73. The thesis's MAP advantage without VTLN
   (+4.79) lies inside our interval (§2 check 5).
   - Should "not reproduced" be qualified to "not reproduced under VTLN; without VTLN the
     direction matches, and the thesis's p@N lies above our interval while its MAP lies
     inside it"?
   - Both features now share peak normalisation and the clip-level mismatch. Lineage, filter
     design and the VTLN response still differ, so is "nothing about Teager energy" still the
     only claim?
6. **Edge pile-up and convergence (`pn`).**
   - The final 1.12 shares are 0.128 (MFCC) and 0.197 (PLP), and still growing.
   - 15–20 % of utterances still change at iteration 4.
   - `ll_decreased` fired at iteration 3 (MFCC) and at 1, 3 and 4 (PLP).
   - The query 1.12 shares are 0.23 and 0.29.

   With level ruled out as the driver of the pile-up, is the grid width (0.88–1.12) the
   next open question? Or should the doc leave it as a caveat only, since D4 fixed the
   procedure?
7. **Other issues** in K1–K5 or S1–S3. Reviewer notes:
   - the test edit in report commit `5c301b9`;
   - the thesis rows in the D6 table carry our profile name;
   - K1's check holds by construction (§2). Is a short note in the doc worthwhile, so a
     reader does not over-read "held in every iteration"?
   - Next cycle preview, plan §10 item 1: GMM-128 under `pn`. Should it wait for the answer
     on the query level (Q4), since a slice/clip choice would change those rows too?

## 4. Response format requested

Write `handoff_response.md` with one section per question number. Mark each as
**agree / change requested / unknown / user decision**. For a requested change, give the
file and the concrete change. Commit it as `handoff_resp: cycle 9 review`, push, and notify
the Orchestrator.
