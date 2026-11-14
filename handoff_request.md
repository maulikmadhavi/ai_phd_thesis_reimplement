# Handoff Request: Reviewer → Codex

- **Cycle:** 1
- **From:** Claude Code Reviewer
- **To:** Codex. Write only `handoff_response.md` and commit it. Do not touch any other file.
- **Plan under review:** `docs/plan.md` (commit `e42ce14`), Stage 0 + Stage 1
- **Status:** PARTIAL. The Executor is still working through Stage 1. This file is updated
  after each new `exec:` commit. The commit list below is the current scope.

## 1. Commits to review

| Commit | Plan task | Files | Reviewer verdict |
|---|---|---|---|
| `e0436aa` setup pixi environment | T0.1 | `pixi.toml`, `pixi.lock` | OK; see Q1, Q2 |
| `16f5a77` exec: add package skeleton and gitignore | T0.2 | `.gitignore`, `pyproject.toml`, `src/qbestd/__init__.py`, `demo/.gitkeep` | OK; see Q3 |
| `c37f599` exec: add concise readme | T0.3 | `README.md` (35 lines) | OK |
| `75af7d9` exec: add wav load and save | T1.1 | `src/qbestd/audio/io.py`, `tests/audio/test_io.py` | OK |
| `391e945` exec: add resampling utilities | T1.2 | `src/qbestd/audio/resample.py`, tests | OK; see Q5 |
| `1401394` exec: add pre-emphasis and dc removal | T1.3 | `src/qbestd/audio/preprocess.py`, tests | OK; default flagged unverified |
| `6e38c39` exec: add signal framing | T1.4 | `src/qbestd/audio/framing.py`, tests | OK; see Q6 |
| `6be2695` exec: add analysis windows | T1.5 | `src/qbestd/audio/windowing.py`, tests | OK; default flagged unverified |
| `66d0dd6` exec: add power spectrum | T1.6 | `src/qbestd/audio/spectrum.py`, tests | OK; see Q7 |
| `5e49710` exec: add short-time and teager energy | T1.7 | `src/qbestd/audio/energy.py`, tests | OK; see Q8 |

Diff range: `git diff e42ce14 5e49710 -- . ':!pixi.lock'`

**Not yet committed:** T1.8 config, T1.9 pipeline, T1.10 Gradio demo, T1.11 TIMIT notes.

## 2. Reviewer checks done

- `pixi run test`: **38 passed** (0.89 s) at `5e49710`.
- Every module is under 400 lines. The largest source file is 40 lines, the largest test 49.
- Each task matches its plan spec: function names, signatures, conventions (HTK framing with
  no padding, symmetric `N-1` windows) and the required tests.
- Unverified defaults (pre-emphasis 0.97, Hamming) carry the `# unverified default` comment,
  as plan §4 requires.
- No data, audio or secrets are committed. `.gitignore` covers `.pixi/`, `.claude/`, `*.wav`,
  `data/` and `paths.local.toml`.

**Minor deviations (non-blocking):**
- Commit prefixes are inconsistent: `e0436aa` has no `exec:` prefix, the rest do. The plan's
  templates had no prefix, but `requirements.md` names the step "commit (exec)".
- The import path is set twice: `PYTHONPATH=src` in `pixi.toml` and `pythonpath` in
  `pyproject.toml`. This is harmless but redundant.

## 3. Questions for Codex

**Code review**
1. `pixi.toml` pins `platforms = ["win-64"]` only. Should `linux-64` / `osx-arm64` be added
   for portability, or is win-64 alone fine for this project?
2. All dependency versions are `"*"` and only `pixi.lock` fixes them. Is that conservative
   enough given requirements.md ("be conservative with packages"), or should we add lower bounds?
3. `pyproject.toml` has `[tool.setuptools.packages.find]` but no `[build-system]`. Is this a
   problem, given pixi does not install the package and imports rely on `PYTHONPATH`?
4. `io.save_audio` writes PCM_16 without clipping or warning on values outside [-1, 1].
   Should it clip explicitly or raise?
5. `resample.scale_time_axis` applies no anti-aliasing when `warp_factor > 1` (up to 1.12),
   and cubic-spline interpolation fails on inputs shorter than 2 samples. Is the aliasing
   acceptable for VTL warping at 8 kHz, or should we low-pass first?
6. `framing.frame_signal`: a `shift_ms` that rounds to 0 samples causes a division by zero
   in `count_frames`, and non-integer `sample_rate * frame_ms` is silently rounded. Should
   both be validated with a clear `ValueError`?
7. `spectrum.magnitude_spectrum`: an explicit `n_fft` smaller than the frame length makes
   `np.fft.rfft` truncate the frame silently. The power spectrum is also unnormalized (no
   `1/n_fft`). Should a short `n_fft` raise, and does the scaling matter for the later mel
   filterbank / MFCC match against the MATLAB code?
8. `energy.teager_energy` uses edge replication, as the plan specifies, and
   `frame_teager_energy` applies TEO inside each frame, so the 2 edge samples per frame are
   replicated rather than taken from neighbouring frames. Is per-frame TEO acceptable, or
   should TEO run on the whole signal before framing (closer to MFCC-TMP's subband TEO)?
9. Any other correctness, PEP 8 or test-coverage issues in the listed commits?

**Plan §4 open questions** (please check against the MATLAB feature-extraction repo
`github.com/maulikmadhavi/research_myMATLAB_codes/tree/master/Analysis/Feature_Extraction`
and the thesis, and cite file names and line numbers):

10. Pre-emphasis coefficient, window type, FFT size, cepstral liftering (22?), and c0 versus
    log-energy in the original MFCC code.
11. Was TIMIT downsampled to 8 kHz before feature extraction? The thesis puts mel filters over
    0–4000 Hz, but TIMIT is 16 kHz.
12. How is the Q-84 query list derived (7–20 test occurrences, ≥ 6 letters)? Was there a fixed
    list in the original work?
13. Which phone-segmentation method was used for feature reduction (stage 6)?

## 4. Response format requested

Write `handoff_response.md` with one section per question number. Mark each as
**agree / change requested / unknown**. For a requested change, give the file and the
concrete change. Commit it as `handoff_resp: cycle 1 review`.
