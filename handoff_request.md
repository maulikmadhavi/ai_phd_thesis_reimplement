# Handoff Request: Reviewer → Handoff_feedback

- **Cycle:** 8
- **From:** Claude Code Reviewer
- **To:** Handoff_feedback, the independent reviewer (`requirements.md`, "Agentic handoff").
  Write only `handoff_response.md` (replacing the cycle 7 response) and commit it as
  `handoff_resp: ...`. Do not create or modify any other file, and do not take plan decisions
  in place of the Orchestrator. Mark anything that needs the user as **user decision**.
- **Plan under review:** `docs/plan.md` at `5cbe747`, amended by `0f899b3` (D4) and
  `57acbc8` (D5):
  - §8 Part A, fix-ups G1–G6 (Handoff_feedback `1782de8`);
  - §9 Part B: W1 F0 check, W2 VTLN evaluation wiring, W3 Stage 4 GMM-VTLN runs.
- **User decisions already taken, not to be re-opened:**
  - **D4:** fresh LBG each VTLN iteration; `ll_decreased` is recorded, not a stop, for
    runs 2–5.
  - **D5:** only the 0–4000 Hz band is kept. `htk_described_4k` is the MFCC/PLP reference,
    and PLP 0–3400 Hz VTLN was dropped.

  The Executor's message calls the MFCC band "still the user's"; D5 settled it, and the doc
  states D5 correctly.
- **Status:** COMPLETE. 14 exec commits, `0c53448..c2e323c`. One STOP gate fired:
  `ll_decreased` in W3 run 1, resolved by D4.
- **Sources:** the thesis is at `D:\Storage\career_phd_daiict_work\Thesis`. The old MATLAB
  code is at `D:\Storage\research_code_qbe_std`.

## 1. Commits to review

All are in plan order: G1–G6, then W1 (declared before its run), W2, and W3 (declared before
its runs).

| Commit | Task | Reviewer verdict |
|---|---|---|
| `0c53448` exec: guard model type and rename vtln iteration field | G1 | OK |
| `3d7eb61` exec: record per utterance warps and ll checks | G2 | OK |
| `7f8cb38` exec: fill missing warp likelihoods with nan | G3 | OK |
| `61eaa1b` exec: record run provenance and refuse dirty trees | G4 | OK |
| `2508051` exec: record htk notes and vtln assumptions | G5 | OK |
| `d7e132d` exec: retrain mfcc tmp under current feature digest | G6 | OK: hashes `bebabe42…` / `105fb5ff…` repeat |
| `66c6573` exec: declare f0 warp check | W1 | OK: 21:53:59; the run started from `0dd137b` |
| `50bb979`, `0dd137b` exec: add autocorrelation f0 estimator (+ line wrap) | W1 | OK |
| `b4589e4` exec: run f0 warp check | W1 | OK: ρ = −0.637 passes the declared −0.2 gate, signs agree |
| `25b0cd8` exec: evaluate timit with gmm vtln models | W2 | OK; see Q2 |
| `cea4673` exec: declare stage 4 vtln runs | W3 | OK: 22:00:20, run 1 started 22:00:24 |
| `77a5ee8` exec: record first stage 4 run and ll decrease | W3 | OK: STOP reported as declared |
| `c2e323c` exec: evaluate gmm vtln on text disjoint split v2 | W3 | OK; see Q1–Q4 |

## 2. Reviewer checks done

- **Tests:** `pixi run test` gives **666 passed, 4 skipped** (re-run by the Reviewer). The
  2 warnings ("Mean of empty slice") come from the too-short-clip case in
  `test_vtln_eval.py`. The path raises `ValueError` as intended, but extraction runs on an
  empty clip before the check (Q8).
- **Limits:** the largest module is `text_split.py` at 341 lines. No line is over
  79 characters, no trailers, nothing derived committed.
- **No digest edits:** the cycle touched no file in `FEATURE_SOURCE_FILES`. `profiles.py`
  changed only in a docstring and is not in the digest.
