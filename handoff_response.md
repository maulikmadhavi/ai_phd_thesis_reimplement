# Handoff Response: Cycle 1 Stage 0 and Stage 1 Review

Scope: `handoff_request.md` at commit `2b212fd`. These are review decisions for the next Orchestrator/Executor cycle; this response changes no implementation files.

## 1. Pixi platforms — **agree**

Keep `win-64` for the current Windows reproduction environment. Add `linux-64` or `osx-arm64` only when that platform will be run and its lockfile solved and tested. Portability is not a Stage 1 acceptance criterion.

## 2. Dependency versions — **agree**

The small core dependency set and committed `pixi.lock` meet the request to be conservative with packages. The lockfile fixes exact resolved versions. Lower bounds would constrain a fresh solve but would not improve reproducibility of this locked environment; add bounds when a supported compatibility range has been tested.

## 3. Build system — **agree**

The current workflow imports from `src` through Pixi/pytest and does not build or install a wheel. A `[build-system]` is appropriate when packaging is added, with explicit `setuptools.build_meta` and a tested editable install. Its absence does not block Stage 1.

## 4. PCM output range — **change requested**

In `src/qbestd/audio/io.py`, make `save_audio` reject non-finite samples and samples outside `[-1, 1]` with `ValueError` before writing PCM_16. Silent clipping would conceal upstream amplitude errors. Add boundary and rejection tests in `tests/audio/test_io.py`. Also document that `load_audio` cannot guarantee `[-1, 1]` for floating-point WAV inputs unless it validates them.

## 5. Time-axis scaling — **change requested**

In `src/qbestd/audio/resample.py`, handle zero-length and one-sample inputs explicitly and test them. For `warp_factor > 1`, apply an anti-alias low-pass before sampling at `warp_factor * n`, with cutoff below `Nyquist / warp_factor`; test a near-Nyquist tone. At 8 kHz and factor 1.12, input above about 3.57 kHz can fold below 4 kHz, so cubic interpolation alone does not make the operation alias-safe. Keep the filter choice explicit for comparisons with the thesis's warping method.

## 6. Frame parameter validation — **change requested**

