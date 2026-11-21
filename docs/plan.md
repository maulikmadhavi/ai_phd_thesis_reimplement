# Execution Plan: QbE-STD Thesis Reimplementation

- **Cycle:** 10 (Orchestrator)
- **Handoff input:** `handoff_response.md` at `fa101e0` (Handoff_feedback review of cycle 9,
  Q1–Q7), plus user decision D7 (2026-11-21)
- **Stage status:** Stages 0–3, split v2 and Stage 4 GMM-VTLN (GMM-64) are done, on the
  un-normalised `htk_described_4k`, on the normalised `htk_described_4k_pn` (per-clip
  query level) and on MFCC-TMP.
- **This cycle:** the level-matched query path `clip_lm` (D7), post hoc tables and doc
  fixes (part A, §8), then the c0 null control, the level-matched reference evaluations,
  and plain GMM-128 under the reference (part B, §9)
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
| D5 | **User decision:** which band carries forward? | **Resolved 2026-11-17 (author):** 0–4000 Hz only. `htk_described_4k` is the MFCC/PLP reference, and the 0–3400 Hz rows are an earlier reference (§9 W3). |
| D6 | **User decision:** did the thesis HTK pipeline normalise level? | **Resolved 2026-11-18 (author):** mean subtraction, then scaling to ±1. `htk_described_4k_pn` (DC removal and peak normalisation on) becomes the MFCC/PLP reference; the band stays 0–4000 Hz; `htk_described_4k` rows are the un-normalised earlier reference. Diagnostic compute approved (§9). |
| D7 | **User decision:** were queries normalised per cut file or cut from the normalised utterance? | **Resolved 2026-11-21 (author):** the whole utterance was normalised (mean subtraction, max set to 1), then the query was cut from it. The level-matched clip path `clip_lm` under `htk_described_4k_pn` becomes the reference; the per-clip `pn` rows are an earlier reference. All diagnostic compute and plain GMM-128 approved (§9). |
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

**Cycle 8 (done, `0c53448..c2e323c`; reviewed in `handoff_response.md` at `5fd6ef0`):**
- Part A fix-ups G1–G6: model-type guard and VTLN metadata; per-utterance α̂ with
  `alpha_ours` / `alpha_thesis`; `ll_decreased`; NaN fills; provenance module with
  `--allow-dirty`; docs; MFCC-TMP retrain, where both hashes repeated. 666 passed,
  4 skipped.
- W1 F0 check: ρ(F0, α̂_thesis) = −0.637 (iteration 0, λ_init, 0–3400 Hz). It passes the
  declared gate and supports D3 (c).
- W2: `run_timit --vtln`, with query clips warped from the clip audio.
- W3 Stage 4 GMM-VTLN results, GMM-64 on v2 (instance p@N / MAP; paired gain in
  brackets):

  | Run | No VTLN | VTLN | Paired gain | Thesis gain |
  |---|---|---|---|---|
  | MFCC 0–4000 Hz | 37.48 / 40.50 | 48.17 / 50.58 | +10.69 / +10.08 | +1.35 / +2.91 |
  | PLP 0–4000 Hz | 38.59 / 39.75 | 45.37 / 48.99 | +6.78 / +9.24 | +1.98 / +2.37 |
  | MFCC-TMP | 39.17 / 41.15 | 44.07 / 47.37 | +4.90 / +6.22 | +2.85 / +4.02 |
  | MFCC 0–3400 Hz (earlier ref.) | 34.58 / 35.73 | 41.65 / 45.21 | +7.07 / +9.47 | +1.35 / +2.91 |

  - The direction matches the thesis in every run. Only MFCC-TMP's gain interval
    contains the thesis gain.
  - `ll_decreased` fired in every run: the fresh-LBG model step is noisy. α̂ still
    changes for 11–20 % of utterances at iteration 4. The 0–4000 Hz runs drift towards
    the male side, with a mean α̂_thesis of 1.02–1.03.
  - The Reviewer's ×2 gain test: MFCC α̂ is level-sensitive (c0 shifts by about +8.8);
    PLP α̂ is not.
  - MFCC-TMP − MFCC is not reproduced against the D5 reference: −4.09 p@N with VTLN,
    +1.70 without.