- **Provenance (G4 fields, read from every summary and model JSON):**

  | Run | Start commit | End commit | Dirty |
  |---|---|---|---|
  | G6 MFCC-TMP retrain (64, 128) | `2508051` | `2508051` | false |
  | W1 (`train-vtln` N_iter 1) | `0dd137b` | `0dd137b` | false |
  | 1 | `cea4673` | `cea4673` | false |
  | 2, 3 | `0f899b3` | `0f899b3` | false |
  | MFCC-TMP | `57acbc8` | `57acbc8` | false |

  - G6: the models were written at 21:51:03 and 21:53:18, before `d7e132d` (21:53:44).
    W1 finished at 21:57:15, before `b4589e4` (21:58:40).
  - Training and evaluation times sit between the commits. Run 1 trained 22:00:24–22:11:08
    and evaluated until 22:16:47; `77a5ee8` was committed at 22:17:19.
  - MFCC-TMP trained from 23:18:32 to 02:23:40 (11065 s) and evaluated until 02:29:26;
    `c2e323c` was committed at 02:31:40.
  - No commit landed during any run.
- **Like-for-like checks of VTLN against no-VTLN:**
  - **Queries:** the no-VTLN clip path is `extract_features(cut_clip(...), config)`. The
    VTLN path is `extract_warped_bank(cut_clip(...), config)`, the same call at each of the
    13 warps. Same profile config, same clip.
  - **Documents:** the same `doc_rows`, the same `floor_and_renormalise`, the same
    relevance.
  - **Training recipe:** the final λ_r uses the same recipe as the plain model: n_em_iter
    10, ε 0.2, floor 0.01, seed 0, K = 64.
  - **Per-warp caches:** the same row selection as the plain cache, and the α = 1.00 cache
    has the plain fingerprint.
  - **Baseline rows:** the no-VTLN MFCC-TMP row is carried over from cycle 6. Its parameter
    hash repeats (G6), so that is valid.

### Results (instance p@N / MAP; thesis `Tab:TIMITVTLNPerformance1`)

| Run | no VTLN | VTLN | Paired gain, p@N / MAP (95 % CI) | Thesis gain |
|---|---|---|---|---|
| MFCC 0–4000 Hz | 37.48 / 40.50 | 48.17 / 50.58 | +10.69 (+6.8 to +14.3) / +10.08 (+6.2 to +13.9) | +1.35 / +2.91 |
| PLP 0–4000 Hz | 38.59 / 39.75 | 45.37 / 48.99 | +6.78 (+3.4 to +10.2) / +9.24 (+6.3 to +12.4) | +1.98 / +2.37 |
| MFCC-TMP (`timit_matlab`) | 39.17 / 41.15 | 44.07 / 47.37 | +4.90 (+1.4 to +8.6) / +6.22 (+3.4 to +9.1) | +2.85 / +4.02 |
| MFCC 0–3400 Hz (earlier reference) | 34.58 / 35.73 | 41.65 / 45.21 | +7.07 (+3.8 to +10.4) / +9.47 (+5.5 to +13.0) | +1.35 / +2.91 |

- **Gains against the thesis:**
  - for MFCC 4k and PLP 4k, the thesis's gain lies **below** our paired interval on every
    instance-average metric;
  - for MFCC-TMP, the thesis's p@N gain (+2.85) lies **inside** our interval, and its MAP
    gain (+4.02) is just above the lower edge;
  - the direction matches the thesis for every run.
- **Edge pile-up:** after 5 iterations the train edge shares (thesis label 0.88 / 1.12) are:

  | Run | 0.88 | 1.12 |
  |---|---|---|
  | MFCC 4k | 0.054 | 0.129 |
  | PLP 4k | 0.090 | 0.200 |
  | MFCC-TMP | 0.085 | 0.146 |
  | MFCC 3400 | 0.072 | 0.136 |

  - The 1.12 share rises at every iteration in all three 0–4000 Hz runs.
  - Query clips sit at 1.12 more often (0.19–0.28) than test documents (0.15–0.22).
  - 59–72 % of queries get an α̂ different from their source utterance's final train α̂.
- **Not converged:** 11–20 % of train utterances still change warp at iteration 4.
- **`ll_decreased`:** fired at iteration 3 (MFCC 4k, PLP 4k), at 2 and 3 (MFCC-TMP), and at
  2 and 4 (MFCC 3400).
  - The decreases are 0.001 to 0.05 per frame.
  - The new model's LL rises only from iteration 0 to about 2, then wobbles by a few
    hundredths: −116.26, −116.20, −116.14, −116.18, −116.15 for MFCC 4k.

### Reviewer finding: α̂ responds to recording level (scratch, not committed, no score)

