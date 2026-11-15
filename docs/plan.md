# Execution Plan: QbE-STD Thesis Reimplementation

- **Cycle:** 6 (Orchestrator)
- **Handoff input:** `handoff_response.md` at `ba99a8a` (Codex review of cycle 5, Q1–Q6)
- **Stage status:** Stages 0–3, TIMIT word alignment, the thesis endpoint rule, keyword-cluster
  statistics and the text-disjoint split v1 are done. 519 passed, 1 skipped at `1b76d12`.
- **This cycle:** provenance fixes and a corrected text-disjoint split `textdisjoint_q20_v2`
  that keeps SX transcript variants together (part A, §8), then PLP and MFCC-TMP on v2
  (part B, §9)
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

---

## 8. Cycle 6, part A: provenance fixes and split v2 (Codex `ba99a8a` Q1, Q3–Q6)

**Order matters.** C1 → C2 → C3 → C4 → C5 → C6, each its own commit.
- C2 changes the feature fingerprint, so the A3 guard rejects every existing model. C3
  rebuilds and re-checks the HF models **before** any v2 model is trained, or the v2 models
  would be stale on arrival.
- C5's split doc (the rule, the reason and the manifest hash) is committed **before** any
  v2 GMM is trained or scored.
- The v1 models are **not** retrained. The guard will reject them from C2 on; their scored
  outputs stay as historical results.

### C1: Results-doc corrections (Codex Q5, Q1)
- **File:** `docs/results_timit_q20.md` (docs only, no new numbers)
- **Do:**
  - Line 212: replace "The text-disjoint split removes this, and its scores are **not**
    lower …" and the causal conclusion after it. HF vs text-disjoint is **descriptive
    only**: queries, documents, relevance and GMM training rows all change, and v1 still has
    8 crossed SX variants. No unpaired test, and no claim that removing overlap raised,
    lowered or failed to explain the scores.
  - Line 223: the claim that **all** paired 128 − 64 intervals contain 0 is wrong. For v1,
    the instance-averaged MAP difference is **+2.95, 95 % keyword-cluster interval
    0.2–5.7**. Say that this positive MAP result is *in the thesis's direction* (thesis
    +1.63 MAP), while the p@N interval and the keyword-averaged MAP interval include 0.
    It describes the fixed v1 experiment. No numerical-parity claim.
  - Label the text-disjoint v1 section: *"8 SX sentence variants crossed sides; government
    affected; not fully sentence-disjoint"*. Keep its numbers as they are.
- **Commit:** `exec: correct results wording per cycle 5 review`

### C2: Row-selection identity and import closure (Codex Q6)
- **Files:** `src/qbestd/data/feature_cache.py`, `tests/data/test_feature_cache.py`
- **Fingerprint.** Changes to row selection and decoding can change the cached rows or
  samples without changing the feature-source digest. Close that gap, but do **not** hash
  `feature_cache.py` itself, because then every edit to the fingerprint code would
  invalidate the caches. Add three entries to the `feature_fingerprint` payload:
  - `row_source_digest`: `feature_source_digest` over `ROW_SOURCE_FILES =
    ("data/timit_hf.py",)`, with the same CRLF → LF normalisation. This covers row
    iteration, decoding, the sample-rate check and `normalize_transcript`.
  - `sa_tokens`: the value of `SA_TOKENS` as a list.
  - `row_selection_version`: a new constant `ROW_SELECTION_VERSION = 1` covering the
    selection loop inside `build_feature_cache` (SA skip, row order, offsets). Its comment
    says to bump it whenever that logic changes.
  - Update the docstring to list everything the fingerprint covers.
- **Import-closure test:**
  - Factor the AST walk into a helper that takes a root directory, so a fixture can run it
    on a temporary tree.
  - Resolve **relative** `ImportFrom` nodes (`level > 0`) against the importing module's
    package.
  - Fixture: copy `src/qbestd/audio` and `src/qbestd/features` into `tmp_path`, add a new
    helper module, and import it from the copied `features/extract.py`. The closure helper
    must report the helper as missing from `FEATURE_SOURCE_FILES`. Run the case once with an
    absolute import and once with a relative one.
  - Docstring: the check still misses dynamic imports and code outside the two packages.