**Decisions adopted from `5fd6ef0` and the user (2026-11-18, D6):**
- **D6 (a), author fact:** the thesis's HTK pipeline **removed the waveform mean and
  scaled the waveform to ±1** before feature extraction. So level normalisation was on.
  Our `htk_described` / `htk_described_4k` have both off; this is a reproduction
  difference.
- **D6 (b), new reference:** a profile `htk_described_4k_pn` (= `htk_described_4k` with
  `remove_dc=True`, `normalize_peak=True`) becomes the MFCC/PLP reference, whatever it
  scores. The band stays 0–4000 Hz (D5 is not re-opened). All `htk_described_4k` rows
  become the **un-normalised earlier reference**. With this, MFCC-TMP (`timit_matlab`,
  peak-normalised, DC removed) and MFCC are matched on level handling.
- **D6 (c), compute approved:**
  - the score-free checks;
  - the 2×2 gain split, optional cells included;
  - plain GMM-64 and GMM-VTLN for MFCC and PLP under `htk_described_4k_pn` (about 2 h,
    6 GB of warp caches).

  The Q3 (b) "level run only if c0 drives α̂" condition is superseded: the author fact
  makes the normalised run the reference.
- Q1: add the column "thesis gain inside our interval" and the baseline sentence. Q2: the
  2×2 split, declared first. Q3: report the level finding as MFCC-only, with the c0
  arithmetic, and run the c0-marginalised α̂ re-estimation. Area-normalised warping is
  not adopted.
- Q4: report the mean α̂ per iteration and an edge caveat per row; the grid is unchanged.
  Q5: new wording, plus `selection_step_ok`. Q6: doc notes, plus within-gender F0
  correlations on the final α̂. Q7: "not reproduced" wording and a heading rename.
  Q8: small fixes.

**Cycle 9 (done, `a1d582b..9785a28`; reviewed in `handoff_response.md` at `fa101e0`):**
- K1–K5: `selection_step_ok`, the small fixes, the `--vtln-cell` options with entropy,
  the profile `htk_described_4k_pn`, and docs.
- S1, score-free checks:
  - the S1 (c) order gate passed;
  - dropping static c0 changes α̂ for 12–14 % of utterances (MFCC) and 6.4 % (PLP). The
    mean and the histogram are unchanged, and no null has been measured yet;
  - α̂ correlates negatively with F0, overall and within each F0 group.
- S2, gain split of the un-normalised rows (instance, paired against no VTLN):
  - MFCC: model only +1.98 / +1.42 (includes 0); selection only +3.77 / +4.07; both
    +10.69 / +10.08;
  - PLP: selection only cannot be told apart from the full row (VTLN − selection only is
    +1.26, interval includes 0);
  - `query_inherit` − VTLN: PLP +1.98 / +1.87 (excludes 0); MFCC includes 0.
- S3, normalised reference `htk_described_4k_pn` (GMM-64, instance p@N / MAP):

  | Feature | No VTLN | VTLN | Paired gain | Thesis gain |
  |---|---|---|---|---|
  | MFCC | 37.04 / 38.75 | 45.10 / 48.10 | +8.07 / +9.35 | +1.35 / +2.91 |
  | PLP | 36.88 / 37.83 | 45.85 / 49.03 | +8.97 / +11.20 | +1.98 / +2.37 |

  - α̂ is now gain-invariant, but the VTLN gain is still above the thesis's on every
    metric.
  - The 1.12 edge share is unchanged.
  - Every thesis row lies inside our marginal intervals; only the paired gain separates
    us from the thesis.
  - MFCC-TMP − MFCC with level handling matched:
    - with VTLN: −1.03 / −0.73;
    - without VTLN: +2.14 / +2.40 (both intervals include 0).
