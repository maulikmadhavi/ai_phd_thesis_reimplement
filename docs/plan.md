# Execution Plan: QbE-STD Thesis Reimplementation

- **Cycle:** 2 (Orchestrator)
- **Handoff input:** `handoff_response.md` at `5b4503b` (Codex review of Stage 0 + 1, cycle 1)
- **Stage status:** Stage 0 and Stage 1 are done (T0.1–T1.11, 49 tests green at `b24097d`)
- **This cycle:** apply the Stage 1 fix-ups Codex requested, then Stage 2 (acoustic features)
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
| 1 | Audio base: I/O, resampling, pre-emphasis, framing, windowing, spectrum, energy, TEO | done; fix-ups in §7 | ExpSetup §Front-end |
| 2 | Features: mel/Bark scales, VTLN frequency warping, mel filterbank, MFCC + Δ/ΔΔ, PLP, MFCC-TMP | **this cycle** | ExpSetup §Acoustic Representation; Warped_Feature appendix |
| 3 | ML: LBG VQ codebook → diagonal GMM by EM, log-likelihood | next | ExpSetup §Posterior Representation; `Backmatter/Algorithm_LC` |
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

| # | Question | Status after cycle 1 |
|---|---|---|
| 13 | Pre-emphasis, window, FFT size, c0, lifter | **Resolved for defaults:** 0.97, Hamming, nextpow2, c0 kept. Lifter configurable (0 / 20 / 22). |
| 14 | TIMIT at 8 kHz or 16 kHz? | **Unknown.** Evidence: MATLAB MFCC-TMP defaults to fs = 16000 with fH = 4000, which points to 16 kHz audio with a 4 kHz mel ceiling. Keep `sample_rate` and `high_hz` as *separate* settings. Default `high_hz = 4000` and leave the sample rate unverified. |
| 15 | Q-84 list | **Unknown.** Derive it deterministically in Stage 7 from the official split and normalized transcripts, compare the count to 84, and commit the list as an artifact. |
| 16 | Phone segmentation for Stage 6 | **Resolved:** STM (`stm_computation.m`, Matching.tex lines 287–339). |
| D1 | **User decision:** is a licensed LDC TIMIT copy with `.WRD` files available? | **Open.** Without it, Q-20/Q-84 query audio has to be cut by forced alignment on the HF copy. That is an approximate experiment and must be labelled as such. Stage 2 does not depend on this; Stage 7 does. |

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

## 7. Cycle 2, part A: Stage 1 fix-ups (Codex "change requested")

Conventions:
- One task per commit, pushed right away.
- Message `exec: …`, 10 words or fewer, no tool signatures.
- Modules under 400 lines, PEP 8, and tests for every change.

### F1: Strict PCM output (Codex Q4)
- **Files:** `src/qbestd/audio/io.py`, `tests/audio/test_io.py`
- **Do:**
  - `save_audio` raises `ValueError` for non-finite samples or samples outside [-1, 1], before anything is written.
  - The `load_audio` docstring states that float WAV input is not range-checked.
- **Tests:** ±1.0 is accepted; 1.0001, NaN and inf are rejected; nothing is written on rejection.
- **Commit:** `exec: validate pcm range in save_audio`

### F2: Resampling validation and alias-safe time scaling (Codex Q5, Q12)
- **Files:** `src/qbestd/audio/resample.py`, `tests/audio/test_resample.py`
- **Do:**
  - `resample_audio` requires positive integer rates and raises `ValueError` otherwise.
  - `scale_time_axis`:
    - Zero-length input returns an empty array; one-sample input returns a copy.
    - For `warp_factor > 1`, low-pass first with an explicit FIR (`firwin` + `filtfilt`), cutoff `0.95·(Nyquist/warp_factor)`. Expose the parameter `antialias=True` and document the filter.
- **Tests:** rates 0, −8000 and 8000.5 raise; empty and one-sample cases; a 3.9 kHz tone at 8 kHz with α = 1.12 is attenuated by at least 20 dB instead of folding.
- **Commit:** `exec: validate rates and anti-alias time scaling`

