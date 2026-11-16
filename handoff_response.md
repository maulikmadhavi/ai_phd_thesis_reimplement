# Handoff Response: Handoff_feedback → Orchestrator

- **Cycle:** 7
- **Answers:** `handoff_request.md` at `1456aa9` (16 exec commits, `c429300..c027e05`).
- **Read for this review:** the request; `features/{profiles,plp,mfcc,cepstral,scales,
  filterbank}.py`; `data/{feature_cache,warped_cache}.py`; `ml/{vtln,vtln_train}.py`;
  `eval/model_guard.py` and the summary block of `eval/run_timit.py`;
  `tests/data/test_warped_cache.py`; `docs/feature_parity.md`,
  `docs/results_timit_q20_features.md`, the tail of `docs/plan.md`; the smoke model JSON
  under `outputs/`; thesis `Representation.tex` 8–35, 84–200, 226–276, 308–318,
  `ExpSetup.tex` 186–200 and `Unsupervised.tex` 525–584.
- **Not done:** I did not re-run the tests, any model or any evaluation. HTK internals
  below are **recalled from memory, not checked against the HTK source or book**; they
  are marked as such.
- **Loop status:** **pauses for the user.** Three user-decision items are in the last
  section. The code changes in Q3, Q7 and Q8 do not depend on them.

Two findings matter more than the rest, so they come first:

1. **A VTLN model passes the plain-evaluation guard (Q8a).** The VTLN model JSON carries
   the *plain* feature fingerprint, and `check_model` compares only kind, profile, split
   and fingerprint. `run_timit` would therefore score a VTLN model on unwarped features
   without an error. Fix this before any Stage 4 score.
2. **Our warp label is probably the mirror of the thesis's (Q4).** Our filter peaks move
   *up* for α > 1. The thesis says male speakers have α > 1, and that filters stretch for
   *lower* α; both statements mean filters move *down* for α > 1. The 13 warps are
   symmetric about 1, so the set of warped features is the same and no score changes, but
   a histogram compared with the thesis must be read as 2 − α. A score-free check is
   given in Q4.

---

## 1. Plan Q31, level check — **agree**, one wording change

- **Reading.** The result is right, the sentence is slightly too strong. "This check
  shows no change in either feature" should be "this check does not detect a change; the
  paired intervals allow differences of up to about 3 to 4 points either way".
  File: `docs/results_timit_q20_features.md`, the paragraph after the paired table.
- **My cycle 6 hypothesis is not supported.** I ranked level handling as the most likely
  cause of MFCC sitting above and PLP below the thesis. L1 gives no evidence for that:
  PLP − MFCC stays at −9.77 (−14.8 to −4.9) with both flipped.
- **MFCC-TMP level handling:** leave it as it is. L1 gives no reason to change it, and
  the MATLAB script is its only source.
- **`timit_matlab`:** keep it as a labelled earlier reference for MFCC and PLP, and as
  the MFCC-TMP profile. Do not spend compute on decomposing its PLP gap into band,
  filter count, LPC order and pre-emphasis; that answers no thesis question.
- **One thing it still affects:** MFCC-TMP − MFCC now compares a MATLAB-described front
  end (26 filters, 0–4000 Hz, peak-normalised) with an HTK-described one (40 filters,
  0–3400 Hz). By the author's statement the thesis did the same. The doc should say so
  wherever that difference is reported, as it did for PLP − MFCC in cycle 6. See also
  Q5, last bullet.

## 2. Plan Q32, HTK defaults — **unknown** (recalled values agree; three additions)

I cannot verify HTK from the sources available here. From memory:

| Item in `_htk_described` | My recollection |
|---|---|
| `PREEMCOEF` 0.97, `CEPLIFTER` 22, `LPCORDER` 12, `COMPRESSFACT` 0.33, `DELTAWINDOW` 2, `ZMEANSOURCE` off | agree |
| MFCC on magnitude (`USEPOWER` off) | agree |
| `log(M|X|)` against our `log((M|X|)²)`: factor 2 on every cepstrum | agree |
| HTK c0 is `sqrt(2/N)·Σ`, ours `sqrt(1/N)·Σ`: factor √2 on c0 only | agree |
| Pre-emphasis per frame, after framing | agree (small edge effect per frame) |
| Filterbank skips the DC bin (`klo = 2`) | agree; see note below |
| HTK PLP has its own internals | agree; details below |

Additions to record in the docstring and in `docs/feature_parity.md`, all as "recalled,
unverified":

- **PLP and `USEPOWER`.** As I recall, with `USEPOWER` off HTK's PLP squares the
  mel-weighted *magnitude* sum, `(M|X|)²`, and uses `M|X|²` only when `USEPOWER = T`.
  Our PLP always uses `M|X|²`. So "PLP on the power spectrum" is right only if the
  thesis config set `USEPOWER = T`. This is one of the author questions below.
