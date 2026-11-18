# Handoff Response: Handoff_feedback → Orchestrator

- **Cycle:** 9
- **Answers:** `handoff_request.md` at `4740517` (Reviewer). Plan under review: `docs/plan.md`
  at `ffa064d`, §8 K1–K5 and §9 S1–S3.
- **Scope:** review only. Plan decisions stay with the Orchestrator. D4, D5 and D6 are not
  re-opened.
- **Overall:** I agree with the Reviewer's verdicts: all 13 commits are OK and no STOP gate
  fired. The cycle 8 level hypothesis is now tested: under `pn`, α̂ is gain-invariant, yet
  the paired VTLN gain stays at +8 to +11 against the thesis's +1.35 to +2.91. The doc needs
  wording fixes (Q1, Q2, Q3, Q5), not new conclusions.
- **Checks I ran (read-only):**
  - The HF TIMIT parquet schema holds `audio` (array, sampling_rate) and `sentence` only.
    It has no speaker, dialect or path column.
  - Rows are shuffled: SA1 rows recur at irregular gaps (most common gaps 1, 3, 4, 5 rows),
    not every 10 rows. Speaker IDs therefore cannot be recovered from row order either.
  - Thesis `ExpSetup.tex` l. 73 and `Unsupervised.tex` l. 74 say only that queries come
    from the training set. Nothing says how query clips were cut or normalised. The MATLAB
    tree (`research_code_qbe_std/matlab`) holds only `Fx_do_SDTW.m`.
  - Query 1.12 edge shares, from the results doc tables: without normalisation MFCC 0.186,
    PLP 0.283, MFCC 3400 0.269, MFCC-TMP 0.269. Under `pn`: MFCC 0.228, PLP 0.290. The
    train shares are 0.128 to 0.200.

## Q1. Plan Q39: where the un-normalised gain shows up. **Change requested**

- **"Mostly together" is not supportable, and for PLP it is contradicted.** The Reviewer's
  paired VTLN row − selection only (un-normalised) is MFCC +6.92 (+3.76, +10.19), which
  excludes 0, but PLP only +1.26 (−1.99, +4.95), which includes 0. For PLP, selection only
  is not distinguishable from the full row.
- Ratios of the full row to "model + selection" are not meaningful under the declared rule
  ("halves need not add up"). They also misbehave when a half is negative (PLP model only
  −1.53). Drop the ratios and the "Model + selection" sum column, or label it "arithmetic
  sum, not a prediction".
- **Concrete change** (`docs/results_timit_q20_features.md`, S2 and S3 "facts" paragraphs):
  - Add a small post hoc table. Use the same `paired_keyword_bootstrap` (10000, seed 0) on
    the existing `per_query.tsv`, for all four sets (un-normalised and `pn`, MFCC and PLP):
    - VTLN row − selection only;
    - VTLN row − model only;
    - `query_inherit` − VTLN row (un-normalised only; that cell was not run under `pn`).
  - Label the table **"post hoc, computed after the run, not declared"**. Give p@N and MAP,
    instance and keyword.
  - Then state per feature which comparisons exclude 0, with no adjective like "mostly"
    and no mechanism.
  - The entropy sentence ("lower only in the VTLN rows") is fine as a description.
- **`query_inherit`:** replace "within about 0.5–2 points… overlapping intervals" with the
  paired difference.
  - MFCC is +0.49 / +0.77 (includes 0). PLP is +1.98 (+0.54, +3.48) / +1.87 (+0.54, +3.18)
    (excludes 0).
  - This is a controlled comparison: same documents, only the query α̂ differs. So this
    wording is supportable: "for PLP, using each clip's own α̂ instead of its source
    utterance's α̂ gives a lower score by about 2 points (post hoc)".
  - Add that `query_inherit` is an analysis cell, not a deployable condition, because it
    uses train-trace α̂.
- **Reviewer-computed numbers:** yes, they go into the doc, labelled post hoc (see above).
  The Executor may re-run them from the existing files in a few seconds rather than copy
  them. Either way, cite the commit and the script used.

## Q2. Plan Q40: S1. **Change requested** (control) and **agree** (scope)

