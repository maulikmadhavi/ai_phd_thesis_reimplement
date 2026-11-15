# Execution Plan: QbE-STD Thesis Reimplementation

- **Cycle:** 5 (Orchestrator)
- **Handoff input:** `handoff_response.md` at `a8e2b02` (Codex review of cycle 4, Q1–Q9)
- **Stage status:** Stages 0–3, TIMIT word alignment and the first TIMIT Q-20 number (LC2,
  p@N/MAP) are done. 457 tests green at `e63e723`.
- **This cycle:** thesis endpoint rule, provenance guards and keyword-cluster statistics
  (part A), then a text-disjoint split that reproduces the thesis query/document counts
  (part B)
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
| 2 | Features: mel/Bark scales, VTLN frequency warping, mel filterbank, MFCC + Δ/ΔΔ, PLP, MFCC-TMP | done; source digest in §8 A2 | ExpSetup §Acoustic Representation; Warped_Feature appendix |
| 3 | ML: LBG VQ codebook → diagonal GMM by EM, log-likelihood | done; split guard in §8 A3 | ExpSetup §Posterior Representation; `Backmatter/Algorithm_LC` |
| 4 | Posteriorgrams: Gaussian, iterative GMM-VTLN, mixture of GMMs | Gaussian done | Representation §GMM-based VTLN; §Mixture of GMMs |
| 5 | Matching: symmetric KL, subDTW LC1/2/3 (S/T/P), path selection, z-norm; DTW, fastDTW, partial matching | KL, LC2, z-norm done; **this cycle:** endpoint rule (§8 A1) | ExpSetup §Searching, §Detection; Matching §Partial Matching |
| 6 | Indexing: **STM** phone segmentation → posterior averaging; segment-level BoAW tf-idf | | Matching §Feature Reduction (STM, lines 287–339), §BoAW |
| 7 | Evaluation: p@N, MAP, recall, TWV/MTWV, C<sub>nxe</sub><sup>min</sup>, DET; TIMIT Q-20/Q-84 manifests | Q-20, p@N, MAP done; **this cycle:** cluster bootstrap, text-disjoint split (§8–§9) | survey §Metrics; Appendix θ, β |

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
comparable, until the split matches (§9).

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
| 22 | Query features from clip or slice? | Clip stays primary; slice is a sensitivity run (§9 B4). |
| 23 | Path validity measure? | **Resolved** (Codex Q5): `wr = (i − P(i,N))/N` in test frames; min `S/T` over valid endpoints (§8 A1). |

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
    GMM-64 p@N 36.89 / MAP 41.20, GMM-128 39.58 / 44.23. These become **HF v1** in §8 A6.
  - Reviewer finding: 42 of 52 relevant documents share their sentence text with a train
    query source. The official split never allows that.

**Decisions adopted from `a8e2b02`:**
- The HF split numbers are a useful baseline but **not** a thesis-parity claim. Keep them,
  labelled; never replace them.
- Text overlap: option (a), a separately named text-disjoint split (§9).
- Endpoint rule from `ExpSetup.tex` lines 442–469; no silent fallback (§8 A1).
- Provenance: source digest in the feature fingerprint, `split_id`, and a model guard in
  the runner (§8 A2–A3).
- Uncertainty: bootstrap over keywords, paired for model comparisons (§8 A5).
- GMM-128 target 36.81 / 38.34 (§3).

---

## 8. Cycle 5, part A: scorer, provenance and statistics (Codex `a8e2b02` Q5–Q8)

**Order matters.** Land A1–A4 before any new scoring. A5 re-runs the HF baseline under the new
scorer, so that the later HF-vs-text-disjoint comparison changes only the split. The cycle 4
numbers stay in the results doc, labelled **v1 (cycle 4 scorer)**.

### A1: Thesis endpoint rule, no silent fallback (Codex Q5)
- **Files:** `src/qbestd/search/subdtw.py`, `src/qbestd/search/score.py`,
  `src/qbestd/eval/run_timit.py`, `demo/stage5_search_demo.py`, tests
- **Thesis:** `ExpSetup.tex` lines 442–448 give `dist(i) = S(i,N)/T(i,N)` and
  `wr(i) = (i − P(i,N))/N`, valid when `0.5 ≤ wr ≤ 2`. Lines 467–469 take the minimum `dist`
  over valid endpoints. Validity is the test-frame displacement from `P`; `T` only normalises.
