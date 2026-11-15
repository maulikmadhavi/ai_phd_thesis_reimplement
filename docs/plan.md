# Execution Plan: QbE-STD Thesis Reimplementation

- **Cycle:** 7 (Orchestrator)
- **Handoff input:** `handoff_response.md` at `0cb6983` (Handoff_feedback review of cycle 6,
  Q1–Q8), plus user decision D2 (2026-11-16)
- **Stage status:** Stages 0–3, TIMIT word alignment, the thesis scorer, split v2, and MFCC,
  PLP and MFCC-TMP on v2 are done. 563 passed, 1 skipped at `ec565b5`.
- **This cycle:** the review fix-ups (part A, §8), then front-end parity (a level-handling
  check and the `htk_described` reference profile) and the Stage 4 GMM-VTLN code, with no
  VTLN score yet (part B, §9)
- **Review agent:** from the cycle 6 review on, `handoff_response.md` comes from the
  Claude Code session Handoff_feedback, not Codex (protocol in `requirements.md`)
- **Source of truth:** thesis `D:\Storage\career_phd_daiict_work\Thesis` (`Chapters/*.tex`,
  `Backmatter/*.tex`) and the MATLAB feature repo
  `github.com/maulikmadhavi/research_myMATLAB_codes/tree/master/Analysis/Feature_Extraction`

Rule for every stage: implement from the thesis first, then cross-check against the MATLAB
code. Expect results to be *similar*, not identical. The thesis says HTK produced its
MFCC/PLP, so every choice that isn't pinned down stays configurable.

---

## 1. Roadmap

| Stage | Scope | Status | Thesis reference |
|---|---|---|---|
| 0 | pixi env, skeleton, test runner | done | requirements.md |
| 1 | Audio base: I/O, resampling, pre-emphasis, framing, windowing, spectrum, energy, TEO | done | ExpSetup §Front-end |
| 2 | Features: mel/Bark scales, VTLN frequency warping, mel filterbank, MFCC + Δ/ΔΔ, PLP, MFCC-TMP | done; row-selection identity **this cycle** (§8 C2) | ExpSetup §Acoustic Representation; Warped_Feature appendix |
| 3 | ML: LBG VQ codebook → diagonal GMM by EM, log-likelihood | done; model and split guard | ExpSetup §Posterior Representation; `Backmatter/Algorithm_LC` |
| 4 | Posteriorgrams: Gaussian, iterative GMM-VTLN, mixture of GMMs | Gaussian done | Representation §GMM-based VTLN; §Mixture of GMMs |
| 5 | Matching: symmetric KL, subDTW LC1/2/3 (S/T/P), path selection, z-norm; DTW, fastDTW, partial matching | KL, LC2, z-norm, thesis endpoint rule done | ExpSetup §Searching, §Detection; Matching §Partial Matching |
| 6 | Indexing: **STM** phone segmentation → posterior averaging; segment-level BoAW tf-idf | | Matching §Feature Reduction (STM, lines 287–339), §BoAW |
| 7 | Evaluation: p@N, MAP, recall, TWV/MTWV, C<sub>nxe</sub><sup>min</sup>, DET; TIMIT Q-20/Q-84 manifests | Q-20, p@N, MAP, cluster bootstrap, text-disjoint v1 done; **this cycle:** split v2 (§8) | survey §Metrics; Appendix θ, β |

Later: re-scoring with detection sources, score fusion, phonetic posteriorgrams (these need
the BUT phone recognizer).

---

## 2. Component inventory

**Data**
- TIMIT, HF copy `Siyong/speech_timit`: parquet files with columns `audio{array, sampling_rate}` and `sentence`.
  - Split is 5040/1260, not the official 4620/1680.
  - No IDs and no `.WRD` boundaries (`docs/data_notes.md`).
- SWS 2013: 8 kHz; 10762 test utterances, 505/503 queries. Stored as a tgz in `research_data`.
- QUESST 2014: 8 kHz; 12492 test utterances, 560/555 queries. Already extracted under `research_code_qbe_std/hquest/data`.
- Scoring: `scoring_atwv_sws2013_full.tgz` is the MTWV/C<sub>nxe</sub> reference.

