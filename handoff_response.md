# Handoff Response: Cycle 6

- **From:** Handoff_feedback. **To:** Orchestrator.
- **Scope:** `handoff_request.md` at `1a0c20f`; exec commits `3fb279d..ec565b5`.
- **Verdicts:** Q1 agree, Q2 agree, Q3 change requested, Q4 change requested with one
  **user decision**, Q5 agree, Q6 unknown, Q7 change requested, Q8 change requested.
- **What I checked myself (read-only, nothing written but this file):** the code and tests
  of C2, C4, C5 and `baa3bc3`; the split and results docs; the thesis chapters
  `ExpSetup.tex`, `Unsupervised.tex`, `Representation.tex`; `Fx_PLPCC_htk.m` and the file
  list of `research_myMATLAB_codes` on GitHub; and one scan of the v2 units against the
  transcripts (Q1). I did not re-run the test suite or any model.
- **Not available:** the local folder `D:\Storage\research_code_qbe_std` holds only the
  matching code (`matlab/*.cpp`, `Fx_do_SDTW.m`). The feature scripts exist only on GitHub.

The loop pauses for the user on Q4 (see "User decision" at the end).

## 1. Plan Q27, link scope: **agree**

Linking all 20 verified pairs is the right reading. Merging only the 8 crossed pairs
changes the step 2 and step 3 placements, so an unlinked pair could cross in v2.

The 7-row check is stronger than the doc says, because the whole corpus adds up. My scan
of the v2 units gives 448 units of 7 rows, 2 units of 6 rows and 1892 single-read units.
TIMIT has 450 SX texts read by 7 speakers and 1890 SI texts read once: 3150 + 1890 = 5040.
The two 6-row units each have a two-token variant among the single-read units, which
accounts for the 2 extra singles. So every multi-read unit is one SX text, and a wrong link
would have broken this count. That covers link 19 (`had/ate`) and the three-variant unit:
both complete a 7-row SX text.

The unlinked pair of two single-read groups (`0573d602eb5a` / `63b6c9fc4ec2`) is a
content-word substitution between two SI texts. Leaving it unlinked is correct.

One thing the doc should add (`docs/split_textdisjoint.md`, "What v2 does not do"):

- Two SX texts still have an unmerged variant that differs by **two** tokens:
  unit `675129c68a2c` (6 rows) with single `b180942ceff1` (a contraction written as two
  words), and unit `6d86e94d8394` (6 rows) with single `4c952c3a51e1` (one word moved).
- In both cases the variant is on the **train** side with its unit, so no SX text crosses
  sides in v2. That is by placement, not by rule.
- State the corpus count above as the evidence for the links.

I do not recommend a v3 for these two: nothing crosses, and merging them would change the
manifest hash for no change in content. That choice is the Orchestrator's.

## 2. Plan Q28, underdetermined components: **agree**

The hash-order choice is not a problem for the reported numbers. It was fixed before any
score and it uses no score. It is the same kind of arbitrary choice as step 3, which places
599 of the 624 test units by hash order.

The doc should say slightly more than the count (`docs/split_textdisjoint.md`, per-component
section):

- The product of the counts is 2,488,320 equal-cost keyword assignments; v2 is one of them.
- For a component with a count above 1, *which* utterances are that keyword's queries and
  documents depends on the fixed choice; the Inst./Occ. counts do not.
- The intervals in the results docs resample keywords. They do not measure this split-draw
  variation, which is unmeasured.

Do not score alternative assignments to look at the spread. Each one needs its own GMMs, and
it would invite choosing a split by score.

## 3. Plan Q29, row-selection scope: **change requested**

Keep the manual `ROW_SELECTION_VERSION`, but add a guard so the loop cannot change
unnoticed. `baa3bc3` shows the gap is real: the loop was edited and nothing forced a
decision about the version.

Concrete change, tests only, no fingerprint change and no cache rebuild:

- `tests/data/test_feature_cache.py`: add a test that hashes the source of
  `build_feature_cache` (`inspect.getsource`, CRLF turned into LF) and compares it with a
  constant pinned next to `ROW_SELECTION_VERSION`.
- The failure message says: "the row loop changed: bump `ROW_SELECTION_VERSION` if rows,
  order, offsets or skips changed, then update the pinned digest".

Moving the loop into its own hashed module is cleaner but changes every fingerprint, so all
caches and models would be rebuilt for no change in rows. If the Orchestrator wants it, fold
it into the next change that invalidates the caches anyway.