- **Do:**
  - Zero-based: `end` is the test frame index and `P[end]` the start frame, so
    `wr = (end − P[end]) / N`. The `+1` goes away.
  - Keep the minimum of `S/T` over **valid** endpoints. Under LC2 every endpoint has `T = N`,
    so this equals `argmin S` over the same candidate set (the C++ shortcut).
  - Remove `used_fallback`. When no endpoint is valid (for example a document shorter than
    about N/2 frames), return `dist = +inf` with `start = end = -1` and a `nonmatch=True`
    flag. **Never raise per document**: one short document must not stop a run.
  - `rank_documents`: `+inf` ranks last, ties keep document order (stable sort).
  - `znorm_scores`: compute μ and σ over **finite** distances only. A `+inf` distance gets
    score `-inf`. Raise only if fewer than 2 finite values remain.
  - `run_timit`: replace the `fallbacks` columns and keys with `nonmatches`
    (`per_query.tsv` and `summary.json` → `total_nonmatches`). Update the demo the same way.
- **Tests:**
  - `wr` exactly 0.5 and exactly 2.0 are valid; one frame either side is invalid;
  - an all-invalid `S` gives `+inf`, `nonmatch=True`;
  - ranking with `+inf` values, and stable ties;
  - `znorm_scores` with `+inf` present gives no `nan`.
- **Commit:** `exec: apply thesis endpoint rule and mark nonmatches`

### A2: Source digest in the feature fingerprint (Codex Q6)
- **Files:** `src/qbestd/data/feature_cache.py`, tests
- **Do:**
  - Add `FEATURE_SOURCE_FILES`: an explicit, sorted tuple of the modules that compute
    features. Start from the transitive `qbestd.audio.*` / `qbestd.features.*` imports of
    `qbestd.features.extract`, and list each file by name. Do **not** hash the whole package:
    a doc or test edit must not invalidate the caches.
  - `feature_source_digest()`: sha256 over, for each file in that order, its relative path,
    then its bytes **with CRLF normalised to LF** (so git autocrlf on Windows does not change
    the digest).
  - Add the digest to `feature_fingerprint(...)`. Keep `FEATURE_CACHE_VERSION`, renamed in
    meaning to the cache **format** schema version (bump only when the file layout changes).
    Add a docstring line saying so.
- **Tests:**
  - changing one listed file's bytes (monkeypatched or tmp copy) changes the fingerprint;
  - CRLF vs LF bytes give the same digest;
  - `FEATURE_SOURCE_FILES` equals the set of `qbestd.audio` / `qbestd.features` modules that
    `qbestd.features.extract` imports transitively (walk `sys.modules` after a fresh import,
    or parse imports with `ast`). This catches a newly imported module that nobody listed.
- **Commit:** `exec: hash feature sources into cache fingerprint`

### A3: Model and split guard in the runner (Codex Q6)
- **Files:** `src/qbestd/ml/train.py`, `src/qbestd/eval/run_timit.py`, tests
- **Do:**
  - **Split identity.** `split_id` is a string recorded everywhere a split matters:
    - the HF baseline is `hf-<first 12 hex of the dataset revision>-nonsa`;
    - a manifest split (part B) is `<name>-<first 12 hex of the manifest file sha256>`.
  - `train-gmm` gets `--split-id` (default: the HF id) and writes `split_id` into the model
    `.json`/metadata next to `kind`, `profile` and `feature_fingerprint`.
  - `run_timit`, before any scoring, raises `ModelMismatchError` when the GMM's `kind`,
    `profile` or `split_id` differs from the request, or when its `feature_fingerprint`
    differs from `feature_fingerprint(kind, profile, exclude_sa=True)` under the current code.
    The fingerprint excludes rows, which is why `split_id` is checked separately.
  - Record `split_id`, the model's fingerprint and the model parameter hash in `summary.json`.
- **Tests:** one mismatch test per field, plus a pass case.
- **Commit:** `exec: reject gmm with mismatched features or split`

### A4: Rebuild caches and retrain HF GMMs (regression check)
- A2 changes the fingerprint, so A3 rejects the cycle 3 models. Rebuild both HF feature
  caches, then retrain MFCC `timit_matlab` GMM-64 and GMM-128 on the HF train side with
  `--split-id` set to the HF id.
