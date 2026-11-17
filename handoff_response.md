# Handoff Response: Handoff_feedback → Orchestrator

- **Cycle:** 8
- **Answers:** `handoff_request.md` at `6985ff7` (14 exec commits, `0c53448..c2e323c`).
- **Settled, not re-opened:** D4 (fresh LBG each VTLN iteration, `ll_decreased` recorded)
  and D5 (0–4000 Hz only; `htk_described_4k` is the MFCC/PLP reference).
- **Read for this review:** the request; `eval/vtln_eval.py`; the cycle 8 diffs of
  `ml/vtln.py`, `ml/vtln_train.py`, `eval/run_timit.py`, `eval/model_guard.py`;
  `audio/pitch.py`; `ml/posteriorgram.py`; `train_gmm_detailed` in `ml/gmm.py`;
  `lpc_to_cepstrum` and `levinson_durbin` in `features/lpc.py`; the Stage 4 part of
  `docs/results_timit_q20_features.md`; `outputs/models/w1_vtln/f0_check.json`.
- **Not done:** I re-ran no test, model or evaluation. The only numbers I computed are
  the mean α̂ and the share above 1, taken from the final histograms in the results doc
  (Q4).
- **Loop status:** **pauses for the user** on two items (last section). The doc and code
  changes below do not wait for them.

The main point: the gains are 2.5 to 8 times the thesis's, so the next useful step is to
**split the gain into parts** (Q2) before reading anything more into it. That needs no
new training.

---

## 1. Plan Q36, direction and size — **change requested** (wording additions)

The current wording is sound: direction matches, gains above the thesis's, "no cause
claimed", "not like-for-like across bands". Add the following to
`docs/results_timit_q20_features.md`, "Paired VTLN minus no-VTLN".

- **A column "thesis gain inside our paired interval"**, per run and per metric:

  | Run | inst. p@N | inst. MAP | kw p@N | kw MAP |
  |---|---|---|---|---|
  | MFCC 0–4000 Hz | below | below | below | below |
  | PLP 0–4000 Hz | below | below | below | below |
  | MFCC-TMP | inside | inside | inside | inside |
  | MFCC 0–3400 Hz (earlier ref.) | below | below | below (1.35 vs +1.7) | below |

  The thesis gain is compared only against the instance interval in the thesis's own
  sense, because the thesis does not say which average it used. Its gain has an unknown
  uncertainty of its own, so this column is descriptive, not a test.
- **One sentence of fact:** our no-VTLN MFCC 0–4000 Hz row (37.48 / 40.50) already
  reaches the thesis's **VTLN** MFCC row (36.26 / 39.62). So the gap to the thesis is
  partly in the baseline, and partly in the gain.
- Keep "no cause claimed" until the Q2 split is in.

## 2. Like-for-like — **change requested** (one declared diagnostic batch, no training)

The Reviewer's path checks are right. I found nothing else in the code that differs
beyond the model and the warp. Documents come from the same rows and the same floor and
renormalisation. Queries come from the same clip and config. λ_r uses the same recipe.
The α = 1.00 cache has the plain fingerprint.

What remains is the design itself. Each VTLN row changes **two** things at once: the
model (λ_init → λ_r) and test-time selection (α = 1 → α̂ by maximum likelihood per
document and per query). A per-utterance argmax over 13 feature versions is also a
per-utterance adaptation that the plain row does not get. The thesis compares the same
two rows, so this is faithful. But it is the reason a number can be large without saying
anything about speakers.

**Smallest split: a 2×2 table, two new cells, about 4 evaluations, no new training.**

| | α = 1 everywhere | α̂ per document and query |
|---|---|---|
| λ_init (plain GMM-64) | existing no-VTLN row | **new: selection only** (α̂ under λ_init) |
| λ_r (final VTLN model) | **new: model only** | existing VTLN row |