- **Triangle shape.** HTK's triangular weights are linear in *mel*; ours are linear in
  Hz between mel-spaced edges. Small, but it is a difference.
- **PLP edge bands.** HTK appends two extra points that copy the first and last band
  (N + 2 points). Ours overwrites the first and last band (N points), as
  `Fx_PLPCC_htk.m` does.
- **Log floor.** HTK floors the filterbank output at 1.0 before the log; ours floors at
  1e-10. With ×32768 scaling this matters only in digital silence.
- **DC bin.** Our first triangle rises from `low_hz = 0`, so bin 0 has weight 0 at every
  warp. DC does not leak in, even without DC removal.

**Is the c0 √2 note worth adding?** Yes, one sentence. The reasoning in the request is
right: EM on a diagonal GMM is invariant to per-dimension scale, the LBG start is not, so
a uniform ×2 changes nothing and the √2 on c0, Δc0 and ΔΔc0 can change the
initialisation. Do **not** change the code for it; a note is enough.

## 3. Plan Q33, VTLN assumptions — **change requested** (small), one item **unknown**

- **Fresh LBG against warm start: unknown.** The thesis says "re-trained" (line 103) and
  "build" (line 161), which reads as a new model. But its claim
  `P(X^α̂ | λ⁽¹⁾) ≥ P(X¹ | λ_init)` (line 138) is guaranteed only when EM continues from
  `λ_init`; a fresh LBG start does not guarantee it. Keep fresh LBG as the declared
  primary, since it is the same recipe as `λ_init`. Then:
  - `ml/vtln_train.py`, `train_vtln`: after each iteration compare
    `mean_ll_new_on_selected` with `mean_ll_init_on_selected`. If the new value is lower,
    log a warning and store `"ll_decreased": true` in the record. The smoke run passed
    (−116.45 → −116.32).
  - Do not run a warm-start variant unless that flag fires or the author says the thesis
    continued from the old model (author question below).
- **Query α̂: agree with the implementation.** Line 104 says "the VTLN warping factors of
  test and query features are estimated against the new GMM model λ_r", so a query gets
  its own estimate. `Fig:VTLNwarpconst` (lines 286–291) is about how stable such
  short-utterance estimates are, which fits. Record in the results doc that this is the
  thesis reading, and report how often a query's α̂ differs from its source utterance's.
- **Save per-utterance α̂: change requested.**
  `ml/vtln_train.py`: store, for every iteration, α̂ keyed by `(hf_split, row)` (a small
  `.npz` or TSV next to the model, under `outputs/`). The thesis's
  `Fig:TIMITiterloglik` (b) plots the change in α̂ between iterations, which needs
  exactly this. Saving the `(n_utt, 13)` log-likelihood matrix as well costs about
  0.4 MB per iteration and makes the Reviewer's scratch analysis repeatable.
- **`n_iter = 0`:** `train_vtln` returns `alphas` before it is assigned. Raise
  `ValueError` for `n_iter < 1`, with a test.
- **For the Orchestrator's declaration, not a code change:** the thesis's VTLN gains at
  GMM-64 are +1.35 / +2.91 (MFCC), +1.98 / +2.37 (PLP) and +2.85 / +4.02 (MFCC-TMP).
  Our paired intervals have half-widths of about 2 to 3 points. Declare before the run
  that an interval including 0 is a likely outcome and what will be written in that case.
  The number of VTLN iterations used for `Tab:TIMITVTLNPerformance1` is not stated next
  to the table; line 196 says 5 was used "empirically".

## 4. Plan Q34, smoke run and warp grid — **change requested** (one score-free check before scoring)

- **Per-warp cache design: agree.** About 300 s and 3 GB per kind and profile, 9 GB for
  three, is acceptable and never re-read more than one warp at a time. Disk is a compute
  cost for the Orchestrator's plan, not a design problem.
- **Do not widen the grid.** The thesis fixes 13 values from 0.88 to 1.12 (lines 33, 93,
  174). A wider grid would be a deviation, whatever the edge share.
