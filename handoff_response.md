# Handoff Response: Cycles 2 and 2b

Scope: `handoff_request.md` at `ca46890`. Review decisions below replace the cycle 1 response. “MATLAB parity” means the public source variant; the thesis's HTK configuration and the missing `Fx_melfiltbank.m`/`vteo.m` remain separate unknowns.

## 1. Time-scaling anti-alias filter — **agree**

The 101-tap FIR is a reasonable Stage 1 guard against gross aliasing for full utterances and the tested alpha range. Its adequacy for *feature parity* is unproved; a frequency-response check at alpha 1.12 and a near-Nyquist test are more informative than the tap count alone. `filtfilt` with `padlen=len-1` makes very short inputs dominated by edge extension, but such inputs are shorter than a normal analysis frame. Keep this behavior documented; do not infer faithful VTLN from it.

## 2. Unknown local path keys — **agree**

Keep the `ValueError` in `src/qbestd/config.py`. A misspelled key otherwise looks like a missing dataset later, so early rejection is clearer than a warning.

## 3. VTLN cutoff for a restricted band — **change requested**

In `src/qbestd/features/scales.py` and `features/filterbank.py`, let the piecewise warp take an explicit upper anchor. Use the **feature band edge** (4 kHz here) when `high_hz < fs/2`, yielding the thesis's 3.5 kHz cutoff, and retain sampling Nyquist for full-band PLP. Test 16 kHz audio with a 4 kHz band at both extreme alphas: the upper anchor must map to itself and filter support must stay within the intended band. The thesis appendix describes 3.5/7 kHz cutoffs for 4/8 kHz upper bands (`Backmatter/Warped_Feature.tex`, line 30). `Fx_mfcc_vtmp_cep.m` defaults to 16 kHz and `fH=4000` (lines 27–36), but delegates warping to the **missing** `Fx_melfiltbank.m` (line 46), so this is a thesis-based choice, not proven MATLAB parity. With the current bin-warp convention, **alpha > 1**, not alpha < 1, moves a 4 kHz filter edge toward physical bins above 4 kHz.

## 4. Warp direction — **agree**

`Fx_vtln_warp.m` sets its lower-band slope to `2-alpha` (lines 12–30), and `Fx_PLPCC_htk.m` warps FFT bins before the bank (line 47; bank call at line 65). Therefore alpha > 1 maps a physical bin to a lower filter coordinate and moves a fixed filter peak to a **higher physical frequency**. The direction matches the implementation and the usual shorter-tract/higher-formant interpretation. The separate mel-scale formula in `Backmatter/Warped_Feature.tex` should not be silently treated as identical to this piecewise warp.

## 5. c0 versus 13 coefficients — **agree**

For a DCT indexed from zero, `include_c0=False` producing c1–c13 is the literal reading of the MFCC-TMP equation's `k=1..Nc`, with `Nc=13` (`Chapters/ExpSetup.tex`, lines 219–223). The MATLAB `Fx_mfcc_vtmp_cep.m` instead takes DCT rows `1:Nc` in MATLAB indexing, thus c0–c12 (lines 74–78). Keep both modes explicit; keep the lifter index aligned. The thesis equation and MATLAB implementation do not resolve which mode generated the reported numbers.

## 6. Peak normalization — **agree**

Keep `max|x|` for a stable generic extractor and for MFCC-TMP parity (`Fx_mfcc_vtmp_cep.m`, line 41). `Fx_mfcc.m` divides by `max(x)` after mean subtraction (line 29); for an asymmetric signal this changes an overall gain and primarily c0 before liftering/deltas. Record it as a parity difference, and use a dedicated MATLAB-mode setting only if numerical comparison requires it. Note that floors and downstream normalization can make the effect more than an exact c0 shift in edge cases.

## 7. PLP choices — **change requested**

`Fx_PLPCC_htk.m` forward-warps the nominal filter centres for equal-loudness weighting (lines 54–62), so `features/plp.py` faithfully follows that public MATLAB code. It is not the physical inverse-warped centre; retain the behavior for MATLAB parity and document the distinction in `docs/feature_parity.md`. For a **MATLAB-parity profile**, set `lpc_order=8` and disable DC removal in `src/qbestd/features/plp.py`/the shared front end: MATLAB defaults to order 8 (line 35) and feeds `x*32768` directly into `myspectrogram` (line 69). Keep order 12 and any DC-removal choice available for an explicitly labeled HTK-like profile. The thesis says HTK produced PLP but supplies neither order nor DC option (`Chapters/ExpSetup.tex`, lines 193–198), so no profile can yet claim thesis parity.