**Front end** (thesis + MATLAB; MATLAB file and line references are from Codex's response)
- Pre-emphasis 0.97, Hamming window, 25 ms window, 10 ms shift, `NFFT = 2^nextpow2(win)` (`Fx_mfcc.m` lines 16–26, 43).
- MATLAB preprocessing: `x − mean(x)`, then divide by `max|x|`, then pre-emphasis. Multiplies by 32768 before the FFT.
- MFCC: 26 mel filters, 13 coefficients **including c0** (DCT rows `1:Nc`). Spectrum is unnormalized FFT magnitude, then `log((M·|X|)²)` (`Fx_mfcc.m` lines 39–51).
- Liftering:
  - `Fx_mfcc.m` applies none.
  - `Fx_mfcc_lift.m` uses `Nlift = −20`, which in rastamat `lifter` means an HTK-style sine lifter of length 20.
  - HTK's default is 22. Keep it configurable.
- Δ/ΔΔ: `Deltacep.m` regression `Σ k·(x[t+k] − x[t−k]) / (2·Σ k²)`, with edge frames replicated.
- VTLN warping (MATLAB `Fx_vtln_warp.m`), piecewise linear:
  - `f' = (2−α)·f` for `f ≤ f0`, with `f0 = 0.875·fs/2`.
  - Above `f0`, a second line maps `fs/2 → fs/2`.
  - If `(2−α)·f0 ≥ fs/2`, lower the factor in steps of 0.05.
  - The cutoff matches the thesis appendix (3500 Hz at a 4 kHz Nyquist).
  - The warp is applied to the FFT bin frequencies before mel mapping.
  - α ∈ {0.88, 0.90, …, 1.12}.
  - Alternative from the thesis appendix: `M_α(f) = 2595·log10(1 + f/(700α))`.
- PLP (`Fx_PLPCC_htk.m`):
  - Mel filterbank over 0–fs/2 applied to the **power** spectrum.
  - Then equal-loudness weights `((f²/(f²+1.6e5))²)·((f²+1.44e6)/(f²+9.61e6))`, then cube root (`^0.33`).
  - Edge bands are copied from their neighbours.
  - LPC by autocorrelation, with order 8 in MATLAB versus 12 in HTK (configurable).
  - Then `lpc2cep` to 13 coefficients, then lifter.
- MFCC-TMP (`Fx_mfcc_vtmp_cep.m`). Defaults: fs = 16000, fL = 0, **fH = 4000**, 26 filters, 13 coefficients, DI = 1, `specopt='mp'`. Per filter k:
  - Multiply the *complex* STFT by the symmetric full-length mel weights.
  - Take the real IFFT to get the time-domain subband frame.
  - Sum the TEO over the frame to get the subband energy.
  - Then `log`, then DCT, keeping rows `1:Nc`.
  - `vteo` is not in the public repo, so take TEO with lag DI as `x²(n) − x(n−DI)·x(n+DI)`, marked unverified.
- TEO: `ψ{x(n)} = x²(n) − x(n+1)·x(n−1)`.

**ML, matching and metrics:** see §1 references. Fixed numbers:
- GMM with 64 or 128 components, LBG initialization; VTLN uses 5 iterations.
- subDTW defaults to LC2. A path is valid when 0.5 ≤ len/N ≤ 2.
- SWS 2013: 7 paths per pair, N_top = 1000. QUESST 2014: all utterances.
- Score normalization: `s = −(d − μ)/σ`, using sample std.
- β = 66.66 for SWS 2013 and 12.49 for QUESST 2014.
- Metric test case: hits `t,t,f,f,t,f,f,t,f,f`, N = 4 → p@N = 50 %, AP = 0.775.

## 3. Reproduction targets

TIMIT Q-20, 64 mixtures (Table `Tab:TIMITVTLNPerformance1`), p@N / MAP:

| Feature | No VTLN | GMM-VTLN |
|---|---|---|
| MFCC | 34.91 / 36.71 | 36.26 / 39.62 |
| PLP | 35.50 / 37.58 | 37.48 / 39.95 |
| MFCC-TMP | 40.03 / 41.50 | 42.88 / 45.52 |

TIMIT Q-20, no VTLN, by local constraint (`Unsupervised.tex` lines 125–141,
`Tab:ExpResultTIMIT`), p@N / MAP:

| Feature | NG | LC | GMM | Mix GMM |
|---|---|---|---|---|
| MFCC | 64 | LC1 | 31.75 / 32.27 | 36.73 / 38.95 |
| MFCC | 64 | **LC2** | **34.91 / 36.71** | 39.22 / 42.18 |
| MFCC | 64 | LC3 | 30.35 / 31.08 | 36.25 / 38.94 |
| MFCC | 128 | LC1 | 33.20 / 35.69 | 39.57 / 41.56 |
| MFCC | 128 | **LC2** | **36.81 / 38.34** | 41.34 / 44.29 |
| MFCC | 128 | LC3 | 30.67 / 32.33 | 35.10 / 37.11 |
| PLP | 64 | LC1 | 33.45 / 34.43 | 39.56 / 42.33 |
| PLP | 64 | LC2 | 35.50 / 37.58 | 41.91 / 44.75 |
| PLP | 64 | LC3 | 31.82 / 33.00 | 37.48 / 39.18 |
| PLP | 128 | LC1 | 33.73 / 36.12 | 39.87 / 41.84 |
| PLP | 128 | LC2 | 37.30 / 40.18 | 43.14 / 45.14 |
| PLP | 128 | LC3 | 31.19 / 32.52 | 35.93 / 38.23 |

**Thesis protocol sizes:** 3696 train utterances, 1344 test documents, 145 query instances,
160 keyword occurrences (tokens). Our numbers are protocol references only, not directly
comparable, until the split matches (§8 C5, split v2).

---

## 4. Open questions and decisions

| # | Question | Status after cycle 2 |
|---|---|---|
| 13 | Pre-emphasis, window, FFT size, c0, lifter | **Resolved for defaults:** 0.97, Hamming, nextpow2, c0 kept. Lifter configurable (0 / 20 / 22). |
| 14 | TIMIT at 8 kHz or 16 kHz? | **Data resolved:** all 6300 HF rows are 16 kHz. Whether the thesis HTK pipeline resampled is unknown. Use the `timit_matlab` profile (C2): MFCC and MFCC-TMP at (16 kHz, 4 kHz), PLP at (16 kHz, 8 kHz). Generic defaults are unchanged. |
| 15 | Q-84 list | **Unknown.** Derive it deterministically in Stage 7 from the official split and normalized transcripts, compare the count to 84, and commit the list as an artifact. |
| 16 | Phone segmentation for Stage 6 | **Resolved:** STM (`stm_computation.m`, Matching.tex lines 287–339). |
| D1 | **User decision:** is a licensed LDC TIMIT copy with `.WRD` files available? | **Resolved 2026-11-14:** no LDC copy. The user chose the forced aligner [`Scicom-intl/Where-Words-Begin-and-End-Whisper-Large-V3`](https://huggingface.co/Scicom-intl/Where-Words-Begin-and-End-Whisper-Large-V3) to produce the word boundaries on the HF copy. This replaces the Reviewer's MFA proposal in `handoff_request.md` Q14. Results are labelled approximate against the thesis. Done in cycle 2b (§7). |
| 20 | How were a keyword's instances combined? | **Unknown** (Codex Q1). Each instance stays its own query; report instance and keyword averages; neither is called the thesis aggregate. |
| 21 | Is Occ. a document or token count? | **Token count** (Codex Q2, `ExpSetup.tex` lines 75, 80). Relevance stays binary per document, exact token match. Morphological variants unknown. |
| 22 | Query features from clip or slice? | Clip stays primary; slice is a sensitivity run (cycle 5 B4). |
| 23 | Path validity measure? | **Resolved** (Codex Q5): `wr = (i − P(i,N))/N` in test frames; min `S/T` over valid endpoints. |
| 24 | Step 2 tie-break? | **Resolved** (Codex `ba99a8a` Q4): keep hash order; disclose minimum-cost assignment counts per component (§8 C4). |
| 25 | Next suspect for the gap? | **None identified** (Codex Q2): fix v2, then PLP / MFCC-TMP / VTLN on v2. Revisit a front-end or aggregation hypothesis only with a parity test or new provenance. |
| D2 | **User decision:** the HTK settings for the thesis MFCC/PLP | **Resolved 2026-11-16 (author):** `NUMCHANS = 40` for both, 16 kHz, band 0–3400 Hz; 25/10 ms and 13 + Δ/ΔΔ as in the thesis. The level check is approved; `htk_described` becomes the MFCC/PLP reference (§9). |
| 26 | Carry the HF baseline forward? | **No** (Codex Q3): v2 is the primary Q-20 comparison; HF v2 and text-disjoint v1 are one-off references. |

Codex decisions adopted:
- Keep `win-64` only.
- Rely on `pixi.lock` rather than version bounds.
- No `[build-system]` until packaging is needed.
- Whole-utterance DC removal is fine.
- `frame_teager_energy` stays a Stage 1 statistic only (it is not MFCC-TMP).
- Keep the unnormalized power spectrum (no `1/n_fft`).

## 5. Thesis errata (do NOT copy these)

- Alg. `pseudocode_vtlnwarping`: `WHILE (k ≥ N_iter)` should be `k < N_iter`.
- Alg. `pseudocode_warping_path_select`: initialize `G` and `CG` once, before the loop.
- Alg. `pseudocode_STP_Computation_LC2`: the first-rows block should write `T(i,j)` / `P(i,j)`, not `T(1,j)` / `P(1,j)`.
- subDTW init equations mix up i and j. Follow the algorithm boxes and `research_qbestd/matlab/NSDTW_c_skel.cpp` (LC2). `Fx_do_SDTW.m` is *segmental* DTW, not the subDTW kernel.
- MFCC-TMP DCT formula indexes `k = 1..N_c` (no c0), but the MATLAB code keeps c0. Make it `include_c0`, defaulting to True per MATLAB.

## 6. Risks

- TEO can be ≤ 0, so log of the subband TEO sum needs a floor. Log every floor hit in tests, and never let `-inf` or `nan` reach later stages.
- `Fx_melfiltbank.m` and `vteo.m` are missing from the public MATLAB repo. Our triangular filterbank follows HTK and the shape of `Fx_PLPCC_htk.m`, so expect small numeric differences.
- Never commit data or audio. Never extract tarballs into the repo.

---

## 7. Done in earlier cycles (details are in git history and `handoff_request.md`)

- **Cycle 1:** Stage 0 and Stage 1 (T0.1–T1.11).
- **Cycle 2:** Stage 1 fix-ups F1–F7 and Stage 2 features T2.1–T2.11 (`11862f2..a0c46c4`).
- **Cycle 2b:** TIMIT word alignment A1–A5 (`9498174..4d6f1af`). All 6300 rows aligned, all
  16 kHz.
- **Cycle 3:** Codex fix-ups C1–C9 and Stage 3 T3.1–T3.6 (`799b826..c992e9d`, 366 tests).
  - The MFCC (`timit_matlab`, 39-dim) GMM-64 and GMM-128 were trained on 4051 non-SA train
    rows.
  - Their EM curves rise monotonically (`docs/gmm_notes.md`).
- Codex reviewed cycle 3 in `handoff_response.md` at `5c5dea8` (Q1–Q15). Its requested
  changes are Part A below. Its SA, SAD and speaker-overlap answers shape Part B.

**Decisions adopted from `5c5dea8`:**
- Keep the band-edge VTLN anchor.
- Keep the float64 one-pass variance.
- Keep the parameter and file hashes.
- 39-dim MFCC with c0 stays the baseline. 13-static and no-c0 variants are later ablations.
- `n_iter=10` stays fixed as an experimental choice, not a thesis fact.
- The variance floor and k-means tolerance stay marked unverified.
- **HF split:** it is **not strictly speaker-independent** (at least 13 speakers' SA
  utterances cross it). Every HF result is labelled *"speaker overlap present; approximate
  versus the thesis"*. No inferred speaker re-split.
- **SA rows:** dropped from the test documents as well as from training (thesis
  `ExpSetup.tex` lines 73–75).
- **SAD:** the baseline uses every frame. Energy SAD or edge trimming is a later named
  ablation, not thesis parity.

- **Cycle 4:** fix-ups E1–E7 and the first TIMIT Q-20 number, T7.1–T7.5 and T5.1–T5.3
  (`73ea23b..e63e723`, 457 tests).
  - MFCC `timit_matlab`, LC2, 221 query instances × 989 documents, 18 scorable keywords:
    GMM-64 p@N 36.89 / MAP 41.20, GMM-128 39.58 / 44.23. These become **HF v1** in cycle 5 A6.
  - Reviewer finding: 42 of 52 relevant documents share their sentence text with a train
    query source. The official split never allows that.

**Decisions adopted from `a8e2b02`:**
- The HF split numbers are a useful baseline but **not** a thesis-parity claim. Keep them,
  labelled; never replace them.
- Text overlap: option (a), a separately named text-disjoint split (cycle 5 B1–B4).
- Endpoint rule from `ExpSetup.tex` lines 442–469; no silent fallback (cycle 5 A1).
- Provenance: source digest in the feature fingerprint, `split_id`, and a model guard in
  the runner (cycle 5 A2–A3).
- Uncertainty: bootstrap over keywords, paired for model comparisons (cycle 5 A5).
- GMM-128 target 36.81 / 38.34 (§3).

- **Cycle 5:** part A (A1–A6) and part B (B1–B4), `7f2d494..1b76d12`, 519 passed and
  1 skipped.
  - A1 thesis endpoint rule (0 nonmatches in every run), A2 feature-source digest, A3 model
    and split guard, A4 HF GMM hashes unchanged (`80a5b016…`, `c0e38a61…`) under fingerprint
    `2c337a26…`, A5 keyword-cluster bootstrap, A6 HF v2 baseline.
  - B1 `textdisjoint_q20_v1-ee27b531237a`: train 3704 / test 1336 rows, step 2 cost 0 for
    all 20 keywords. B2 manifest selection layer, B3 scores, B4 clip vs slice (paired
    difference includes 0).
  - MFCC, LC2, clip, instance average, p@N / MAP: HF v2 36.95 / 41.25 (GMM-64) and
    39.36 / 44.21 (GMM-128); text-disjoint v1 38.45 / 40.61 and 40.60 / 43.57.
    Keyword-cluster intervals are about ±11 points.
  - **Reviewer finding:** B1 groups by exact text, so one-token transcript variants split
    an SX text into several groups. 8 such SX texts sit on opposite sides of v1, one of
    them a government sentence. v1 is not fully sentence-disjoint.

**Decisions adopted from `ba99a8a`** (Codex review of cycle 5, Q1–Q6):
- **v1 is kept** as a historical result, labelled *"8 SX sentence variants crossed sides;
  government affected; not fully sentence-disjoint"*. It is never redrawn.
- **A versioned correction, `textdisjoint_q20_v2`, is allowed.** The breach is objective,
  and its reason is written before v2 is scored. Scores never choose v2.
- **Variant links are an explicit list of verified group-hash pairs**, not a general
  transitive one-edit rule (that could join unrelated SI sentences).
- **Step 2 keeps its minimum-cost rule after merging.** Keep cost 0 if it is attainable.
  Never break a verified sentence component to force it. Report any nonzero cost.
- **The hash-order tie-break stays.** Disclose the number of minimum-cost assignments per
  connected keyword component. A large count is a disclosure, not a reason to look for a
  better-scoring tie.
- **HF vs text-disjoint stays descriptive:** no unpaired test, and no claim that removing
  overlap raised, lowered or failed to explain the scores.
- **v2 carries forward** as the primary Q-20 comparison. HF v2 and text-disjoint v1 stay as
  one-off references in the historical table, not as rows in every later table.
- **Next suspect (Q25): none identified.** Do not tune to the thesis number. Keep instance
  and keyword averages both visible. Speaker overlap cannot be measured without speaker IDs.
- **Orchestrator extension, flagged for the cycle 6 review (Q27):** link *every* verified
  variant pair, not only the 8 that crossed in v1. Merging those 8 changes the step 2 and
  step 3 placements, so an unlinked pair (for example the shellfish 5 + 2 groups) could
  cross in v2. Codex's own test ("linked variants cannot cross sides") needs the full list.
- **Cycle 6 part A done** (`3fb279d..220d321`): C1 `3fb279d`, C2 `b57397b`, C3 `2a93634`
  (HF parameter hashes unchanged), C4 `d6de36b`, C5 `4e95d7e` (v2 split doc before any v2
  model; all 20 keywords at cost 0, coverage kept), C6 `220d321`.
  - MFCC v2: GMM-64 p@N 40.02 / MAP 42.23, GMM-128 42.94 / 44.96 (instance average). The
    paired 128 − 64 intervals exclude 0 for both metrics and both averages.
- **Protocol change** (`1286fad`, `0f513f4`): Codex is retired. The Claude Code session
  Handoff_feedback writes `handoff_response.md`; every role hands on by SendMessage
  (`requirements.md`, "Agentic handoff").
- **Cycle 6 part B done** (`5145ced..ec565b5`, 563 tests). On v2, p@N / MAP, instance
  average:
  - PLP `timit_matlab`: GMM-64 33.22 / 33.55, GMM-128 31.91 / 32.26;
  - MFCC-TMP: GMM-64 39.17 / 41.15, GMM-128 41.94 / 43.88; 0 TEO floor hits;
  - paired PLP − MFCC excludes 0 *against* the thesis's direction. MFCC-TMP does not
    reproduce the thesis's +5 over MFCC.
- Handoff_feedback reviewed cycle 6 in `handoff_response.md` at `0cb6983` (Q1–Q8).

**Decisions adopted from `0cb6983` and the user (2026-11-16):**
- Q1, Q2: keep v2 with all 20 links; no v3. Document the two-token variants, the corpus
  count and the unmeasured split-draw variation (§8 F1).
- Q3: keep the manual `ROW_SELECTION_VERSION` and pin the row-loop source digest in a test
  (§8 F2). No module move now; fold it into the next change that invalidates the caches.
- Q4, Q5: front-end parity comes before any VTLN score.
  - **User decision D2:** the HTK configuration used `NUMCHANS = 40` for both MFCC and PLP,
    a 16 kHz sample rate and a 0–3400 Hz band. The user approved the level-handling check,
    and chose an `htk_described` profile as the new comparison reference for MFCC and PLP
    (§9 L1, H1, H2).
- Q6: MFCC above the thesis stays **unknown**. The front end is the leading hypothesis,
  tested by L1 and H2. Speaker overlap cannot be checked.
- Q7, Q8: wording and test fixes (§8 F4, F5). New run rule: no commits during a background
  run (§8).
- The user also approved building Stage 4 code now, with no VTLN score until parity is
  reviewed (§9 V1–V3).

---

## 8. Cycle 7, part A: review fix-ups (Handoff_feedback `0cb6983` Q1–Q3, Q7, Q8)

These change no reported number, and none of them rebuilds a cache or retrains a model.

**Run rule, new from this cycle (Q8, provenance).** Never commit while a background
training or evaluation run is going. Either wait for it, or start the run from a fixed
commit in a separate worktree (`git worktree add ../qbestd_run <hash>`). Every
`summary.json` and training log records the commit the run **started** from.

### F1: Split doc additions (Q1, Q2)
- **File:** `docs/split_textdisjoint.md` (docs only)
- **Under "What v2 does not do":**
  - two SX texts keep an unmerged **two-token** variant:
    - unit `675129c68a2c` (6 rows) with single `b180942ceff1`, a contraction written as two
      words;
    - unit `6d86e94d8394` (6 rows) with single `4c952c3a51e1`, one word moved.
  - Both variants are on the train side with their unit, so nothing crosses. That is by
    placement, not by rule. No v3 (Orchestrator decision: nothing crosses, and a v3 would
    change the manifest hash for no change in content).
  - **Corpus-count evidence for the links:** the v2 units are 448 × 7 rows, 2 × 6 rows and
    1892 singles. TIMIT has 450 SX texts × 7 readers and 1890 SI texts, which is 5040 rows.
    The two 6-row units account for the 2 extra singles. A wrong link would break this count.
- **Per-component section:**
  - the product of the counts is 2,488,320 equal-cost keyword assignments, and v2 is one of
    them;
  - for a component with a count above 1, *which* utterances are that keyword's queries and
    documents depends on the fixed choice; the Inst./Occ. counts do not;
  - the keyword-cluster intervals do not measure this split-draw variation, which stays
    unmeasured. Do **not** score alternative assignments.
- **Commit:** `exec: record split v2 limits and corpus evidence`

### F2: Row-loop digest guard (Q3)
- **Files:** `src/qbestd/data/feature_cache.py` (one constant), `tests/data/test_feature_cache.py`
- **Do:**
  - Next to `ROW_SELECTION_VERSION`, add `ROW_LOOP_SOURCE_SHA256`: the sha256 of
    `inspect.getsource(build_feature_cache)` with CRLF turned into LF.
  - Add a test that recomputes the digest and compares it with the constant. On a mismatch
    it fails with: *"the row loop changed: bump `ROW_SELECTION_VERSION` if rows, order,
    offsets or skips changed, then update the pinned digest"*.
  - No fingerprint change and no cache rebuild. The constant is **not** part of the
    fingerprint.
- **Commit:** `exec: pin row loop digest in a test`

### F3: Feature-parity doc correction (Q4)
- **File:** `docs/feature_parity.md` (docs only)
- **Do:**
  - Correct the PLP row and the "What the thesis says" table: both MFCC and PLP were
    extracted with **HTK**, 25 ms / 10 ms, **26 subband filters** in the thesis text,
    13 coefficients + Δ/ΔΔ (`Unsupervised.tex` line 113; `ExpSetup.tex` lines 191, 194, 198).
  - Add a row **"Author statement, 2026-11-16 (user decision D2)"**: the HTK configuration
    used `NUMCHANS = 40` for **both** MFCC and PLP (so the thesis's "26" is inaccurate for
    them), a 16 kHz sample rate and a **0–3400 Hz** band. MFCC-TMP is unaffected: it came from
    the MATLAB script, which uses 26 filters.
  - Add the table from Handoff_feedback Q4 showing how `timit_matlab` MFCC and PLP differ
    (tool, filters, band, pre-emphasis, LPC order, level handling).
- **Commit:** `exec: correct feature parity with thesis and author htk values`

### F4: Feature-results wording (Q7)
- **File:** `docs/results_timit_q20_features.md` (docs only)
- **Do:**
  - Do **not** say "PLP is near its thesis value". Add a small descriptive table of
    per-feature gaps to the thesis at both sizes (for example PLP 64: −2.28 / −4.03;
    PLP 128: −5.39 / −7.92; MFCC 128: +6.13 / +6.62), with no cause attached.
  - **Sources:** MFCC and PLP come from `Tab:ExpResultTIMIT`. MFCC-TMP 40.03 / 41.50 comes
    from `Tab:TIMITVTLNPerformance1` (`Representation.tex` line 270). Name both tables.
  - Under "Feature minus MFCC", add: *"PLP and MFCC differ here in band, filter count,
    pre-emphasis and level handling, so 'against the thesis's direction' describes this
    profile, not PLP as such."*
  - State that the paired tables hold 28 unadjusted 95 % intervals. Add that the single
    marginal one (MFCC-TMP − MFCC, keyword p@N, −2.8 to −0.1) should not be read on its own.
  - Write the thesis values with two decimals: 35.50, 41.50, 37.30.
- **Commit:** `exec: correct feature comparison wording`

### F5: Small code and test gaps (Q8)
- **Files:** `tests/data/test_feature_cache.py`, `src/qbestd/data/text_variants.py`,
  `tests/data/test_text_variants.py`, `src/qbestd/data/text_split.py`,
  `tests/data/test_text_split.py`, `docs/gmm_notes.md`
- **Do:**
  - **Import closure:** add a fixture case with `from ..audio import newhelper`. In the
    helper's docstring, add the two known limits: `from qbestd import features` followed by
    attribute access, and names re-exported through an `__init__.py`.
  - **Finder:** add a test with a 4-row group that has a 1-row and a 2-row partner; both
    candidates come out in a fixed order. Put a three-variant unit into
    `test_v2_manifest_is_identical_under_shuffled_rows_and_links`.
  - **`_merge_units` with `links=()`:** skip the 7-row cap when there are no links, so the
    v1 rule gains no new failure mode. The v1 manifest must stay byte-identical
    (`ee27b531237a…`); test it on a synthetic group of 8 rows.
  - **`gmm_notes.md`:** add the PLP variances at the floor (4 of 2496 at 64, 7 of 4992 at
    128), as the MFCC section does.
- **Commit:** `exec: close import closure finder and merge test gaps`

---

## 9. Cycle 7, part B: front-end parity (Q4, Q5, user decision D2) and Stage 4 code

### L1: Level-handling check (Q4 items 1–2, Q5; user approved)
- **Declare first.** Commit a new section in `docs/results_timit_q20_features.md`,
  "Level-handling check (declared)", **before** the runs:
  - setting: MFCC `timit_matlab` with `normalize_peak=False`, and PLP `timit_matlab` with
    `normalize_peak=True`; nothing else changes;
  - scope: GMM-64 only, split v2, LC2, clip query features, A1 scorer;
  - rule: both results are reported, the primary rows stay unchanged whatever the outcome,
    and no tuning follows from it;
  - commit `exec: declare level handling check`.
- **Code:** add a named ablation profile `timit_matlab_levelflip` in
  `src/qbestd/features/profiles.py`. For `mfcc` it is `timit_matlab` with
  `normalize_peak=False`; for `plp` it is `timit_matlab` with `normalize_peak=True`; it
  raises for `mfcc_tmp`. Add tests, then commit `exec: add level flip ablation profile`.
- **Run:** build the caches for the two HF splits, train GMM-64 on the v2 train side, and
  evaluate. This is 2 caches, 2 models and 2 evals.
- **Report** in the same doc section:
  - p@N / MAP for both averages, with intervals;
  - paired differences against the primary GMM-64 row of the same feature (same queries);
  - PLP − MFCC under the flip.

  No cause is claimed beyond what the paired intervals show.
- **Commit:** `exec: run level handling check`

### H1: `htk_described` profile (user decision D2)
- **File:** `src/qbestd/features/profiles.py` (plus `plp.py` and `filterbank.py` if an
  option is missing), tests
- **Name and status:** `htk_described`. Every value carries its source in the docstring:
  - **author-stated (2026-11-16):** `NUMCHANS = 40` for MFCC and PLP, 16 kHz, band
    **0–3400 Hz**. The band was stated for the HTK configuration and applied to both
    features; the thesis text says 0–4000 Hz for MFCC, and this conflict is recorded;
  - **thesis-stated:** 25 ms Hamming / 10 ms, 13 coefficients + Δ/ΔΔ, 39 dimensions;
  - **HTK defaults, recalled and unverified:**
    - pre-emphasis 0.97;
    - cepstral lifter 22;
    - LPC order 12 for PLP;
    - PLP compression 0.33 with equal-loudness weighting;
    - c0 kept, no energy term (the thesis labels PLP `PLP_D_A_0`, `Unsupervised.tex`
      line 610);
    - delta window 2;
    - no DC removal and no peak normalisation (`ZMEANSOURCE` off);
    - MFCC on the magnitude spectrum, PLP on the power spectrum.
- **PLP filterbank:** HTK PLP uses a **mel**-spaced filterbank of `NUMCHANS` channels.
  - If `PlpConfig` only builds Bark spacing, add `filter_scale: "bark" | "mel"`, defaulting
    to `"bark"` so `timit_matlab` is unchanged.
  - Use the existing `mel_filterbank` with `low_hz` / `high_hz`.
- **MFCC log:** if HTK's log of the mel-weighted magnitude differs from our
  `log((M·|X|)²)` only by a factor 2, note that in the docstring and keep the code.
- **Tests:**
  - a `timit_matlab` regression: features byte-identical before and after;
  - `htk_described` gives 39 dimensions, 40 channels, and a top edge of 3400 Hz;
  - `mfcc_tmp` under `htk_described` raises: MFCC-TMP stays `timit_matlab` (MATLAB script,
    26 filters).
- **Commit:** `exec: add htk described profile for mfcc and plp`

### H2: Run `htk_described` and make it the reference (user decision D2)
- **Run:** MFCC and PLP, GMM-64 and GMM-128, on split v2: 4 caches, 4 models and 4 evals.
  Record the EM curves, floor counts and hashes in `docs/gmm_notes.md`.
- **Report** in `docs/results_timit_q20_features.md`, new section "HTK-described profile
  (reference from cycle 7)":
  - both averages with intervals, and gaps to the thesis;
  - paired PLP − MFCC, plus 128 − 64 per feature;
  - paired `htk_described` − `timit_matlab` per feature and size.
  - Same wording rule as C6.
- From here on, `htk_described` is the comparison reference for MFCC and PLP (user decision
  D2). MFCC-TMP stays `timit_matlab`. The `timit_matlab` rows stay as a labelled earlier
  reference. **Do not tune** anything towards §3.
- **Commit:** `exec: evaluate htk described profile on split v2`

### V1–V3: Stage 4 GMM-VTLN code (no VTLN scoring this cycle)
Thesis: `Representation.tex` lines 100–138 and Algorithm `pseudocode_vtlnwarping`
(lines 140–171). Use **`k < N_iter`** (erratum §5). The warps are 13 values,
0.88, 0.90, …, 1.12. `N_iter = 5` (`Representation.tex` line 229: gains saturate at 4–5).
Build on the existing `warp_factor` support and `extract_warped_bank`.

**Memory:** the machine is short of memory (background shells were killed). Never hold more
than **one** warp's features for a whole split in memory at once.

- **V1: warp estimation.** File `src/qbestd/ml/vtln.py`, with tests.
  - `WARP_FACTORS`, the 13 values.
  - `utterance_log_likelihoods(features, offsets, gmm) -> (n_utt,)`: the summed frame
    log-likelihood per utterance.
  - `estimate_warp_factors(ll_matrix) -> alphas`: argmax over the warps, `ll_matrix` shape
    `(n_utt, 13)`. Ties go to the warp closest to 1.0, then the smaller one. Frame counts do
    not depend on α, so sum and mean give the same argmax.
  - Tests: a synthetic case where one warp is planted; the tie rule; shape checks.
  - **Commit:** `exec: add vtln warp factor estimation`
- **V2: per-warp caches.** Files `src/qbestd/data/warped_cache.py`, tests.
  - `build_warped_caches(split, kind, profile, out_dir, warps=WARP_FACTORS)` writes **one
    file per warp**, `<split>_<kind>_<profile>_a<α×100>.npz`, using the
    `build_feature_cache` row selection and fingerprint, with the warp added to the
    fingerprint.
  - `ll_matrix_from_caches(paths, gmm, rows)` streams one warp at a time.
  - `select_warped_features(paths, alphas, rows)` assembles X^α̂, one warp file at a time.
  - Tests: a tiny parquet in `tmp_path`, 3 warps; streaming gives the same matrix as the
    in-memory version; α = 1.0 equals the plain cache.
  - **Commit:** `exec: add per warp feature caches`
- **V3: iterative GMM-VTLN training.** File `src/qbestd/ml/vtln_train.py` (CLI, pixi task
  `train-vtln`), with tests.
  1. λ_init is the plain GMM, α = 1.
  2. For k = 0 … N_iter − 1:
     - estimate α̂ for every train utterance with λ_init;
     - build λ_r on X^α̂ with the **same LBG + EM recipe** (fresh initialisation; the thesis
       says "build", which is an assumption to record);
     - set λ_init ← λ_r.
  3. Write per iteration: the α̂ histogram, the mean log-likelihood on X^α̂, and the model
     hash. Then save the final λ_r with metadata (`kind`, `profile`, `split_id`,
     `n_iter`, warps, fingerprint).
  - Test-side estimation (α̂ per document with λ_r) and the posteriorgram go in
    `estimate_test_warps(...)`. **Do not wire them into `run_timit` this cycle.**
  - **Query warps (assumption):** estimate α̂ on the query clip itself with λ_r, as for a
    separate file. Record this as an open question.
  - Tests: a synthetic two-iteration run on tiny data; the log-likelihood on X^α̂ does not
    fall from iteration to iteration (`Representation.tex` line 138); the metadata round
    trip.
  - **Commit:** `exec: add iterative gmm vtln training`
- **STOP before scoring:** no VTLN p@N/MAP this cycle. A smoke run of `train-vtln` with
  N_iter = 1 on GMM-64 `htk_described` MFCC is allowed, to check runtime and memory. Report
  its runtime and peak memory, not a score.

**Cycle 7 definition of done:**
- F1–F5, L1, H1, H2 and V1–V3 are on `main` in that order, with L1's declaration before
  L1's runs.
- `pixi run test` is green in the core env. Every module is under 400 lines, no line is
  over 79 characters, and every new function has tests. No derived data is committed.
- No commit was made while a background run was going.
- The Reviewer writes `handoff_request.md` for cycle 7 with the questions below.

**Open questions for the cycle 7 review:**
- 31: What does the level check show? Does it explain MFCC above the thesis and PLP below
  it, and should level handling change for MFCC-TMP?
- 32: Are the recalled HTK defaults in `htk_described` right, especially MFCC log
  magnitude vs log power, the DCT normalisation and the PLP mel filterbank? Should MFCC use
  the author's 0–3400 Hz band or the thesis text's 0–4000 Hz?
- 33: Stage 4: fresh LBG + EM per VTLN iteration, or warm start from λ_init? Should query
  clips get their own α̂ or inherit the train utterance's α̂ from the last iteration?
- 34: Is the per-warp cache design (13 files per split and kind, streamed) acceptable for
  disk and runtime, given the smoke-run numbers?

---

## 10. Next cycles (preview)

1. **Stage 4 scoring:** GMM-VTLN for MFCC and PLP (`htk_described`) and MFCC-TMP
   (`timit_matlab`) on v2, against `Tab:TIMITVTLNPerformance1` (§3).
2. LC1 and LC3 (§3 has their TIMIT targets), Q-84, and the optional SAD ablation.
3. Mixture of GMMs (§3 targets), then DTW and fastDTW, then indexing (STM, BoAW).
4. SWS 2013 and QUESST 2014: path selection with 7 paths, z-norm, MTWV and Cnxe.