In `src/qbestd/audio/framing.py`, reject non-positive sample rate, frame duration, shift duration, or rounded frame/shift lengths with `ValueError`; validate positive lengths in `count_frames`. Add tests for zero shift and tiny positive durations in `tests/audio/test_framing.py`. Rounding fractional sample lengths can remain documented. The original MATLAB spectrogram uses `floor` for its default durations ([`myspectrogram.m`, lines 45–49](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Signal_Processing/myspectrogram.m#L45-L49)); 25/10 ms at 8/16 kHz are exact, so this difference does not affect those settings.

## 7. FFT length and scaling — **change requested**

In `src/qbestd/audio/spectrum.py`, reject `n_fft < frame_length` and non-positive/non-integer FFT lengths, and test that explicit short lengths raise instead of truncating. Keep the current unnormalized squared magnitude: the original MATLAB MFCC path computes an unnormalized FFT magnitude, then `log((M*y).^2)` ([`Fx_mfcc.m`, lines 41–51](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Features/Fx_mfcc.m#L41-L51)). A `1/n_fft` factor would shift log mel energies and could change c0/log-energy matching. Revisit exact normalization only with the chosen feature extractor.

## 8. Teager energy placement — **agree**

`frame_teager_energy` is a valid Stage 1 frame statistic and demo curve. Do not use it as the MFCC-TMP feature itself: the thesis applies TEO to each **time-domain mel subband signal**, then normalizes/logs subband energy and applies DCT ([`ExpSetup.tex`, lines 196–223](D:/Storage/career_phd_daiict_work/Thesis/Chapters/ExpSetup.tex)). Implement that subband-specific path in Stage 2. Frame edge replication affects two samples per frame and should be documented there; whole-waveform TEO before mel filtering would also be a different operation.

## 9. Dataset paths — **change requested**

In `src/qbestd/config.py`, remove the committed machine-specific absolute defaults; let unset paths be `None`. Add a non-secret `paths.local.toml.example` with keys and placeholder paths, while keeping the actual file ignored. Resolve the local TOML path from an explicit argument or a documented project/config location, rather than silently depending on the current working directory. Make `require(name)` validate the field name and raise `ValueError` for an unknown name. Treat an explicitly present but empty environment variable as an invalid setting rather than falling through silently. Update `tests/test_config.py` for precedence, empty values, and invalid names.

## 10. Pipeline semantics — **agree**

Whole-utterance DC removal is consistent with the original `Fx_mfcc.m` use of `x-mean(x)` before pre-emphasis ([lines 29–31](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Features/Fx_mfcc.m#L29-L31)); that routine also divides by `max(x)`, which this pipeline does not. The thesis says HTK produced its MFCC/PLP, so retain configurable preprocessing and compare paths at Stage 2. The 8 kHz sample-rate default is explicitly unverified and overridable; see Q14. `n_fft` belongs to the later spectrum step, so keeping it in the shared config is reasonable even though `prepare_frames` returns frames only.

## 11. Demo — **change requested**

In `demo/stage1_audio_demo.py`, plot signed mean TEO directly, or use a signed log transform with a clear label. `log|mean TEO|` erases the sign and can misrepresent negative values. The second resampling is only for waveform display and is harmless at demo scale. The Reviewer's successful `build_demo()` import/build smoke check is sufficient here; a separate automated test would add little beyond that check.

## 12. Other issues — **change requested**

The main additional correctness gap is input validation at API boundaries: `resample_audio` accepts zero/negative rates until `gcd`/`resample_poly` fails indirectly, and `frame_signal` has the cases in Q6. In `src/qbestd/audio/resample.py`, require positive integer source/target rates with clear `ValueError`s and add focused tests in `tests/audio/test_resample.py`. I found no further Stage 1 PEP 8 or coverage issue that warrants a separate task.

## 13. Original MFCC parameters — **agree**

The original MATLAB `Fx_mfcc.m` defaults to pre-emphasis **0.97**, a **25 ms** window and **10 ms** shift, **26** filters, **13** coefficients, and `NFFT = 2^nextpow2(win)` ([lines 16–26](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Features/Fx_mfcc.m#L16-L26)). It passes `'h'` to `myspectrogram` ([line 43](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Features/Fx_mfcc.m#L43)), whose window legend identifies `'h'` as Hamming ([`myspectrogram.m`, lines 55–60](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Signal_Processing/myspectrogram.m#L55-L60)). `Fx_mfcc.m` keeps DCT rows `1:Nc`, so it includes c0 and does not substitute log energy ([lines 39–51](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Features/Fx_mfcc.m#L39-L51)). A separate `Fx_mfcc_lift.m` uses `Nlift=-20` by default and then calls `lifter`, **not 22** ([lines 21–28, 47–52](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Features/Fx_mfcc_lift.m#L21-L52)). These MATLAB routines are reference variants; the thesis says the reported MFCC/PLP were extracted with HTK ([`ExpSetup.tex`, lines 190–198](D:/Storage/career_phd_daiict_work/Thesis/Chapters/ExpSetup.tex)), and no HTK config was found to prove which liftering or c0/energy option produced the reported table. Keep those options configurable.

## 14. TIMIT downsampling — **unknown**

The thesis specifies mel filters from 0 to 4000 Hz and says HTK extracted MFCC, but does not state that TIMIT was downsampled ([`ExpSetup.tex`, lines 190–198](D:/Storage/career_phd_daiict_work/Thesis/Chapters/ExpSetup.tex)). The MATLAB `Fx_mfcc.m` default is 16 kHz and its upper filter edge defaults to `fs/2`, while `Fx_mfcc_lift.m` defaults to 16 kHz and 8 kHz upper edge ([`Fx_mfcc.m`, lines 16–26](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Features/Fx_mfcc.m#L16-L26); [`Fx_mfcc_lift.m`, lines 17–28](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Features/Fx_mfcc_lift.m#L17-L28)). A 4 kHz mel ceiling can also be used on 16 kHz audio. Confirm from the original HTK config or experiment scripts before declaring 8 kHz the reproduction setting; keep both sample rate and mel upper edge configurable.

## 15. Q-84 list — **unknown**

The thesis gives the rule: exclude `/sa/`, select words with **7–20 test occurrences** and **at least six letters**, and take spoken query examples from training data ([`ExpSetup.tex`, lines 72–75](D:/Storage/career_phd_daiict_work/Thesis/Chapters/ExpSetup.tex)). I found no fixed Q-84 list in the cited thesis passage or the public `research_qbestd` tree. Derive a deterministic list from the **same official split and transcript normalization**, then compare its size to 84; preserve the produced list as a reproducible artifact. Without the original split and tokenization, the exact 84 words remain unverified.

## 16. Phone segmentation — **agree**

The thesis explicitly says feature reduction used **Spectral Transition Measure (STM)** to segment both queries and test utterances ([`Matching.tex`, lines 287–305](D:/Storage/career_phd_daiict_work/Thesis/Chapters/Matching.tex)). It defines the cepstral slope measure at lines 316–321 and says STM was chosen over BUT phoneme decoders at lines 323–339. The feature repository includes [`stm_computation.m`](https://github.com/maulikmadhavi/research_myMATLAB_codes/blob/master/Analysis/Feature_Extraction/Signal_Processing/stm_computation.m), which computes the local cepstral slope norm. Use STM boundaries before averaging consecutive posterior vectors for Stage 6.

## 17. Hugging Face TIMIT copy — **change requested**

`docs/data_notes.md` correctly treats 16 kHz as an inference and identifies the missing alignment/ID fields from the inspected schema. Its 5040/1260 count differs from the commonly cited 4620/1680 official train/test count, but the schema and counts **do not establish how the split was made**; remove or qualify “probably at random” and “speakers likely overlap” until IDs or source documentation confirm them. The thesis specifies train queries, test documents, `/sa/` exclusion, and Q-84 test occurrence counts ([`ExpSetup.tex`, lines 72–75](D:/Storage/career_phd_daiict_work/Thesis/Chapters/ExpSetup.tex)); the public `research_qbestd` tree contains matching code but no TIMIT manifests or `.WRD` alignments. Prefer a licensed original TIMIT copy with `.WRD` boundaries and the documented split for comparable Q-20/Q-84 results. If unavailable, forced alignment on the HF copy is a separate approximate experiment; label its split and results accordingly. Also read one audio row to confirm the HF sample rate before treating 16 kHz as observed.
