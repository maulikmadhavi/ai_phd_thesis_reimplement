# Handoff Request: Reviewer → Codex

- **Cycle:** 2 + 2b
- **From:** Claude Code Reviewer
- **To:** Codex. Write only `handoff_response.md` (replacing the cycle 1 response) and commit
  it. Do not touch any other file.
- **Plans under review:**
  - `docs/plan.md` at `11862f2`: Stage 1 fix-ups F1–F7 and Stage 2 (acoustic features)
    T2.1–T2.11. Sections 1–4 below, Q1–Q13.
  - `docs/plan.md` at `9498174`, §9: cycle 2b, TIMIT word alignment A1–A5. **Section 4**
    below, Q14–Q20.
- **Status:** COMPLETE. Cycle 2 (18 tasks, head `a0c46c4`) and cycle 2b (5 tasks, head
  `4d6f1af`) are committed and reviewed.
- **D1 (user decision, resolved 2026-11-14):** no LDC `.WRD` files. Query boundaries come from
  automatic forced alignment on the HF copy. The user picked the aligner
  `Scicom-intl/Where-Words-Begin-and-End-Whisper-Large-V3`, which replaces the Reviewer's
  earlier MFA proposal. Results are labelled approximate against the thesis.

## 1. Commits to review

| Commit | Task | Files | Reviewer verdict |
|---|---|---|---|
| `609baf2` exec: validate pcm range in save_audio | F1 | `audio/io.py`, tests | OK |
| `b734af3` exec: validate rates and anti-alias time scaling | F2 | `audio/resample.py`, tests | OK; see Q1 |
| `78d4ea2` exec: validate framing parameters | F3 | `audio/framing.py`, tests | OK |
| `21027a8` exec: reject short or invalid fft lengths | F4 | `audio/spectrum.py`, tests | OK |
| `2855038` exec: remove absolute defaults from dataset config | F5 | `config.py`, `paths.local.toml.example`, tests | OK; adds a check beyond the plan (see Q2) |
| `315a732` exec: plot signed teager energy in demo | F6 | `demo/stage1_audio_demo.py` | OK; builds |
| `af02b45` exec: qualify timit split and confirm sample rate | F7 | `docs/data_notes.md` | OK; 16 kHz observed on row 0 only |
| `6d62dcf` exec: add frequency scales and vtln warping | T2.1 | `features/scales.py`, tests | OK; see Q3 |
| `d682de8` exec: add mel filterbank with vtln warping | T2.2 | `features/filterbank.py`, tests | OK; see Q3, Q4 |
| `f7bb3e9` exec: add dct and liftering utilities | T2.3 | `features/cepstral.py`, tests | OK; see Q5 |
| `f82356d` exec: add delta and acceleration features | T2.4 | `features/deltas.py`, tests | OK |
| `be80918` exec: add mfcc extractor | T2.5 | `features/mfcc.py`, `features/frontend.py`, tests | OK; see Q6 |
| `35ce7f6` exec: add lpc analysis helpers | T2.6 | `features/lpc.py`, tests | OK; also contains unrelated line-length fixes |
| `eabc383` exec: add plp extractor | T2.7 | `features/plp.py`, tests | OK; see Q7 |
| `c8c5d98` exec: add mfcc-tmp extractor | T2.8 | `features/mfcc_tmp.py`, `audio/spectrum.py`, tests | OK; see Q8 |
| `51c71f6` exec: add unified and warped feature extraction | T2.9 | `features/extract.py`, tests | OK; see Q9 |
| `eecc784` exec: add stage 2 features demo | T2.10 | `demo/stage2_features_demo.py` (124 lines), `pixi.toml` | OK; builds |
| `a0c46c4` exec: document feature parity with matlab and htk | T2.11 | `docs/feature_parity.md` | OK; see Q10 |

Diff range: `git diff 11862f2 a0c46c4`

Cycle 2 definition of done (plan §8): all tasks are on `main`, tests are green, every module
is under 400 lines, and this handoff covers D1 and the parity gaps. **Met.**

## 2. Reviewer checks done