- Run it for MFCC 0–4000 Hz and PLP 0–4000 Hz (the two runs whose gain is outside the
  thesis's). MFCC-TMP is optional.
- **Code** (`eval/run_timit.py`, `eval/vtln_eval.py`): add an explicit diagnostic option,
  for example `--vtln-cell {model_only,selection_only}`.
  - `model_only` loads a VTLN model and scores plain documents and plain clips.
  - `selection_only` loads a plain model and runs `vtln_inputs` under it.
  - Each cell checks its own `model_type`, so the guard stays strict for the normal
    paths. The cell name goes into `summary.json`, and both new cells get tests.
- **Free with it:** the mean posteriorgram entropy of documents and queries, per cell.
  This is descriptive only; it shows whether selection sharpens the posteriors.
- **Optional fifth cell:** queries inherit their source utterance's final α̂
  (`iter4_alphas.tsv`), with documents as in the VTLN row. It measures what the
  short-clip α̂, with 59–72 % disagreement, costs or gains.
- **Declare before running** that all cells are reported, that nothing is chosen from
  them, and that the paired differences are cell minus no-VTLN on the same queries.
- **Compute:** 4 evaluations at about 6 minutes each, plus about 2 per optional cell.
  Warp caches exist; no training. See the user-decision item.

## 3. Level finding — **change requested**: report it as an MFCC observation, add one score-free step

- **Report it in the results doc as an MFCC observation, with the gain-test table.**
  Say plainly that it is scratch-derived, MFCC-only, and not a cause.
- **The arithmetic is exact, and worth one sentence in the doc.** A waveform gain g adds
  `2 ln g` to each of the 40 log channel outputs. The orthonormal DCT gives
  `c0 += 40 · 2 ln g / √40 = √40 · 2 ln g`. For g = 2 that is 8.77, matching the
  Reviewer's "about +8.8".
- **PLP c0 is much less level-sensitive by construction.** `levinson_durbin` returns the
  prediction error power, which scales with the autocorrelation. The auditory spectrum
  is power^0.33, so for g = 2, `c0 += 0.66 ln 2 ≈ 0.46`, about 19 times smaller than
  MFCC's in absolute terms. This fits the 8–9 % α̂ changes. It also means PLP's excess
  gain needs another explanation, which the Q2 split is meant to give.
- **HTK would not have avoided this.** Scaling one dimension leaves a diagonal Gaussian's
  argmax over α unchanged, apart from the LBG initialisation. So HTK's c0 conventions
  (`sqrt(2/N)`, `log(M|X|)`) give the same level sensitivity. If the thesis's HTK
  configuration had no level normalisation, its runs had the same property and still
  showed a small gain. That makes the author fact the deciding input; see the
  user-decision item. As I recall, HTK's `ENORMALISE` acts on the energy term E, not on
  c0, and `ZMEANSOURCE` removes DC only. Both are recalled, not verified.
- **Score-free step first** (`ml/vtln.py` or a small script; seconds to minutes):
  - re-estimate the train α̂ under each final λ_r with static c0 removed from the
    likelihood. A diagonal GMM marginalises it by dropping that dimension.
  - Report the share of utterances whose α̂ changes, for MFCC 4k, MFCC 3400 and PLP 4k.
  - This measures how much of the **actual** α̂ distribution c0 drives, rather than the
    response to an artificial ×2.
- **Options (a), (b), (c):**
  - (c), report the gain-test table: yes, in any case.
  - (b), MFCC 0–4000 Hz with `normalize_peak=True` and its own no-VTLN baseline: the
    right scored check, if the score-free step shows c0 drives a large share. Peak
    normalisation makes the features exactly gain-invariant. Cost: 26 caches (about
    3 GB), one plain GMM-64, one 5-iteration VTLN run, 2 evaluations, about 1 hour.
    MFCC only; PLP does not need it. A compute item for the user (below).
  - (a), area-normalised warp: **not recommended.** It changes the method away from
    both the thesis and HTK's `WARPFREQ`, so it answers a different question.
- **Asking the author whether the HTK configuration normalised level: user decision**
  (an author fact).

## 4. Edge pile-up and convergence — **change requested** (reporting only)

- **Do not widen the grid.** The thesis fixes 0.88–1.12 in 13 steps.
- **Report the mean α̂_thesis per iteration** from the traces. From the final histograms
  in the doc, I get:

  | Run | Final mean α̂_thesis | Share above 1.00 |
  |---|---|---|
  | MFCC 0–4000 Hz | 1.020 | 0.594 |
  | PLP 0–4000 Hz | 1.032 | 0.665 |
  | MFCC-TMP | 1.030 | 0.664 |
  | MFCC 0–3400 Hz (earlier ref.) | 0.990 | 0.296 |

  The 0–4000 Hz runs drift towards the male side at every iteration. That is consistent
  with TIMIT's roughly 70 % male speakers, and also with the known drift of unanchored
  iterative ML warping, where each new model is trained on already-warped data. The
  per-iteration mean will show which: a mean that keeps rising after the share changed
  falls points to drift.
- **The 0–3400 Hz histogram still alternates after 5 iterations** (1.10: 47, 1.06: 66,
  1.02: 79, against 169–611 at their neighbours). The 0–4000 Hz histograms hardly do.
  This points to the narrow low filters of the 0–3400 Hz bank. It is the earlier
  reference only; record it as such.
- **Level and the edge:** the ×2 gain test raises the MFCC 1.12 count from 17 to 24 of
  100, so level can feed the edge for MFCC. PLP is level-insensitive and has the
  largest edge share, so it cannot be the only cause.
- **Add a one-line caveat on each VTLN row:** final train edge shares, query edge
  shares, and the share still changing at iteration 4.
- **Convergence differs from the thesis.** The thesis says α̂ "converges" (line 194). Ours
  still changes for 11–20 % of utterances at iteration 4. With fresh LBG, the model
  noise between iterations is of the same order as the remaining LL gain (Q5), which
  would keep some α̂ moving. State this as a likely reason, not a proven one.

## 5. Plan Q37, `ll_decreased` — **agree**, with one wording change and one assertion

- **Wording:** "after iteration 2 the new model's LL plateaus, and its changes (up to
  0.05 per frame) are of the same size as the fresh-LBG initialisation noise". This is
  better than "isolated decreases" and better than "non-monotone", which suggests a
  trend.
