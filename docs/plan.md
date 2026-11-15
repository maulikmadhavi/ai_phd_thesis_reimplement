# Execution Plan: QbE-STD Thesis Reimplementation

- **Cycle:** 3 (Orchestrator)
- **Handoff input:** `handoff_response.md` at `bc8279a` (Codex review of cycles 2 and 2b, Q1–Q20)
- **Stage status:** Stages 0–2 are done, and TIMIT word alignment (D1) is done. 178+ tests green.
- **This cycle:** Codex's requested fix-ups C1–C9, then Stage 3 (LBG codebook and diagonal GMM by EM)
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
| 2 | Features: mel/Bark scales, VTLN frequency warping, mel filterbank, MFCC + Δ/ΔΔ, PLP, MFCC-TMP | done; fix-ups in §8 | ExpSetup §Acoustic Representation; Warped_Feature appendix |
| 3 | ML: LBG VQ codebook → diagonal GMM by EM, log-likelihood | **this cycle** (§9) | ExpSetup §Posterior Representation; `Backmatter/Algorithm_LC` |
| 4 | Posteriorgrams: Gaussian, iterative GMM-VTLN, mixture of GMMs | | Representation §GMM-based VTLN; §Mixture of GMMs |
| 5 | Matching: symmetric KL, subDTW LC1/2/3 (S/T/P), path selection, z-norm; DTW, fastDTW, partial matching | | ExpSetup §Searching, §Detection; Matching §Partial Matching |
| 6 | Indexing: **STM** phone segmentation → posterior averaging; segment-level BoAW tf-idf | | Matching §Feature Reduction (STM, lines 287–339), §BoAW |
| 7 | Evaluation: p@N, MAP, recall, TWV/MTWV, C<sub>nxe</sub><sup>min</sup>, DET; TIMIT Q-20/Q-84 manifests | | survey §Metrics; Appendix θ, β |

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

**First milestone:** MFCC, then a 64-component Gaussian posteriorgram, then subDTW-LC2, landing
near p@N ≈ 35 / MAP ≈ 37 on TIMIT Q-20. The numbers are only comparable if the TIMIT copy
matches (see §4, D1).

---

## 4. Open questions and decisions