- `pixi run test`: **178 passed** (1.37 s) at `a0c46c4`, with a clean working tree.
- Every module is under 400 lines. The largest source file is `config.py` at 100 lines.
- In the demo environment, both `demo/stage1_audio_demo.py` and `demo/stage2_features_demo.py`
  import and `build_demo()` without error. Neither was launched in a browser.
- I hand-checked these against their standard forms:
  - Levinson–Durbin update and LPC→cepstrum recursion (HTK `LPC2Cepstrum`, c0 = log gain).
  - rastamat `dolpc` autocorrelation and the PLP edge-band copy.
  - The `Deltacep.m` regression.
  - The `Fx_vtln_warp.m` piecewise warp with 0.05 back-off.
  - The orthonormal DCT-II.
  - The MFCC-TMP subband construction: symmetric mirrored weights → IFFT → lagged TEO → sum.
- Every commit message uses the `exec:` prefix and has no tool trailers.

**Minor deviations (non-blocking):**
- `35ce7f6` (LPC) also carries line-length fixes in `scales.py`, `deltas.py`,
  `filterbank.py`, `mfcc.py` and `features/__init__.py`. It's not strictly one task per commit.
- 37 lines exceed 79 characters (PEP 8). They're spread over 14 files, mostly tests, plus
  `audio/pipeline.py` (3), `config.py` (2) and both demos.
- `tests/features/test_mfcc_tmp.py::test_floor_hits_on_noise_are_counted_and_output_finite`
  only prints the floor-hit count. Its assertion `0 <= hits <= size` is always true. Plan §6
  asked to "log every floor hit in tests".
- `scale_waveform` peak-normalises the raw waveform *before* DC removal. MATLAB subtracts the
  mean first. This only changes an overall scale, so only c0 shifts.

## 3. Questions for Codex

**Code review**

1. `resample.scale_time_axis` anti-aliasing uses `firwin(101)` + `filtfilt` at a cutoff of
   `0.95·Nyquist/α`. `padlen` is capped at `len − 1` for short signals. Is 101 taps
   adequate for α ≤ 1.12 at 8 kHz? Is the short-signal `filtfilt` edge behaviour acceptable?
2. F5 also rejects unknown keys in `paths.local.toml` with `ValueError`, which the plan
   didn't ask for. Keep this, or downgrade it to a warning?
3. **VTLN cutoff at 16 kHz with a 4 kHz band.** `warp_frequency_piecewise` takes f0 from
   the *sampling* Nyquist, so f0 = 7000 Hz at 16 kHz. With `high_hz = 4000`, every filter
   then sits on the pure linear part `(2−α)·f`, and for α < 1 the top filters see content
   above 4 kHz. The thesis cutoff (3500 Hz) is tied to a 4 kHz band. Should the warp's
   Nyquist and cutoff follow `high_hz` (the band edge) rather than `fs/2` when
   `high_hz < fs/2`? What does `Fx_mfcc_vtmp_cep.m` (16 kHz, fH 4000) do?
4. `mel_filterbank` with α ≠ 1 warps the bin frequencies and keeps the triangles fixed. For
   α > 1 the peaks move to higher bins, which the tests assert. Can you confirm this direction
   matches `Fx_vtln_warp.m` usage in FP:47, and the thesis convention that α > 1 means a
   shorter vocal tract?
5. `dct_cepstra(include_c0=False)` returns c1..c13, keeping 13 coefficients, rather than
   dropping c0 to leave 12. `lifter_cepstra(first_index=1)` keeps the lifter aligned. Is
   this the right reading of the thesis MFCC-TMP formula (k = 1..N_c)?
6. MFCC peak normalisation uses `max|x|`, as `Fx_mfcc_vtmp_cep.m` does. `Fx_mfcc.m` (FM:29)
   uses `max(x)`. Do you agree to keep `max|x|` for both, given that it only shifts c0?
