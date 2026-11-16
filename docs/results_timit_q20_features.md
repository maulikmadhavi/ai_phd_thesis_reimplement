# TIMIT Q-20: MFCC, PLP and MFCC-TMP on split v2

All rows use the text-disjoint split `textdisjoint_q20_v2-0e913c50aae7` (declared in
`docs/split_textdisjoint.md`), the same 145 queries, 1344 documents and
relevance for every feature, LC2, clip query features, the A1 scorer and the
keyword-cluster bootstrap (10000 resamples, seed 0). **No VTLN** (Stage 4 is
not built), **no tuning**, and no front-end change after seeing scores.
The HF split v2 and v1 rows, the MFCC section and the per-keyword tables are
in `docs/results_timit_q20.md` and are not repeated.

**Labels: closer to the thesis on sentence context; not an official TIMIT
reconstruction; speaker overlap present (amount unknown).** The per-keyword
instances and relevant documents equal the thesis table for all 20 keywords.
"Instance average" and "keyword average" are both given because the thesis
does not say which it reports (open question 20).

## Results

| Row | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Non-matches |
|---|---|---|---|---|---|---|
| MFCC, GMM-64, thesis | 34.91 | 36.71 | not stated | not stated | 145 | n/a |
| MFCC, GMM-64, ours v2 | 40.02 (30.8-49.7) | 42.23 (31.5-53.6) | 36.92 (28.1-45.9) | 39.09 (29.3-49.2) | 145 | 0 |
| PLP, GMM-64, thesis | 35.50 | 37.58 | not stated | not stated | 145 | n/a |
| PLP, GMM-64, ours v2 | 33.22 (22.8-45.0) | 33.55 (22.6-46.1) | 29.41 (21.2-38.5) | 30.03 (21.4-39.7) | 145 | 0 |
| MFCC-TMP, GMM-64, thesis | 40.03 | 41.50 | not stated | not stated | 145 | n/a |
| MFCC-TMP, GMM-64, ours v2 | 39.17 (29.6-48.9) | 41.15 (30.7-52.1) | 35.44 (26.4-44.5) | 37.65 (28.3-47.3) | 145 | 1 |
| MFCC, GMM-128, thesis | 36.81 | 38.34 | not stated | not stated | 145 | n/a |
| MFCC, GMM-128, ours v2 | 42.94 (32.8-54.1) | 44.96 (34.2-56.7) | 40.19 (31.3-49.5) | 42.38 (32.9-52.3) | 145 | 1 |
| PLP, GMM-128, thesis | 37.30 | 40.18 | not stated | not stated | 145 | n/a |
| PLP, GMM-128, ours v2 | 31.91 (23.6-41.0) | 32.26 (21.9-43.9) | 30.11 (22.9-37.9) | 30.46 (21.7-40.0) | 145 | 0 |
| MFCC-TMP, GMM-128, thesis | not in thesis | not in thesis | not stated | not stated | - | n/a |
| MFCC-TMP, GMM-128, ours v2 | 41.94 (33.0-51.1) | 43.88 (33.9-54.3) | 38.04 (29.5-46.5) | 40.20 (30.8-49.5) | 145 | 1 |

The thesis does **not** give a GMM-128 value for MFCC-TMP; there is no
target for that row. The thesis does not state intervals.

**Sources of the thesis values.** MFCC and PLP come from
`Tab:ExpResultTIMIT` (GMM rows, `Unsupervised.tex`). MFCC-TMP 40.03 / 41.50
comes from `Tab:TIMITVTLNPerformance1` (`Representation.tex` line 270, the
MFCC-TMP "no VTLN" row), a different table.

### Gap to the thesis (descriptive, no cause attached)

Ours v2 minus thesis, instance average, p@N / MAP:

| Feature | GMM-64 | GMM-128 |
|---|---|---|
| MFCC | +5.11 / +5.52 | +6.13 / +6.62 |
| PLP | -2.28 / -4.03 | -5.39 / -7.92 |
| MFCC-TMP | -0.86 / -0.35 | no thesis value |

The gaps differ in sign and size across features. This table states them and
nothing more: it gives no reason for them, and no feature is called near or
far from its thesis value.

## Paired differences