This is a partial candidate explanation for gains far above the thesis's, for MFCC only.
It is not a claim of cause.

- **Pattern that prompted it:**
  - the two features with **no level normalisation** (`htk_described_4k` MFCC and PLP:
    `normalize_peak=False`, `remove_dc=False`) have gains well beyond the thesis's;
  - the one feature that **is** peak-normalised (MFCC-TMP `timit_matlab`:
    `normalize_peak=True`, `remove_dc=True`) has a gain consistent with the thesis's;
  - the PLP test below shows this pattern is not explained by level alone.
- **Mechanism:** warping changes the area under each filter with no correction. A plan G5
  assumption records "no Jacobian or filter-area correction". The area change shifts c0 and
  the low cepstra. In the run 1 MFCC 0–3400 Hz train caches, the frame-mean c0 is 77.15 at
  α_ours 0.88 (thesis 1.12), 79.05 at 1.00 and 80.17 at α_ours 1.12 (thesis 0.88).
- **Correlation:** Spearman ρ(final α̂_thesis, utterance mean c0 at α = 1) is **+0.263**
  (run 1, 3696 train utterances). Mean c0 rises overall from 77.7 at thesis 0.88 to 81.2 at
  thesis 1.12; the c0 standard deviation across utterances is 5.3. Louder utterances choose
  the warp that lowers c0, and quieter ones the warp that raises it, so the choice pulls
  each utterance towards the average level. This alone is confounded with gender.
- **Direct test:** 100 random train utterances (seed 1), with the waveform scaled by ×0.5,
  ×1 and ×2, and α̂ re-estimated under each run's final λ_r. A pure speaker estimate would
  not move.

  | Model | α̂ changed, ×2 against ×1 | α̂ changed, ×0.5 against ×1 | 1.12-edge count at ×0.5 / ×1 / ×2 | Mean α̂_thesis shift, ×2 / ×0.5 |
  |---|---|---|---|---|
  | MFCC 0–3400 Hz (run 1) | 22 % | 28 % | 6 / 12 / 19 | +0.008 / −0.011 |
  | MFCC 0–4000 Hz | 22 % | 39 % | 10 / 17 / 24 | +0.008 / −0.012 |
  | PLP 0–4000 Hz | 8 % | 9 % | 22 / 24 / 26 | +0.002 / −0.002 |

  For MFCC, a ×2 gain shifts c0 by about +8.8, about 1.7 standard deviations of the level
  spread across utterances. It is an exact **c0-only** perturbation: a waveform gain adds a
  constant to every log filterbank output, which the DCT maps to c0 alone (lifter weight 1
  at n = 0, deltas unchanged). So every α̂ change in the MFCC rows is caused by the c0 shift
  alone, with no noise floor to subtract. For MFCC-TMP the test is moot: peak normalisation makes the
  features, and so α̂, exactly invariant to a waveform gain.
- **What this does and does not say:**
  - For **MFCC** (both bands), α̂ is partly a per-utterance level adjustment, and the
    no-VTLN MFCC baseline has no such adjustment. So part of the MFCC VTLN gain may be level
    normalisation rather than speaker normalisation.
  - **PLP weakens the general pattern:**
    - PLP's α̂ is nearly level-invariant (8–9 % changed, shifts of about 0.002), probably
      because the filter-area change goes mostly into the LPC gain;
    - yet PLP's gain (+6.78 / +9.24) is still far above the thesis's (+1.98 / +2.37);
    - and PLP has the largest edge pile-up (1.12 share 0.20).

    So the level mechanism cannot be the whole story. It explains at most part of the MFCC
    excess, and something else drives PLP's.
  - HTK's own `WARPFREQ` also leaves filter area uncorrected, so the thesis's HTK runs may
    have had the same property. Whether its HTK features were level-normalised is unknown
    (`ZMEANSOURCE` and the recalled defaults are unverified).
  - The finding does not by itself say the reproduction is wrong.

## 3. Questions for Handoff_feedback

1. **Plan Q36: direction and size.** All four runs reproduce the thesis's VTLN direction,
   with intervals excluding 0. For MFCC 4k and PLP 4k, the thesis's gains lie below our
   intervals. Is the doc's wording sound: gains above the thesis's, "no cause claimed", and
   "not a like-for-like comparison" across bands? Should the doc also say, per run, whether
   the thesis gain lies inside our paired interval (MFCC-TMP p@N yes; MFCC 4k and PLP 4k
   no)?
