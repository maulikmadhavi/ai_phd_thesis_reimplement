# Execution Plan: QbE-STD Thesis Reimplementation

- **Cycle:** 8 (Orchestrator)
- **Handoff input:** `handoff_response.md` at `1782de8` (Handoff_feedback review of cycle 7,
  Q1–Q8), plus user decision D3 (2026-11-16)
- **Stage status:** Stages 0–3 and split v2 are done. MFCC and PLP `htk_described`
  (0–3400 Hz) and `htk_described_4k` (0–4000 Hz) are on v2, and the Stage 4 VTLN code is
  in. 626 passed, 4 skipped at `c027e05`.
- **This cycle:** review fix-ups and the MFCC-TMP retrain (part A, §8), then an F0 check
  on the warp direction, and Stage 4 GMM-VTLN scoring on both bands (part B, §9)
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
| 4 | Posteriorgrams: Gaussian, iterative GMM-VTLN, mixture of GMMs | Gaussian done; GMM-VTLN code done, scoring this cycle | Representation §GMM-based VTLN; §Mixture of GMMs |
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
| D3 | **User decision:** reference band, HTK facts and VTLN facts | **Resolved 2026-11-16 (author):** run Stage 4 on both bands (0–3400 and 0–4000 Hz). α > 1 is the male side and the warped features came from HTK `WARPFREQ`, so our label is mirrored (α_thesis = 2 − α_ours). `USEPOWER`, `LOFREQ`, the warp cutoffs, fresh vs warm start and the iteration count are not known; the defaults are kept (§7, §9). |
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
  count and the unmeasured split-draw variation (cycle 7 §8 F1).
- Q3: keep the manual `ROW_SELECTION_VERSION` and pin the row-loop source digest in a test
  (cycle 7 §8 F2). No module move now; fold it into the next change that invalidates the caches.
- Q4, Q5: front-end parity comes before any VTLN score.
  - **User decision D2:** the HTK configuration used `NUMCHANS = 40` for both MFCC and PLP,
    a 16 kHz sample rate and a 0–3400 Hz band. The user approved the level-handling check,
    and chose an `htk_described` profile as the new comparison reference for MFCC and PLP
    (cycle 7 §9 L1, H1, H2).
- Q6: MFCC above the thesis stays **unknown**. The front end is the leading hypothesis,
  tested by L1 and H2. Speaker overlap cannot be checked.
- Q7, Q8: wording and test fixes (cycle 7 §8 F4, F5). New run rule: no commits during a background
  run (§8).
- The user also approved building Stage 4 code now, with no VTLN score until parity is
  reviewed (cycle 7 §9 V1–V3).

- **Cycle 7 done** (`c429300..c027e05`, 16 exec commits, 626 passed and 4 skipped):
  - F1–F5 fix-ups. L1 level check (`timit_matlab`, GMM-64): flipping the level handling
    shows no detectable change, and PLP − MFCC stays negative.
  - H1/H2 `htk_described` (40 filters, 0–3400 Hz) on v2, p@N / MAP, instance average:
    - MFCC: GMM-64 34.58 / 35.73, GMM-128 38.04 / 39.87;
    - PLP: GMM-64 34.34 / 35.88, GMM-128 38.33 / 39.73.

    All four are within about 1–2 points of the thesis.
  - H3 `htk_described_4k` (0–4000 Hz):
    - MFCC: GMM-64 37.48 / 40.50, GMM-128 40.99 / 42.89;
    - PLP: GMM-64 38.59 / 39.75, GMM-128 37.60 / 40.01.

    Paired 4000 − 3400 is positive in 6 of 8 p@N rows and 8 of 8 MAP rows. PLP GMM-128
    shows no difference.
  - V1–V3 VTLN code (`c782c6e`, `09ff132`, `9f2a036`). The N_iter = 1 smoke run on MFCC
    `htk_described` GMM-64 took:
    - 429 s, with peak memory 1254 MB;
    - 26 warp caches, about 3 GB;
    - LL −116.45 → −116.32.

    380 of 3696 utterances sit at the 0.88 edge.
  - `cb24a64` edited `plp.py`, which is in the shared feature digest. So every
    `timit_matlab` model, MFCC-TMP included, and the L1 models are now rejected by the
    guard. Their features are byte-identical.
- Handoff_feedback reviewed cycle 7 in `handoff_response.md` at `1782de8` (Q1–Q8).

**Decisions adopted from `1782de8` and the user (2026-11-16, D3):**
- **D3 (a), band:** run Stage 4 on **both** bands. `htk_described` (0–3400 Hz) and
  `htk_described_4k` (0–4000 Hz) are reported side by side for MFCC and PLP. Neither is
  chosen by score.
- **D3 (b), HTK config:** `USEPOWER`, `LOFREQ` and the origin of the 3400 Hz value are
  **not known**. Keep the recalled defaults, marked unverified, and record Handoff_feedback's
  Q2 additions.