The queries, documents and relevance are identical across features, so a
paired keyword-cluster bootstrap applies (95 %, difference "second minus
first"). "In the thesis's direction" is said only where the interval
excludes 0 on the thesis side; it is never a claim of numerical parity.
Thesis differences are computed from the thesis table values.

### Feature minus MFCC

**MFCC-TMP minus MFCC compares a MATLAB-described front end** (26 filters,
0-4000 Hz, peak-normalised) **with an HTK-described one**, which is what the
thesis did by the author's statement. Under `timit_matlab` both features
here are MATLAB-derived, so the rows below are not that comparison; the
`htk_described` comparison is in the Stage 4 section below.

Bounds that round to 0.0 are printed with two decimals, and "excludes 0"
is taken from the unrounded value.

PLP and MFCC differ here in band, filter count, pre-emphasis and level
handling, so "against the thesis's direction" describes this profile, not PLP
as such (`docs/feature_parity.md`).

The paired tables below hold 28 unadjusted 95 % intervals (16 for feature
minus MFCC, 12 for GMM-128 minus GMM-64). With that many, an interval that
barely excludes 0 is not strong evidence. The single marginal one,
MFCC-TMP minus MFCC at GMM-64, keyword p@N (-2.8 to -0.1), should not be
read on its own.

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Thesis diff p@N / MAP | p@N verdict | MAP verdict |
|---|---|---|---|---|---|---|
| PLP - MFCC, GMM-64 | instance | -6.80 (-11.9 to -2.0) | -8.67 (-14.0 to -3.8) | +0.59 / +0.87 | against the thesis's direction (interval excludes 0) | against the thesis's direction (interval excludes 0) |
| PLP - MFCC, GMM-64 | keyword | -7.51 (-12.6 to -2.8) | -9.05 (-14.4 to -4.1) | +0.59 / +0.87 | against the thesis's direction (interval excludes 0) | against the thesis's direction (interval excludes 0) |
| MFCC-TMP - MFCC, GMM-64 | instance | -0.85 (-2.5 to +0.6) | -1.08 (-2.7 to +0.2) | +5.12 / +4.79 | interval includes 0: no direction claimed | interval includes 0: no direction claimed |
| MFCC-TMP - MFCC, GMM-64 | keyword | -1.48 (-2.8 to -0.1) | -1.43 (-3.2 to +0.2) | +5.12 / +4.79 | against the thesis's direction (interval excludes 0) | interval includes 0: no direction claimed |
| PLP - MFCC, GMM-128 | instance | -11.03 (-14.7 to -7.5) | -12.70 (-17.1 to -8.7) | +0.49 / +1.84 | against the thesis's direction (interval excludes 0) | against the thesis's direction (interval excludes 0) |
| PLP - MFCC, GMM-128 | keyword | -10.08 (-14.6 to -5.7) | -11.92 (-17.3 to -7.0) | +0.49 / +1.84 | against the thesis's direction (interval excludes 0) | against the thesis's direction (interval excludes 0) |
| MFCC-TMP - MFCC, GMM-128 | instance | -1.00 (-4.2 to +2.2) | -1.08 (-3.8 to +2.1) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |
| MFCC-TMP - MFCC, GMM-128 | keyword | -2.15 (-4.6 to +0.4) | -2.19 (-4.4 to +0.1) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |

### GMM-128 minus GMM-64, per feature

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Thesis diff p@N / MAP | p@N verdict | MAP verdict |
|---|---|---|---|---|---|---|
| MFCC: GMM-128 - GMM-64 | instance | +2.92 (+0.5 to +5.6) | +2.73 (+0.7 to +5.1) | +1.90 / +1.63 | in the thesis's direction (interval excludes 0) | in the thesis's direction (interval excludes 0) |
| MFCC: GMM-128 - GMM-64 | keyword | +3.27 (+0.8 to +5.7) | +3.30 (+0.8 to +6.0) | +1.90 / +1.63 | in the thesis's direction (interval excludes 0) | in the thesis's direction (interval excludes 0) |
| PLP: GMM-128 - GMM-64 | instance | -1.31 (-4.9 to +1.8) | -1.30 (-3.7 to +1.5) | +1.80 / +2.60 | interval includes 0: no direction claimed | interval includes 0: no direction claimed |
| PLP: GMM-128 - GMM-64 | keyword | +0.70 (-2.3 to +3.6) | +0.43 (-2.8 to +3.9) | +1.80 / +2.60 | interval includes 0: no direction claimed | interval includes 0: no direction claimed |
| MFCC-TMP: GMM-128 - GMM-64 | instance | +2.76 (+0.8 to +4.6) | +2.73 (+0.6 to +5.0) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |
| MFCC-TMP: GMM-128 - GMM-64 | keyword | +2.61 (+0.7 to +4.4) | +2.55 (+0.8 to +4.2) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |

## Reading the tables (descriptive; nothing was changed after seeing them)

- **PLP is below MFCC on this setup**, at both sizes, in both averages, and
  every paired interval excludes 0 (for example GMM-64 instance p@N -6.80,
  -11.9 to -2.0). The thesis has PLP slightly above MFCC. This is the
  opposite of the thesis direction. No PLP front-end setting was changed or
  tuned; whether a front-end parity check is warranted before VTLN is open
  question 30 for the review.
- **MFCC-TMP against MFCC at GMM-64:** the point differences are small and
  negative (about -1 p@N and -1 MAP). Only the keyword-averaged p@N interval
  excludes 0 (-1.48, -2.8 to -0.1), against the thesis direction; the other
  three intervals include 0, so no direction is claimed. The thesis gain of
  about +5 is not reproduced here, and the point estimates do not reach it.
- **GMM-128 against GMM-64:** MFCC and MFCC-TMP gain about +2.6 to +3.3 with
  intervals above 0 (the thesis gives no MFCC-TMP value for 128). PLP does
  not gain: its paired intervals include 0, and the point estimate is
  negative for the instance average.
- All intervals come from 20 keyword clusters and are wide (about 20 points
  for one row); the paired intervals are narrower. Non-match counts of 1
  (MFCC-TMP and MFCC GMM-128) rank a document last and are counted, not
  dropped.

## Level-handling check (declared)

**Declared before any run of it** (cycle 7, L1; Handoff_feedback Q4 items 1
and 2, Reviewer Q5). The two features differ in several settings at once
(`docs/feature_parity.md`). The one difference the thesis cannot settle is
level handling: our MFCC removes DC and peak-normalises the waveform, our PLP
does neither (as `Fx_PLPCC_htk.m` does not). This check flips only that, in
both directions. A gain change moves only the static c0 (a constant per
utterance in MFCC, and through the LPC gain in PLP).

- **Setting:** the ablation profile `timit_matlab_levelflip`.
  - MFCC: `timit_matlab` with `normalize_peak=False`.
  - PLP: `timit_matlab` with `normalize_peak=True`.
  - Nothing else changes: band, filters, pre-emphasis, LPC order, DC
    removal, lifter, deltas, the GMM recipe, the seed and the split.
  - It raises for MFCC-TMP.
- **Scope:** GMM-64 only, split v2 (`textdisjoint_q20_v2`), LC2, clip query
  features, the A1 scorer and the keyword-cluster bootstrap (10000
  resamples, seed 0). 2 caches, 2 models, 2 evaluations.
- **Rule:** both results are reported, whatever they show. The primary
  `timit_matlab` rows above stay unchanged. No tuning follows from this
  check, and no setting is chosen because of it. Reported: p@N and MAP for
  both averages with intervals; paired differences against the primary
  GMM-64 row of the same feature (same queries); PLP minus MFCC under the
  flip. No cause is claimed beyond what the paired intervals show.

### Result of the level-handling check

Run as declared: GMM-64, split v2, LC2, clip query features, A1 scorer, the
same 145 queries and 1344 documents, the keyword-cluster bootstrap (10000
resamples, seed 0). The primary rows above are unchanged. Nothing was tuned
and no setting was chosen from this result.

| Row | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Non-matches |
|---|---|---|---|---|---|---|
| MFCC primary (`timit_matlab`) | 40.02 (30.8-49.7) | 42.23 (31.5-53.6) | 36.92 (28.1-45.9) | 39.09 (29.3-49.2) | 145 | 0 |
| MFCC flipped (peak normalisation off) | 41.54 (32.3-51.4) | 42.32 (31.8-53.7) | 38.60 (29.7-47.6) | 38.79 (29.3-48.6) | 145 | 0 |
| PLP primary (`timit_matlab`) | 33.22 (22.8-45.0) | 33.55 (22.6-46.1) | 29.41 (21.2-38.5) | 30.03 (21.4-39.7) | 145 | 0 |
| PLP flipped (peak normalisation on) | 31.77 (21.6-43.7) | 32.30 (21.3-45.5) | 28.93 (20.8-38.0) | 28.95 (20.4-38.8) | 145 | 0 |

Paired differences (same queries; second minus first; 95 % keyword-cluster
bootstrap; the last column says whether the interval excludes 0 for p@N /
MAP). They are descriptive: no thesis direction is attached.

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) |
|---|---|---|---|---|
| MFCC: flipped - primary | instance | +1.51 (-0.9 to +3.6) | +0.09 (-2.6 to +2.8) | no / no |
| MFCC: flipped - primary | keyword | +1.68 (-0.8 to +4.0) | -0.30 (-3.0 to +2.5) | no / no |
| PLP: flipped - primary | instance | -1.45 (-3.0 to +0.3) | -1.26 (-2.8 to +0.4) | no / no |
| PLP: flipped - primary | keyword | -0.48 (-2.2 to +1.3) | -1.08 (-2.6 to +0.4) | no / no |
| PLP - MFCC, both flipped | instance | -9.77 (-14.8 to -4.9) | -10.02 (-14.8 to -5.4) | yes / yes |
| PLP - MFCC, both flipped | keyword | -9.67 (-14.9 to -4.9) | -9.84 (-14.7 to -5.3) | yes / yes |
| PLP - MFCC, both primary (for reference) | instance | -6.80 (-11.9 to -2.0) | -8.67 (-14.0 to -3.8) | yes / yes |
| PLP - MFCC, both primary (for reference) | keyword | -7.51 (-12.6 to -2.8) | -9.05 (-14.4 to -4.1) | yes / yes |