## 4. Plan Q30, front-end parity before VTLN: **change requested**, with one **user decision**

A parity check is warranted before any VTLN number is scored. Stage 4 code can be built
meanwhile; VTLN rows would inherit whatever profile is in place.

The reason is in the thesis, not in the scores. The chapter that reports the PLP and MFCC
numbers says both were extracted with **HTK**, with 25 ms / 10 ms frames, **26 subband
filters**, 13 coefficients plus delta and delta-delta (`Unsupervised.tex` line 113; also
`ExpSetup.tex` lines 191, 194, 198). Our `timit_matlab` profile takes each feature from a
different MATLAB script instead:

| Setting | Our MFCC | Our PLP | Thesis text |
|---|---|---|---|
| Tool | from `Fx_mfcc.m` | from `Fx_PLPCC_htk.m` defaults | HTK for both |
| Filters | 26 | 21 | 26 for both |
| Band | 0-4000 Hz | 0-8000 Hz | 0-4000 Hz stated for MFCC only |
| Pre-emphasis | 0.97 | none | not stated |
| LPC order | n/a | 8 | not stated |
| Level handling | DC removed, peak-normalised | neither | not stated |

So our two features differ in band, filter count, pre-emphasis and level handling at once,
and PLP − MFCC on this setup does not test the thesis's PLP − MFCC. `Fx_PLPCC_htk.m` takes
`nfilt` and `LP_order` as arguments; 21 and 8 are only its defaults, and no caller is in
the repository.

`docs/feature_parity.md` says the PLP filter count is "not stated". That is true of
`ExpSetup.tex` only. Correct the PLP row and the "What the thesis says" table with
`Unsupervised.tex` line 113.

**Smallest check** (GMM-64 only, split v2, same scorer; declared before running, both
results reported, primary rows unchanged):

1. MFCC with `normalize_peak=False`, everything else as now.
2. PLP with `normalize_peak=True`, everything else as now.

This isolates level handling, the one difference that the thesis cannot settle. A gain
change moves only the static c0 (a constant per utterance, in MFCC exactly and in PLP
through the LPC gain), so the two runs answer the Reviewer's Q5 as well.

**User decision.** Two things here are not the Orchestrator's to settle:

- **Data access:** the HTK configuration used for the thesis (target kind, `NUMCHANS`,
  band, sample rate, `LPCORDER`, c0 or energy) is not in the thesis sources or in either
  repository. Only the author can say whether it still exists. Without it, an "HTK-like"
  PLP profile (26 filters, pre-emphasis, order 12) would rest on HTK defaults recalled from
  memory.
- **Compute cost and scope:** the smallest check is 2 feature caches and 2 GMM-64 runs. An
  HTK-described profile for both features would be 4 more models and would replace the
  MATLAB-derived profile as the comparison reference.

## 5. PLP level dependence: **agree** (run it as part of Q4)

A named, untuned ablation is a diagnostic, not tuning, under these conditions: it is
declared with its setting before it runs; it is run in both directions (Q4 items 1 and 2);
every result is reported; and the primary rows stay on the declared profile whatever the
outcome. "c0 dropped" is not needed as a separate run, because level reaches the features
through c0 alone.

On the sources:

- `Fx_PLPCC_htk.m` does not normalise: it only scales by 32768 (line 69). No script in
  `research_myMATLAB_codes` calls it, so whether the experiment code normalised first is
  **unknown**.
- The thesis does not mention waveform normalisation for any feature.
- The thesis labels PLP as `PLP_D_A_0` in its phoneme-recognition tables (for example
  `Unsupervised.tex` line 610). That is an HTK target kind with c0 and no energy term. It is
  a hint that the thesis PLP also carried the raw level, not proof for the QbE-STD runs.

## 6. MFCC above the thesis: **unknown**

No listed cause can be confirmed from what is in the repository. My ranking:

1. **Front end (most likely).** The thesis MFCC came from HTK; ours follows a MATLAB script
   with peak normalisation. The pattern across features fits one explanation, as a
   hypothesis only: the two peak-normalised features sit at or above the thesis (MFCC +5.1
   p@N, MFCC-TMP −0.9 against a thesis MFCC-TMP that also came from the peak-normalising
   MATLAB script), and the one feature without it sits below (PLP −2.3). If that holds, part
   of the thesis's +5 for MFCC-TMP over MFCC could be a level-handling difference between
   two tools. Q4 item 1 tests this directly and needs no speaker IDs.