- **Found in review:**
  - under `pn`, each query clip is normalised on its own, which makes clips louder than
    their source utterance (median ratio 1.44, p90 2.70);
  - the HF TIMIT copy has no speaker field, and its rows are shuffled.

**Decisions adopted from `fa101e0` and the user (2026-11-21, D7):**
- **D7 (a), author fact, query level:** the thesis's pipeline normalised the **whole
  utterance** (mean subtraction, max set to 1) and then cut the query from it. So under
  `pn` our per-clip normalisation does not match the thesis.
- **D7 (b), new reference query path:** the **level-matched clip** (`clip_lm`) becomes
  the reference query path under `htk_described_4k_pn`:
  1. take the utterance waveform after the utterance-level normalisation, exactly as the
     documents get it;
  2. cut the clip from it at the usual word boundaries;
  3. extract its features with `remove_dc=False` and `normalize_peak=False`.

  It keeps clip-mode edges and deltas, and query α̂ under VTLN is estimated as usual. The
  per-clip `pn` rows from S3 become the **per-clip earlier reference**. Documents and
  models are unchanged.
- **D7 (c), compute approved, all:**
  - the c0 null control (score-free);
  - the level-matched evaluations;
  - then plain GMM-128 for MFCC and PLP under the reference.
- **Speaker IDs (Q2):** not pursued. The user has no LDC copy (D1), and the HF copy has
  no speaker field.
- Q1: post hoc paired table, with no "mostly" and no ratios or sum column; `query_inherit`
  given as a paired difference. Q2: churn null and drop-c_k control; F0 wording without
  "speaker" or "gender"; partial ρ is not evidence of the level mechanism.
- Q3: "does not bring our gain to the thesis's", plus the two-changes caveat. Q5:
  qualified "not reproduced". Q6: the edge LL-margin check (zero compute), no grid change.
  Q7: relabel the thesis rows, add the K1 note, and add the process note below.
- **Process rule (Q7):** a report commit (`exec: evaluate ...`, `exec: run ...`) touches
  docs only. Code and test changes go in their own commits.

---

## 8. Cycle 10, part A: level-matched query path, post hoc tables, doc fixes (`fa101e0`)

**No task in cycle 10 edits a file in `FEATURE_SOURCE_FILES`.** The level-matched path
lives in `eval/` and calls the existing `scale_waveform` and `remove_dc_offset`
read-only. If a digest edit turns out to be needed, STOP and report.

**Process rule (Q7):** report commits touch docs only. Code and test changes go in their
own commits.

### M1: Query mode `clip_lm` (D7 b)
- In `eval/query_features.py`, add `clip_lm` to `MODES`. In `eval/run_timit.py`, add
  `--query-features clip_lm`. The VTLN path is `clip_warp_features` in
  `eval/vtln_eval.py`.
- **For each query:**
  1. Normalise the **source utterance** as the document path does under the active
     profile: `scale_waveform(x, normalize_peak=True, pcm_scale=1.0)`, then
     `remove_dc_offset` on the whole utterance. This is the same order as the document
     path; the ×32768 is applied once, later.
  2. Cut the clip with `cut_clip` at the usual boundaries.
  3. Extract features, plain or warped, with the profile config changed to
     `remove_dc=False` and `normalize_peak=False`.
- `clip_lm` is defined only for profiles that normalise (`remove_dc` and
  `normalize_peak` both true): `htk_described_4k_pn` and `timit_matlab` MFCC / MFCC-TMP.
  It raises on any other profile.
- The query mode goes into `summary.json`.
- **Tests:**
  - **identity:** a `clip_lm` "clip" spanning the whole utterance gives the document
    features of that utterance to float tolerance, plain and warped;
  - **gain invariance:** a `clip_lm` clip is invariant to a waveform gain on the source
    utterance (×0.5, ×2);
  - **level matching:** `clip_lm` and `clip` differ by exactly the per-query ratio
    `max|clip − m_clip| / max|x|`, up to the DC term;
  - **guard:** a profile without normalisation raises.
