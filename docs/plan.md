# Execution Plan: QbE-STD Thesis Reimplementation

- **Cycle:** 1 (Orchestrator)
- **Handoff input:** no `handoff_response.md` yet. This is the first cycle.
- **Current stage:** Stage 1, audio processing base (plus Stage 0 scaffolding)
- **Source of truth:** `D:\Storage\career_phd_daiict_work\Thesis\Maulik201121003.tex`
  and `Chapters/*.tex`, `Backmatter/*.tex`

Rule for every stage: implement from the thesis first, then cross-check against the old
MATLAB code. Expect results to be *similar*, not identical. The thesis used HTK for
MFCC/PLP, so a Python front end will not match bit for bit.

---

## 1. Roadmap

| Stage | Scope | Thesis reference |
|---|---|---|
| 0 | pixi env, repo skeleton, test runner | requirements.md |
| 1 | Audio base: wav I/O, resampling, pre-emphasis, framing, windowing, power spectrum, energy, TEO | ExpSetup §Front-end; Warped_Feature appendix (time resampling) |
| 2 | Features: mel filterbank (+ warped `M_α`), MFCC + Δ/ΔΔ, PLP, MFCC-TMP | ExpSetup §Acoustic Representation; Warped_Feature appendix |
| 3 | ML: LBG VQ codebook → GMM by EM (diag cov), log-likelihood | ExpSetup §Posterior Representation; appendix "Flowchart of VQ" (`Backmatter/Algorithm_LC`) |
| 4 | Posteriorgrams: Gaussian posteriorgram, GMM-based iterative VTLN posteriorgram, mixture-of-GMMs posteriorgram | Representation §GMM-based VTLN, Alg. `pseudocode_vtlnwarping`; §Mixture of GMMs |
| 5 | Matching: symmetric-KL local distance, subDTW (LC1/LC2/LC3, S/T/P matrices), warping-path selection, z-norm scoring; plain DTW, fastDTW, partial matching | ExpSetup §Searching, §Detection; Matching §Partial Matching |
| 6 | Indexing / search-space reduction: feature reduction (phone-segment averaging), segment-level BoAW tf-idf | Matching §Feature Reduction, §BoAW Model (*confirm details next cycle*) |
| 7 | Evaluation: p@N, MAP, recall, TWV/MTWV, C<sub>nxe</sub><sup>min</sup>, DET | survey §Performance Evaluation Metrics; Appendix θ selection, role of β |

Later (out of scope until stages 1–7 are stable): re-scoring with detection sources
(DetectionSources chapter), score-level fusion, phonetic posteriorgrams.

---

## 2. Component inventory (from the thesis)

**Data**
- TIMIT (HF `Siyong/speech_timit`): queries come from the train set, documents from the test set; `/sa/` sentences excluded.
  - Q-20: 20 keywords (Table `Table:TIMITdata`).
  - Q-84: rule-defined (7–20 test occurrences, ≥ 6 letters). Ranked evaluation.