- **Invalidation tests:** each of these changes the fingerprint:
  - the bytes of a temporary copy of `data/timit_hf.py`;
  - a monkeypatched `SA_TOKENS`;
  - a monkeypatched `ROW_SELECTION_VERSION`.

  CRLF and LF copies of `timit_hf.py` give the same digest.
- **Commit:** `exec: fingerprint row selection and resolve relative imports`

### C3: Rebuild caches and retrain HF GMMs (regression check)
- Rebuild both HF MFCC `timit_matlab` caches. Then retrain GMM-64 and GMM-128 on the HF train
  side with the HF `split_id`.
- **Check:** the parameter hashes must still be `80a5b016…` (64) and `c0e38a61…` (128). If
  either differs, **stop and report**: no code that decides rows or features was supposed
  to change.
- Add one line to `docs/gmm_notes.md`: the new fingerprint, and "parameter hashes unchanged".
- **Commit:** `exec: retrain hf gmms under row selection fingerprint`

### C4: Count minimum-cost assignments (Codex Q4)
- **Files:** `src/qbestd/data/text_split.py`, `tests/data/test_text_split.py`
- **Do:**
  - While `_choose` enumerates a component's assignments, count how many reach the minimum
    summed cost. Keep the existing tie-break exactly.
  - The count is **per connected keyword component**, never per keyword. For example,
    birth and organizations are one component with one count.
  - `report["components"]` becomes a list of
    `{"keywords", "n_groups", "cost", "n_min_assignments"}`.
- **Tests:**
  - a synthetic component with exactly two cost-0 assignments reports 2;
  - a two-keyword shared-group component reports one count, not two;
  - the tie-break result is unchanged.
- **v1 check:** re-run `python -m qbestd.data.text_split` into a scratch path. The manifest
  sha256 must still start with `ee27b531237a`. Note the v1 counts for C5's doc.
- **Commit:** `exec: count minimum cost assignments per component`

### C5: Split v2 rule, links, manifest and doc (Codex Q1, Q3)
- **Files:** `src/qbestd/data/text_split.py`, `tests/data/test_text_split.py`,
  `docs/split_textdisjoint.md`
- **Rule `textdisjoint_q20_v2`:** v1's rule plus a merge step 1b. Everything else is
  unchanged, including the 120 / 504 test quotas.
  - **1b. Merge verified variant links.** `V2_VARIANT_LINKS` is an explicit, sorted tuple of
    `(hash_a, hash_b)` pairs of v1 group hashes, committed in code. Its units are the
    connected components of those explicit links only, with no general one-edit rule.
  - **Hashes:** the group-hash prefix stays `qbestd-textsplit-v1\n`, so the links refer to
    existing v1 hashes and v1 and v2 differ only where they must. A merged unit's key is its
    **smallest member hash**.
  - Steps 2 and 3 and the manifest work on **units**. A unit is `multi` when it holds more
    than one row. The tie-break, the step 3 hash order and the manifest `group_hash` column
    all use the unit key. As a result, B2's "queries and documents never share a text group"
    check covers variants automatically.
  - The header is `# rule=textdisjoint_q20_v2`. The output is
    `outputs/splits/textdisjoint_q20_v2.tsv`, and `split_id` is
    `textdisjoint_q20_v2-<12 hex>`.
  - **API:** keep `build_text_split(rows, keywords)` byte-identical for v1, and add
    `rule=` / `links=` parameters (or a v2 entry point). Add `--rule v1|v2` to `main`. If
    `text_split.py` would pass about 330 lines, move the links and the candidate finder
    into `src/qbestd/data/text_variants.py`.