### F3: Framing validation (Codex Q6)
- **Files:** `src/qbestd/audio/framing.py`, `tests/audio/test_framing.py`
- **Do:**
  - Non-positive sample rate, frame_ms or shift_ms raise `ValueError`.
  - So do frame or shift lengths that round to 0.
  - `count_frames` validates positive lengths.
- **Tests:** zero shift; `shift_ms = 0.01` at 8 kHz; negative rate.
- **Commit:** `exec: validate framing parameters`

### F4: FFT length validation (Codex Q7)
- **Files:** `src/qbestd/audio/spectrum.py`, `tests/audio/test_spectrum.py`
- **Do:** `n_fft < frame_length`, a non-integer n_fft or n_fft ≤ 0 raises `ValueError`. Keep the scaling unnormalized and add a docstring line explaining why (matches `Fx_mfcc.m`).
- **Tests:** n_fft = 128 for a 200-sample frame raises; 255.5 raises.
- **Commit:** `exec: reject short or invalid fft lengths`

### F5: Dataset config cleanup (Codex Q9)
- **Files:** `src/qbestd/config.py`, `tests/test_config.py`, new `paths.local.toml.example`
- **Do:**
  - Remove the machine-specific defaults (all None).
  - The TOML path comes from an explicit argument, else `$QBESTD_PATHS_FILE`, else `<repo root>/paths.local.toml`, with the repo root found from the module location. It no longer depends on the current working directory.
  - An env var that is present but empty raises `ValueError`.
  - `require("typo")` raises `ValueError`.
  - The example file lists the keys with placeholder paths.
- **Tests:** precedence (env > file > None); empty env var; unknown name; the file is found outside the current working directory.
- **Commit:** `exec: remove absolute defaults from dataset config`

### F6: Demo TEO curve (Codex Q11)
- **Files:** `demo/stage1_audio_demo.py`
- **Do:** plot the signed mean TEO directly, or a signed log `sign(x)·log1p(|x|)` with a clear axis label.
- **Accept:** `build_demo()` still builds (smoke check in the Reviewer step).
- **Commit:** `exec: plot signed teager energy in demo`

### F7: Qualify the TIMIT data notes (Codex Q17)
- **Files:** `docs/data_notes.md`
- **Do:**
  - Remove "probably at random" and "speakers likely overlap", and say the split method is undocumented.
  - Confirm the sample rate by reading **one** row through the HF dataset-viewer rows API (`datasets-server.huggingface.co/rows?dataset=Siyong/speech_timit&config=default&split=train&offset=0&length=1`). Download only that row's audio and read its header. Do not download the parquet files and add no new dependency.
  - Record whether the rate is observed or still inferred.
  - Add §4 D1 as an explicit pending user decision.
- **Commit:** `exec: qualify timit split and confirm sample rate`

---

## 8. Cycle 2, part B: Stage 2 (acoustic features), atomic tasks

Package: `src/qbestd/features/`. Each module gets a matching test file under `tests/features/`.
Arrays are `(n_frames, n_dims)` throughout, and all logs use an explicit floor (`1e-10`).

### T2.1: Frequency scales and VTLN warping
- **Files:** `features/scales.py`
- **Functions:**
  - `hz_to_mel`, `mel_to_hz` (HTK 2595·log10)
  - `hz_to_bark`, `bark_to_hz` (`6·asinh(f/600)`, Warped_Feature appendix)
  - `warp_frequency_piecewise(freqs_hz, warp_factor, sample_rate, cutoff_ratio=0.875)`, exactly as `Fx_vtln_warp.m`, including the 0.05 cutoff back-off
  - `warp_mel_scale(freqs_hz, warp_factor)` (thesis `M_α`)
  - `VTLN_WARP_FACTORS = 0.88…1.12` in steps of 0.02 (13 values)
- **Tests:**
  - Round trips are within 1e-9.
  - α = 1 is the identity.
  - The warp is continuous at f0 and maps Nyquist to Nyquist.
  - It is monotonic for every α in the grid.
  - At α = 0.88, fs = 8 kHz: f0 = 3500 and the slope is 1.12.
