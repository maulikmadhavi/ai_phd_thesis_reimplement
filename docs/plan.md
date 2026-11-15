# Execution Plan: QbE-STD Thesis Reimplementation

- **Cycle:** 4 (Orchestrator)
- **Handoff input:** `handoff_response.md` at `5c5dea8` (Codex review of cycle 3, Q1–Q15)
- **Stage status:** Stages 0–3 and TIMIT word alignment are done. 366 tests green at `c992e9d`.
- **This cycle:** Codex's requested fix-ups E1–E7, then the first end-to-end TIMIT Q-20 number (Stage 5 LC2 + Stage 7 p@N/MAP)
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
| 3 | ML: LBG VQ codebook → diagonal GMM by EM, log-likelihood | done; fix-ups in §8 | ExpSetup §Posterior Representation; `Backmatter/Algorithm_LC` |
| 4 | Posteriorgrams: Gaussian, iterative GMM-VTLN, mixture of GMMs | | Representation §GMM-based VTLN; §Mixture of GMMs |
| 5 | Matching: symmetric KL, subDTW LC1/2/3 (S/T/P), path selection, z-norm; DTW, fastDTW, partial matching | **this cycle:** KL, LC2, z-norm (§9) | ExpSetup §Searching, §Detection; Matching §Partial Matching |
| 6 | Indexing: **STM** phone segmentation → posterior averaging; segment-level BoAW tf-idf | | Matching §Feature Reduction (STM, lines 287–339), §BoAW |
| 7 | Evaluation: p@N, MAP, recall, TWV/MTWV, C<sub>nxe</sub><sup>min</sup>, DET; TIMIT Q-20/Q-84 manifests | **this cycle:** Q-20, p@N, MAP (§9) | survey §Metrics; Appendix θ, β |

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

---

## 8. Cycle 4, part A: fix-ups (Codex "change requested", `5c5dea8`)

Conventions: one commit per task, `exec: …`, 10 words or fewer, no trailers. Push after every
commit. Tests for every change; every file under 400 lines.

### E1: Drop the `htk_like` profile (Codex Q2)
- **Files:** `features/profiles.py`, its tests, any doc mention
- **Do:** remove `htk_like`. Keep the generic `PlpConfig` options and the `timit_matlab`
  profile.
- **Commit:** `exec: drop unverified htk_like profile`

### E2: Two parity-doc cells (Codex Q3)
- **Files:** `docs/feature_parity.md`
- **Do:**
  - Move `Fx_mfcc_lift.m` `Nlift=-20` out of the **Thesis** column. The thesis gives no
    lifter.
  - Change the "Delta formula" thesis cell from "same" to "not stated".
- **Commit:** `exec: fix lifter and delta thesis cells`

### E3: k-means stop rule (Codex Q4)
- **Files:** `ml/vq.py`, `tests/ml/test_vq.py`
- **Do:** stop only when `0 ≤ relative decrease < tol`. A distortion increase, for example
  after an empty-cluster re-seed, continues until it recovers or `max_iter` is reached.
- **Tests:** a forced re-seed whose distortion rises does not stop the refinement early.
- **Commit:** `exec: continue kmeans after distortion increase`

### E4: Feature-cache fingerprint (Codex Q6, Q15)
- **Files:** `data/feature_cache.py`, `ml/train.py`, tests
- **Do:**
  - Store `fingerprint = sha256(json(sorted))` over:
    - `get_profile(...).to_dict()`
    - feature kind
    - dataset revision
    - `exclude_sa`
    - `FEATURE_CACHE_VERSION`, a module constant bumped by hand whenever feature semantics
      change.
  - `load_feature_cache(path, expected=...)` raises `CacheMismatchError` on a mismatch.
  - `train.py` rebuilds on mismatch when `--rebuild-cache` is given, and otherwise fails with
    a clear message.
- **Tests:** a changed config, `exclude_sa` or version is never silently reused.
- **Commit:** `exec: fingerprint feature cache and validate on load`

### E5: `huggingface_hub` in the core env (Codex Q7)
- **Files:** `pixi.toml`, `pixi.lock`, `ml/train.py` docstring
- **Do:**
  - Add `huggingface_hub` to the core dependencies. torch and transformers stay in `align`
    only.
  - `pixi run train-gmm` must work from the core env. Verify this with
    `--help` plus a cached run.