What the intervals show, and no more: flipping the level handling gives
paired differences whose intervals all include 0, for both features and both
averages, so this check does not detect a change; the paired intervals allow
differences of up to about 3 to 4 points either way. PLP minus MFCC
stays negative with both features flipped (instance p@N -9.77, -14.8 to -4.9),
with intervals that exclude 0. The check does not say why the two features
sit on different sides of their thesis values, and it gives no reason to
change level handling for MFCC-TMP. The profile changes level handling only;
band, filter count and pre-emphasis still differ (`docs/feature_parity.md`).

Provenance:

| Model | Parameter SHA-256 | Feature fingerprint | Non-matches | Commit the run started from |
|---|---|---|---|---|
| MFCC flipped GMM-64 | `16d28a65ecbb4488...` | `662051e26345...` | 0 | `6f72775` |
| PLP flipped GMM-64 | `b93620c6635e2fab...` | `627b4edd180b...` | 0 | `6f72775` |

The primary models are `docs/gmm_notes.md`; the EM curves of these two models
are in `outputs/models/textdisjoint_q20_v2/` (git-ignored).

## HTK-described profile (reference from cycle 7)

**Profile `htk_described`** (user decision D2): 16 kHz, **0-3400 Hz band**,
`NUMCHANS = 40` for MFCC and PLP (author statement, 2026-11-16); 25 ms / 10
ms, 13 coefficients plus delta and delta-delta (thesis); pre-emphasis 0.97,
lifter 22, PLP LPC order 12, no DC removal and no peak normalisation (HTK
defaults, **recalled and unverified**). Every value and its source is in the
docstring of `qbestd.features.profiles._htk_described`. **Open user item:**
whether MFCC should use the author's 0-3400 Hz band or the thesis text's
0-4000 Hz is not confirmed; 0-3400 Hz is kept and flagged. From here on
`htk_described` is the comparison reference for MFCC and PLP; **MFCC-TMP stays
`timit_matlab`** (it came from the MATLAB script with 26 filters). The
`timit_matlab` rows stay as a labelled earlier reference. Same split v2, 145
queries, 1344 documents, LC2, clip query features, A1 scorer and bootstrap
(10000 resamples, seed 0) as above. **Nothing was tuned** towards the thesis
values, and no setting was changed after seeing a score.