- **Commit:** `exec: add frequency scales and vtln warping`

### T2.2: Mel filterbank
- **Files:** `features/filterbank.py`
- **Function:** `mel_filterbank(n_filters=26, n_fft=256, sample_rate=8000, low_hz=0.0, high_hz=4000.0, warp_factor=1.0) -> (n_filters, n_fft//2+1)`
  - Triangles are equally spaced in mel between low_hz and high_hz.
  - When α ≠ 1, the FFT bin frequencies are warped by `warp_frequency_piecewise` before mel mapping, as in `Fx_PLPCC_htk.m`.
  - Raise if `high_hz > sample_rate/2`.
- **Tests:**
  - Shape and non-negativity.
  - Filter peaks increase strictly.
  - No energy outside `[low_hz, high_hz]` when α = 1.
  - α = 1 equals the unwarped bank.
  - For α > 1, filter peaks move to higher bins, because the warped bin frequency is (2−α)·f. Assert this direction and document it.
- **Commit:** `exec: add mel filterbank with vtln warping`

### T2.3: Cepstral utilities
- **Files:** `features/cepstral.py`
- **Functions:**
  - `log_compress(x, floor=1e-10)`
  - `dct_cepstra(log_energies, n_ceps=13, include_c0=True)`, using `scipy.fft.dct` type 2 with `norm="ortho"` to match MATLAB `dct(eye(p))`
  - `lifter_cepstra(ceps, lifter_length=0)`: HTK sine lifter `1 + (L/2)·sin(πn/L)`; 0 means none
- **Tests:**
  - Matches an explicit cosine-matrix product.
  - `include_c0=False` drops column 0.
  - Lifter 0 is the identity.
  - Lifter 22 matches the HTK formula.
  - The floor prevents `-inf`.
- **Commit:** `exec: add dct and liftering utilities`

### T2.4: Delta features
- **Files:** `features/deltas.py`
- **Functions:**
  - `compute_deltas(features, window=2)`, regression per `Deltacep.m` with edge frames replicated
  - `append_deltas(static, window=2, order=2)`, which gives 13 → 39 dimensions
- **Tests:** a linear ramp gives a delta equal to the slope in interior frames; a constant gives 0; shapes; edge replication matches a hand-computed value.
- **Commit:** `exec: add delta and acceleration features`

### T2.5: MFCC extractor
- **Files:** `features/mfcc.py`
- **Functions:** `MfccConfig` and `extract_mfcc(samples, sample_rate, config) -> (n_frames, 13 or 39)`
- **`MfccConfig` fields:**
  - Audio front-end: frame, shift, pre-emphasis, window, n_fft.
  - `n_filters=26`, `low_hz=0`, `high_hz=4000`, `n_ceps=13`, `include_c0=True`, `lifter_length=0`.
  - `spectrum_type="magnitude"` (`# unverified default`; "power" is also allowed).
  - `normalize_peak=True` (MATLAB `/max|x|`), `pcm_scale=32768.0`.
  - `deltas=True`, `delta_window=2`, `warp_factor=1.0`.
- **Pipeline:** Stage 1 `prepare_frames`, then `power_spectrum` (sqrt for magnitude), then filterbank, then `log((M·S)²)` for magnitude or `log(M·P)` for power, then DCT, then lifter, then deltas.
- **Tests:**
  - Shapes for 1 s at 8 kHz and at 16 kHz.
  - Deterministic output.
  - Finite on silence.
  - c0 rises with signal amplitude when `normalize_peak=False`.
  - `warp_factor=1.0` gives the same result as the default.
  - Config round-trips to and from a dict.
- **Commit:** `exec: add mfcc extractor`

### T2.6: LPC helpers
- **Files:** `features/lpc.py`
- **Functions:**
  - `autocorrelation_from_power(power_bands)`: real IDFT of the band spectrum, as in rastamat `dolpc`
  - `levinson_durbin(autocorr, order) -> (lpc_coeffs, gain)`
  - `lpc_to_cepstrum(lpc_coeffs, gain, n_ceps)`