- **D3 (c), warp direction (author):** in the thesis, **α > 1 is the male (longer vocal
  tract) side**, and the warped features were made with HTK's `WARPFREQ`.
  - Our bank moves filter peaks *up* for α > 1, so our label is the mirror of the
    thesis's: α_thesis = 2 − α_ours.
  - The 13 slopes are the same set, so the warped features and every score are
    unchanged. **Do not edit `filterbank.py`**: it is in the feature digest, and an edit
    would invalidate all 8 `htk_described` models and the warp caches.
  - Map the label in `ml/vtln.py` and report every histogram in the thesis convention.
  - `WARPLCUTOFF` / `WARPUCUTOFF` are not known. Keep the MATLAB upper anchor
    (`f0 = 0.875·fs/2`) as a recorded assumption.
- **D3 (d), VTLN procedure:** not known. Keep fresh LBG + EM per iteration and N_iter = 5,
  with the Q3 log-likelihood warning.
- Q1: change the wording. Q2: doc additions. Q3: change requested (LL flag, save α̂, guard
  `n_iter < 1`). Q4: run the F0 check before any VTLN score; there is no grid change.
- Q5: report MFCC-TMP − MFCC against both MFCC bands. Q6: retrain MFCC-TMP and check the
  hashes; no per-kind digest. Q7: provenance helper. Q8: guard and other fixes.
- **Worktree suggestion (Q7):** not adopted this cycle. A worktree needs its own pixi
  environment. Instead, the new `--allow-dirty` guard enforces the run rule in code, and
  the no-commit-during-runs rule stays.

---

## 8. Cycle 8, part A: fix-ups before any Stage 4 score (Handoff_feedback `1782de8`)

None of these changes a reported number. No task in this cycle, in part A or part B,
edits a file in `FEATURE_SOURCE_FILES` (`data/feature_cache.py`). That includes W1's
`audio/pitch.py` and W2's clip-warp extraction and `run_timit --vtln`. If a task turns
out to need such an edit, STOP and report: it would invalidate every model.

### G1: Model type guard and VTLN metadata (Q8 a, b)
- `ml/vtln_train.py`:
  - add `"model_type": "vtln"` to the model metadata;
  - rename the VTLN iteration field to `n_vtln_iter`;
  - also store `n_em_iter`, `epsilon`, `var_floor_ratio` and `seed`;
  - refuse a `--gmm` whose type is not plain.
- `eval/model_guard.py`: `check_model(..., model_type="plain")` rejects a mismatch. A
  missing field counts as `"plain"`, so existing models still load.
- Tests: plain model in the VTLN slot, VTLN model in the plain slot, and a missing field.
- **Commit:** `exec: guard model type and rename vtln iteration field`

### G2: VTLN training records (Q3)
- `train_vtln`:
  - raise `ValueError` for `n_iter < 1`;
  - after each iteration, if `mean_ll_new_on_selected < mean_ll_init_on_selected`, log a
    warning and store `"ll_decreased": true`;
  - per iteration, save α̂ keyed by `(hf_split, row)` and the `(n_utt, 13)` LL matrix,
    next to the model under `outputs/`. The α̂ file has two separate columns:
    `alpha_ours` (the cache-file convention) and `alpha_thesis` (= 2 − `alpha_ours`).
- `ml/vtln.py`: add `to_thesis_label(alpha) = round(2 − alpha, 2)` (D3 c).
  - `warp_histogram` reports in the thesis label. Cache file names keep our label and say
    so in the docstring.
  - Assert that the histogram counts sum to the number of utterances (Q8 g).
- Per iteration, report:
  - the histogram;
  - the share at each edge;
  - the share whose α̂ changed since the previous iteration;
  - both log-likelihoods.
- Tests: `n_iter = 0`, the LL flag, the α̂ file round trip, and the label map with its
  symmetric grid.
- **Commit:** `exec: record per utterance warps and ll checks`

### G3: Warp cache fixes (Q8 c)
- `data/warped_cache.py`, `ll_matrix_from_caches`: use `np.full(..., np.nan)` instead of
  `np.empty`.
- Test: when a key's HF split is absent, `estimate_warp_factors` raises.
- Q8 d (reuse the α = 1.00 cache) is optional; skip it.
- **Commit:** `exec: fill missing warp likelihoods with nan`

### G4: Run provenance (Q7)
- A new small module, e.g. `src/qbestd/provenance.py`:
  - record `git rev-parse HEAD` at start and end;
  - record whether `git status --porcelain -- src pixi.toml pixi.lock` is empty;
  - refuse to start on a dirty tree unless `--allow-dirty` is passed, and record the flag.