- **Finding and verifying the links.** Do this on transcripts only, before any v2 score.
  - `find_variant_candidates(groups)` proposes a pair when:
    - the two token sequences differ by exactly one substitution, insertion or deletion;
    - at least one of the two groups is multi-read;
    - the combined row count is ≤ 7, since an SX text is read by 7 speakers.

    The finder only proposes; the committed list is what verification keeps.
  - Verify every candidate against the full normalised transcripts and the row counts. If a
    group pairs with two different multi-read groups, or a unit would exceed 7 rows,
    **exclude it and list it as rejected with the reason**. Never guess.
  - The list must contain all 8 reviewer pairs:
    - 6 + 1 will ↔ would (government);
    - 6 + 1 shimmered ↔ simmered;
    - 4 + 2 ± "the";
    - five 6 + 1 pairs with ± "a" / "the" / "at".

    If any of the 8 is not found, **stop and report**.
  - It must also contain every other verified pair (§7 Q27), including shellfish 5 + 2.
- **Tests:**
  - linked variants never cross sides, in a synthetic case where v1's rule would split
    them;
  - the manifest is byte-identical under shuffled row order **and** shuffled link order;
  - `links=()` reproduces v1's output on a synthetic universe;
  - the unit key is the smallest member hash;
  - a link that names an unknown hash raises;
  - the finder detects substitution, insertion and deletion, and rejects two-token edits,
    pairs of single-read groups and combined counts over 7.
- **`docs/split_textdisjoint.md`**, new section "v2". Commit it in the same commit as the
  code, **before C6**. Include no sentence text.
  - the reason, verbatim: *"variant groups split SX texts across sides (found in review)"*;
  - the v2 rule (v1 plus step 1b, the unit key and the unchanged prefix);
  - **link evidence:** one row per link, with both hashes (12 hex), the row counts, the
    edit type, the differing token only, the keyword if any, the v1 sides, and whether the
    reviewer named it;
  - rejected candidates and why;
  - the manifest sha256 and `split_id`;
  - per component: the cost and `n_min_assignments` for v2, with v1 alongside for
    reference;
  - per keyword: train and test tokens against the thesis Inst./Occ., marking every change
    from v1 and **any nonzero cost**;
  - rows per side, units per stratum, the quota report, and how many rows changed side
    relative to v1 and to the HF split;
  - **post-build scan:** run the finder on the final v2 manifest and report how many
    one-edit candidate pairs cross sides. The target is 0; list and explain any that
    remain;
  - the v1 labels still apply: closer to the thesis on sentence context, not an official
    TIMIT reconstruction, speaker overlap present.
- **Gate:** a nonzero step 2 cost is reported, not fixed. If v2 loses keyword coverage
  (any keyword with no test document or no train instance), commit the doc, then **stop
  before C6 and report**. Choosing a replacement protocol is the Orchestrator's decision
  (Codex Q3).
- **Commit:** `exec: declare text disjoint split v2 with variant links`

### C6: Train and evaluate on `textdisjoint_q20_v2`
- Train MFCC `timit_matlab` GMM-64 and GMM-128 on the v2 train side
  (`--split-manifest`). Then run `eval-timit` with LC2, clip query features and the A1
  scorer.
- **`docs/results_timit_q20.md`:** add a section **"Text-disjoint split v2"**:
  - query instances and relevant pairs per keyword against the thesis table, marking any
    change from v1;
  - p@N / MAP for both averages, keyword-cluster intervals, the paired 128 − 64 interval,
    nonmatches, `split_id`, model hashes and the commit;
  - **direction check, made afresh on v2:** say "in the thesis's direction" only for a
    metric whose paired interval excludes 0, and never claim numerical parity;
  - the historical table gains a v2 row next to thesis, HF v2 and text-disjoint v1. It is
    descriptive, with no unpaired test;
  - state that later result docs compare on v2 and point to this table for HF v2 and v1.