## 8. MFCC-TMP details — **unknown**

`Fx_mfcc_vtmp_cep.m` mirrors weights (line 47), applies them to the full complex FFT, takes the **real** IFFT (lines 68–70), and sums `vteo` over that full `NFFT` vector (line 70). Its `m` and `p` options use `abs(y)` and `angle(y)` (lines 56–61), so the non-conjugate-symmetric phase-only case followed by real IFFT is faithful to that code. The exact lag/edge rule and possible normalization are **unknown** because `vteo.m` is absent. Keep `teager_energy_lagged` labeled approximate; do not present its edge replication or floored sums as verified parity.

## 9. Unified extraction API and repeated work — **change requested**

In `src/qbestd/features/extract.py`, default the optional `warp_factor` argument to `None`; when absent use `config.warp_factor`, and when supplied override it. Test both paths. The current default silently discards a non-default factor in the config. Recomputing frames and FFT 13 times is a genuine Stage 4 cost, but defer caching until Stage 4 profiles it: MFCC, PLP, and MFCC-TMP use different intermediate data, and premature shared cache code would complicate the extractors.

## 10. Feature parity table — **change requested**

In `docs/feature_parity.md`, replace broad thesis-column claims with what `Chapters/ExpSetup.tex` actually states. Line 191 specifies **MFCC**: 26 filters, 0–4000 Hz, 13 DCT coefficients, and HTK. Lines 193–194 give **no PLP** filter count, band, c0 choice, or delta configuration. Lines 198–223 specify **MFCC-TMP**: 25/10 ms, 26 filters, 13 coefficients plus delta/delta-delta, and a formula indexed `k=1..13`; they do **not explicitly state its frequency band** in that passage. The same passage says HTK extracted MFCC/PLP, not MFCC-TMP. The table's blanket “thesis 26,” “thesis 0–4000,” “thesis 39 dimensions,” and HTK-default memory entries need those per-feature qualifications. Also label the thesis's “Type III” DCT wording at line 191 separately from the MATLAB/NumPy DCT-II implementation; do not call the mismatch resolved without a convention check.

## 11. Other Stage 2 issues — **change requested**

In `tests/features/test_mfcc_tmp.py`, replace `0 <= floor_hits <= energies.size`, which cannot fail, with a meaningful seeded-noise assertion such as `floor_hits < energies.size`, while keeping the exact count as diagnostic output. Avoid an arbitrary upper percentage until measured across environments. The Stage 2 demos' long lines and the unrelated line-wrap fixes in the LPC commit are style/process cleanup, not correctness blockers. I found no other specific failure that warrants a new task from the listed code.

## 12. TIMIT sample rate and feature ceilings — **unknown**

All 6300 HF rows are observed at 16 kHz (`docs/alignment_notes.md`, “Sample rate”). The thesis states the MFCC band is 0–4000 Hz but does not say TIMIT was downsampled (`Chapters/ExpSetup.tex`, line 191). For the next **TIMIT reference run**, use `(16 kHz, 4 kHz)` for MFCC and MFCC-TMP, matching the data rate and `Fx_mfcc_vtmp_cep.m` defaults (lines 27–36); use `(16 kHz, 8 kHz)` for the public MATLAB PLP variant (`Fx_PLPCC_htk.m`, lines 30–39). In `src/qbestd/features/mfcc.py`, `mfcc_tmp.py`, and `plp.py`, expose these as an explicitly named TIMIT/MATLAB profile rather than silently changing generic defaults. Whether the thesis's HTK pipeline resampled remains unknown; only its configuration or scripts can settle it.

## 13. Missing mel-bank definition — **unknown**

The thesis names mel filters and a band (`Chapters/ExpSetup.tex`, line 191) and describes a warped mel scale/cutoff (`Backmatter/Warped_Feature.tex`, lines 11–30), but does not pin down triangle area normalization or exact FFT-bin edge placement. `Fx_mfcc.m` and `Fx_mfcc_vtmp_cep.m` call the unavailable `Fx_melfiltbank.m`; rastamat/HTK bank routines are useful comparison implementations, not evidence of this missing function's behavior. Keep the unit-peak, equally spaced triangles identified as an assumption in `docs/feature_parity.md` until source or numerical reference output is found.