- **Commit:** `exec: add huggingface hub to core environment`

### E6: Speaker-overlap wording (Codex Q9)
- **Files:** `docs/data_notes.md`, `docs/alignment_notes.md`
- **Do:** replace "near-certain"/"unverified" with the narrower finding:
  - SA1 and SA2 counts differ (train 488/501, test 142/129);
  - so the split is **not strictly speaker-independent**: at least 13 speakers' SA
    utterances cross it;
  - the counts do not prove a random split.
- Add the standard label *"speaker overlap present; approximate versus the thesis"*.
- **Commit:** `exec: state narrower speaker overlap finding`

### E7: GMM evidence and convergence notes (Codex Q11, Q13, Q14)
- **Files:** `ml/gmm.py`, `ml/vq.py` docstrings, `docs/gmm_notes.md`
- **Do:**
  - Variance floor `0.01×` global is "HTK HCompV-style, unverified for the thesis". The
    k-means `tol` is "unverified".
  - `n_iter=10` is "experimental choice". `Representation.tex` line 1089 states ten
    iterations only for the **mixture-of-GMMs** setup; line 196 is commented out.
  - Record the c0 choice: c0 kept, as `Fx_mfcc.m` retains DCT row 1.
  - **Optional:** a 30-iteration sensitivity run of GMM-64, with its curve recorded in the
    notes. The 10-iteration model stays the baseline.
- **Commit:** `exec: correct gmm evidence and convergence notes`

---

## 9. Cycle 4, part B: first comparable number (TIMIT Q-20, MFCC, subDTW-LC2)

The goal is **one end-to-end number** to compare with the thesis target: MFCC Gaussian
posteriorgram, 64 mixtures, no VTLN, p@N **34.91**, MAP **36.71** (§3). Every result is
labelled *"speaker overlap present; approximate versus the thesis"*.

**Thesis and MATLAB facts** (cite these in docstrings):
- **Q-20 keywords and counts:** `ExpSetup.tex` lines 78–97 (`Table:TIMITdata`). Keyword
  (Inst./Occ.):
  - artists 7/7, beautiful 3/8, birth 4/7, destroy 9/7, development 9/8
  - garbage 8/7, government 14/8, intelligence 8/7, love 4/16, marriage 3/7
  - meeting 7/7, morning 15/14, ocean 7/7, organizations 7/7, problems 5/7
  - shellfish 14/7, simple 8/8, surface 3/7, tomorrow 3/7, youngsters 7/7
  - Queries come from train and documents from test; `/sa/` is excluded (lines 73–75).
- **Local distance:** symmetric KL,
  `Σ t log(t/q) + Σ q log(q/t)` (`ExpSetup.tex` line 304).
- **subDTW LC2:** the reference kernel is **`research_qbestd/matlab/NSDTW_c_skel.cpp`**.
  `Fx_do_SDTW.m` is *segmental* DTW, so do not follow it. `D` is (test frames M × query
  frames N).
  - **First column (n = 0):** `S = D`, `T = 1`, `P = m`.
  - **First two test rows (m = 0, 1):** accumulate along n, so
    `S(m,n) = S(m,n−1) + D(m,n)`, `T = n+1`, `P = m`.
  - **Otherwise:** predecessors are `(m, n−1)`, `(m−1, n−1)` and `(m−2, n−1)`.
    - `S = D + min`, `T = T_pred + 1`, `P = P_pred`.
    - **Tie order:** `(m, n−1)` first, then `(m−1, n−1)`, then `(m−2, n−1)`
      (`min_fun_ind`).
  - Every predecessor is in column n−1, so each query column can be computed
    **vectorised over m**.
- **Distance per test utterance:** `dist(i) = S(i,N)/T(i,N)` (`ExpSetup.tex` line 442).
  - A path is valid when `0.5 ≤ (i − P(i,N) + 1)/N ≤ 2`, the interval in test frames.
  - The utterance distance is the minimum over valid end frames.
- **p@N** (`survey.tex` lines 40–50): N is the number of relevant documents, and p@N is the
  number of relevant documents in the top N, divided by N, × 100.
- **AP** (`survey.tex` line 65): `(1/N) Σ_k p@k · 1(k)`. MAP is the mean over queries.
  - Test case: `t,t,f,f,t,f,f,t,f,f` with N = 4 gives p@N = 50 % and AP = 0.775.