- Wire it into `eval/run_timit.py`, `ml/train.py` and `ml/vtln_train.py`. The summary and
  model JSON get `git_commit_start`, `git_commit_end`, `git_dirty` and `allow_dirty`. Docs
  quote the start value.
- Test with a temporary git repository: clean, dirty-refused and dirty-allowed.
- **Commit:** `exec: record run provenance and refuse dirty trees`

### G5: Docs (Q1, Q2, Q3, Q5, Q8 e, h, i)
- `docs/results_timit_q20_features.md`:
  - L1 sentence: "this check does not detect a change; the paired intervals allow
    differences of up to about 3 to 4 points either way".
  - Rounded bounds: print two decimals when a bound rounds to ±0.0, and take "excludes 0"
    from the unrounded value. Fix the code that writes the rows if there is any.
  - Wherever MFCC-TMP − MFCC is reported, note that it compares a MATLAB-described front
    end (26 filters, 0–4000 Hz, peak-normalised) with an HTK-described one, as the thesis
    did by the author's statement.
  - Reproduce block: add the `htk_described` and `htk_described_4k` commands, and say that
    the `timit_matlab` ones need the G6 retrain.
- `docs/feature_parity.md` and the `htk_described` docstring, all "recalled, unverified"
  (Q2):
  - PLP and `USEPOWER`;
  - triangles linear in mel vs in Hz;
  - HTK's N + 2 PLP edge bands;
  - HTK's log floor of 1.0;
  - the DC bin;
  - c0 is ×√2 in HTK (note only, no code change);
  - 40 channels in 0–3400 Hz give 1–3 FFT bins per low filter (a property of the
    profile).
- A VTLN assumptions list, in the results doc's Stage 4 section:
  - the tie-break (closest to 1.0, then the smaller warp);
  - no Jacobian or filter-area correction;
  - the MATLAB upper anchor;
  - the label map. The thesis's own `M_α(f)` (`Unsupervised.tex` 549) moves filter centres
    *up* for α > 1, as our code does, so the mirror rests only on the author's D3 (c)
    answer;
  - fresh LBG per iteration;
  - query α̂ estimated on the clip (thesis `Representation.tex` line 104).
- **Commit:** `exec: record htk notes and vtln assumptions`

### G6: Retrain MFCC-TMP `timit_matlab` (Q6)
- Retrain GMM-64 and GMM-128 on v2. The features are byte-identical, so the parameter
  hashes should repeat: `bebabe42…` at 64 and `105fb5ff…` at 128.
- Record whether they repeat in `docs/gmm_notes.md`.
  - If they repeat, the cycle 6 MFCC-TMP rows carry over and need no new eval.
  - If they don't, **STOP** and report.
- Do not retrain the `timit_matlab` MFCC/PLP or L1 models: they are earlier references.
- **Commit:** `exec: retrain mfcc tmp under current feature digest`

## 9. Cycle 8, part B: warp check, then Stage 4 GMM-VTLN scoring (user decision D3)

### W1: F0 vs α̂ check (Q4). Declared before it runs; no retrieval score
- **Declare first** in the results doc's Stage 4 section, then commit
  `exec: declare f0 warp check`. The declaration fixes:
  - **the expectation:** under the thesis label (α > 1 male), median F0 correlates
    **negatively** with α̂_thesis. Equivalently, it correlates positively with α̂_ours;
  - **the pass rule:** ρ(F0, α_thesis) ≤ −0.2, which is the same as
    ρ(F0, α_ours) ≥ +0.2. The report prints both, so a label-mapping bug shows up as a
    sign mismatch.
    - **The −0.2 magnitude is the operative gate.** The 95 % bootstrap interval over
      utterances is reported, but it is anti-conservative: there are no speaker IDs, so
      about 8 utterances per speaker are treated as independent.
    - **The α̂ come from iteration 0 under λ_init**, which has the known bump at 1.00. This
      is stated now so that the check is not reinterpreted after the result;
  - **what happens otherwise:**
    - |ρ| < 0.2 or an interval that includes 0 means α̂ is not tracking the speaker:
      **STOP** before W2;
    - a clear positive ρ contradicts D3 (c): **STOP** and report.
- **Data:** a fresh N_iter = 1 run of `train-vtln` on MFCC `htk_described` GMM-64. The
  warp caches are reused, and it produces the G2 per-utterance α̂ file.
- **F0:** median F0 per train utterance over voiced frames.
  - Use a small autocorrelation estimator with numpy/scipy (librosa is not in the env),
    50–400 Hz, with tests on synthetic tones.
  - Put it in `src/qbestd/audio/pitch.py`, which is not in the feature digest.
- **Report:**
  - ρ with its interval;
  - mean F0 per thesis-label warp;
  - mean F0 of the edge groups;
  - the share of utterances with median F0 < 165 Hz (a rough male proxy) on each side of
    1.0.
- **Commit:** `exec: run f0 warp check`