- **Do not tune anything** and do not change v2 after seeing scores.
- **Commit:** `exec: evaluate q20 on text disjoint split v2`

---

## 9. Cycle 6, part B: PLP and MFCC-TMP on split v2 (Codex Q2)

**Gate:** start only after C6 is on `main` and C5 kept full keyword coverage. Same v2
manifest, LC2, clip features, A1 scorer and bootstrap. **No VTLN yet** (Stage 4 is not
built). No tuning towards §3.

### P1: PLP, GMM-64 and GMM-128
- `timit_matlab` profile (16 kHz, 8 kHz band, §4 Q14). Build the per-HF-split caches, then
  train on the v2 train side and evaluate.
- Check that the EM log-likelihood curve rises monotonically, and add the hashes and curves
  to `docs/gmm_notes.md`.
- **Commit:** `exec: evaluate plp on text disjoint split v2`

### P2: MFCC-TMP, GMM-64 and GMM-128
- `timit_matlab` profile (16 kHz, 4 kHz band). Log the count of TEO floor hits per cache
  build (§6 risk) and report it. A non-finite feature stops the run.
- **Commit:** `exec: evaluate mfcc tmp on text disjoint split v2`

### P3: Feature comparison doc
- **File:** new `docs/results_timit_q20_features.md`. It points to the historical table in
  `docs/results_timit_q20.md` and does not repeat HF v2 or v1 rows.
- **Tables:** feature × NG (64, 128), with p@N / MAP for both averages, keyword-cluster
  intervals and the thesis targets:
  - PLP: 64 is 35.50 / 37.58 and 128 is 37.30 / 40.18;
  - MFCC-TMP: 64 is 40.03 / 41.50. The thesis gives **no** 128 target for MFCC-TMP; say so.
- **Paired keyword bootstrap**, valid here because the queries, documents and relevance are
  identical: PLP − MFCC and MFCC-TMP − MFCC per NG, plus 128 − 64 per feature.
  - Thesis directions at 64: PLP − MFCC is +0.59 / +0.87, and MFCC-TMP − MFCC is
    +5.12 / +4.79.
  - Same wording rule as C6: say "in the thesis's direction" only when the interval
    excludes 0.
- **Commit:** `exec: compare features on text disjoint split v2`

**Cycle 6 definition of done:**
- C1–C6 are on `main` in that order, with the C5 doc before any v2 model. Part B is done
  too, or the report says which gate stopped it.
- `pixi run test` is green in the core env. Every module is under 400 lines, no line is
  over 79 characters, and every new function has tests. No derived data is committed.
- The Reviewer writes `handoff_request.md` for cycle 6 with the questions below.

**Open questions for the cycle 6 review:**
- 27: Is linking every verified variant pair, rather than only the 8 that crossed in v1,
  the right reading of Codex Q1? Are the rejected candidates handled correctly?
- 28: Do the v2 tie counts show a component that is badly underdetermined, and if so,
  what should the doc say?
- 29: Is the row-selection identity (the `timit_hf.py` digest, `SA_TOKENS` and
  `ROW_SELECTION_VERSION`) the right scope, or should `build_feature_cache` move into its
  own hashed module?
- 30: Where PLP or MFCC-TMP moves against the thesis direction, is a front-end parity check
  warranted before Stage 4 VTLN, or should VTLN go ahead on the same v2 setup?

---

## 10. Next cycles (preview)

1. **Stage 4:** iterative GMM-VTLN (5 iterations, 13 warps) for MFCC, PLP and MFCC-TMP on
   the v2 split. Use the `extract_warped_bank` caching that Codex deferred to here.
2. LC1 and LC3 (§3 has their TIMIT targets), Q-84, and the optional SAD ablation (Codex Q12).
3. Mixture of GMMs (§3 targets), then DTW and fastDTW, then indexing (STM, BoAW).
4. SWS 2013 and QUESST 2014: path selection with 7 paths, z-norm, MTWV and Cnxe.