| Row | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Non-matches |
|---|---|---|---|---|---|---|
| MFCC, GMM-64, thesis | 34.91 | 36.71 | not stated | not stated | 145 | n/a |
| MFCC, GMM-64, `htk_described` | 34.58 (25.6-44.1) | 35.73 (26.4-45.8) | 32.51 (24.8-40.7) | 33.50 (25.0-42.3) | 145 | 1 |
| MFCC, GMM-64, `timit_matlab` (earlier reference) | 40.02 (30.8-49.7) | 42.23 (31.5-53.6) | 36.92 (28.1-45.9) | 39.09 (29.3-49.2) | 145 | 0 |
| PLP, GMM-64, thesis | 35.50 | 37.58 | not stated | not stated | 145 | n/a |
| PLP, GMM-64, `htk_described` | 34.34 (26.1-42.6) | 35.88 (26.5-45.8) | 31.83 (24.3-39.6) | 33.37 (25.2-42.0) | 145 | 0 |
| PLP, GMM-64, `timit_matlab` (earlier reference) | 33.22 (22.8-45.0) | 33.55 (22.6-46.1) | 29.41 (21.2-38.5) | 30.03 (21.4-39.7) | 145 | 0 |
| MFCC, GMM-128, thesis | 36.81 | 38.34 | not stated | not stated | 145 | n/a |
| MFCC, GMM-128, `htk_described` | 38.04 (29.7-47.0) | 39.87 (30.7-50.0) | 36.20 (28.2-44.3) | 37.53 (29.1-46.3) | 145 | 1 |
| MFCC, GMM-128, `timit_matlab` (earlier reference) | 42.94 (32.8-54.1) | 44.96 (34.2-56.7) | 40.19 (31.3-49.5) | 42.38 (32.9-52.3) | 145 | 1 |
| PLP, GMM-128, thesis | 37.30 | 40.18 | not stated | not stated | 145 | n/a |
| PLP, GMM-128, `htk_described` | 38.33 (29.8-47.0) | 39.73 (30.2-49.9) | 35.96 (28.6-43.6) | 37.11 (29.2-45.5) | 145 | 0 |
| PLP, GMM-128, `timit_matlab` (earlier reference) | 31.91 (23.6-41.0) | 32.26 (21.9-43.9) | 30.11 (22.9-37.9) | 30.46 (21.7-40.0) | 145 | 0 |

### Gap to the thesis (descriptive, no cause attached)

`htk_described`, instance average, ours minus thesis, p@N / MAP:

| Feature | GMM-64 | GMM-128 |
|---|---|---|
| MFCC | -0.33 / -0.98 | +1.23 / +1.53 |
| PLP | -1.16 / -1.70 | +1.03 / -0.45 |

Thesis values are `Tab:ExpResultTIMIT` (`Unsupervised.tex`).

Paired differences use the same queries (second minus first, 95 %
keyword-cluster bootstrap); the thesis-direction wording rule is as above.
There are 32 unadjusted intervals in these three tables.