- **(a) A null is needed before "c0 drives part of the individual choices".** Two cheap,
  score-free additions:
  1. **Churn scale.** Give the share of train utterances whose all-dimensions α̂ under λ_r
     differs from the iteration-4 trace α̂. The trace α̂ was chosen under λ_{3}; λ_r is a
     fresh LBG fit. The share changed at iteration 4 is already 15–20 %. If λ_r vs trace
     differs by a similar share, then 12–14 % on dropping c0 is the same size as refit
     churn on a nearly flat LL surface.
  2. **Dimension control.** Use the same code with a non-c0 static cepstral dimension
     dropped. Recommended: each of static c1…c12 for MFCC 4k un-normalised. (a) took
     337 s for 4 runs, so this is about 12 × 85 s ≈ 17 min. Report where the c0 share
     falls among the 12. Declare it before running.
  - Until both exist, reword to: "dropping static c0 changes α̂ for 12–14 % (MFCC) and
    6.4 % (PLP) of utterances; the mean and histogram are unchanged; no null has been
    measured".
  - The baseline note (α̂ under λ_r, not the trace) is enough once item 1 gives the number.
- **(b) "α̂ tracks the speaker within gender" is not supportable.** There are no speaker
  IDs and no gender labels. The 165 Hz split is an F0 proxy, and ρ is between two utterance
  properties. Supportable wording: "α̂ correlates negatively with utterance F0 overall and
  within each F0 group (< 165 Hz, ≥ 165 Hz)". Avoid "speaker" and "gender" in the sentence.
- **Partial ρ(c0, α̂ | F0): yes, the doc should say it is not evidence of the level
  mechanism.**
  - PLP gives +0.206, near MFCC's +0.235, although PLP's α̂ barely responds to gain
    (cycle 8: 8–9 %).
  - c0 at α = 1 also carries speaker and recording loudness, which F0 does not remove.
  - Suggested sentence: "the partial correlation is similar for MFCC and PLP although only
    MFCC's α̂ responds to gain, so it does not indicate the level mechanism".
- **Speaker IDs:** the HF copy has none (see the checks above), and its row order is
  shuffled. A speaker-cluster bootstrap would need a different TIMIT source. That is a data
  and licence question (LDC TIMIT), so it is a **user decision** if anyone wants it. **Not
  recommended now:**
  - Keep the "anti-conservative, utterance-level intervals" caveat, which is already in the
    doc.
  - Add one line saying the HF copy carries no speaker field.

## Q3. Plan Q41: normalised reference. **Change requested** (wording)

- **"Level handling does not explain the excess VTLN gain"** reads as ruling out any
  partial contribution, which the data cannot do: every `pn` − un-normalised interval is
  wide and includes 0. Supportable wording, using the declared paired gain:
  - "Under peak normalisation, where α̂ is invariant to waveform gain (K4 tests; Reviewer
    check on 100 utterances under λ_r), the paired VTLN gain remains +8.07 / +9.35 (MFCC)
    and +8.97 / +11.20 (PLP). The thesis's gain lies below our interval on every metric.
  - "Level normalisation therefore does not bring our VTLN gain to the thesis's."
  - "The 1.12 edge share is unchanged (0.128 vs 0.129, 0.197 vs 0.200)."
  - Put the gain-invariance check on real utterances in the doc as a Reviewer post hoc
    check, with its count (100 utterances, seed 1, ×0.5 and ×2, 0 % changed).
- **Two-changes caveat: yes, required on every `pn` − un-normalised comparison.** `pn`
  changes the normalisation and also introduces the query/document level mismatch (Q4).
  - Within-`pn` gains (VTLN − no VTLN) share the mismatch on both sides. They need only a
    one-line note that clip-level and utterance-level normalisation differ.
- **Marginal intervals (Reviewer check 4): agree.** Add one sentence: "every thesis row lies
  inside our marginal keyword-cluster intervals; the paired gain is the comparison that
  separates us from the thesis".

## Q4. New: query level under `pn`. **User decision** (author fact) plus recommendation

- **User decision:** in the thesis HTK pipeline, was each cut query file normalised on its
  own, or was the query cut from the already normalised utterance? The thesis text does not
  say (checks above).
  - If the answer is "cut after normalising the utterance", clip mode under `pn` does not
    match the thesis. The reference query path would change, which is a reference
    definition and needs the user.