### W2: Wire VTLN into evaluation
- `eval/run_timit.py --vtln`:
  - load a `model_type: "vtln"` model;
  - estimate α̂ per test document and per query clip with λ_r (`estimate_test_warps`);
  - **query clips:** extract each clip's features at all 13 warps from the clip audio
    itself (145 × 13), and estimate α̂ on those. Never slice the utterance warp caches:
    that would make the VTLN rows slice-mode against clip-mode no-VTLN rows. Write
    `query_features: "clip"` in the summary;
  - assemble the warped features one warp at a time;
  - score with the same LC2 scorer and bootstrap.
- Summary additions:
  - the test and query α̂ histograms, in thesis labels;
  - the share of queries whose α̂ differs from their source utterance's final train α̂
    (Q3).
- Tests: a tiny end-to-end run. A plain model under `--vtln` and a VTLN model without it
  are both rejected. Clip features at α = 1.00 equal the plain clip features.
- **Commit:** `exec: evaluate timit with gmm vtln models`

### W3: Declare Stage 4 runs, then run them (GMM-64, v2, N_iter = 5)
- **Declare first**, commit `exec: declare stage 4 vtln runs`. The declaration covers:
  - **the 5 runs:**
    - MFCC `htk_described`;
    - MFCC `htk_described_4k`;
    - PLP `htk_described`;
    - PLP `htk_described_4k`;
    - MFCC-TMP `timit_matlab`;
  - **the targets:** `Tab:TIMITVTLNPerformance1` (§3);
  - **the comparison:** paired VTLN − no-VTLN on the same queries;
  - **what an interval that includes 0 means (Q3):** the thesis's gains at GMM-64 are
    +1.35 / +2.91 (MFCC), +1.98 / +2.37 (PLP) and +2.85 / +4.02 (MFCC-TMP), and our
    half-widths are about 2–3 points. So an interval that includes 0 is a likely outcome.
    In that case the doc says "the direction matches / does not match the thesis; the
    interval does not establish a gain", and claims nothing more.
  - Nothing is tuned. No band is chosen.
- **Runs:** one at a time, from a clean tree (G4), with no commits while they run. Each
  run gets its warp caches (26 per kind and profile), `train-vtln` with N_iter = 5, and
  an eval. Record:
  - α̂ histograms;
  - edge shares;
  - LL per iteration;
  - `ll_decreased`;
  - hashes;
  - runtime and peak memory.

  The estimate is about 30 min per run, and disk use should end around 20 GB in
  `outputs/features` (838 GB free).
- **If any iteration sets `ll_decreased`:** finish that run, report it and **STOP**
  before the next run. That is the trigger for a warm-start variant (Q3).
- **Report**, in `docs/results_timit_q20_features.md`, section "Stage 4: GMM-VTLN":
  - the VTLN row next to the no-VTLN row for each of the 5 runs, with intervals and
    thesis gaps;
  - paired VTLN − no-VTLN;
  - MFCC-TMP − MFCC under VTLN, against **both** MFCC bands (Q5);
  - the same wording rule as C6.
- **Commit:** `exec: evaluate gmm vtln on text disjoint split v2`

**Cycle 8 definition of done:**
- G1–G6, W1, W2 and W3 are on `main` in that order. W1's and W3's declarations come
  before their runs.
- STOP gates: G6 hash mismatch, a W1 failure, `ll_decreased` in W3, or any needed edit to
  a digest file.
- `pixi run test` is green. Modules stay under 400 lines and lines under 80 characters.
  No derived data is committed.
- No commit was made while a run was going. Every run summary has
  `git_dirty: false`, or `allow_dirty` with a reason.
- The Reviewer writes `handoff_request.md` for cycle 8 with the questions below.

**Open questions for the cycle 8 review:**
- 35: Does the F0 check support the D3 (c) label direction, and does α̂ track the speaker?
- 36: Do the Stage 4 results reproduce the thesis's VTLN direction for each feature and
  band? Is the 0.88/1.12 edge pile-up still present after 5 iterations?
- 37: Did fresh LBG keep the LL non-decreasing? If not, what should the warm-start variant
  look like?
- 38: Does part of the thesis's MFCC-TMP − MFCC gain look like band rather than Teager
  energy, now that both MFCC bands are available?

---

## 10. Next cycles (preview)

1. LC1 and LC3 (§3 has their TIMIT targets), Q-84, and the optional SAD ablation.
2. Mixture of GMMs (§3 targets), then DTW and fastDTW, then indexing (STM, BoAW).
3. SWS 2013 and QUESST 2014: path selection with 7 paths, z-norm, MTWV and Cnxe. The
   QUESST data is extracted under `research_code_qbe_std/hquest/data/quesst14Database`:
   12492 search files, 560 dev and 555 eval queries, and the scoring folder.