### PLP minus MFCC, `htk_described`

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Thesis diff p@N / MAP | p@N verdict | MAP verdict |
|---|---|---|---|---|---|---|
| PLP - MFCC, GMM-64 | instance | -0.24 (-3.5 to +3.4) | +0.14 (-2.4 to +3.0) | +0.59 / +0.87 | interval includes 0: no direction claimed | interval includes 0: no direction claimed |
| PLP - MFCC, GMM-64 | keyword | -0.68 (-4.2 to +3.0) | -0.13 (-2.8 to +2.8) | +0.59 / +0.87 | interval includes 0: no direction claimed | interval includes 0: no direction claimed |
| PLP - MFCC, GMM-128 | instance | +0.28 (-1.9 to +2.3) | -0.15 (-2.5 to +2.1) | +0.49 / +1.84 | interval includes 0: no direction claimed | interval includes 0: no direction claimed |
| PLP - MFCC, GMM-128 | keyword | -0.25 (-2.8 to +2.2) | -0.42 (-2.7 to +2.0) | +0.49 / +1.84 | interval includes 0: no direction claimed | interval includes 0: no direction claimed |

### GMM-128 minus GMM-64, `htk_described`

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Thesis diff p@N / MAP | p@N verdict | MAP verdict |
|---|---|---|---|---|---|---|
| MFCC: GMM-128 - GMM-64 | instance | +3.46 (+0.6 to +7.6) | +4.14 (+1.8 to +7.3) | +1.90 / +1.63 | in the thesis's direction (interval excludes 0) | in the thesis's direction (interval excludes 0) |
| MFCC: GMM-128 - GMM-64 | keyword | +3.69 (+0.2 to +7.9) | +4.03 (+1.8 to +6.9) | +1.90 / +1.63 | in the thesis's direction (interval excludes 0) | in the thesis's direction (interval excludes 0) |
| PLP: GMM-128 - GMM-64 | instance | +3.98 (+1.6 to +6.5) | +3.85 (+1.6 to +6.3) | +1.80 / +2.60 | in the thesis's direction (interval excludes 0) | in the thesis's direction (interval excludes 0) |
| PLP: GMM-128 - GMM-64 | keyword | +4.12 (+1.9 to +6.5) | +3.75 (+1.6 to +5.9) | +1.80 / +2.60 | in the thesis's direction (interval excludes 0) | in the thesis's direction (interval excludes 0) |

### `htk_described` minus `timit_matlab`

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Thesis diff p@N / MAP | p@N verdict | MAP verdict |
|---|---|---|---|---|---|---|
| MFCC GMM-64: `htk_described` - `timit_matlab` | instance | -5.44 (-8.6 to -1.9) | -6.50 (-10.1 to -2.6) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |
| MFCC GMM-64: `htk_described` - `timit_matlab` | keyword | -4.41 (-8.0 to -0.7) | -5.59 (-9.3 to -1.8) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |
| MFCC GMM-128: `htk_described` - `timit_matlab` | instance | -4.90 (-8.4 to -1.0) | -5.09 (-8.7 to -1.2) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |
| MFCC GMM-128: `htk_described` - `timit_matlab` | keyword | -3.99 (-7.2 to -0.8) | -4.86 (-8.0 to -1.5) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |
| PLP GMM-64: `htk_described` - `timit_matlab` | instance | +1.12 (-4.6 to +6.8) | +2.32 (-2.7 to +7.5) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |
| PLP GMM-64: `htk_described` - `timit_matlab` | keyword | +2.42 (-3.1 to +8.3) | +3.33 (-1.6 to +8.9) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |
| PLP GMM-128: `htk_described` - `timit_matlab` | instance | +6.42 (+3.2 to +10.0) | +7.47 (+4.0 to +11.4) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |
| PLP GMM-128: `htk_described` - `timit_matlab` | keyword | +5.84 (+1.7 to +10.4) | +6.65 (+2.1 to +11.4) | not stated | no thesis value: descriptive only | no thesis value: descriptive only |

### Provenance

| Model | Parameter SHA-256 | Feature fingerprint | Non-matches | Commit the eval started from |
|---|---|---|---|---|
| MFCC GMM-64 | `0faff5b8234e81bb...` | `ab3ef12487f2...` | 1 | `cb24a64` |
| MFCC GMM-128 | `36693f287491491f...` | `ab3ef12487f2...` | 1 | `cb24a64` |
| PLP GMM-64 | `fa99eafd6a2aa01b...` | `dc733b030de8...` | 0 | `cb24a64` |
| PLP GMM-128 | `e2bcd79b2ba0bc1b...` | `dc733b030de8...` | 0 | `cb24a64` |

EM curves, floor counts and hashes: `docs/gmm_notes.md`. The PLP GMM-128
evaluation was interrupted once (the session restarted at query 120 of 145)
and re-run from the same, unchanged model file (hash checked against the
training log); its summary records the commit of the re-run.

## Band comparison

Declared in `docs/feature_parity.md` ("Band comparison (declared)") before
any run. `htk_described_4k` is `htk_described` with the band widened from
0-3400 Hz to 0-4000 Hz for both MFCC and PLP; nothing else differs. Same
split v2, 145 queries, 1344 documents, LC2, clip query features, A1 scorer
and bootstrap (10000 resamples, seed 0). **No band is chosen by its score;**
`htk_described` (0-3400 Hz) stays the reference, and the choice is the
user's. Nothing was tuned.