- **The comparison is right (also Q8).** `train_gmm_detailed` appends the LL of the
  final parameters after the loop, so `ll_new` belongs to the model actually kept and
  the flag does not over-report. The iteration is a coordinate ascent with two steps:
  - the **selection step**, `L(λ_{k−1}, α̂_{k−1}) ≤ L(λ_{k−1}, α̂_k)`, is guaranteed by
    the argmax. It holds in every row of all four tables: the "init" LL at k is never
    below the "new" LL at k − 1;
  - the **model step**, `L(λ_{k−1}, α̂_k) ≤ L(λ_k, α̂_k)`, is guaranteed only for EM
    started from λ_{k−1}. Fresh LBG can break it, and that is what `ll_decreased` tests.

  Comparing the new model on the new α̂ with the previous model on the previous α̂
  would mix the two steps and hide a model-step decrease.
- **Change** (`ml/vtln_train.py`): record the selection-step check as
  `selection_step_ok` per iteration, warn if it ever fails (it would mean a bug), and
  add a test.

## 6. Plan Q35, F0 check — **agree**, with two notes and one cheap extension

- **It supports D3 (c), and supports "α̂ tracks the speaker" in a limited sense.**
  ρ = −0.637, with the signs agreeing under the label map, passes the declared gate by
  a wide margin.
- **Note in the doc:**
  - it ran at iteration 0 under λ_init, on the 0–3400 Hz profile, not on the D5
    reference;
  - a large ρ can come from the two gender clusters alone. It shows α̂ separates men
    from women. It does not show that α̂ tracks vocal-tract length within a gender.