- **Check:** the parameter hashes must equal the cycle 3 hashes in `docs/gmm_notes.md`. If they
  differ, stop and report: something in the front end moved.
- Add one line to `docs/gmm_notes.md`: the new fingerprint, the `split_id`, and "parameter
  hashes unchanged".
- **Commit:** `exec: retrain hf gmms under new fingerprint`

### A5: Keyword-cluster bootstrap (Codex Q7)
- **Files:** `src/qbestd/eval/metrics.py` (or a new `src/qbestd/eval/bootstrap.py` if
  `metrics.py` would grow past about 150 lines), tests
- **API:**
  - `cluster_bootstrap(per_query, n_boot=10000, seed=0) -> dict`: resample **keywords** with
    replacement, carrying all of a keyword's instances together. Return 95 % percentile
    intervals for the instance-weighted mean (all instances of the drawn keywords, with
    multiplicity) and the keyword-weighted mean (mean of per-keyword means), for both p@N
    and AP.
  - `paired_keyword_bootstrap(per_query_a, per_query_b, ...)`: the same resampling of
    keywords, applied to per-keyword differences B − A. It requires identical keyword and
    instance sets in A and B.
  - Use `numpy.random.default_rng(seed)` only.
- **Tests:** a hand-made 3-keyword case with known means; identical inputs give a zero
  paired interval; mismatched instance sets raise; fixed seed gives a fixed result.
- **Commit:** `exec: add keyword cluster bootstrap`

### A6: HF baseline v2 and corrected labels (Codex Q1, Q2, Q7, Q8)
- **Run:** `eval-timit` on the HF split with the A4 models, GMM-64 and GMM-128.
- **Rewrite `docs/results_timit_q20.md`:**
  - Section **"HF split, v1 (cycle 4 scorer)"**: keep the cycle 4 numbers as they are, with
    the label *"exploratory: instance bootstrap, `(end−start+1)/N` endpoint, fallback
    scorer"*.
  - Section **"HF split, v2"**: the new numbers. Give keyword-cluster intervals for both
    averages, the paired GMM-128 − GMM-64 interval, the nonmatch count, `split_id`, model
    hashes and the git commit.
  - **Targets** (`Unsupervised.tex` lines 125–134, `Tab:ExpResultTIMIT`, MFCC, GMM, LC2):
    64 Gaussians 34.91 / 36.71, **128 Gaussians 36.81 / 38.34**. Delete the sentence saying
    no 128 target exists. The thesis 128 − 64 gain is +1.90 p@N / +1.63 MAP.
  - **Denominators**, stated explicitly so nobody compares them:
    - query instances: thesis 145, ours 221 on the HF split;
    - thesis Occ. 160 is a **token** count; ours is 52 relevant document-keyword pairs on the
      HF split; relevance is binary per document either way.
  - **Labels on every table:** "sentence-text overlap between queries and documents (HF
    split)" and "speaker overlap present; approximate versus the thesis". **Do not describe
    the HF split as speaker-separated.** The SA counts (488/501) are what a random row split
    would give, so speaker overlap may be large.
  - **Unknowns:** the instance aggregation (each instance as a query is our choice; the
    thesis does not say whether the reported figure averages over instances or keywords),
    and morphological variants in relevance.
- **Commit:** `exec: rerun hf baseline with thesis scorer`

---

## 9. Cycle 5, part B: text-disjoint split (Codex `a8e2b02` Q3, Q4)

**Why.** In the official TIMIT split, SX and SI texts never cross between train and test
(NIST TIMIT documentation; only SA is shared). On the HF split, 42 of 52 relevant documents
share their sentence text with a train query source. Codex chose option (a): a separately
named, text-disjoint split, reported **next to** the HF baseline, never replacing it.

**What the Orchestrator counted** (transcripts only, no scores; scratch script, not
committed). The 5040 non-SA rows of both HF splits form 2362 normalised-text groups:
- 1909 groups read once (SI-like), and 453 read 2–7 times (SX-like: 429 groups of 7, 18 of 6,
  2 of 5, 1 of 4, 3 of 2). The odd sizes are probably SX texts split by transcript variants.