- **Score normalisation:** `s = −(d − μ_q)/σ_q`, sample std (`ExpSetup.tex` lines 497–515).
  It is monotonic per query, so it does not change p@N or MAP. Implement it anyway for
  SWS/QUESST later.
- **Assumptions** (thesis silent; configurable, listed in the results doc):
  - **Instances:** each spoken instance is its own query; p@N and AP are averaged over all
    instances. A per-keyword average is reported too.
  - **Relevance:** exact token match against `normalize_transcript`; a document is relevant
    if it contains the token at least once.
  - **Query audio:** cut from the train audio at aligner `[start − 20 ms, end + 20 ms]`,
    clipped to the utterance, with features extracted **from the clip** (like a separate
    query file). Rows flagged `collapsed_run` or under 20 ms are skipped.
  - **Posterior floor:** `1e-10`, then renormalise (`floor_and_renormalise`).

### T7.1: Q-20 query and relevance manifests
- **Files:** `src/qbestd/eval/__init__.py`, `src/qbestd/eval/timit_queries.py`, tests,
  `docs/q20_counts.md`
- **API:**
  - `Q20_KEYWORDS`: a tuple of `(keyword, thesis_inst, thesis_occ)`.
  - `build_query_examples(train_word_manifest, train_rows, keywords, pad_s=0.02)
    -> list[QueryExample]`, skipping SA rows and flagged segments.
  - `build_relevance(test_rows, keywords, exclude_sa=True) -> dict[keyword, set[row_index]]`.
    Use `is_sa_sentence` and `normalize_transcript` from the existing modules.
  - `write_*` / `read_*` TSV helpers. Outputs go to `outputs/eval/` (git-ignored).
- **`docs/q20_counts.md`** (committed; small derived statistics, no audio or transcripts):
  - per keyword: thesis Inst/Occ against ours (train instances, test documents, test token
    occurrences);
  - document-set size after SA exclusion (expect 1260 − 271 = 989);
  - skipped flagged instances.
- **Tests:** synthetic manifests:
  - SA rows excluded from both queries and documents;
  - padding clipped to the utterance bounds;
  - flagged segments skipped;
  - exact token matching (`love` does not match `lovely`).
- **Commit:** `exec: add timit q20 query and relevance manifests`

### T7.2: Ranked-retrieval metrics
- **Files:** `src/qbestd/eval/metrics.py`, tests
- **API:**
  - `precision_at_n(ranked_is_relevant, n_relevant)`;
  - `average_precision(ranked_is_relevant, n_relevant)`;
  - `summarise(per_query) -> {p_at_n, map, n_queries}`.
  - If `n_relevant == 0`, raise `ValueError`.
- **Tests:** the thesis example gives 50 % and 0.775; a perfect ranking gives 100 %; no
  relevant document in the ranking gives 0.
- **Commit:** `exec: add p at n and map metrics`

### T5.1: Symmetric KL local distance
- **Files:** `src/qbestd/search/__init__.py`, `src/qbestd/search/distance.py`, tests
- **API:** `symmetric_kl_matrix(test_post (M,K), query_post (N,K), floor=1e-10) -> (M,N)`,
  vectorised as `(t·log t).sum − t·log qᵀ + (q·log q).sum − log t·qᵀ`.
- **Tests:**
  - identical rows give 0;
  - the result is symmetric under swapping the inputs (transposed);
  - it is non-negative;
  - it equals a double-loop reference;
  - zeros in the input stay finite through the floor.
- **Commit:** `exec: add symmetric kl distance matrix`

### T5.2: subDTW LC2 kernel and path selection
- **Files:** `src/qbestd/search/subdtw.py`, tests
- **API:**
  - `subdtw_lc2(D) -> (S, T, P)`, with columns vectorised over test frames and
    `NSDTW_c_skel.cpp` initialisation and tie order.
  - `best_utterance_distance(S, T, P, min_ratio=0.5, max_ratio=2.0) -> (dist, start, end,
    used_fallback)`. If no end frame is valid, take the minimum over all of them with
    `used_fallback=True`.
- **Tests:**
  - matches a plain double-loop transcription of the C++ (kept in the test file) on 20
    random `D` matrices, including tie-heavy integer `D`;
  - a query planted inside a random utterance is found at the right start and end;
  - `M < 3` and `N = 1` edge cases;
  - the fallback flag.