- **(a) the 0.88 edge, and the label direction.** These need one check before scoring:
  - Our bank evaluates the triangles at `(2 − α)·f`, so peaks sit at `c / (2 − α)`:
    *higher* bins for α > 1. That suits a *shorter* vocal tract.
  - The thesis says male speakers have α > 1 (lines 43, 176) and that for *lower* α
    "filters are stretched away" past Nyquist (`Unsupervised.tex` 552). Both mean peaks
    move *down* for α > 1. As I recall, HTK's `WARPFREQ` scales centre frequencies by
    1/α, which is that direction. The thesis formula `M_α(f)` (same file, 549) points
    the other way, so the thesis is not consistent with itself.
  - The slopes are the same set either way (1/0.88 … 1/1.12), so **the warped features
    and every score are unchanged**; only the label is mirrored (α ↔ 2 − α). Under the
    mirror, our 0.88 pile-up is the thesis's 1.12 end.
  - TIMIT is about 70 % male. Whichever label is right, most utterances should sit on
    the male side. Ours has 29 % below 1.00 and 50 % above, so the labels alone do not
    settle whether α̂ follows the speaker.
  - **Requested check (no retrieval score, minutes of compute):** estimate a median F0
    per train utterance and report its rank correlation with α̂ from the smoke run, plus
    the mean F0 of the 0.88 group. A clear negative or positive correlation fixes the
    label direction and shows that α̂ tracks vocal-tract length. No correlation would
    mean α̂ is fitting something else, and that would be a reason to stop before scoring.
    Declare the check in the results doc before running it.
- **(b) narrow low filters: not gating.** One to three bins per filter follows from 40
  channels in 0–3400 Hz on a 512-point FFT. If the author's configuration is right, HTK
  had the same geometry. Record it as a property of the profile.
- **(c) the bump at α = 1.00: not gating.** It is expected in iteration 0, because
  `λ_init` saw only unwarped features. The thesis's own figure shows α̂ still changing
  over the first iterations.
- **Filter area.** The area changes with α and no Jacobian term is applied, so c0
  carries a small α-dependent offset. The thesis mentions no correction either, so this
  is faithful; record it as an assumption. The mean curve in the request falls on both
  sides of 1.02, so the offset is not what drives the choice.
- **Report per iteration:** the histogram, the share at each edge, the share that
  changed since the previous iteration, and both log-likelihoods.

## 5. H3 band — reading **agree**; reference band is a **user decision**

- **Reading:** sound. The doc already says the barely-excluding intervals should not be
  read alone and that no band is chosen by score. Keep it.
- **What the thesis text can and cannot tell the user, without using scores:**
  - "0–4000 Hz" appears once, in `ExpSetup.tex` 191, in the same sentence as "26 subband
    filters". The author has since said the HTK runs used 40 channels, so that sentence
    does not describe the HTK configuration reliably. 26 filters and 4000 Hz are exactly
    the MATLAB MFCC-TMP settings.
  - `Unsupervised.tex` 113 gives no band at all.
  - So the thesis text is weak evidence for 0–4000 Hz in the HTK runs, and the author's
    statement is the only direct evidence for 0–3400 Hz. Neither is a config file.
  - 3400 Hz is the usual `HIFREQ` in HTK configurations for 8 kHz telephone speech,
    often with a non-zero `LOFREQ`. Whether the recalled 0–3400 Hz came from the TIMIT
    config itself is an author question below.
- **Consequence for a later table, stated as a hypothesis only.** The paired
  4000 − 3400 Hz difference for MFCC at GMM-64 is +2.89 / +4.77. The thesis's
  MFCC-TMP − MFCC gain at GMM-64 is +5.12 / +4.79. If the thesis's MFCC used 0–3400 Hz
  and MFCC-TMP used 0–4000 Hz, part of that gain may be band and not the Teager energy.
  This is not tested: the MFCC-TMP models are stale. After the retrain (Q6), report
  MFCC-TMP − MFCC paired against **both** MFCC bands.

## 6. Stale models and the shared digest — **agree** (no change now)

- The shared digest erred on the safe side, and the cost is known: retrain MFCC-TMP
  GMM-64 and GMM-128 on `timit_matlab`.
- A per-kind digest would itself change every fingerprint. That would invalidate the 8
  valid `htk_described` models and the 26 warp caches to save a few minutes later. Not
  worth it now. If it is ever wanted, fold it into a change that already rebuilds
  everything, with an explicit per-kind file map (the import closure will not separate
  the kinds, because `extract.py` imports all three).
- **Requested with the retrain:** the features are byte-identical, the data and seed are
  unchanged, so the parameter hashes should repeat (`bebabe42…` at 64, `105fb5ff…` at
  128). Record whether they do in `docs/gmm_notes.md`. If they repeat, the cycle 6
  MFCC-TMP rows carry over without a new evaluation. If they do not, stop and report.

## 7. Provenance code — **change requested**

- `eval/run_timit.py`, `ml/train.py`, `ml/vtln_train.py`: at process start record
  `git rev-parse HEAD` and whether `git status --porcelain -- src pixi.toml pixi.lock`
  is empty. Write `git_commit_start` and `git_dirty` into the summary and the model
  JSON. At the end record `git_commit_end` as well; the docs quote the start value.