- **Commit:** `exec: add level matched clip query mode`

### M2: Post hoc paired tables (Q1)
- Write a small script (`scripts/` or `eval/`) that runs `paired_keyword_bootstrap`
  (10000 resamples, seed 0) on the existing `per_query.tsv` files. For the un-normalised
  and `pn` rows, MFCC and PLP, it computes:
  - VTLN row − selection only;
  - VTLN row − model only;
  - `query_inherit` − VTLN row (un-normalised only).
- Also give the per-query ratio table for `clip` against `clip_lm` levels (Reviewer:
  median 1.44, p90 2.70), recomputed by the script.
- **Commit:** `exec: add post hoc paired comparison script`

### M3: Docs (Q1, Q2, Q3, Q5, Q6, Q7)
- **Q1:**
  - add the M2 table, labelled **"post hoc, computed after the run, not declared"**,
    with the commit and script cited;
  - for each feature, state which comparisons exclude 0, with no "mostly" and no
    mechanism;
  - drop the ratios and the "Model + selection" sum column;
  - `query_inherit` becomes a paired difference ("for PLP, using each clip's own α̂
    instead of its source utterance's α̂ gives a lower score by about 2 points (post
    hoc)"), with a note that it is an analysis cell, not a deployable condition.
- **Q2:**
  - wording for now: "dropping static c0 changes α̂ for 12–14 % (MFCC) and 6.4 % (PLP) of
    utterances; the mean and histogram are unchanged; no null has been measured". N1
    replaces this;
  - F0 wording: "α̂ correlates negatively with utterance F0 overall and within each F0
    group (< 165 Hz, ≥ 165 Hz)", with no "speaker" or "gender";
  - the partial-ρ sentence from the review;
  - one line saying the HF copy carries no speaker field.
- **Q3:**
  - "Level normalisation therefore does not bring our VTLN gain to the thesis's", with
    the paired gains, the unchanged edge share, and the Reviewer's real-utterance
    gain-invariance check (100 utterances, seed 1, ×0.5 and ×2, 0 % changed) labelled
    post hoc;
  - the two-changes caveat on every `pn` − un-normalised comparison;
  - the marginal-interval sentence.
- **Q5:** the qualified "not reproduced" wording from the review. The Teager claim stays
  nothing.
- **Q6:** the convergence caveat, linking the query edge shares to "mostly a clip
  property".
- **Q7:**
  - relabel the D6 thesis rows as "thesis (`Tab:TIMITPerformance` /
    `Tab:TIMITVTLNPerformance1`)";
  - add the K1 sentence: "`selection_step_ok` holds by construction; it is a bug guard,
    not an empirical finding";
  - relabel the S3 per-clip `pn` rows "per-clip, earlier reference (D7)".
- **Commit:** `exec: document cycle 9 review findings`

---

## 9. Cycle 10, part B: c0 null, level-matched reference, GMM-128 (D7)

Runs go one at a time, from a clean tree, with no commits while they run. Every summary
records `git_commit_start` and `git_dirty: false`.

### N1: c0 null and edge margins. Declared first; score-free
- **Declare**, commit `exec: declare c0 null control`:
  - **churn null:** the share of train utterances whose all-dimensions α̂ under λ_r
    differs from the iteration-4 trace α̂. Do this for the 4 un-normalised runs and the 2
    `pn` runs;
  - **dimension control:** MFCC 4k un-normalised; drop each static c_k, k = 1…12, in
    turn, as S1 (a) dropped c0. Report each changed share and where c0's share ranks
    among the 13;
  - **edge margins:** from `iter4_ll_matrix.npy`, for train utterances at α̂ = 1.12
    (thesis label), the distribution of LL(1.12) − LL(1.10) (median, p10, p90). Do the
    same at the 0.88 edge with LL(0.88) − LL(0.90). Cover all VTLN runs;
  - **reading rule, fixed now:** c0 is "distinct from refit churn" only if its share is
    above both the churn null and the largest c_k share. Otherwise the doc says "of the
    same size as churn / other dimensions". For the edges, the doc reports the margins
    and does not label them.