- SWS 2013: `D:\Storage\research_data\speech_qbe-std\sws2013Database.tgz`. 8 kHz, 16-bit; 10762 test utterances, 505 dev and 503 eval queries.
- QUESST 2014: already extracted at `D:\Storage\research_code_qbe_std\hquest\data\quesst14Database\quesst14Database\` (tgz also in research_data). 8 kHz; 12492 test utterances, 560 dev and 555 eval queries; match types T1/T2/T3.
- Scoring tools: `scoring_atwv_sws2013_full.tgz`, the reference for MTWV and C<sub>nxe</sub>.

**Front end**
- MFCC: 25 ms window, 10 ms shift, 26 mel filters over 0–4000 Hz, 13 DCT coefficients, plus Δ and ΔΔ (39-dim).
- Mel warping: `M_α(f) = 2595·log10(1 + f/(700α))`, α ∈ {0.88, 0.90, …, 1.12} (13 values). Filters above the cutoff map to Nyquist; the thesis cutoff is 3500 Hz / 7000 Hz.
- Warped features by time resampling are an alternative (`x(at) ↔ X(f/a)/|a|`).
- TEO: `ψ{x(n)} = x²(n) − x(n+1)·x(n−1)`. MFCC-TMP uses TEO subband energy computed from the time-domain subband signal.
- MFCC-TMP DCT: `Σ_j S_ij·cos(k(j−0.5)π/N_F)`, N_F = 26, N_c = 13.

**ML / posteriorgram**
- GMM with 64 or 128 components, initialized from an LBG VQ codebook, trained by EM.
- Posterior: `P(C_k|o_t) = π_k N(o_t; μ_k, Σ_k) / Σ_j π_j N(o_t; μ_j, Σ_j)`.
- VTLN: train λ_init on α = 1, pick per-utterance α̂ = argmax_α P(X^α|λ), retrain, and iterate 5 times. The same procedure gives test/query α̂ against the final model.

**Matching / detection**
- Local distance: symmetric KL between posterior vectors (needs a probability floor for log 0).
- subDTW returns S (accumulated), T (path length), P (start frame). LC2 neighbours are {(i,j−1), (i−1,j−1), (i−2,j−1)} and LC2 is the default.
- A path is valid when 0.5 ≤ (end − start)/N ≤ 2. Distance = S(i,N)/T(i,N).
- SWS 2013: up to 7 best paths per pair, N_top = 1000 per query.
- QUESST 2014: one score per utterance, N_top = all utterances.
- Score normalization: `s_i = −(ds_i − μ_q)/σ_q`, using sample std (N−1).

**Metrics**
- p@N, AP/MAP, recall.
- TWV(θ) = 1 − mean_q(P_miss + β·P_fa), with β = 66.66 for SWS 2013 and 12.49 for QUESST 2014. MTWV = max over θ.
- C<sub>nxe</sub> and C<sub>nxe</sub><sup>min</sup>, the latter minimized over an affine calibration `γ·llr + δ`.
- Ready-made test case (survey.tex): hits = `t,t,f,f,t,f,f,t,f,f`, N = 4 → **p@N = 50 %**, **AP = 0.775**.

## 3. Reproduction targets

TIMIT Q-20 (Table `Tab:TIMITVTLNPerformance1`, 64 mixtures):

| Feature | No VTLN p@N / MAP | GMM-VTLN p@N / MAP |
|---|---|---|
| MFCC | 34.91 / 36.71 | 36.26 / 39.62 |
| PLP | 35.50 / 37.58 | 37.48 / 39.95 |
| MFCC-TMP | 40.03 / 41.50 | 42.88 / 45.52 |

SWS 2013 MTWV by local constraint (Table `Tab:LocalConst`, phonetic posteriorgrams). For
CZ, Dev LC1/LC2/LC3 = 0.348 / 0.375 / 0.356. This depends on the external BUT phone
recognizer, so it is low priority.

**First milestone:** an end-to-end Python pipeline with MFCC, a 64-component Gaussian
posteriorgram and subDTW-LC2 that lands near **p@N ≈ 35 / MAP ≈ 37** on TIMIT Q-20.

---

## 4. Open questions (configurable; do not hard-code a guess)

Verify each of these against the MATLAB feature repo
(`research_myMATLAB_codes/Analysis/Feature_Extraction`). Until then, expose each one as a
parameter, with the HTK-like value as the default *and a comment saying it is unverified*.

1. Pre-emphasis coefficient (HTK default 0.97?), window type (Hamming?), FFT size, cepstral liftering (22?), and whether c0 or log-energy is used.
2. TIMIT sample rate. TIMIT is 16 kHz, but the thesis states mel filters over 0–4000 Hz, which suggests downsampling to 8 kHz. Stage 1 must support resampling, and the default stays open.
3. The Q-84 query list. It has to be derived from TIMIT word transcripts using the rule above.
4. Phone-segmentation method used for feature reduction (stage 6).

## 5. Thesis errata (do NOT copy these)

- Alg. `pseudocode_vtlnwarping`: `WHILE (k ≥ N_iter)` should be `k < N_iter`.
- Alg. `pseudocode_warping_path_select`: `G` and `CG` are re-initialized inside the per-frame loop. Initialize them once, before the loop.
- Alg. `pseudocode_STP_Computation_LC2`: the first-rows block writes `T(1,j)` / `P(1,j)=i` inside an `i=1..2` loop. It should write `T(i,j)` / `P(i,j)`.
- subDTW init text (eqs. `Eq:DTW_inti1/2`) mixes the i/j roles. Follow the algorithm boxes instead.
- Settle any remaining ambiguity with `D:\Storage\research_code_qbe_std\matlab\Fx_do_SDTW.m`.

## 6. Risks and dependencies

- Phonetic posteriorgrams (CZ/HU/RU) need the external BUT phoneme recognizer, so Gaussian posteriorgrams come first.
- Never extract tarballs into this repo and never commit audio or data. Data paths come from config.
- The GitHub MCP is currently down (expired token). Read the MATLAB repos with `gh` or the web-fetch agent.

---

## 7. Stage 0 + Stage 1: atomic tasks (Executor)

Conventions for every task:
- One task per commit, pushed right away.
- Commit message ≤ 10 words, no tool signatures.
- Each module stays under 400 lines.
- PEP 8, descriptive names, and a test file per module.
- Package name: `qbestd` under `src/`.

### T0.1: pixi environment
- **Files:** `pixi.toml`
- **Do:** create a `default` env with python 3.11, numpy, scipy, soundfile and pytest. Add a task `test = "pytest -q"`. Add a separate `demo` feature with gradio and matplotlib, so the core env stays lean.
- **Accept:** `pixi run test` runs, even with zero tests collected.
- **Commit:** `setup pixi environment`

### T0.2: Repo skeleton and ignore rules
- **Files:** `.gitignore`, `src/qbestd/__init__.py`, `tests/__init__.py` (if needed), `demo/.gitkeep`, `pyproject.toml` (minimal, for the src-layout import path)
- **Do:** ignore `.pixi/`, `.claude/`, `__pycache__/`, `*.wav`, `*.flac`, `data/` and `outputs/`.
- **Accept:** `pixi run python -c "import qbestd"` succeeds.
- **Commit:** `add package skeleton and gitignore`

### T0.3: README
- **Files:** `README.md` (≤ 40 lines)
- **Do:** state the purpose, list stages 1–7, explain how to run tests and the demo, and link `docs/plan.md`.
- **Commit:** `add concise readme`

### T1.1: Audio I/O
- **Files:** `src/qbestd/audio/io.py`, `tests/audio/test_io.py`
- **Functions:**
  - `load_audio(path) -> (samples: float64 ndarray in [-1, 1], sample_rate: int)`
  - `save_audio(path, samples, sample_rate)`
- **Do:** downmix to mono. Raise a clear error for missing files.
- **Tests:** a round trip through a temp wav keeps the sample rate and keeps values within 1/32768; a stereo file is downmixed to mono.
- **Commit:** `add wav load and save`

### T1.2: Resampling
- **Files:** `src/qbestd/audio/resample.py`, tests
- **Functions:**
  - `resample_audio(samples, source_rate, target_rate)` using `scipy.signal.resample_poly`
  - `scale_time_axis(samples, warp_factor)`, the time-resampling route to VTL warping from the Warped_Feature appendix
- **Tests:**
  - 16 k → 8 k halves the length (±1 sample).
  - A 1 kHz tone keeps its peak frequency.
  - Identity when the rates are equal.
  - Under `scale_time_axis` with α, the peak frequency moves by the expected factor.
- **Commit:** `add resampling utilities`

### T1.3: Pre-emphasis
- **Files:** `src/qbestd/audio/preprocess.py`, tests
- **Functions:**
  - `apply_preemphasis(samples, coefficient=0.97)`, with the comment `# unverified default`
  - `remove_dc_offset(samples)`