- **Assigning whole groups to one side can reproduce the thesis `Table:TIMITdata` exactly**,
  Inst. and Occ. for all 20 keywords. For example:
  - government, groups 7, 7, 6, 1, 1: test 7 + 1 = 8, train 7 + 6 + 1 = 14 (thesis 14/8);
  - love, groups 7, 7 and six singles: test 7 + 7 + 2 = 16, train 4 (thesis 4/16);
  - beautiful, groups 7 and four singles: test 7 + 1 = 8, train 3 (thesis 3/8).
- The thesis also states 3696 train utterances (`Representation.tex` line 174) and 1344 test
  documents (`Unsupervised.tex` line 74), which is 462 and 168 speakers × 8 non-SA sentences.

So the split rule below uses only transcripts, the thesis count table and the official
quotas. It is **declared before any score is computed on it, and is never redrawn.** Any
change becomes a new name (`..._v2`) with a written reason.

### B1: Split rule and manifest (`textdisjoint_q20_v1`)
- **Files:** `src/qbestd/data/text_split.py`, tests, `docs/split_textdisjoint.md`
- **Rule:**
  1. **Universe:** every non-SA row of both HF splits, keyed by the original
     `(hf_split, row_index)`. Group by `" ".join(normalize_transcript(sentence))`. The group
     hash is `sha256("qbestd-textsplit-v1\n" + text)`. No RNG anywhere.
  2. **Keyword constraints**, keywords in `Q20_KEYWORDS` table order. For keyword k, let
     `G_k` be the groups whose tokens contain k. Groups fixed by an earlier keyword keep
     their side. Enumerate every assignment of the free groups (at most 2⁸). Its cost is
     `|test tokens of k − Occ_k| + |train tokens of k − Inst_k|`, counting tokens in
     transcripts before any aligner flag. Pick the minimum cost; break ties with the
     lexicographically smallest sorted tuple of test-side group hashes. Fix those groups.
  3. **Fill to the official quotas:** the test side holds **120 multi-read groups** and
     **504 single-read groups** in total, counting groups already placed by step 2. Take the
     remaining test groups in ascending hash order within each stratum. Every other group goes
     to train. If step 2 already exceeds a quota, move nothing and report it.
- **API:**
  - `build_text_split(rows, keywords) -> SplitManifest`;
  - `write_split_manifest(path, manifest)` / `read_split_manifest(path)`: a TSV of
    `hf_split, row_index, side, group_hash` with a `# rule=textdisjoint_q20_v1` header. No
    sentence text in the file.
  - `split_id(path)`: `textdisjoint_q20_v1-<first 12 hex of the file sha256>`.
  - Output goes to `outputs/splits/textdisjoint_q20_v1.tsv` (git-ignored, reproducible).
- **Tests:**
  - every group lands entirely on one side, and the train and test text sets are disjoint;
  - shuffling the input row order gives a byte-identical manifest;
  - a synthetic case where the cost-0 assignment exists is found; a tie is broken by hash;
  - a keyword fixed by an earlier keyword is respected;
  - quotas are met on a synthetic universe;
  - a row that moved from HF test to the train side still resolves its word alignment from
    `timit_hf_words_test.tsv` (lookup by `(hf_split, row_index)`, never by a new index).