2. **Speaker overlap.** Plausible, since the GMM has seen other utterances of the test
   speakers. Not checkable without speaker IDs.
3. **Split draw.** Unmeasured (Q2). The keyword-cluster interval is not the right yardstick
   for a gap to the thesis, because the thesis used the same 20 keywords.
4. **16 kHz with a 4 kHz band, c0 and 39 dimensions, aggregation.** The band and the 39
   dimensions match the thesis text. The sample rate and the c0-or-energy choice are part
   of the HTK question in Q4. Both averages are already shown.

## 7. Wording: **change requested**

The verdict labels follow the C6 rule. Four corrections in
`docs/results_timit_q20_features.md`:

- **Do not add "PLP is near its thesis value" as written.** It holds at GMM-64 only
  (−2.28 p@N, −4.03 MAP). At GMM-128 PLP is −5.39 / −7.92 below the thesis, while MFCC is
  +6.13 / +6.62 above. Add the per-feature gaps to the thesis at both sizes as a small
  descriptive table instead, with no cause attached.
- **Source of the thesis values.** The doc says they are the `Tab:ExpResultTIMIT` rows.
  That table has no MFCC-TMP row. MFCC-TMP 40.03 / 41.50 comes from
  `Tab:TIMITVTLNPerformance1` (`Representation.tex` line 270). Name both tables.
- **Say what the feature comparison compares.** Add one sentence under "Feature minus MFCC":
  PLP and MFCC differ here in band, filter count, pre-emphasis and level handling (Q4), so
  "against the thesis's direction" describes this profile, not PLP as such.
- **Many intervals.** The paired tables hold 28 unadjusted 95 % intervals. Say so, and note
  that the single marginal one (MFCC-TMP − MFCC, keyword p@N, −2.8 to −0.1) should not be
  read on its own.

Minor: the thesis values are printed as 35.5, 41.5 and 37.3; write 35.50, 41.50 and 37.30.

## 8. Other issues: **change requested**

None of these affects a reported number.

- **Import-closure helper** (`tests/data/test_feature_cache.py`): the relative-import
  resolution is correct for `from .x import y`, `from . import x` and two-dot imports. The
  fixture covers one-dot forms only. Add a case with `from ..audio import newhelper`. The
  helper still misses `from qbestd import features` followed by attribute access, and
  names re-exported through an `__init__.py`; both `__init__.py` files are docstrings
  today, so nothing is missed now. Add both limits to the docstring.
- **Finder with two partners** (`text_variants.find_variant_candidates`): deterministic.
  Each pair is judged on its own and the result is `sorted(set(...))`, so a group with two
  partners yields two candidates in a fixed order. No test pins it. Add one in
  `tests/data/test_text_variants.py` (a 4-row group with a 1-row and a 2-row partner), and
  put a three-variant unit into `test_v2_manifest_is_identical_under_shuffled_rows_and_links`.
- **`_merge_units` runs for v1 too** (`text_split.py`): with `links=()` it still raises
  for any group of more than 7 rows. That is a new failure mode of the v1 rule, harmless on
  TIMIT (the largest group has 7 rows) and undocumented. Either skip the cap when there are
  no links or say so in the docstring.
- **`gmm_notes.md`:** add the PLP variances at the floor (4 of 2496, 7 of 4992), as the
  MFCC section does.
- **Provenance of runs:** the feature fingerprint pins features and rows, not the GMM or
  evaluation code. `4e95d7e..5145ced` changed only docs, `requirements.md`,
  `feature_cache.py` and its tests, so the cycle 6 numbers stand. For later cycles, do not
  commit to the working tree while a background chain is running, or run the chain from a
  fixed commit in a separate worktree.
- **MFCC-TMP cache build** computes the Teager energies twice (once for the features, once
  for the floor count). Correct, only slower; no change needed.
- **PEP 8 and security:** nothing found. No sentence text, credentials or derived data are
  committed.

## User decision (the loop pauses here)

From Q4:

1. Does the HTK configuration used for the thesis MFCC and PLP still exist, or can the
   author state the target kind, filter count, band, sample rate and LPC order?
2. Approve the two-run level-handling check (2 caches, 2 GMM-64 models), yes or no.
3. Should an HTK-described profile replace `timit_matlab` as the comparison reference for
   MFCC and PLP? This is larger: 4 more models, and every later table changes reference.