- **Tests:** matches `y[n] = x[n] − c·x[n−1]` with `y[0] = x[0]`; coefficient 0 is the identity; output is zero mean after DC removal.
- **Commit:** `add pre-emphasis and dc removal`

### T1.4: Framing
- **Files:** `src/qbestd/audio/framing.py`, tests
- **Functions:**
  - `frame_signal(samples, sample_rate, frame_ms=25.0, shift_ms=10.0) -> (n_frames, frame_len)`
  - `count_frames(n_samples, frame_len, shift_len)`
- **Convention:** HTK-style, with no padding: `n_frames = 1 + (n_samples − frame_len) // shift_len`. Return 0 frames if the signal is shorter than one frame. Document this in the docstring.
- **Tests:**
  - 1 s at 8 kHz gives 98 frames of 200 samples.
  - Frame k starts at `k·shift`.
  - Short input returns shape `(0, frame_len)`.
- **Commit:** `add signal framing`

### T1.5: Windowing
- **Files:** `src/qbestd/audio/windowing.py`, tests
- **Functions:** `make_window(name, length)` supporting hamming, hann and rectangular; `apply_window(frames, window)`.
- **Tests:** shape preserved; Hamming endpoints are 0.08; rectangular is the identity; unknown names raise `ValueError`.
- **Commit:** `add analysis windows`