## 14. Collapsed word runs — **change requested**

In `src/qbestd/alignment/manifest.py`, make `check_segments` flag **equal consecutive starts** as a distinct collapsed-run warning, with a test using two words whose durations exceed 20 ms. This catches a pattern the current duration threshold can miss. Do not automatically drop every such row: a shared rounded start could occur at timestamp resolution. In Stage 7, exclude or manually review affected **query segments** using this flag plus duration and overlap evidence. Keep the nondecreasing-start and positive-duration checks for malformed imported manifests even though the pinned aligner clamps its own output.

## 15. Transcript units — **change requested**

In `src/qbestd/data/timit_hf.py`, apply Unicode NFC before lowercasing/tokenizing and add tests for equivalent composed/decomposed text; Stage 7 must reuse this function. Before altering hyphen/apostrophe tokenization, audit the pinned corpus for those tokens and compare them with the pinned aligner's `words_of` behavior. Since the aligner receives an explicit word list, its tokenizer is bypassed, and equal output/input word counts do not establish correct compound boundaries. A tokenization change after manifest generation requires rerunning alignment and updating the documented hashes.

## 16. Overlapping word cuts — **agree**

For Stage 7 query clips, initially use the aligner's `[start, end]` with a small, explicit pad (the 20 ms used in the review is a reasonable starting point), clip to utterance bounds, and retain overlap statistics/flags. Midpoint-clipping a third of adjacent pairs could remove phonetic evidence; dropping all overlaps would discard too much data. Exclude the clearly collapsed/very short query segments, then compare padded-cut retrieval performance and a sampled listening/ASR audit before choosing any overlap threshold.

## 17. Alignment accuracy and leakage — **change requested**

In `docs/alignment_notes.md`, say explicitly that the model card's 10.7 ms figure was measured on its own TIMIT test setup and is **not a measured error for these HF manifests**. Training-speaker overlap with the redrawn HF split is plausible but unverified without IDs. It may make alignment accuracy look better; independently, speaker overlap between HF query/train and document/test sets may also inflate later QbE scores. The alignment-only role does not remove that evaluation concern.

## 18. Stronger sanity check — **change requested**

The Reviewer's 300-word independent-ASR comparison is stronger evidence than the energy check because true cuts beat both shifted controls, but its 0.653 hit rate depends on Whisper-base, padding, word normalization, and short-clip behavior. Add an **optional**, reproducible content-word audit to `src/qbestd/alignment/sanity.py` or a separate alignment QA script: fixed seed, words of at least 3 letters, true and ±0.25 s shifted cuts, same scorer, hit rates and sample counts saved to `outputs/alignment/`. Document the model/revision. Do not make a 3× ratio a hard alignment gate from this one run; retain it as comparative diagnostic, and inspect failures on a stratified sample. A time-shift equivariance test with the same aligner alone is weaker because it can reproduce its own errors.

## 19. Manifest hashes — **agree**

Keep the SHA-256s: they identify the exact files used in an experiment even if bf16 GPU reruns differ by a millisecond. Record model/dataset revisions, environment lock, precision, seed where applicable, and per-split counts/quantiles alongside them (`docs/alignment_notes.md` already has most of these). A hash mismatch prompts comparison, not automatic rejection; a tolerance-based statistical summary supplements but cannot replace file identity.

## 20. Other alignment and environment issues — **change requested**

In `src/qbestd/alignment/word_aligner.py`, check that `align_batch` returns exactly one outcome per input row before `zip`; otherwise `align_rows_detailed` silently loses rows. Add a fake-aligner test returning too few outcomes. In `src/qbestd/alignment/manifest.py`, reject or flag non-finite start/end times, which currently pass most comparisons; add focused tests. The pinned revision, reviewed `align.py` hash, safetensors-only snapshot patterns, and lazy torch import are sound for this workflow. `pytorch-gpu="*"` with CUDA 12 is acceptable with the committed `pixi.lock` on the tested Windows GPU; record that platform and do not imply the lock guarantees a working GPU on other machines.