- **Tests:**
  - Levinson matches `scipy.linalg.solve_toeplitz`.
  - The AR(1) case `a` gives cepstrum `c_n = a^n / n`.
  - Order larger than the number of lags raises.
- **Commit:** `exec: add lpc analysis helpers`

### T2.7: PLP extractor
- **Files:** `features/plp.py`
- **Functions:** `PlpConfig` (`lpc_order=12  # unverified; MATLAB 8, HTK 12`, `n_ceps=13`, `lifter_length=22`, `warp_factor`, …) and `extract_plp(samples, sample_rate, config)`
- **Pipeline (per `Fx_PLPCC_htk.m`):**
  1. Power spectrum.
  2. Mel bank over 0–fs/2 (filter count from the Bark span, or configured).
  3. Equal-loudness weights.
  4. `^0.33` compression.
  5. Copy the edge bands from their neighbours.
  6. LPC.
  7. Cepstrum.
  8. Lifter.
  9. Optional deltas.
- **Tests:** shape; finite output; the equal-loudness curve matches the formula at 1 kHz; the lifter is applied.
- **Commit:** `exec: add plp extractor`

### T2.8: MFCC-TMP extractor
- **Files:** `features/mfcc_tmp.py`
- **Functions:**
  - `teager_energy_lagged(frames, lag=1)` (`# unverified: vteo.m not public`)
  - `subband_signals(complex_spectrum, mel_weights_full)`: complex STFT × symmetric weights, then real IFFT
  - `extract_mfcc_tmp(samples, sample_rate, config)`, following `Fx_mfcc_vtmp_cep.m`. Use `specopt` "mp" (default), "m" or "p", and keep `include_c0`.
  - Stage 1 needs a complex STFT. Add `complex_spectrum(frames, n_fft)` to `audio/spectrum.py`, with its own test.
- **Tests:**
  - With a single tone, most of the subband energy lands in the filter that contains it.
  - Output is finite on silence (floor).
  - Shape 13 / 39.
  - A lag-1 TEO of a cosine matches `A²·sin²Ω`.
- **Commit:** `exec: add mfcc-tmp extractor`

### T2.9: Unified and warped feature extraction
- **Files:** `features/extract.py`
- **Functions:**
  - `extract_features(samples, sample_rate, kind, warp_factor=1.0, config=None)`, with kind one of {"mfcc", "plp", "mfcc_tmp"}
  - `extract_warped_bank(samples, sample_rate, kind, warp_factors=VTLN_WARP_FACTORS) -> dict[float, ndarray]`, the input to Stage 4 VTLN
- **Tests:** 13 keys; α = 1 equals `extract_features`; frame counts agree across α; an unknown kind raises.
- **Commit:** `exec: add unified and warped feature extraction`

### T2.10: Stage 2 Gradio demo
- **Files:** `demo/stage2_features_demo.py` (≤ 250 lines); pixi task `demo-stage2`
- **Inputs:** audio upload or mic; kind; warp factor slider (0.88–1.12); n_filters; high_hz; c0 and lifter toggles.
- **Outputs:** unwarped versus warped filterbank plot; feature heatmap (static plus deltas); a per-dimension mean/std table.
- Add a usage note at the top. Import from `qbestd` only.
- **Commit:** `exec: add stage 2 features demo`

### T2.11: Feature parity notes
- **Files:** `docs/feature_parity.md`
- **Do:** write a table of every Stage 2 setting, with columns ours / `Fx_mfcc.m` / `Fx_mfcc_vtmp_cep.m` / `Fx_PLPCC_htk.m` / HTK default / thesis. Cite file and line for each. List the remaining unknowns (§4 #14, the missing `vteo.m` and `Fx_melfiltbank.m`).
- **Commit:** `exec: document feature parity with matlab and htk`

**Cycle 2 definition of done:**
- F1–F7 and T2.1–T2.11 are on `main`, and `pixi run test` is green.
- Every module is under 400 lines.
- The Reviewer has written `handoff_request.md` for cycle 2, including the D1 status and any parity gaps.