| Row | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Non-matches |
|---|---|---|---|---|---|---|
| MFCC, GMM-64, thesis | 34.91 | 36.71 | not stated | not stated | 145 | n/a |
| MFCC, GMM-64, 0-3400 Hz (`htk_described`, reference) | 34.58 (25.6-44.1) | 35.73 (26.4-45.8) | 32.51 (24.8-40.7) | 33.50 (25.0-42.3) | 145 | 1 |
| MFCC, GMM-64, 0-4000 Hz (`htk_described_4k`) | 37.48 (28.0-47.6) | 40.50 (30.1-52.1) | 35.07 (26.6-43.9) | 37.84 (28.4-47.6) | 145 | 3 |
| PLP, GMM-64, thesis | 35.50 | 37.58 | not stated | not stated | 145 | n/a |
| PLP, GMM-64, 0-3400 Hz (`htk_described`, reference) | 34.34 (26.1-42.6) | 35.88 (26.5-45.8) | 31.83 (24.3-39.6) | 33.37 (25.2-42.0) | 145 | 0 |
| PLP, GMM-64, 0-4000 Hz (`htk_described_4k`) | 38.59 (29.1-48.5) | 39.75 (29.3-50.9) | 35.82 (27.1-44.8) | 36.81 (27.5-46.5) | 145 | 0 |
| MFCC, GMM-128, thesis | 36.81 | 38.34 | not stated | not stated | 145 | n/a |
| MFCC, GMM-128, 0-3400 Hz (`htk_described`, reference) | 38.04 (29.7-47.0) | 39.87 (30.7-50.0) | 36.20 (28.2-44.3) | 37.53 (29.1-46.3) | 145 | 1 |
| MFCC, GMM-128, 0-4000 Hz (`htk_described_4k`) | 40.99 (31.2-51.8) | 42.89 (32.2-54.5) | 37.75 (29.2-46.7) | 39.80 (30.6-49.5) | 145 | 1 |
| PLP, GMM-128, thesis | 37.30 | 40.18 | not stated | not stated | 145 | n/a |
| PLP, GMM-128, 0-3400 Hz (`htk_described`, reference) | 38.33 (29.8-47.0) | 39.73 (30.2-49.9) | 35.96 (28.6-43.6) | 37.11 (29.2-45.5) | 145 | 0 |
| PLP, GMM-128, 0-4000 Hz (`htk_described_4k`) | 37.60 (29.8-45.7) | 40.01 (30.3-50.3) | 35.62 (28.2-43.2) | 37.51 (28.9-46.5) | 145 | 1 |

### Gap to the thesis (descriptive, no cause attached)

Instance average, ours minus thesis, p@N / MAP:

| Feature, band | GMM-64 | GMM-128 |
|---|---|---|
| MFCC, 0-3400 Hz | -0.33 / -0.98 | +1.23 / +1.53 |
| MFCC, 0-4000 Hz | +2.57 / +3.79 | +4.18 / +4.55 |
| PLP, 0-3400 Hz | -1.16 / -1.70 | +1.03 / -0.45 |
| PLP, 0-4000 Hz | +3.09 / +2.17 | +0.30 / -0.17 |

### Paired 4000 minus 3400 Hz

Same queries, 95 % keyword-cluster bootstrap; "second minus first". There is
no thesis difference for a band, so these rows are descriptive and no
direction is claimed beyond what the interval shows. 8 rows,
16 unadjusted intervals.

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) |
|---|---|---|---|---|
| MFCC GMM-64: 4000 - 3400 Hz | instance | +2.89 (+0.05 to +5.9) | +4.77 (+2.1 to +7.5) | yes / yes |
| MFCC GMM-64: 4000 - 3400 Hz | keyword | +2.55 (-0.6 to +5.8) | +4.34 (+1.6 to +7.4) | no / yes |
| MFCC GMM-128: 4000 - 3400 Hz | instance | +2.95 (+0.2 to +5.9) | +3.02 (+0.5 to +5.3) | yes / yes |
| MFCC GMM-128: 4000 - 3400 Hz | keyword | +1.55 (-0.9 to +4.1) | +2.27 (+0.3 to +4.2) | no / yes |
| PLP GMM-64: 4000 - 3400 Hz | instance | +4.25 (+0.6 to +7.6) | +3.88 (+1.2 to +6.5) | yes / yes |
| PLP GMM-64: 4000 - 3400 Hz | keyword | +3.99 (+0.4 to +7.8) | +3.44 (+0.7 to +6.2) | yes / yes |
| PLP GMM-128: 4000 - 3400 Hz | instance | -0.73 (-3.1 to +1.4) | +0.28 (-2.5 to +2.7) | no / no |
| PLP GMM-128: 4000 - 3400 Hz | keyword | -0.34 (-2.7 to +1.9) | +0.40 (-2.3 to +3.1) | no / no |

Reading, descriptive only: the point differences are positive in 6 of the 8
rows for p@N and 8 of 8 for MAP, and the intervals exclude 0 in 10 of 16
cases, several of them barely (lower edge +0.05 to +0.6). PLP at GMM-128 shows
no difference. With 16 unadjusted intervals, the barely-excluding ones should
not be read on their own. Both bands stay on the record; this does not say
which band the thesis used, and the choice of the reference band is the
user's. In the gap table the 0-4000 Hz MFCC rows sit above the thesis and
the 0-3400 Hz rows close to it; no cause is claimed.