7. PLP:
   - Equal-loudness weights are evaluated at the *forward*-warped centre
     `warp(center)`. FP:57 seems to do the same. But since the bins are warped by
     `(2−α)·f`, a filter's physical centre is the *inverse* warp of its nominal centre. Is the
     forward warp a faithful copy of MATLAB, or a MATLAB bug we shouldn't copy?
   - `lpc_order` is 12 (HTK) against MATLAB's 8. Which should be the default for reproducing
     the thesis PLP numbers?
   - DC removal is still applied to PLP even though FP does none. Should it be off by default?
8. MFCC-TMP:
   - `teager_energy_lagged` is a guess because `vteo.m` isn't public. Edges are replicated
     and the sum is unnormalised.
   - Subband TEO is summed over the full zero-padded `n_fft` IFFT frame, not just the
     original 200 samples.
   - The `"p"` (phase-only) option takes `np.angle`, which isn't conjugate-symmetric. The
     real part of its IFFT is then taken.

   Are these consistent with `Fx_mfcc_vtmp_cep.m` lines 54–78?
9. `extract_features(kind, warp_factor=1.0, config)` always overrides `config.warp_factor`,
   so a config with `warp_factor = 1.1` is silently ignored unless the argument is passed
   too. Should the argument default to `None`, meaning "use the config"? Separately,
   `extract_warped_bank` recomputes the whole front end (frames and STFT) 13 times when only
   the filterbank changes. Is it worth caching before Stage 4?
10. `docs/feature_parity.md`: the HTK column was written from memory, and the thesis column
    copies `plan.md` §2 without re-reading the `.tex`. Can you spot-check the cells that matter
    for reproduction against the thesis: band, filter count, c0 and deltas for PLP and
    MFCC-TMP? Is anything wrong?
11. Any other correctness, PEP 8 or test-coverage issues? In particular, should the
    MFCC-TMP floor-hit test assert a bound on noise?

**Open questions carried forward**

12. Plan §4 #14: did the thesis downsample TIMIT to 8 kHz? Data is confirmed 16 kHz on all 6300 rows (cycle 2b).
    MATLAB defaults to 16 kHz with fH 4000 for MFCC-TMP but fH `fs/2` for MFCC. Which
    `(sample_rate, high_hz)` pair should each extractor default to?
13. Missing `Fx_melfiltbank.m`: is there any other source (thesis appendix, rastamat
    `fft2melmx`, an old copy) that pins down the triangle normalisation (unit peak versus unit
    area) and edge placement?

## 4. Cycle 2b: TIMIT word alignment (A1–A5)

### Commits to review

| Commit | Task | Files | Reviewer verdict |
|---|---|---|---|
| `7fd4848` exec: add align pixi environment | A1 | `pixi.toml`, `pixi.lock` | OK; torch only in `align`, `pyarrow` in core |
| `bb7ba6c` exec: add hugging face timit loader | A2 | `data/timit_hf.py`, tests | OK; takes an extra `split` argument (plan deviation 2) |
| `a957ba6` exec: add whisper word aligner wrapper | A3 | `alignment/word_aligner.py`, `alignment/manifest.py`, tests | OK; see Q14, Q15 |
| `7054dc0` exec: align timit words and record notes | A4 | `alignment/run.py`, `alignment/sanity.py`, `docs/alignment_notes.md`, `.gitignore`, tests | OK; see Q16–Q18 |
| `4d6f1af` exec: record d1 resolution in data notes | A5 | `docs/data_notes.md` | OK |

Diff range: `git diff 9498174 4d6f1af -- . ':!pixi.lock'`

Cycle 2b definition of done (plan §9): A1–A5 are on `main`; core tests are green with no torch
and no network; manifests exist locally with hashes and checks recorded. **Met.**

### Reviewer checks done

- `pixi run test` (core env): **233 passed, 1 skipped** (the real-model smoke test, gated by
  `QBESTD_RUN_ALIGNER=1`).
- **Remote code check.** I read the cached `align.py` at the pinned revision. Its SHA-256
  `8f7a3590…0ee0` matches the pin. It does no file, network or subprocess I/O and doesn't use
  `trust_remote_code`. `from_pretrained` only gets `*.json` and `*.safetensors` (no pickle
  weights, per `allow_patterns`). `load_align_module` refuses on a hash mismatch and never
  touches `sys.path`.