- **Commit:** `exec: add subdtw lc2 kernel and path selection`

### T5.3: Score normalisation
- **Files:** `src/qbestd/search/score.py`, tests
- **API:**
  - `znorm_scores(distances) -> -(d − mean)/std(ddof=1)`, raising on fewer than 2 values or
    zero std;
  - `rank_documents(distances) -> order`, stable.
- **Tests:** a hand-worked example; ranking by z-score equals ranking by distance.
- **Commit:** `exec: add score normalisation and ranking`

### T7.3: TIMIT Q-20 evaluation runner
- **Files:** `src/qbestd/eval/run_timit.py` (CLI), a pixi task `eval-timit`, tests for
  argument parsing and the aggregation helpers
- **CLI:** `python -m qbestd.eval.run_timit --kind mfcc --profile timit_matlab --gmm
  <model.npz> --keywords q20 --out outputs/eval/<run_name>/`
- **Steps:**
  1. Load or build the test feature cache (`exclude_sa=True`, fingerprint-validated).
  2. Cut the query clips from the train audio and extract their features.
  3. Compute posteriorgrams for queries and documents.
  4. For every query × document pair: KL matrix, then LC2, then utterance distance.
  5. Rank, then p@N and AP per instance.
- **Outputs:**
  - `per_query.tsv` (keyword, instance row, p@N, AP, fallbacks);
  - `summary.json`: instance-averaged and keyword-averaged p@N/MAP, counts, runtime, model
    and feature fingerprints, git commit.
- **Commit:** `exec: add timit q20 evaluation runner`

### T7.4: Run and record the first numbers
- **Run:** MFCC `timit_matlab` with GMM-64, then GMM-128, both LC2.
- **Write `docs/results_timit_q20.md`:**
  - a table of ours against the thesis (GMM-64 target 34.91 / 36.71);
  - both averaging modes;
  - per-keyword AP;
  - the fallback count;
  - runtime;
  - the assumption list above;
  - the speaker-overlap label.
- The gap is explained with evidence, not tuned away. **Do not change any setting to chase
  the target.**
- **Commit:** `exec: record first timit q20 results`

### T7.5: Stage 5 search demo
- **Files:** `demo/stage5_search_demo.py` (≤ 250 lines); pixi task `demo-stage5` in the
  `demo` feature
- **Inputs:** either two audio clips (query and document) or a Q-20 keyword plus an
  instance; a GMM selector.
- **Outputs:**
  - both posteriorgrams;
  - KL matrix `D`, and `S` with the best path overlaid;
  - the utterance distance;
  - for a keyword: the top-10 ranked documents with relevance marks and p@N/AP.
- Put a usage note at the top. Import from `qbestd` only.
- **Commit:** `exec: add stage 5 search demo`

**Cycle 4 definition of done:**
- E1–E7, T7.1, T7.2, T5.1–T5.3 and T7.3–T7.5 are on `main`, and `pixi run test` is green in
  the core env.
- Every module is under 400 lines.
- `docs/results_timit_q20.md` has the first MFCC GMM-64 and GMM-128 numbers.
- The Reviewer writes `handoff_request.md` for cycle 4 with the open questions below.

**Open questions for the cycle 4 review:**
- 20: How did the thesis combine a keyword's several spoken instances (Inst. 3–15)? Was each
  instance its own query, or were scores fused per keyword?
- 21: Is "Occ." in `Table:TIMITdata` a document count or a token count? Did relevance include
  morphological variants?
- 22: Query features: from the cut clip (current) or sliced from the full-utterance features?
- 23: Path validity: is the interval measured in test frames from `P` (current) or as the path
  length `T`?

---

## 10. Next cycles (preview)

1. **Gap analysis** of the first numbers, then PLP and MFCC-TMP on the same pipeline (§3
   targets).
2. **Stage 4:** iterative GMM-VTLN (5 iterations, 13 warps). Use the `extract_warped_bank`
   caching that Codex deferred to here.
3. LC1 and LC3, Q-84, and the optional SAD ablation (Codex Q12).
4. Mixture of GMMs, then DTW and fastDTW, then indexing (STM, BoAW).
5. SWS 2013 and QUESST 2014: path selection with 7 paths, z-norm, MTWV and Cnxe.