### Provenance

| Model | Parameter SHA-256 | Feature fingerprint | Mean LL per frame, start -> end | Variances at the floor | Non-matches | Commit the eval started from |
|---|---|---|---|---|---|---|
| MFCC GMM-64 | `324ebb5f6fee9d41...` | `cacb263d6c29...` | -118.303 -> -116.610 (monotonic) | 3 of 2496 | 3 | `be5c4f0` |
| MFCC GMM-128 | `e7ef90b43b90b859...` | `cacb263d6c29...` | -117.723 -> -115.807 (monotonic) | 4 of 4992 | 1 | `be5c4f0` |
| PLP GMM-64 | `751a0f9578e3c0d6...` | `56f4d6ed50e3...` | 11.615 -> 13.137 (monotonic) | 3 of 2496 | 0 | `be5c4f0` |
| PLP GMM-128 | `f8b51f4d4c8b0bfa...` | `56f4d6ed50e3...` | 12.268 -> 13.956 (monotonic) | 6 of 4992 | 1 | `be5c4f0` |

## MFCC-TMP: TEO floor hits

Subband Teager sums at or below the log floor (1e-10) are floored before the
log. Counts over the whole cache build (HF split, both sides of the v2
manifest are drawn from these two caches):

| HF split | Rows | Floor hits | Values | Share |
|---|---|---|---|---|
| train | 4051 | 0 | 32055712 | 0.0000 % |
| test | 989 | 0 | 7873606 | 0.0000 % |

Every cached feature was finite (the build stops otherwise).

## Provenance

| Model | Parameter SHA-256 | Feature fingerprint | Non-matches | Commit of the run |
|---|---|---|---|---|
| MFCC GMM-64 | `a029dbfa60b9e632...` | `200751d44f47...` | 0 | `4e95d7e` |
| MFCC GMM-128 | `0f05ea082f748240...` | `200751d44f47...` | 1 | `4e95d7e` |
| PLP GMM-64 | `76308673789e6332...` | `81ab5664f83b...` | 0 | `baa3bc3` |
| PLP GMM-128 | `832fbb03a3929b08...` | `81ab5664f83b...` | 0 | `5145ced` |
| MFCC-TMP GMM-64 | `bebabe4220162631...` | `d4410351e5a9...` | 1 | `5145ced` |
| MFCC-TMP GMM-128 | `105fb5ff5093fbcb...` | `d4410351e5a9...` | 1 | `5145ced` |

PLP hashes and EM curves: `docs/gmm_notes.md`.

## Reproduce

```
pixi run train-gmm --kind plp --components 64 --split-manifest outputs/splits/textdisjoint_q20_v2.tsv
pixi run eval-timit --kind plp --gmm outputs/models/textdisjoint_q20_v2/plp_timit_matlab_gmm64.npz --split-manifest outputs/splits/textdisjoint_q20_v2.tsv --out outputs/eval/td2_plp_gmm64
```

and the same for `--components 128`, and for `--kind mfcc_tmp` (outputs
`td2_mfcc_tmp_gmm64`, `td2_mfcc_tmp_gmm128`). Outputs go to git-ignored
`outputs/`; only this summary is committed. The `timit_matlab` commands need
the cycle 8 retrain (G6): editing a feature source file changed the feature
fingerprint, so the older `timit_matlab` models are rejected by the model
guard until retrained.

The `htk_described` and `htk_described_4k` rows (`--profile htk_described`
or `htk_described_4k`; outputs `td2_htk_<kind>_gmm<N>`,
`td2_4k_<kind>_gmm<N>`):

```
pixi run train-gmm --kind mfcc --profile htk_described --components 64 --split-manifest outputs/splits/textdisjoint_q20_v2.tsv
pixi run eval-timit --kind mfcc --profile htk_described --gmm outputs/models/textdisjoint_q20_v2/mfcc_htk_described_gmm64.npz --split-manifest outputs/splits/textdisjoint_q20_v2.tsv --out outputs/eval/td2_htk_mfcc_gmm64
pixi run train-gmm --kind plp --profile htk_described_4k --components 128 --split-manifest outputs/splits/textdisjoint_q20_v2.tsv
pixi run eval-timit --kind plp --profile htk_described_4k --gmm outputs/models/textdisjoint_q20_v2/plp_htk_described_4k_gmm128.npz --split-manifest outputs/splits/textdisjoint_q20_v2.tsv --out outputs/eval/td2_4k_plp_gmm128
```

and the same for the other kind and size. Runs refuse a dirty tree unless
`--allow-dirty` is passed.

## Stage 4: GMM-VTLN

Code: `ml/vtln.py`, `ml/vtln_train.py`, `data/warped_cache.py`. Nothing here
is scored yet; this section holds the assumptions, declared before any
Stage 4 number.

### Assumptions (listed so a result cannot be re-read against them)