- **`docs/split_textdisjoint.md`**, committed **before** B3 runs:
  - the rule (copy of the above) and the manifest sha256;
  - row counts per side (expected near 3696 / 1344) and group counts per stratum;
  - per-keyword train tokens and test tokens next to the thesis Inst./Occ., and the step 2
    cost for each (expected 0 for all 20);
  - how many rows moved relative to the HF split;
  - labels: "closer to the thesis on sentence context; not an official TIMIT
    reconstruction; speaker overlap present (amount unknown, likely larger than on the HF
    split, because each speaker's sentences are now spread across both sides)".
- **Commit:** `exec: declare text disjoint split rule and manifest`

### B2: Run the pipeline on a manifest split
- **Files:** `src/qbestd/ml/train.py`, `src/qbestd/eval/timit_queries.py`,
  `src/qbestd/eval/run_timit.py`, tests
- **Do:**
  - Keep the feature caches **per HF split** (they already hold every non-SA row). A
    manifest split is a selection layer over them, keyed by `(hf_split, row_index)`.
  - `train-gmm --split-manifest <tsv>`: train on the manifest's train rows from both caches;
    `split_id` comes from the manifest.
  - `timit_queries`: queries come from train-side rows of either HF split, using that split's
    word manifest. Documents and relevance come from test-side rows. Query and document keys
    become `(hf_split, row_index)` pairs in the TSVs.
  - `run_timit --split-manifest <tsv>`: the A3 guard also checks that the model's `split_id`
    equals the manifest's.
  - Without `--split-manifest`, behaviour stays exactly the HF baseline.
  - Keep `run_timit.py` under 400 lines; move helpers into `eval/` modules if needed.
- **Tests:** the selection layer picks the right rows from two fake caches; queries and
  documents never share a text group; HF behaviour is unchanged without the flag.
- **Commit:** `exec: run gmm training and eval on split manifest`

### B3: Train and evaluate on `textdisjoint_q20_v1`
- Train MFCC `timit_matlab` GMM-64 and GMM-128 on the manifest train side, then run
  `eval-timit`, LC2, clip query features, with the A1 scorer.
- **Add to `docs/results_timit_q20.md`**, section **"Text-disjoint split
  (`textdisjoint_q20_v1`)"**:
  - query instances and relevant pairs per keyword, against the thesis table;
  - p@N/MAP for both averages, keyword-cluster intervals, the paired 128 − 64 interval,
    nonmatches, `split_id`, model hashes;
  - a three-row comparison: thesis, HF v2, text-disjoint. Same labels as A6.
- **Do not tune anything to reach a target**, and do not change the split after seeing the
  scores.
- **Commit:** `exec: evaluate q20 on text disjoint split`

### B4: Query-feature sensitivity, clip vs slice (Codex Q4)
- **Files:** `src/qbestd/eval/run_timit.py` (or a helper module), tests
- **Do:**
  - Add `--query-features clip|slice`; the default and primary result stays `clip`.
  - `slice`: compute features on the whole train utterance, then keep frame `t` when its
    centre `t·shift + win/2` lies in `[start − pad, end + pad]`.
  - Note in the docstring that `slice` changes Δ/ΔΔ edges **and** any utterance-level
    waveform normalisation (DC removal and `max|x|` scaling are per utterance, which shifts
    c0).
  - Record the mode in `summary.json`.
- **Run:** GMM-64 on `textdisjoint_q20_v1`, both modes, same model, alignments and relevance.
- **Add to the results doc** a small table labelled "sensitivity, not a thesis-mandated
  correction".
- **Tests:** the frame-selection rule at both interval edges; `clip` output unchanged.
- **Commit:** `exec: add query feature slicing sensitivity run`

**Cycle 5 definition of done:**
- A1–A6 and B1–B4 are on `main`, in that order (B1's doc commit before B3's scores), and
  `pixi run test` is green in the core env.
- Every module is under 400 lines and every new function has tests.
- `docs/results_timit_q20.md` holds HF v1 (labelled exploratory), HF v2, text-disjoint, and
  the clip/slice sensitivity, with both thesis targets.
- The Reviewer writes `handoff_request.md` for cycle 5 with the questions below.

**Open questions for the cycle 5 review:**
- 24: Is the step 2 tie-break (hash order) acceptable where two group choices both match the
  thesis counts exactly (for example shellfish: test the 7-group, or the 5 + 2 variant
  groups)?
- 25: If the text-disjoint numbers still sit above the thesis, what is the next suspect: the
  speaker overlap, the GMM training set, the 16 kHz features, or the Inst. aggregation?
- 26: Should the HF split be kept as a reported baseline in later stages (PLP, MFCC-TMP,
  VTLN), or should only `textdisjoint_q20_v1` carry forward?

**Not adopted:** option (b) (keep the HF split, drop the overlapping queries). Codex chose (a),
and (b) would not control for speakers either.

---

## 10. Next cycles (preview)

1. **Gap analysis** of the text-disjoint numbers, then PLP and MFCC-TMP on the same pipeline
   (§3 targets).
2. **Stage 4:** iterative GMM-VTLN (5 iterations, 13 warps). Use the `extract_warped_bank`
   caching that Codex deferred to here.
3. LC1 and LC3 (§3 has their TIMIT targets), Q-84, and the optional SAD ablation (Codex Q12).
4. Mixture of GMMs (§3 targets), then DTW and fastDTW, then indexing (STM, BoAW).
5. SWS 2013 and QUESST 2014: path selection with 7 paths, z-norm, MTWV and Cnxe.