- **Nothing derived is committed.** Manifests, weights, parquet, `outputs/` and the spot-check
  WAVs are all git-ignored (`.gitignore:10 outputs/`, `*.wav`). The CC BY-NC 4.0 licence is
  recorded in both docs.
- The Executor reports the full run with 6300/6300 rows aligned and 0 failed. All rows are
  16 kHz, because the loader raises otherwise. Median word duration is 0.285 s, and 15 rule
  violations (all < 20 ms) fall in 9 rows. All of this is documented with row indices in
  `docs/alignment_notes.md`. I didn't re-run the 8-minute alignment, but `outputs/alignment/`
  holds the summary, sanity report and manifests.
- Every module is under 400 lines (largest: `sanity.py`, 172).
- **Plan deviations:**
  1. `.gitignore` `data/` became `/data/`, so it no longer ignores `src/qbestd/data`. Correct.
  2. `iter_timit_rows` takes a `split` argument.
  3. `check_segments(expected_words=)` is extended.
  4. `align_rows_detailed` / `RowResult` were added.
  5. `sanity.py`, `--limit` and the rows TSV are extras.

  All are reasonable and covered by tests.

**For the user (not Codex):** the 10 spot-check WAVs in `outputs/alignment/spot_check/` have
not been listened to yet.

### Questions for Codex (cycle 2b)

14. **Vacuous rules in `check_segments`.** `align.py` (lines 146–151) already clamps each
    start to at least the previous start, and each end to at least start + 0.01 s. So the
    "decreasing starts" and "end ≤ start" rules can never fire on real output, and a collapsed
    run of words is caught only when it falls under 20 ms. Should `check_segments` add a rule
    for **consecutive words sharing the same start** (the collapse signature in rows 908, 3213,
    3505 and test 1151), so Stage 7 can drop those rows cleanly rather than relying on a
    duration threshold?
15. **`normalize_transcript` units.** The aligner is given our tokens as a word list, so
    `align.py`'s own `words_of` (NFC normalisation, markup removal, dropping tokens without a
    letter or digit) is bypassed. Our tokens keep hyphenated compounds as one word and inner
    apostrophes. Is there a TIMIT transcript form that splits into a unit the model handles
    badly, for example a hyphenated compound, or a digit if any appear? Should we NFC-normalise
    too?
16. **Overlapping boundaries.** 12,732 of 38,197 adjacent train pairs overlap, by up to
    0.23 s. For cutting queries, should Stage 7:
    - use `[start − pad, end + pad]` as is,
    - clip each word to the midpoint of any overlap with its neighbours, or
    - drop keywords overlapping a neighbour by more than X ms?
17. **Accuracy claim and speaker leakage.** The model was trained on TIMIT *training*
    speakers' human boundaries, and this HF copy's split was redrawn. So many HF "test" rows
    may come from speakers the aligner saw in training. That doesn't affect QbE scoring
    (alignment only cuts queries and labels), but should `alignment_notes.md` say the card's
    10.7 ms figure isn't transferable to this split?
18. **Sanity-check strength.** The energy check (word mean > the utterance's 10th-percentile
    frame energy) passed 20/20 but is a low bar. Is there a cheap, stronger automatic check
    without reference `.WRD` files? For example, re-align a time-shifted or concatenated copy
    and check that the boundaries shift accordingly, or cross-check against a second aligner on
    a sample of 50 rows.
19. **Reproducibility.** The aligner runs in bf16 on GPU, so a re-run may change the last digit
    of some times and therefore the manifest SHA-256s. Is recording the hashes still useful, or
    should we record a tolerance-based fingerprint, such as summary statistics per split?
20. Any other correctness, PEP 8, security or test-coverage issues in A1–A5? In particular:
    `pytorch-gpu = "*"` with `cuda = "12"`, and pinning only by `pixi.lock`.

## 5. Response format requested

Write `handoff_response.md` with one section per question number. Mark each as
**agree / change requested / unknown**. For a requested change, give the file and the
concrete change. Commit it as `handoff_resp: cycle 2 and 2b review`.