- **Extension, score-free:** `f0_check.json` holds only summaries, so per-utterance F0
  must be recomputed (minutes). Save it this time, keyed by `(hf_split, row)`. Then
  report ρ(F0, final α̂_thesis) for each of the three D5 runs, overall and within the
  F0 < 165 Hz and ≥ 165 Hz groups.
- **Also score-free:** the partial correlation of α̂ with utterance mean c0, controlling
  for F0. It separates the Reviewer's ρ(α̂, c0) = +0.263 from gender.

## 7. Plan Q38, MFCC-TMP − MFCC — **agree** that nothing is claimed about Teager energy

- **Supportable reading, against the D5 reference:** the thesis's MFCC-TMP advantage
  (+5.12 / +4.79 without VTLN, +6.62 / +5.90 with) is **not reproduced**.
  - Without VTLN: +1.70 (−0.6 to +3.9), so no direction is claimed.
  - With VTLN: −4.09 (−7.1 to −1.0) for p@N, excluding 0 against the thesis's direction;
    MAP includes 0.
- **Why no front-end claim is possible:** the two features differ in tool lineage
  (MATLAB-described against HTK-described), filter count (26 against 40), level handling
  (peak-normalised against none) and VTLN response. By the author's statement the
  thesis had the first two differences as well, but its level handling is unknown.
- **The 0–3400 Hz comparison** (+2.42, interval includes 0) is labelled earlier
  reference only. It must not be read as the band question, which D5 settled.
- **Change:** in `docs/results_timit_q20_features.md`, rename the heading
  "MFCC-TMP minus MFCC under VTLN (Q5)". "Q5" refers to an old review question number
  and reads as plan Q5. Add the two sentences above.

## 8. Other issues — **change requested**

None of these changes a reported number.

- **`clip_warp_features`: agree.** Check `len(clip)` against one frame length before
  `extract_warped_bank`. Keep the empty-bank check as a second guard. The two
  "Mean of empty slice" warnings should go away; add `-W error::RuntimeWarning` to that
  test, or assert that no warning is raised.
- **Edge shares and histograms printed as raw dicts: agree.** Use 3-decimal columns
  for shares and a table for the histograms (thesis label 0.88 → 1.12). These appear in
  the LL tables and the warp-statistics table.
- **`pitch.frame_f0` with no peak: agree.** Set `first` to 0 and mark the frame unvoiced
  explicitly when `top` is `-inf`. Add a test with a frame that has no peak, such as a
  linear ramp. Also drop the unused aliases `peak = top` and `best = first`.
- **`ll_decreased` comparison:** right as it is; see Q5.
- **Import order:** `from qbestd.provenance import ...` sits between `qbestd.eval` and
  `qbestd.ml` imports in `run_timit.py` and `vtln_train.py`. This is cosmetic: isort
  order, not a PEP 8 rule.
- **"Commit as the run started":** the G4 fields resolve the cycle 7 issue. Keep quoting
  `git_commit_start`.
- **Security, line limits:** nothing found in what I read.

---

## User decision (loop pauses)

1. **Author fact:** did the HTK configuration used for the thesis normalise waveform
   level in any way, or was the TIMIT audio already level-normalised before HCopy? The
   possibilities are a peak or RMS scaling script, or `ENORMALISE` with an energy term
   instead of c0. "Not known" is a valid answer. It decides whether the MFCC level
   sensitivity in Q3 is a reproduction difference or a property the thesis shared.
2. **Compute for the diagnostics:**
   - the Q2 split: 4 evaluations, about 25 minutes, no training;
   - optional extra cells: about 2 minutes each;
   - the score-free steps in Q3 and Q6: minutes;
   - the Q3 (b) level-normalised MFCC run, only if the score-free step shows c0 driving
     a large share of α̂: about 1 hour and 3 GB.

   Approve all, some or none.

D4 and D5 stay closed. Nothing above changes the procedure or the band.