- **Tie-break:** a warp tie goes to the warp closest to 1.0, then the
  smaller one.
- **No Jacobian or filter-area correction** is applied for the warp.
- **Upper anchor:** the MATLAB one: the warp maps the band edge (`high_hz`)
  to itself.
- **Label map:** the thesis label is the mirror of ours, `alpha_thesis = 2 -
  alpha_ours`, applied in `ml/vtln.py` for reporting only; cache file names,
  the filterbank and the models keep our label. It rests on the author's
  answer D3 (c) (alpha > 1 is the male side; HTK `WARPFREQ`). The thesis's
  own `M_alpha(f)` (`Unsupervised.tex` 549) moves filter centres *up* for
  alpha > 1, as our code does, so the code alone does not support a mirror.
- **Fresh LBG** (plus EM) in every iteration: the thesis says "build" for
  lambda_r; a warm start is the alternative.
- **Query alpha-hat** is estimated on the query clip itself
  (`Representation.tex` line 104), not inherited from the source utterance.
- N_iter = 5 (`Representation.tex` line 229), warps 0.88 to 1.12 in steps of
  0.02, 13 values, `k < N_iter` (plan section 5).

### F0 against alpha-hat check (declared)

**Declared before it runs** (cycle 8, W1, Handoff_feedback Q4). It gives no
retrieval score; it asks whether the warp factors track the speaker.

- **Data:** a fresh N_iter = 1 run of `train-vtln` on MFCC `htk_described`
  GMM-64 (split v2, the warp caches reused). The alpha-hat are those of
  **iteration 0 under lambda_init**, the plain GMM, which has a known bump at
  1.00. This is stated now so the check is not reinterpreted after the
  result.
- **F0:** median F0 over the voiced frames of every train-side utterance,
  from a small autocorrelation estimator (50 to 400 Hz, `audio/pitch.py`).
- **Expectation (D3 c):** under the thesis label (alpha > 1 is the male
  side), median F0 correlates **negatively** with alpha_thesis, which is the
  same as a positive correlation with alpha_ours (Spearman).
- **Pass rule:** rho(F0, alpha_thesis) <= -0.2, equivalently rho(F0,
  alpha_ours) >= +0.2. The report prints both, so a label-mapping bug shows
  as a sign mismatch. **The -0.2 magnitude is the operative gate.** A 95 %
  bootstrap interval over utterances is reported, but it is anti-conservative
  (no speaker IDs; about 8 utterances per speaker are treated as
  independent).
- **Otherwise:** |rho| < 0.2, or an interval that includes 0, means alpha-hat
  does not track the speaker: STOP before W2. A clear positive rho(F0,
  alpha_thesis) contradicts D3 (c): STOP and report.
- **Also reported:** mean F0 per thesis-label warp; mean F0 of the edge
  groups; the share of utterances with median F0 below 165 Hz (a rough male
  proxy) on each side of 1.0.

### F0 against alpha-hat check (result)

Run as declared: `train-vtln` N_iter = 1, MFCC `htk_described` GMM-64, split
v2, from commit `0dd137b` on a clean tree (`git_dirty: false`); alpha-hat from
iteration 0 under lambda_init. Median F0 (50 to 400 Hz autocorrelation,
`audio/pitch.py`) for all 3696 of 3696 train-side utterances.

| | Spearman rho with median F0 | 95 % interval (bootstrap over utterances) |
|---|---|---|
| alpha_thesis (= 2 - alpha_ours) | -0.637 | -0.659 to -0.615 |
| alpha_ours | +0.637 | (the sign-flipped value) |

**The declared rule is met:** rho(F0, alpha_thesis) = -0.637
<= -0.2, and rho(F0, alpha_ours) = +0.637 >= +0.2; the two
signs agree, so there is no sign mismatch from the label map. The interval
is anti-conservative (no speaker IDs); the operative gate is the magnitude.
The result agrees with D3 (c) (alpha_thesis > 1 on the male, low-F0 side) and
says alpha-hat tracks the speaker in this respect. It says nothing about
retrieval.

| alpha_thesis | Mean median-F0 (Hz) | Utterances |
|---|---|---|
| 0.88 | 230.7 | 71 |
| 0.90 | 210.5 | 227 |
| 0.92 | 205.0 | 282 |
| 0.94 | 194.8 | 220 |
| 0.96 | 152.3 | 429 |
| 0.98 | 127.1 | 619 |
| 1.00 | 129.7 | 765 |
| 1.02 | 130.0 | 110 |
| 1.04 | 114.6 | 253 |
| 1.06 | 111.3 | 74 |
| 1.08 | 115.0 | 209 |
| 1.10 | 115.5 | 57 |
| 1.12 | 115.0 | 380 |

Edge groups: mean F0 230.7 Hz at thesis 0.88 (71 utterances) against
115.0 Hz at thesis 1.12 (380 utterances). Share of utterances with
median F0 below 165 Hz: 0.474 for alpha_thesis < 1
(1848), 0.865 at 1.00
(765), 0.976 for alpha_thesis > 1
(1083). The 1.00 group is a bump of lambda_init (765
utterances), as the declaration said.