### T1.6: Power spectrum
- **Files:** `src/qbestd/audio/spectrum.py`, tests
- **Functions:**
  - `next_power_of_two(n)`
  - `power_spectrum(frames, n_fft=None) -> (n_frames, n_fft//2 + 1)`, where None means the next power of two
  - `magnitude_spectrum(...)`
  - `fft_bin_frequencies(n_fft, sample_rate)`
- **Tests:**
  - A pure tone peaks at the expected bin.
  - Parseval check, within tolerance.
  - A 200-sample frame uses n_fft = 256.
- **Commit:** `add power spectrum`

### T1.7: Short-time energy and TEO
- **Files:** `src/qbestd/audio/energy.py`, tests
- **Functions:**
  - `short_time_energy(frames)`, the l² energy per frame
  - `log_energy(frames, floor=1e-10)`
  - `teager_energy(samples)`: ψ{x(n)} = x²(n) − x(n+1)x(n−1), edges padded by replicating neighbours
  - `frame_teager_energy(frames)`, the mean TEO per frame
- **Tests:**
  - For `A·cos(Ωn)`, the TEO interior equals `A²·sin²(Ω)` within 1e-9.
  - Energy of a frame of ones equals the frame length.
  - The log floor is applied to silence.
- **Commit:** `add short-time and teager energy`

### T1.8: Dataset path config
- **Files:** `src/qbestd/config.py`, tests
- **Functions:** `DatasetPaths` dataclass with fields timit, sws2013, quesst2014 and scoring.
  - Read from env vars (`QBESTD_TIMIT`, …), falling back to a git-ignored `paths.local.toml`.
  - Defaults: the QUESST 2014 extracted folder and the research_data tgz paths listed in §2.
- **Tests:** an env var overrides the default; a missing path gives a clear error only when accessed.
- **Commit:** `add dataset path configuration`

### T1.9: Stage 1 pipeline helper
- **Files:** `src/qbestd/audio/pipeline.py`, tests
- **Function:** `AudioFrontEndConfig` (sample_rate, frame_ms, shift_ms, preemphasis, window, n_fft) plus `prepare_frames(samples, sample_rate, config) -> windowed frames`. It chains resample → DC removal → pre-emphasis → frame → window.
- **Tests:** shape check on a synthetic 1 s signal; the config round-trips to and from a dict.
- **Commit:** `add audio front-end pipeline`

### T1.10: Gradio demo for Stage 1
- **Files:** `demo/stage1_audio_demo.py` (≤ 200 lines)
- **Do:**
  - Inputs: audio upload or mic, plus sliders for frame_ms, shift_ms, pre-emphasis, window and target sample rate.
  - Outputs: waveform, spectrogram (log power), short-time energy and TEO curves, and the frame count.
  - Add a short usage note at the top of the page.
  - Add pixi task `demo-stage1` in the `demo` feature.
- **Accept:** `pixi run -e demo demo-stage1` launches; the core functions are imported from `qbestd`, not duplicated.
- **Commit:** `add stage 1 gradio demo`

### T1.11: Inspect the TIMIT HF dataset (read-only)
- **Do:**
  - Find out the format of `Siyong/speech_timit` (audio encoding, sample rate, whether word and phone transcripts exist, and the splits) *without* adding the `datasets` dependency. Use the HF API / `huggingface_hub` only if necessary.
  - Record the findings in `docs/data_notes.md`.
- **Accept:** the doc answers open question 2's input side and whether Q-20 / Q-84 can be derived.
- **Commit:** `document timit dataset format`

**Stage 1 definition of done:**
- T0.1–T1.11 are merged on `main` and `pixi run test` is green.
- Every module is under 400 lines.
- The Reviewer has written `handoff_request.md` covering the open questions in §4.