- **Run** (about 20 min). **Commit:** `exec: run c0 null control`, with docs only.

### N2: Level-matched reference evaluations. Declared first; eval only
- **Declare**, commit `exec: declare level matched reference runs`:
  - **rows**, all `--query-features clip_lm` with the existing models:
    1. `pn` MFCC: no VTLN, VTLN, model only, selection only;
    2. `pn` PLP: the same four;
    3. MFCC-TMP `timit_matlab`: no VTLN and VTLN. This is applied for consistency; the
       author fact was stated for the HTK pipeline.
  - **the reference:** `pn` + `clip_lm` is the MFCC/PLP reference whatever it scores
    (D7 b);
  - **comparisons**, all paired on the same 145 queries with keyword-cluster bootstrap,
    10000 resamples, seed 0:
    - `clip_lm` − `clip`, per row. This is a single change: only the query level differs;
    - VTLN − no VTLN under `clip_lm`, against the thesis gain, with the "thesis gain
      inside our interval" column;
    - the 2×2 cells minus no VTLN;
    - MFCC-TMP − MFCC and PLP − MFCC, under `clip_lm`;
  - **query edge shares** for every VTLN row. No mechanism is claimed.
- **Run:** 10 evaluations, about 1 h.
- **Report:** in `docs/results_timit_q20_features.md`, a new section "Level-matched
  reference (D7)", kept separate from the D6 tables, with the gap to the thesis.
- **Commit:** `exec: evaluate level matched reference on v2`, with docs only.

### N3: Plain GMM-128 under the reference. Declared first
- **Declare**, commit `exec: declare gmm128 normalised runs`:
  - **runs:** MFCC and PLP `htk_described_4k_pn`, plain GMM-128 on the v2 train split,
    with the same recipe as H2/H3;
  - **evaluation:** with `clip_lm` (reference) and `clip` (continuity);
  - **target:** `Tab:TIMITPerformance` GMM-128 rows;
  - **comparisons:** paired GMM-128 − GMM-64 (`clip_lm`), and PLP − MFCC. No VTLN at
    GMM-128.
- **Report:** extend the D7 section with the Stage 3 GMM-128 rows.
- **Commit:** `exec: evaluate gmm128 normalised reference on v2`, with docs only.

**Cycle 10 definition of done:**
- M1–M3, N1, N2 and N3 are on `main` in that order. Each declaration comes before its
  run.
- STOP gates:
  - a failing M1 identity test (it would mean `clip_lm` does not reproduce the document
    path);
  - a failing `selection_step_ok`;
  - any needed digest edit.
- `pixi run test` is green. Modules stay under 400 lines and lines under 80 characters.
  No derived data is committed. Report commits touch docs only.
- No commit was made while a run was going.
- The Reviewer writes `handoff_request.md` for cycle 10 with the questions below.

**Open questions for the cycle 10 review:**
- 43: Is c0's share of α̂ changes distinct from refit churn and from the other cepstral
  dimensions? What do the edge LL margins say about the 1.12 pile-up?
- 44: Does the level-matched query path change the scores (`clip_lm` − `clip`)? Is the
  reference VTLN gain still above the thesis's?
- 45: Under the reference, how do the GMM-128 rows compare with the thesis's
  `Tab:TIMITPerformance`?
- 46: Should MFCC-TMP keep `clip_lm` as its reference query path, given that the author
  fact was stated for the HTK pipeline?

---

## 10. Next cycles (preview)

1. LC1 and LC3 (§3 has their TIMIT targets), Q-84, and the optional SAD ablation.
2. Mixture of GMMs (§3 targets), then DTW and fastDTW, then indexing (STM, BoAW).
3. SWS 2013 and QUESST 2014: path selection with 7 paths, z-norm, MTWV and Cnxe. The
   QUESST data is extracted under `research_code_qbe_std/hquest/data/quesst14Database`:
   12492 search files, 560 dev and 555 eval queries, and the scoring folder.