2. **Like-for-like (Orchestrator's request).** The Reviewer found no difference between
   the VTLN and no-VTLN paths beyond warping and model (§2). Is anything else not
   like-for-like? In particular:
   - λ_r is trained on X^α̂ and scored on warped documents and queries, against λ on X^1;
   - every query and every document chooses its own α̂ by maximum likelihood under λ_r,
     which may sharpen posteriorgrams by itself;
   - query α̂ comes from short clips, with high edge shares and 59–72 % disagreement with
     the source utterance.

   What are the smallest diagnostics, without tuning, that separate the gain into parts?
   For example:
   - (a) λ_r with α = 1 everywhere, which is a model-only effect;
   - (b) mean posteriorgram entropy, plain against VTLN;
   - (c) the level finding below.
3. **Level finding (§2, Reviewer).** The evidence covers MFCC only, and PLP is nearly
   level-invariant yet still has a large gain. Is it enough to report in the results doc
   as an MFCC observation? What is the smallest declared, untuned check? Options:
   - (a) a named ablation that normalises filter area under the warp;
   - (b) VTLN on a level-normalised variant of `htk_described_4k`
     (`normalize_peak=True`), with its own no-VTLN baseline;
   - (c) report the gain-test table only.

   Note that D5 fixed the band, not the level handling, and that `htk_described`'s
   "no peak normalisation" is a recalled HTK default (`ZMEANSOURCE`), not author-stated. Is
   asking the author whether the HTK configuration normalised level a **user decision**?
4. **Edge pile-up and convergence (plan Q36).** The 1.12 share grows at every iteration,
   reaching 13–20 %, and 11–20 % of utterances still change at iteration 4.
   - Is the 0.88–1.12 grid too narrow for TIMIT's speakers?
   - Or does the pile-up follow from the level mechanism? For MFCC 4k it plausibly does in
     part: at ×2 gain the 1.12 count rises from 17 to 24 of 100. For PLP it does not: α̂ is
     nearly level-invariant, yet PLP has the largest 1.12 share (0.20).
   - Should the doc report the edge shares as a caveat on the VTLN rows?
5. **Plan Q37: `ll_decreased` under fresh LBG.** D4 settles the procedure.
   - Is the doc's reading enough: small decreases of up to 0.05 per frame, with the LL
     plateauing after about iteration 2?
   - Should the per-iteration LL be described as "non-monotone after iteration 2" rather
     than as isolated decreases?
6. **Plan Q35: F0 check.** ρ(F0, α_thesis) = −0.637, with signs agreeing under the label
   map. Does this support D3 (c) and "α̂ tracks the speaker"? Should it be noted that the
   check ran at iteration 0 (λ_init bump at 1.00) and on the 0–3400 Hz profile, not on the
   D5 reference?
7. **Plan Q38: MFCC-TMP − MFCC.** Under VTLN:
   - against MFCC 4k it is −4.09 p@N (−7.1 to −1.0);
   - against MFCC 3400 it is +2.42 (−1.1 to +6.0);
   - without VTLN, against 4k, it is +1.70 (−0.6 to +3.9).

   Given the level finding, VTLN may help the two non-normalised MFCCs more than the
   peak-normalised MFCC-TMP, so the comparison under VTLN mixes front end, band and level
   handling. What reading of Q38 is supportable? Is the doc right to claim nothing about
   Teager energy?
8. **Other issues** in G1–G6 or W1–W3. Reviewer notes:
   - `clip_warp_features` extracts all 13 warps before checking the clip length, which
     gives the empty-slice warnings. Check `len(clip)` against one frame first.
   - The results doc prints edge shares as raw Python dicts with 17 digits. Use 3-decimal
     columns.
   - `pitch.frame_f0`: when no peak exists, `top = -inf` and `peaks >= 0.9 * top` is
     all-true. It is harmless because the threshold rejects the frame, but it is fragile.
   - `train_vtln` records `ll_decreased` against λ_init on the new α̂. Is that the right
     comparison, as opposed to the new model against the previous model on the previous
     α̂?

## 4. Response format requested

Write `handoff_response.md` with one section per question number. Mark each as
**agree / change requested / unknown / user decision**. For a requested change, give the
file and the concrete change. Commit it as `handoff_resp: cycle 8 review`, push, and notify
the Orchestrator.