- Refuse to start on a dirty tree under `src/` unless `--allow-dirty` is passed, and
  record that flag. Put the helper in one small module and test it with a temporary
  repository.
- Under this rule the PLP GMM-128 re-run, made with uncommitted V1/V2 code in the tree,
  would have needed `--allow-dirty`. That is the intended behaviour. The Reviewer's
  argument that the result stands is sound.
- **The plan commits during the smoke run.** They affected nothing. A rule that depends
  on four sessions remembering it will be broken again, so I repeat the cycle 6
  suggestion: run background chains from a `git worktree` at a fixed commit, with
  absolute output paths. Then a commit on `main` cannot touch a run. Whether to adopt
  that is the Orchestrator's choice.

## 8. Other issues — **change requested**

None of these changes a reported number.

- **(a) VTLN model accepted by the plain evaluation. Fix before Stage 4 scoring.**
  The smoke model JSON has `kind`, `profile`, `split_id` and the plain
  `feature_fingerprint` (`ab3ef124…`), which are the four fields `check_model` compares.
  - `ml/vtln_train.py`: add `"model_type": "vtln"` to the metadata.
  - `eval/model_guard.py`: `check_model` takes the expected model type, default
    `"plain"`, and rejects a mismatch. A missing field counts as `"plain"`, so existing
    models still load.
  - Test both directions.
- **(b) `n_iter` name clash: agree, rename to `n_vtln_iter`.** It is more than a naming
  point. `vtln_train.main` reads `info.get("n_iter", 10)` as the EM iteration count, so a
  VTLN model passed as `--gmm` would run 1 EM iteration without a message. Also store
  `n_em_iter`, `epsilon`, `var_floor_ratio` and `seed` in the VTLN JSON. With (a),
  `vtln_train` should refuse a `--gmm` whose type is not plain.
- **(c) `np.empty` in `ll_matrix_from_caches`: agree.** Use `np.full(..., np.nan)`, and
  add a test where a key's HF split is absent from `paths[alpha]`; it must raise through
  `estimate_warp_factors`.
- **(d) α = 1.00 cache: agree, optional.** A test already shows that its fingerprint
  equals the plain one. Reusing the plain file saves 1 build in 13 and about 0.2 GB.
- **(e) Rounded interval bounds: agree.** In `docs/results_timit_q20_features.md` (and
  whatever writes those rows), print a bound with two decimals when it rounds to ±0.0,
  and take "excludes 0" from the unrounded value. The row in question is MFCC GMM-64,
  instance p@N, "+0.0 to +5.9".
- **(f) `estimate_test_warps` memory: acceptable.** 1344 documents come to roughly 0.2 GB
  at 64 components and 0.4 GB at 128 in float64. Stream only if Q-84 or a larger corpus
  needs it.
- **(g) Histogram total.** `warp_histogram` matches floats exactly. That works today
  because every α comes from the same tuple. Add an assertion that the counts sum to the
  number of utterances.
- **(h) Tie-break.** "Closest to 1.0, then the smaller warp" is our choice; the thesis
  says nothing. List it with the other assumptions in the results doc.
- **(i) Stale reproduce block.** `docs/results_timit_q20_features.md` ends with
  commands for `plp_timit_matlab_gmm64.npz`, a model the guard now rejects. Add the
  `htk_described` commands and say that the `timit_matlab` ones need a retrain.
- **PEP 8, security, limits:** nothing found in what I read. `peak_memory_mb` divides
  `ru_maxrss` by 1024, which is right on Linux and wrong on macOS; harmless here.

---

## User decision (loop pauses)

1. **Reference band for MFCC and PLP: 0–3400 Hz or 0–4000 Hz.** Evidence apart from
   scores is in Q5. Whichever is chosen, both stay reported. A change to 0–4000 Hz makes
   `htk_described_4k` the Stage 4 profile, with 26 new warp caches per feature.
2. **Author facts about the HTK configuration** (any that can be recalled or found):
   - was `USEPOWER = T` set, for PLP in particular;
   - was `LOFREQ` 0, and did 3400 Hz come from the TIMIT config or from a telephone-band
     one;
   - were the warped MFCC and PLP features made with HTK's `WARPFREQ`, and with which
     `WARPLCUTOFF` and `WARPUCUTOFF`;
   - is α > 1 the male (longer vocal tract) side in the thesis's figures.
3. **Author facts about the VTLN procedure:**
   - did each VTLN iteration train the GMM from a new LBG start, or continue EM from
     the previous model;
   - how many VTLN iterations were used for `Tab:TIMITVTLNPerformance1`.

Items 2 and 3 can be answered "not known"; the code changes above do not wait for them.
Stage 4 scoring should wait for item 1, for Q8 (a) and (b), and for the F0 check in Q4.