| # | Question | Status after cycle 2 |
|---|---|---|
| 13 | Pre-emphasis, window, FFT size, c0, lifter | **Resolved for defaults:** 0.97, Hamming, nextpow2, c0 kept. Lifter configurable (0 / 20 / 22). |
| 14 | TIMIT at 8 kHz or 16 kHz? | **Data resolved:** all 6300 HF rows are 16 kHz. Whether the thesis HTK pipeline resampled is unknown. Use the `timit_matlab` profile (C2): MFCC and MFCC-TMP at (16 kHz, 4 kHz), PLP at (16 kHz, 8 kHz). Generic defaults are unchanged. |
| 15 | Q-84 list | **Unknown.** Derive it deterministically in Stage 7 from the official split and normalized transcripts, compare the count to 84, and commit the list as an artifact. |
| 16 | Phone segmentation for Stage 6 | **Resolved:** STM (`stm_computation.m`, Matching.tex lines 287–339). |
| D1 | **User decision:** is a licensed LDC TIMIT copy with `.WRD` files available? | **Resolved 2026-11-14:** no LDC copy. The user chose the forced aligner [`Scicom-intl/Where-Words-Begin-and-End-Whisper-Large-V3`](https://huggingface.co/Scicom-intl/Where-Words-Begin-and-End-Whisper-Large-V3) to produce the word boundaries on the HF copy. This replaces the Reviewer's MFA proposal in `handoff_request.md` Q14. Results are labelled approximate against the thesis. Done in cycle 2b (§7). |

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
- subDTW init equations mix up i and j. Follow the algorithm boxes and `research_code_qbe_std/matlab/Fx_do_SDTW.m`.
- MFCC-TMP DCT formula indexes `k = 1..N_c` (no c0), but the MATLAB code keeps c0. Make it `include_c0`, defaulting to True per MATLAB.

## 6. Risks

- TEO can be ≤ 0, so log of the subband TEO sum needs a floor. Log every floor hit in tests, and never let `-inf` or `nan` reach later stages.
- `Fx_melfiltbank.m` and `vteo.m` are missing from the public MATLAB repo. Our triangular filterbank follows HTK and the shape of `Fx_PLPCC_htk.m`, so expect small numeric differences.
- Never commit data or audio. Never extract tarballs into the repo.

---

## 7. Done in earlier cycles (details are in git history and `handoff_request.md`)

- **Cycle 1:** Stage 0 and Stage 1 (T0.1–T1.11).
- **Cycle 2:** Stage 1 fix-ups F1–F7 and Stage 2 features T2.1–T2.11 (`11862f2..a0c46c4`).
- **Cycle 2b:** TIMIT word alignment A1–A5 (`9498174..4d6f1af`).
  - 6300/6300 rows aligned, every row confirmed 16 kHz.
  - Manifests are local in `outputs/alignment/`, documented in `docs/alignment_notes.md`.
- Codex reviewed all of this in `handoff_response.md` at `bc8279a` (Q1–Q20). Its requested
  changes are Part A below.

---

## 8. Cycle 3, part A: fix-ups (Codex "change requested", `bc8279a`)

Conventions:
- One commit per task, `exec: …`, 10 words or fewer, no trailers. Push after every commit.
- Tests for every changed function; every file under 400 lines.

### C1: VTLN warp anchored at the band edge (Codex Q3)
- **Files:** `features/scales.py`, `features/filterbank.py`, tests
- **Do:**
  - Give `warp_frequency_piecewise` / `vtln_cutoff_frequency` an explicit `upper_hz`
    anchor, replacing the hard-wired `sample_rate / 2`.
  - `mel_filterbank` passes `upper_hz = high_hz` when `high_hz < fs/2`, otherwise `fs/2`.
    The cutoff is `0.875 · upper_hz`, which gives 3500 Hz for a 4 kHz band (thesis
    `Warped_Feature.tex` line 30).
  - Full-band PLP keeps `fs/2`.
  - Document it as thesis-based, not proven MATLAB parity, because `Fx_melfiltbank.m` is
    missing.
- **Tests:** 16 kHz audio, `high_hz=4000`, α ∈ {0.88, 1.12}:
  - `upper_hz` maps to itself;
  - every filter's nonzero support stays at or below 4 kHz;
  - α = 1 is unchanged from before;
  - the full-band case is unchanged.
- **Commit:** `exec: anchor vtln warp at feature band edge`

### C2: Named feature profiles (Codex Q7, Q12)
- **Files:** `src/qbestd/features/profiles.py`, `features/plp.py` (DC-removal switch if
  missing), tests
- **Do:** add `get_profile(name, kind) -> config` without changing the generic defaults.
  - `"timit_matlab"`:
    - MFCC and MFCC-TMP use 16 kHz with `high_hz=4000`;
    - PLP uses 16 kHz with `high_hz=8000`, `lpc_order=8`, no DC removal, `x·32768` scaling
      (`Fx_PLPCC_htk.m` lines 30–39, 35, 69).
  - `"htk_like"`: PLP `lpc_order=12`, DC removal on.
  - An unknown name or kind raises `ValueError`. Each profile's docstring cites its sources
    and says that **no profile is thesis-verified**.
- **Tests:** profile values; generic defaults unchanged; unknown name raises; each profile
  extracts finite features from 1 s of noise.
- **Commit:** `exec: add named feature profiles`

### C3: `warp_factor=None` in `extract_features` (Codex Q9)
- **Files:** `features/extract.py`, tests
- **Do:** default `warp_factor=None`, meaning use `config.warp_factor`. An explicit value
  overrides the config.
- **Tests:** both paths. Caching across the 13 warps is deferred until Stage 4 profiling.
- **Commit:** `exec: let config warp factor apply by default`

### C4: Parity doc corrections (Codex Q6, Q7, Q10, Q13)
- **Files:** `docs/feature_parity.md`
- **Do:** re-read `Chapters/ExpSetup.tex` lines 191–223 and fill the thesis column **per
  feature**:
  - MFCC: 26 filters, 0–4 kHz, 13 coefficients, HTK.
  - PLP: no filter count, band, c0 or delta setting is stated.
  - MFCC-TMP: 25/10 ms, 26 filters, 13 + Δ + ΔΔ, `k=1..13`, band not stated in that passage.
  - Label the thesis's "Type III DCT" wording separately from our orthonormal DCT-II
    ("convention not checked").
  - Record these as parity differences or assumptions:
    - forward-warped equal-loudness centres (MATLAB-faithful);
    - `max|x|` versus `max(x)` peak normalisation;
    - unit-peak triangles.
  - Mark HTK cells written from memory as "unverified".
- **Commit:** `exec: correct thesis claims in feature parity doc`

### C5: Test and style cleanup (Codex Q11, Reviewer minor notes)
- **Files:** `tests/features/test_mfcc_tmp.py`, plus the 14 files with lines over 79
  characters
- **Do:**
  - Make the floor-hit test assert `floor_hits < energies.size` on seeded noise, and keep
    printing the count.
  - Wrap the 37 lines over 79 characters.
  - No behaviour change.
- **Commit:** `exec: tighten floor hit test and wrap long lines`

### C6: Manifest checks (Codex Q14, Q20)
- **Files:** `alignment/manifest.py`, tests
- **Do:**
  - In `check_segments`, add a distinct `collapsed_run` warning for equal consecutive
    starts.
  - Reject or flag non-finite start/end values.
  - Keep the existing rules.
- **Tests:** two words over 20 ms with an equal start are flagged `collapsed_run`; `nan` and
  `inf` are flagged.
- **Re-run the checks** over the existing local manifests (no re-alignment). Add the
  collapsed-run counts and rows to `docs/alignment_notes.md`.
- **Commit:** `exec: flag collapsed runs and non-finite times`

### C7: One outcome per row (Codex Q20)
- **Files:** `alignment/word_aligner.py`, tests
- **Do:** raise if `len(align_batch(...)) != len(batch)` before the `zip`.
- **Tests:** a fake aligner that returns too few outcomes raises.
- **Commit:** `exec: check aligner returns one outcome per row`

### C8: NFC transcript normalisation and token audit (Codex Q15)
- **Files:** `data/timit_hf.py`, tests, `docs/alignment_notes.md`
- **Do:**
  - Apply `unicodedata.normalize("NFC", …)` before lowercasing.
  - Audit both splits for tokens with hyphens, apostrophes or non-ASCII characters. List the
    distinct tokens and counts in the notes.
  - Re-normalise every sentence and compare with the tokens in the manifests.
    - **If identical** (expected for ASCII TIMIT), no re-alignment is needed. Say so in the
      notes.
    - **If not**, stop and report it in the review. Do not silently re-run.
- **Tests:** composed and decomposed `é` give the same tokens.
- **Commit:** `exec: nfc normalise transcripts and audit tokens`

### C9: Alignment caveats and optional ASR audit (Codex Q17, Q18, Q19)
- **Files:** `docs/alignment_notes.md`, `src/qbestd/alignment/asr_audit.py` (align env),
  tests for its pure functions (word filter, shift, hit scoring)
- **Do:**
  - **Notes:** the model card's 10.7 ms was measured on the card's own TIMIT test setup.
    It is **not** a measured error for these manifests.
  - **Notes:** speaker overlap between the HF query/train and document/test sets is
    unverified, and it may inflate both the alignment quality and later QbE scores.
  - **Notes:** record environment lock, precision and per-split quantiles next to the hashes.
  - **Audit:** `python -m qbestd.alignment.asr_audit`, an optional, reproducible check:
    - `openai/whisper-base` at a pinned revision;
    - fixed seed, words of at least 3 letters, 300 words;
    - true cuts and ±0.25 s shifted cuts, 20 ms padding;
    - hit means an exact match or difflib ratio ≥ 0.75;
    - writes `outputs/alignment/asr_audit.json`.
  - The audit is a **diagnostic, not a gate**. Record its numbers in the notes.
- **Commit:** `exec: add asr alignment audit and caveats`

---

## 9. Cycle 3, part B: Stage 3 (LBG codebook and diagonal GMM)

**Thesis facts** (cite these in docstrings):
- **Posterior:** `P(C_k|o_t) = π_k N(o_t; μ_k, Σ_k) / Σ_j π_j N(o_t; μ_j, Σ_j)`
  (`ExpSetup.tex` lines 229–237).
- **Estimation:** EM, initialised from an LBG VQ codebook (line 238).
- **LBG** (`Algorithm_LC.tex`, Fig. VQ):
  - K-means VQ with splitting constant **ε = 0.2**;
  - each split uses the per-dimension mean μ and std σ ("data uncorrelated assumption");
  - so a centroid splits into μ ± ε·σ, where σ is the std of that cluster's members;
  - the codebook doubles until `N_clust`.
- **EM:** **10 iterations** (`Representation.tex` lines 196 and 1089).
- **Mixtures:** 64 and 128 for TIMIT (line 335). 128 is the main setting from Chapter 4 on.
- **Training set:** the thesis used 3696 TIMIT training utterances (line 174), which is the
  official train set without SA. Our equivalent is the HF train split minus the two SA texts.
- **Assumptions** (thesis silent; keep configurable, document as assumptions):
  - diagonal covariances;
  - variance floor at `0.01 ×` the global per-dimension variance (HTK `vFloor` style);
  - k-means refinement inside LBG stops at a relative distortion change < 1e-3 or after 20
    iterations;
  - an empty cluster is re-seeded by splitting the cluster with the highest distortion.

### T3.1: LBG vector quantiser
- **Files:** `src/qbestd/ml/__init__.py`, `src/qbestd/ml/vq.py`, tests
- **API:**
  - `lbg_codebook(features, n_clusters, epsilon=0.2, max_kmeans_iter=20, tol=1e-3, seed=0)
    -> (codebook, assignments, distortion_history)`;
  - `assign_to_codebook(features, codebook)`, chunked so memory stays bounded.
- `n_clusters` must be a power of two; otherwise raise.
- **Tests:**
  - 4 well-separated 2-D blobs give 4 centroids within 0.1 of the truth;
  - distortion is non-increasing;
  - empty-cluster re-seed path;
  - deterministic under a seed;
  - chunked assignment equals full assignment.
- **Commit:** `exec: add lbg vector quantiser`

### T3.2: Diagonal GMM with EM
- **Files:** `src/qbestd/ml/gmm.py`, tests
- **API:**
  - `DiagonalGmm(weights, means, variances)`, a frozen dataclass with shape validation.
  - `init_gmm_from_codebook(features, codebook, assignments, var_floor)`.
  - `frame_log_likelihoods(gmm, features) -> (T,)`, using log-sum-exp.
  - `component_posteriors(gmm, features) -> (T, K)`, with rows summing to 1.
  - `em_step(gmm, features, var_floor, chunk_frames=100_000)`, accumulating sufficient
    statistics chunk by chunk.
  - `train_gmm(features, n_components, n_iter=10, epsilon=0.2, var_floor_ratio=0.01, seed=0)
    -> (gmm, log_likelihood_history)`.
  - `save_gmm` / `load_gmm`: `.npz` with a metadata JSON string (feature kind, profile,
    dims, n_iter, training row count).
- **Tests:**
  - recovers the means and weights of a synthetic 3-component 2-D mixture;
  - average log-likelihood is non-decreasing over iterations (tolerance 1e-6);
  - posteriors sum to 1 and are finite even for an outlier frame 1e3 σ away;
  - variance floor engages on a constant dimension;
  - chunked EM equals unchunked EM;
  - save/load round-trip.
- **Commit:** `exec: add diagonal gmm trained by em`

### T3.3: Gaussian posteriorgram
- **Files:** `src/qbestd/ml/posteriorgram.py`, tests
- **API:**
  - `gaussian_posteriorgram(gmm, features) -> (T, K)`;
  - `floor_and_renormalise(posteriorgram, floor=1e-10)`, for KL in Stage 5;
  - `utterance_log_likelihood(gmm, features)`, the mean frame log-likelihood (Stage 4 VTLN
    picks α by maximising it).
- **Tests:** shape, row sums, floor effect, the likelihood ranks a matched GMM above a
  mismatched one.
- **Commit:** `exec: add gaussian posteriorgram`

### T3.4: Feature cache for TIMIT
- **Files:** `src/qbestd/data/feature_cache.py`, tests
- **Do:**
  - `is_sa_sentence(tokens)` uses `normalize_transcript` and matches the two SA texts.
  - `build_feature_cache(split, kind, profile, out_dir, exclude_sa=True)`:
    - iterate `iter_timit_rows`, then `extract_features` with `get_profile(...)`, appending
      Δ+ΔΔ to give 39 dims;
    - write one `.npz` with the concatenated `features (float32)`, `offsets` and
      `row_indices`, plus metadata (profile, kind, dataset revision, excluded SA count).
  - `load_feature_cache(path) -> (features, offsets, row_indices, meta)`.
  - The cache lives in `outputs/features/` (git-ignored). Never commit it.
- **Tests:** a two-row synthetic parquet (reuse the A2 fixture) round-trips; SA rows are
  excluded; offsets index correctly.
- **Commit:** `exec: add timit feature cache`

### T3.5: Train the baseline GMM and record it
- **Files:** `src/qbestd/ml/train.py` (CLI: `python -m qbestd.ml.train --kind mfcc --profile
  timit_matlab --components 64 --out outputs/models/`), a pixi task `train-gmm`, tests for
  argument parsing
- **Run:**
  - MFCC with the `timit_matlab` profile, 64 components, then 128;
  - training data is the HF train split without SA.
- **Write `docs/gmm_notes.md`:**
  - row and frame counts;
  - LBG distortion history;
  - EM log-likelihood per iteration (it must rise and flatten by iteration 10, as in thesis
    Fig. `LthetaConverge`);
  - smallest component weight;
  - number of variance-floored dims;
  - wall time;
  - model SHA-256s.
- Models stay in `outputs/models/` (git-ignored).
- **Commit:** `exec: train baseline mfcc gmm and record notes`

### T3.6: Stage 3 Gradio demo
- **Files:** `demo/stage3_gmm_demo.py` (≤ 250 lines); pixi task `demo-stage3` in the `demo`
  feature
- **Inputs:**
  - audio upload or mic;
  - feature kind;
  - a GMM picked from `outputs/models/*.npz`. If none exists, train a small GMM on the
    uploaded clip, with the component count from a slider (4–64).
- **Outputs:**
  - posteriorgram heatmap (frames × components);
  - top-component track;
  - EM log-likelihood curve when it trained one;
  - per-frame log-likelihood plot.
- Put a usage note at the top. Import from `qbestd` only.
- **Commit:** `exec: add stage 3 gmm demo`

**Cycle 3 definition of done:**
- C1–C9 and T3.1–T3.6 are on `main`, and `pixi run test` is green in the core env.
- Every module is under 400 lines.
- `docs/gmm_notes.md` shows a rising EM curve for MFCC GMM-64 and GMM-128.
- The Reviewer writes `handoff_request.md` for cycle 3. It should cover:
  - the open questions below;
  - whether the C8 audit changed any tokens;
  - the C9 audit numbers.

**Open questions for the Cycle 3 review:**
- 17: Variance floor and the k-means stopping rule are assumptions. Is there any MATLAB or HTK
  evidence (`HCompV`/`HERest` `-v`) for what the thesis used?
- 18: SAD. The thesis SAD uses BUT phone posteriors (`ExpSetup.tex` lines 242–243), which we
  don't have. Should TIMIT GMM training and search drop leading and trailing silence? If so,
  how: energy-based, or by trimming to the aligner's first and last word?
- 19: Should the GMM train on static+Δ+ΔΔ (39 dims), as we plan, or on the 13 statics?

---

## 10. Next cycle (preview)

The goal is to get the **first comparable number** before broadening any stage:
1. Q-20 query list from thesis Table `Table:TIMITdata`, cut from the train split with the
   alignment manifests (20 ms padding, collapsed-run segments excluded).
2. Symmetric-KL local distance and subDTW-LC2, from `Fx_do_SDTW.m` and the algorithm boxes,
   with the §5 errata fixed.
3. Score normalisation, p@N and MAP, tested on the §2 metric test case.
4. A run on MFCC GMM-64 against the target p@N ≈ 34.91 and MAP ≈ 36.71 (labelled
   approximate).

After that, PLP, MFCC-TMP, GMM-128, VTLN (Stage 4), mixture of GMMs, then LC1/LC3, DTW,
fastDTW and indexing.