- **Pending the answer, recommended: a declared, untuned level-matched clip run, not slice
  mode.**
  - Cut the clip from the utterance after utterance-level DC removal and peak scaling, so
    the clip carries the utterance's scale factor. Then extract features from the clip with
    normalisation off.
  - This changes only the level and keeps clip-mode deltas at the edges. Slice mode would
    also change the deltas (cycle 5) and, under VTLN, needs a query-α̂ design choice. The
    level-matched clip run needs neither: clip α̂ is estimated the usual way.
  - Rows: `pn` MFCC and PLP, no VTLN and VTLN, existing models. That is evaluation only,
    about 4 × 6 min.
  - Report paired level-matched − clip, plus the per-query ratio table (median 1.44, p90
    2.70) and query edge shares.
  - The run is a sensitivity analysis. It does not replace the D6 reference unless the user
    answers that queries were cut after normalising.
- **Expectation, so nobody over-reads the result:** the query 1.12 share is already high
  without normalisation (MFCC 0.186, PLP 0.283, with no mismatch there). `pn` adds about
  +0.04 for MFCC and +0.01 for PLP. The clip edge excess is therefore mostly a clip
  property, probably short clips giving noisy α̂, not a level effect.
- **Ratio table:** report it in the doc either way, labelled as a Reviewer post hoc check.

## Q5. Plan Q42: MFCC-TMP − MFCC with level matched. **Change requested** (wording) and **agree**

- **Agree with the qualification.** Suggested wording: "Not reproduced under VTLN (−1.03 /
  −0.73; the thesis's +6.62 / +5.90 lie above our intervals). Without VTLN the direction
  matches (+2.14 / +2.40, both intervals include 0); the thesis's p@N advantage (+5.12) lies
  above our interval and its MAP advantage (+4.79) lies inside it."
- **"Nothing about Teager energy" stays the only claim: agree.** Level handling is now
  closer, but the features still differ in lineage, filter count and band design, and VTLN
  response. Both now share clip-level peak normalisation, so the Q4 mismatch also applies
  to both.

## Q6. Edge pile-up and convergence (`pn`). **Agree** (caveat only), plus one free check

- **Do not widen the grid.** 0.88–1.12 in 13 steps is the thesis's grid. Widening it would
  depart from the reproduced method and would need the user. D4 fixed the procedure, not
  the grid, but that does not make widening a free choice.
- **Zero-compute check, recommended:** from `iter4_ll_matrix.npy`, for train utterances at
  α̂ = 1.12 (thesis label), report the distribution of LL(1.12) − LL(1.10).
  - If the margin is mostly large, the optimum likely lies outside the grid (a true edge
    effect).
  - If it is mostly near 0, the edge share reflects a flat LL plus tie-breaking.
  - Do the same for the 0.88 edge. This tells the doc which caveat to write without
    running anything.
- **Convergence:** caveat only. 15–20 % of utterances still change at iteration 4, and
  `ll_decreased` fired at iterations 3 (MFCC) and 1, 3, 4 (PLP), consistent with fresh-LBG
  churn (D4). N_iter 5 is the thesis value.
- **Query edge shares** (0.23, 0.29): link to the Q4 expectation paragraph, a clip
  property also present without normalisation.

## Q7. Other issues. **Agree** / **change requested** (small)

- **Test edit in report commit `5c301b9`:** harmless, no revert. Add a one-line process note
  to the plan: report commits touch docs only.
- **D6 table thesis rows:** relabel them "thesis (`Tab:TIMITPerformance` /
  `Tab:TIMITVTLNPerformance1`)" instead of our profile name.
- **K1 note:** yes, one sentence. "`selection_step_ok` holds by construction (α̂_k maximises
  each utterance's LL under λ_{k−1}); it is a bug guard, not an empirical finding."
- **GMM-128 under `pn` (plan §10 item 1):** suggested order is the Q4 level-matched run
  first (about 25 min), then GMM-128.
  - If level-matched − clip shows no difference, GMM-128 goes ahead in clip mode regardless
    of the author's answer.
  - If it differs, GMM-128 waits for the user's Q4 answer, so it is not run twice.
  - This is an ordering suggestion. The Orchestrator decides.

## User decisions (for the Orchestrator to put to the user)

1. **Author fact (Q4):** in the thesis HTK pipeline, were query clips normalised per cut
   file, or cut from the already normalised utterance?
2. **Data/licence (Q2, only if wanted):** use a TIMIT copy with speaker IDs (LDC) for a
   speaker-cluster bootstrap and true gender split. Not recommended now.
3. **Compute (Q2, Q4):** about 17 min score-free c0 control, plus about 25 min
   level-matched clip evaluation. Neither needs training.
