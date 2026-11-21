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

**User decision D6 (2026-11-18): the reference is the normalised profile
`htk_described_4k_pn`** (`htk_described_4k` with mean subtraction and
scaling to +-1, the author's statement of the thesis pipeline); the
`htk_described_4k` rows are the un-normalised earlier reference.

**User decision D5 (2026-11-17): 0-4000 Hz only.** `htk_described_4k` is the
reference for MFCC and PLP in Stage 4; the 0-3400 Hz rows (run 1 and the H2
rows) are an earlier reference. Results are at the end of this section.

Code: `ml/vtln.py`, `ml/vtln_train.py`, `data/warped_cache.py`. The
assumptions below were declared before any Stage 4 number.

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
says alpha-hat is negatively related to utterance F0 in this respect. It says
nothing about retrieval. Two notes: the check ran at iteration 0 under lambda_init on the
0-3400 Hz profile, not on the D5 reference; and a large rho can come from
the two F0 groups alone, so it does not show that alpha-hat tracks anything
within a group.

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

### Stage 4 runs (declared)

**Declared before any Stage 4 run** (cycle 8, W3, user decision D3).

- **Runs (5, GMM-64, split v2, N_iter = 5, one at a time, clean tree):**
  MFCC `htk_described`; MFCC `htk_described_4k`; PLP `htk_described`; PLP
  `htk_described_4k`; MFCC-TMP `timit_matlab`. Each: the 26 warp caches
  (13 warps, two HF splits), `train-vtln` from the plain GMM-64 of that
  feature and profile (fresh LBG per iteration), then `eval-timit --vtln`
  (LC2, clip query features, A1 scorer, keyword-cluster bootstrap with 10000
  resamples, seed 0). Records: alpha-hat histograms, edge shares, LL per
  iteration, `ll_decreased`, hashes, runtime, peak memory.
- **Targets** (`Tab:TIMITVTLNPerformance1`, p@N / MAP, no VTLN to VTLN): MFCC
  34.91 / 36.71 to 36.26 / 39.62; PLP 35.50 / 37.58 to 37.48 / 39.95;
  MFCC-TMP 40.03 / 41.50 to 42.88 / 45.52. The thesis gains are +1.35 /
  +2.91 (MFCC), +1.98 / +2.37 (PLP) and +2.85 / +4.02 (MFCC-TMP).
- **Comparison:** paired VTLN minus no-VTLN on the same queries (the plain
  GMM-64 row of the same feature and profile), keyword-cluster bootstrap.
- **What an interval that includes 0 means:** our half-widths are about 2 to
  3 points, so an interval that includes 0 is a likely outcome. Then the
  doc says "the direction matches / does not match the thesis; the interval
  does not establish a gain", and claims nothing more. "In the thesis's
  direction" is said only where the interval excludes 0 on the thesis side.
- **STOP rule:** if any iteration sets `ll_decreased`, that run is finished,
  reported, and no further run starts (that is the trigger for a warm-start
  variant).
- Nothing is tuned. No band is chosen; the 0-3400 Hz profile stays the
  reference. MFCC-TMP minus MFCC under VTLN is reported against both MFCC
  bands.

### Stage 4 run 1: MFCC `htk_described` (0-3400 Hz), earlier reference, stopped on `ll_decreased`

The declared STOP rule fired: iterations 2 and 4 set `ll_decreased`. This run
was finished and is reported; **no further Stage 4 run was started.** Run
from commit `cea4673` (clean tree, `git_dirty: false`), train-vtln
644 s, peak memory 930 MB, eval 338 s.

| Iteration | LL of lambda_init on X^alpha_hat | LL of new model on X^alpha_hat | ll_decreased | Share whose warp changed | Edge shares thesis 0.88 / 1.12 | Model hash |
|---|---|---|---|---|---|---|
| 0 | -116.4544 | -116.3199 | no | 0.793 | 0.019 / 0.103 | `455a873913f7...` |
| 1 | -116.2789 | -116.2680 | no | 0.394 | 0.044 / 0.142 | `70c1a8d326c4...` |
| 2 | -116.2589 | -116.2715 | **yes** | 0.226 | 0.060 / 0.145 | `5cdd9adcc79e...` |
| 3 | -116.2688 | -116.2452 | no | 0.122 | 0.070 / 0.140 | `a1b5a5202cbb...` |
| 4 | -116.2416 | -116.2677 | **yes** | 0.152 | 0.072 / 0.136 | `1bf1a1570ddb...` |

The decreases are small (0.013 and 0.026 per frame, against a spread of
about 0.1 between iterations). Each iteration trains a fresh LBG + EM model
(`fresh_lbg_each_iteration`), so a new initialisation can end slightly below
the previous model on the same data; this was the trigger for a warm-start variant, which
user decision D4 declined. After iteration 2 the new model's LL plateaus,
and its changes (up to 0.05 per frame) are of the same size as the
fresh-LBG initialisation noise. The reading is the Reviewer's.

Final alpha-hat histogram of the training utterances (thesis label):

| 1.12 | 1.10 | 1.08 | 1.06 | 1.04 | 1.02 | 1.00 | 0.98 | 0.96 | 0.94 | 0.92 | 0.90 | 0.88 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 501 | 47 | 169 | 66 | 231 | 79 | 611 | 546 | 343 | 150 | 242 | 445 | 266 |

The pile-up at the 1.12 edge (501 of 3696) and at 1.00 persists
after 5 iterations.

| Row | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Non-matches |
|---|---|---|---|---|---|---|
| MFCC `htk_described` GMM-64, no VTLN | 34.58 (25.6-44.1) | 35.73 (26.4-45.8) | 32.51 (24.8-40.7) | 33.50 (25.0-42.3) | 145 | 1 |
| MFCC `htk_described` GMM-64, GMM-VTLN (N_iter 5) | 41.65 (31.9-51.4) | 45.21 (34.3-56.2) | 37.90 (28.6-47.6) | 41.18 (30.9-52.0) | 145 | 1 |

Thesis (`Tab:TIMITVTLNPerformance1`, MFCC GMM-64): 34.91 / 36.71 without VTLN,
36.26 / 39.62 with. Paired VTLN minus no-VTLN (same queries; 95 %
keyword-cluster bootstrap):

| Average | p@N diff | MAP diff |
|---|---|---|
| instance | +7.07 (+3.8 to +10.4) | +9.47 (+5.5 to +13.0) |
| keyword | +5.38 (+1.7 to +9.1) | +7.68 (+3.8 to +11.7) |

Test documents' alpha-hat edge shares (thesis 0.88 / 1.12): 0.068 / 0.133;
query clips: 0.069 / 0.269; **0.60 of the queries**
get an alpha-hat different from their source utterance's final train
alpha-hat. Query features were extracted from the clips at all 13 warps
(`query_features: "clip"`).
### Stage 4 runs 2 to 5: results

**User decision D5 (2026-11-17): only the 0-4000 Hz band is kept; user
decision D6 (2026-11-18): the reference is the normalised profile
`htk_described_4k_pn`** (see "Normalised HTK reference (D6)" below). The
`htk_described_4k` rows here are therefore the **un-normalised, earlier
reference**; their numbers do not change. PLP `htk_described` (0-3400 Hz)
VTLN was not run. Run 1 (MFCC 0-3400 Hz, above) and the H2 0-3400 Hz rows
stay as a labelled earlier reference. **User decision D4 (2026-11-17):**
`ll_decreased` is recorded for runs 2 to 5 and does not stop the chain;
fresh LBG every iteration, no warm start. So four runs were made, not five:
MFCC 0-3400 Hz (run 1), MFCC 0-4000 Hz, PLP 0-4000 Hz and MFCC-TMP. Runs 2
and 3 ran from `0f899b3`, MFCC-TMP from `57acbc8` after the first attempt
was killed by a machine shutdown (warp caches from the killed attempt were
reused only where their fingerprint matched; the rest were built, which is
why its train-vtln time is much longer); `0f899b3` and `57acbc8` differ in
`docs/plan.md` only. All runs: clean tree, GMM-64, split v2, N_iter 5, 145
queries, 1344 documents, clip query features, A1 scorer, 10000 bootstrap
resamples, seed 0. Nothing was tuned and no band was chosen by its score.

| Row | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Non-matches |
|---|---|---|---|---|---|---|
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)), thesis, no VTLN | 34.91 | 36.71 | not stated | not stated | 145 | n/a |
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)), thesis, VTLN | 36.26 | 39.62 | not stated | not stated | 145 | n/a |
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)), GMM-64, no VTLN | 37.48 (28.0-47.6) | 40.50 (30.1-52.1) | 35.07 (26.6-43.9) | 37.84 (28.4-47.6) | 145 | 3 |
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)), GMM-64, GMM-VTLN | 48.17 (37.3-59.9) | 50.58 (39.0-62.9) | 44.95 (34.5-55.9) | 46.88 (35.7-58.5) | 145 | 1 |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)), thesis, no VTLN | 35.50 | 37.58 | not stated | not stated | 145 | n/a |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)), thesis, VTLN | 37.48 | 39.95 | not stated | not stated | 145 | n/a |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)), GMM-64, no VTLN | 38.59 (29.1-48.5) | 39.75 (29.3-50.9) | 35.82 (27.1-44.8) | 36.81 (27.5-46.5) | 145 | 0 |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)), GMM-64, GMM-VTLN | 45.37 (35.5-56.2) | 48.99 (38.2-60.9) | 43.29 (33.6-53.5) | 46.55 (36.0-57.7) | 145 | 0 |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz), thesis, no VTLN | 40.03 | 41.50 | not stated | not stated | 145 | n/a |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz), thesis, VTLN | 42.88 | 45.52 | not stated | not stated | 145 | n/a |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz), GMM-64, no VTLN | 39.17 (29.6-48.9) | 41.15 (30.7-52.1) | 35.44 (26.4-44.5) | 37.65 (28.3-47.3) | 145 | 1 |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz), GMM-64, GMM-VTLN | 44.07 (33.7-55.1) | 47.37 (36.0-59.2) | 41.43 (31.1-51.8) | 44.55 (33.5-55.7) | 145 | 2 |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1), thesis, no VTLN | 34.91 | 36.71 | not stated | not stated | 145 | n/a |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1), thesis, VTLN | 36.26 | 39.62 | not stated | not stated | 145 | n/a |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1), GMM-64, no VTLN | 34.58 (25.6-44.1) | 35.73 (26.4-45.8) | 32.51 (24.8-40.7) | 33.50 (25.0-42.3) | 145 | 1 |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1), GMM-64, GMM-VTLN | 41.65 (31.9-51.4) | 45.21 (34.3-56.2) | 37.90 (28.6-47.6) | 41.18 (30.9-52.0) | 145 | 1 |

Fact: our no-VTLN MFCC 0-4000 Hz row (37.48 / 40.50) already reaches the
thesis's **VTLN** MFCC row (36.26 / 39.62). So the gap to the thesis is
partly in the baseline and partly in the gain.

### Gap to the thesis (descriptive, no cause attached)

Instance average, ours minus thesis, p@N / MAP. The last column is the
thesis's own gain, for comparison.

| Run | no VTLN | VTLN | Thesis gain (VTLN minus no VTLN) |
|---|---|---|---|
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | +2.57 / +3.79 | +11.91 / +10.96 | +1.35 / +2.91 |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | +3.09 / +2.17 | +7.89 / +9.04 | +1.98 / +2.37 |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz) | -0.86 / -0.35 | +1.19 / +1.85 | +2.85 / +4.02 |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1) | -0.33 / -0.98 | +5.39 / +5.59 | +1.35 / +2.91 |

### Paired VTLN minus no-VTLN (same queries, keyword-cluster bootstrap)

The last column puts the thesis's gain (p@N / MAP, from the table above)
against **our instance-average paired interval**: "below" means the thesis
gain is below the interval's lower end, "inside" within it, "above" over
its upper end. It is descriptive, not a test: the thesis gain has an
unknown uncertainty of its own, and the thesis does not say which average
it used.

| Run | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) | Thesis gain against our instance interval (p@N / MAP) |
|---|---|---|---|---|---|
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | instance | +10.69 (+6.8 to +14.3) | +10.08 (+6.2 to +13.9) | yes / yes | below / below |
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | keyword | +9.88 (+5.1 to +15.1) | +9.04 (+3.5 to +14.8) | yes / yes |  |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | instance | +6.78 (+3.4 to +10.2) | +9.24 (+6.3 to +12.4) | yes / yes | below / below |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | keyword | +7.46 (+3.4 to +12.4) | +9.74 (+5.7 to +14.7) | yes / yes |  |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz) | instance | +4.90 (+1.4 to +8.6) | +6.22 (+3.4 to +9.1) | yes / yes | inside / inside |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz) | keyword | +5.99 (+2.3 to +10.1) | +6.90 (+3.6 to +10.4) | yes / yes |  |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1) | instance | +7.07 (+3.8 to +10.4) | +9.47 (+5.5 to +13.0) | yes / yes | below / below |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1) | keyword | +5.38 (+1.7 to +9.1) | +7.68 (+3.8 to +11.7) | yes / yes |  |

The thesis gains are +1.35 / +2.91 (MFCC), +1.98 / +2.37 (PLP) and
+2.85 / +4.02 (MFCC-TMP). Our paired gains are above these in the MFCC and
PLP runs (MFCC-TMP is closest); this is stated as a fact and no cause is
claimed. The no-VTLN rows also differ by band, so the VTLN rows are not a
like-for-like comparison with the 0-3400 Hz run.

### MFCC-TMP minus MFCC under VTLN, and PLP minus MFCC

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) |
|---|---|---|---|---|
| MFCC-TMP minus MFCC 0-4000 Hz (un-normalised), both VTLN | instance | -4.09 (-7.1 to -1.0) | -3.22 (-6.4 to +0.2) | yes / no |
| MFCC-TMP minus MFCC 0-4000 Hz (un-normalised), both VTLN | keyword | -3.52 (-6.9 to -0.3) | -2.33 (-6.4 to +1.8) | yes / no |
| MFCC-TMP minus MFCC 0-3400 Hz (earlier ref.), both VTLN | instance | +2.42 (-1.1 to +6.0) | +2.16 (-2.1 to +6.6) | no / no |
| MFCC-TMP minus MFCC 0-3400 Hz (earlier ref.), both VTLN | keyword | +3.53 (+0.2 to +7.0) | +3.38 (-0.2 to +7.1) | yes / no |
| PLP minus MFCC, both 0-4000 Hz (un-normalised), both VTLN | instance | -2.80 (-5.5 to +0.1) | -1.59 (-4.0 to +1.2) | no / no |
| PLP minus MFCC, both 0-4000 Hz (un-normalised), both VTLN | keyword | -1.66 (-4.5 to +1.1) | -0.33 (-2.8 to +2.3) | no / no |
| MFCC-TMP minus MFCC 0-4000 Hz (un-normalised), both no VTLN | instance | +1.70 (-0.6 to +3.9) | +0.64 (-1.8 to +3.0) | no / no |
| MFCC-TMP minus MFCC 0-4000 Hz (un-normalised), both no VTLN | keyword | +0.37 (-1.9 to +2.6) | -0.19 (-2.5 to +2.1) | no / no |

**The thesis's MFCC-TMP advantage is not reproduced under VTLN** against the D5
reference: the thesis's +6.62 / +5.90 lie above our intervals, and p@N is below
0 with an interval that excludes 0 (MAP includes 0). Without VTLN both thesis
advantages (+5.12 / +4.79) lie above our un-normalised intervals (+1.70 / +0.64,
both include 0). The 0-3400 Hz comparison is an earlier
reference only and is not the band question, which D5 settled. The two
features differ in four ways at once, so no front-end claim is possible:
tool lineage (MATLAB-described against HTK-described), filter count (26
against 40), level handling (peak-normalised against none in these
un-normalised rows) and VTLN response. By the author's statement the thesis
had the first two differences too; its level handling was settled by D6.
**Nothing is claimed about Teager energy.**

### LL per iteration and `ll_decreased` (fresh LBG each iteration, D4)

After iteration 2 the new model's LL plateaus, and its changes (up to 0.05
per frame) are of the same size as the fresh-LBG initialisation noise.

**MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6))**

| Iteration | LL of lambda_init on X^alpha_hat | LL of new model | ll_decreased | Share changed | Edge share 0.88 | Edge share 1.12 |
|---|---|---|---|---|---|---|
| 0 | -116.3560 | -116.2613 | no | 0.738 | 0.012 | 0.042 |
| 1 | -116.2149 | -116.2017 | no | 0.495 | 0.040 | 0.068 |
| 2 | -116.1846 | -116.1366 | no | 0.326 | 0.055 | 0.095 |
| 3 | -116.1269 | -116.1762 | **yes** | 0.257 | 0.056 | 0.112 |
| 4 | -116.1705 | -116.1512 | no | 0.197 | 0.054 | 0.129 |

**PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6))**

| Iteration | LL of lambda_init on X^alpha_hat | LL of new model | ll_decreased | Share changed | Edge share 0.88 | Edge share 1.12 |
|---|---|---|---|---|---|---|
| 0 | 13.5453 | 13.7348 | no | 0.871 | 0.071 | 0.078 |
| 1 | 13.8230 | 13.8474 | no | 0.542 | 0.106 | 0.129 |
| 2 | 13.8606 | 13.8714 | no | 0.268 | 0.103 | 0.162 |
| 3 | 13.8748 | 13.8353 | **yes** | 0.146 | 0.096 | 0.188 |
| 4 | 13.8375 | 13.8749 | no | 0.110 | 0.090 | 0.200 |

**MFCC-TMP (`timit_matlab`, 0-4000 Hz)**

| Iteration | LL of lambda_init on X^alpha_hat | LL of new model | ll_decreased | Share changed | Edge share 0.88 | Edge share 1.12 |
|---|---|---|---|---|---|---|
| 0 | -32.4569 | -32.3155 | no | 0.889 | 0.048 | 0.046 |
| 1 | -32.2463 | -32.2243 | no | 0.505 | 0.091 | 0.081 |
| 2 | -32.2111 | -32.2124 | **yes** | 0.250 | 0.094 | 0.107 |
| 3 | -32.2088 | -32.2143 | **yes** | 0.149 | 0.091 | 0.129 |
| 4 | -32.2099 | -32.2064 | no | 0.154 | 0.085 | 0.146 |

**MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1)**

| Iteration | LL of lambda_init on X^alpha_hat | LL of new model | ll_decreased | Share changed | Edge share 0.88 | Edge share 1.12 |
|---|---|---|---|---|---|---|
| 0 | -116.4544 | -116.3199 | no | 0.793 | 0.019 | 0.103 |
| 1 | -116.2789 | -116.2680 | no | 0.394 | 0.044 | 0.142 |
| 2 | -116.2589 | -116.2715 | **yes** | 0.226 | 0.060 | 0.145 |
| 3 | -116.2688 | -116.2452 | no | 0.122 | 0.070 | 0.140 |
| 4 | -116.2416 | -116.2677 | **yes** | 0.152 | 0.072 | 0.136 |

### Warp statistics and provenance

Mean alpha-hat in the thesis label per iteration over the train utterances,
with the share above 1.00 in brackets (iterations 0 to 4):

| Run | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | 1.002 (0.382) | 1.006 (0.479) | 1.011 (0.536) | 1.015 (0.571) | 1.020 (0.594) |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | 1.014 (0.551) | 1.023 (0.637) | 1.028 (0.656) | 1.030 (0.661) | 1.032 (0.665) |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz) | 1.008 (0.518) | 1.017 (0.612) | 1.023 (0.643) | 1.027 (0.658) | 1.030 (0.664) |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1) | 0.997 (0.293) | 0.995 (0.314) | 0.993 (0.310) | 0.992 (0.307) | 0.990 (0.296) |

The 0-4000 Hz runs drift towards the male side (above 1.00) at every
iteration. That is consistent with TIMIT's roughly 70 % male speakers, and
also with the drift of unanchored iterative ML warping, where each new model
is trained on already-warped data; the table alone does not tell which.

Final train alpha-hat histogram (thesis label, counts of 3696 utterances; the
0-3400 Hz row alternates, e.g. 47 at 1.10 and 66 at 1.06 against 169 and 231
at their neighbours, an earlier-reference observation):

| Run | 1.12 | 1.10 | 1.08 | 1.06 | 1.04 | 1.02 | 1.00 | 0.98 | 0.96 | 0.94 | 0.92 | 0.90 | 0.88 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | 478 | 216 | 172 | 571 | 448 | 309 | 385 | 110 | 216 | 245 | 255 | 93 | 198 |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | 738 | 567 | 238 | 538 | 262 | 113 | 154 | 38 | 179 | 159 | 237 | 139 | 334 |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz) | 539 | 517 | 547 | 395 | 221 | 234 | 141 | 102 | 136 | 203 | 202 | 143 | 316 |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1) | 501 | 47 | 169 | 66 | 231 | 79 | 611 | 546 | 343 | 150 | 242 | 445 | 266 |

Convergence differs from the thesis's "converges" (`Representation.tex`
line 194): 11 to 20 % of the utterances still change warp at iteration 4. A
likely reason is the model noise of the fresh LBG between iterations, which
is of the same order as the remaining LL gain; this is a likely reason, not
a proven one.

| Run | VTLN model hash | ll_decreased at iteration | selection_step_ok | Train edge shares 0.88 / 1.12 (final) | Share changed (final) | Test-document edge shares 0.88 / 1.12 | Query edge shares 0.88 / 1.12 | Queries with alpha-hat different from source | train-vtln time / peak memory | Start commit | Dirty |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | `1c0742a0603b...` | 3 | not recorded | 0.054 / 0.129 | 0.197 | 0.051 / 0.153 | 0.055 / 0.186 | 0.72 | 989 s / 1246 MB | `0f899b3` | False |
| PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference (D6)) | `03f7143df3fd...` | 3 | not recorded | 0.090 / 0.200 | 0.110 | 0.078 / 0.225 | 0.055 / 0.283 | 0.59 | 978 s / 1280 MB | `0f899b3` | False |
| MFCC-TMP (`timit_matlab`, 0-4000 Hz) | `390547cd8d45...` | 2, 3 | not recorded | 0.085 / 0.146 | 0.154 | 0.076 / 0.172 | 0.048 / 0.269 | 0.72 | 11065 s / 1138 MB | `57acbc8` | False |
| MFCC 0-3400 Hz (`htk_described`, earlier reference, run 1) | `1bf1a1570ddb...` | 2, 4 | not recorded | 0.072 / 0.136 | 0.152 | 0.068 / 0.133 | 0.069 / 0.269 | 0.60 | 644 s / 930 MB | `cea4673` | False |

### MFCC level observation (scratch-derived, MFCC only, not a cause)

Derived in review from scratch runs, not from a declared experiment. A
waveform gain g adds `2 ln g` to each of the 40 log channel outputs; the
orthonormal DCT maps that to c0 alone: `c0 += sqrt(40) * 2 ln g` (8.77 for
g = 2). For PLP the level enters through the prediction error power and an
auditory spectrum of power^0.33, about `0.66 ln g` (0.46 for g = 2), roughly
19 times smaller. Test: 100 random train utterances (seed 1), waveform
scaled by 0.5, 1 and 2, alpha-hat re-estimated under each run's final
lambda_r. A pure speaker estimate would not move.

| Model | alpha-hat changed, x2 against x1 | alpha-hat changed, x0.5 against x1 | 1.12-edge count at x0.5 / x1 / x2 | Mean alpha_thesis shift, x2 / x0.5 |
|---|---|---|---|---|
| MFCC 0-3400 Hz (run 1) | 22 % | 28 % | 6 / 12 / 19 | +0.008 / -0.011 |
| MFCC 0-4000 Hz (un-normalised, earlier reference) | 22 % | 39 % | 10 / 17 / 24 | +0.008 / -0.012 |
| PLP 0-4000 Hz (un-normalised, earlier reference) | 8 % | 9 % | 22 / 24 / 26 | +0.002 / -0.002 |

For MFCC the alpha-hat changes come from the c0 shift alone; for MFCC-TMP
the features are peak-normalised, so alpha-hat is exactly invariant to
gain. This says that, for MFCC, alpha-hat carries a level component that the
no-VTLN row does not have; it does not say that the level component causes
the gain. **Author fact (D6 a, 2026-11-18): the thesis's HTK pipeline
subtracted the mean and scaled the waveform to +-1**, so the un-normalised
rows differ from the thesis on this point.

### Score-free VTLN checks (declared)

**Declared before any S1 number** (cycle 9, S1). No retrieval score is
computed. Each part is reported in full and nothing is chosen from it.
Clean tree; every summary records `git_commit_start` and `git_dirty`.

- **(a) c0-marginalised alpha-hat.** Under each final lambda_r (MFCC
  0-4000 Hz, MFCC 0-3400 Hz, PLP 0-4000 Hz, MFCC-TMP) the train alpha-hat is
  re-estimated twice on the 3696 train utterances, with the same 13 warps and
  tie-break: with all 39 dimensions, and with the static c0 dimension
  (column 0) dropped from the diagonal GMM (means, variances and that
  dimension of the log-likelihood; the weights stay). Reported: the share of
  utterances whose alpha-hat differs between the two, the new histogram and
  the new mean alpha_thesis. The baseline is alpha-hat under lambda_r itself,
  not the iteration-4 alpha-hat (which was chosen under the previous model).
- **(b) F0 against final alpha-hat.** Per-utterance median F0
  (`audio/pitch.py`, 50 to 400 Hz) is recomputed for the 3696 train
  utterances and saved under `outputs/` keyed by `(hf_split, row)` (not
  committed). For the three D5 runs (MFCC 0-4000 Hz, PLP 0-4000 Hz,
  MFCC-TMP), with the iteration-4 alpha-hat in the thesis label: Spearman rho
  with F0 overall, and within F0 < 165 Hz and >= 165 Hz, each with a 95 %
  percentile bootstrap interval over utterances (10000 resamples, seed 0;
  anti-conservative, as there are no speaker IDs); and the partial
  correlation of alpha-hat with the utterance mean c0 at alpha = 1, controlling
  for F0 (Spearman partial: Pearson on ranks of the residuals of the ranks on
  the ranks of F0). Utterances without F0 are left out of every statistic and
  counted. Descriptive: the D3 (c) gate already passed.
- **(c) Order approximation (K4).** Over all 5040 train and test utterances
  of split v2, `r = max|x - m| / max|x|` of the raw waveform (`m` its mean)
  and the implied MFCC c0 offset `sqrt(40) * 2 * |ln r|`. **Gate:** if the
  99th percentile of the offset is <= 0.1 the approximation is negligible and
  S3 goes ahead; otherwise **STOP** and report (matching the author's order
  needs a feature source edit, which is a user decision). The distribution
  (min, median, 99th percentile, max) is reported either way.
- Nothing is tuned. Code: `ml/vtln_checks.py` and `eval/s1_checks.py`; outputs
  go to `outputs/s1/`.

### Score-free VTLN checks

Run as declared above, no retrieval score. Part (c) ran from `fa01e4d`;
parts (a) and (b) from `cc086de` (the first attempt failed on PLP, which has
no `include_c0` switch although its c0 is column 0; `cc086de` fixed that
guard). All clean trees (`git_dirty: false`). Run time: (a) 337 s,
(b) 148 s, (c) 14 s. Outputs are in
git-ignored `outputs/s1/`, including per-utterance F0 (`f0_train.tsv`).

#### (c) Order approximation: gate met

`r = max|x - m| / max|x|` over all 5040 train and test
utterances of split v2:

| Quantity | min | median | 99th percentile | max |
|---|---|---|---|---|
| r | 0.999650 | 0.999999 | 1.000205 | 1.000428 |
| implied MFCC c0 offset | 2.49e-07 | 6.14e-04 | 0.0030 | 0.0054 |

**The declared gate is met:** the 99th percentile of the offset is
0.0030, at most 0.1, so the order approximation (peak-normalise
first, remove the mean afterwards) is negligible and S3 goes ahead. For
scale, the c0 spread across utterances is about 5.3 and a gain of 2 shifts
c0 by 8.77.

#### (a) c0-marginalised alpha-hat (train utterances, 3696)

Under each final lambda_r, alpha-hat with all 39 dimensions against alpha-hat
with the static c0 dimension dropped (same warps, same tie-break):

| Run | Share whose alpha-hat changes | Mean alpha_thesis, all dims | Mean alpha_thesis, c0 dropped | Edge shares 0.88 / 1.12, all dims | Edge shares 0.88 / 1.12, c0 dropped |
|---|---|---|---|---|---|
| MFCC 0-4000 Hz (un-normalised, earlier reference) | 0.136 | 1.0221 | 1.0219 | 0.051 / 0.141 | 0.054 / 0.151 |
| MFCC 0-3400 Hz (run 1, earlier reference) | 0.124 | 0.9889 | 0.9888 | 0.078 / 0.133 | 0.078 / 0.141 |
| PLP 0-4000 Hz (un-normalised, earlier reference) | 0.064 | 1.0339 | 1.0338 | 0.087 / 0.216 | 0.089 / 0.215 |
| MFCC-TMP (`timit_matlab`) | 0.138 | 1.0310 | 1.0307 | 0.082 / 0.152 | 0.091 / 0.162 |

Histograms (thesis label, counts):

| Run | 1.12 | 1.10 | 1.08 | 1.06 | 1.04 | 1.02 | 1.00 | 0.98 | 0.96 | 0.94 | 0.92 | 0.90 | 0.88 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MFCC 0-4000 Hz (un-normalised, earlier reference), all 39 dimensions | 521 | 236 | 185 | 586 | 426 | 303 | 336 | 105 | 221 | 247 | 246 | 94 | 190 |
| MFCC 0-4000 Hz (un-normalised, earlier reference), c0 dropped | 558 | 233 | 174 | 548 | 421 | 270 | 382 | 113 | 222 | 236 | 249 | 91 | 199 |
| MFCC 0-3400 Hz (run 1, earlier reference), all 39 dimensions | 491 | 38 | 166 | 66 | 225 | 70 | 622 | 545 | 367 | 135 | 252 | 432 | 287 |
| MFCC 0-3400 Hz (run 1, earlier reference), c0 dropped | 520 | 39 | 164 | 60 | 202 | 67 | 588 | 542 | 392 | 137 | 267 | 428 | 290 |
| PLP 0-4000 Hz (un-normalised, earlier reference), all 39 dimensions | 797 | 561 | 240 | 507 | 261 | 108 | 144 | 42 | 179 | 169 | 234 | 134 | 320 |
| PLP 0-4000 Hz (un-normalised, earlier reference), c0 dropped | 793 | 558 | 246 | 514 | 253 | 110 | 142 | 46 | 183 | 166 | 229 | 126 | 330 |
| MFCC-TMP (`timit_matlab`), all 39 dimensions | 563 | 535 | 541 | 394 | 213 | 227 | 128 | 111 | 137 | 202 | 202 | 140 | 303 |
| MFCC-TMP (`timit_matlab`), c0 dropped | 597 | 547 | 516 | 374 | 208 | 225 | 130 | 92 | 134 | 195 | 201 | 142 | 335 |

Dropping static c0 changes alpha-hat for 12 to 14 % of the MFCC utterances
(12.4 to 13.8 % across the runs) and 6.4 % of the PLP utterances. The mean
alpha_thesis moves by less than 0.001 in every run, and the histograms keep
their shape. No null has been measured: it is not known whether dropping any
other static dimension would change a similar share, and that control is
declared in section N1. This is a description; it does not say what a level
normalisation would do to retrieval.

#### (b) F0 and c0 against the final alpha-hat

Spearman correlations, alpha-hat in the thesis label (iteration 4), 3696 train
utterances (none without F0 or c0); 95 % percentile bootstrap over utterances,
10000 resamples (anti-conservative: no speaker IDs). The two F0 groups hold
2595 (F0 < 165 Hz) and 1101 (>= 165 Hz) utterances. The partial correlation
is of alpha-hat with the utterance mean c0 at alpha = 1, controlling for F0.

| Run | rho(F0, alpha) all | within F0 < 165 Hz | within F0 >= 165 Hz | rho(c0, alpha) | partial rho(c0, alpha given F0) |
|---|---|---|---|---|---|
| MFCC 0-4000 Hz (un-normalised, earlier reference) | -0.697 (-0.716 to -0.677) | -0.235 (-0.272 to -0.198) | -0.441 (-0.490 to -0.388) | +0.252 (+0.223 to +0.281) | +0.235 (+0.205 to +0.266) |
| PLP 0-4000 Hz (un-normalised, earlier reference) | -0.688 (-0.707 to -0.667) | -0.181 (-0.220 to -0.143) | -0.422 (-0.472 to -0.369) | +0.160 (+0.129 to +0.191) | +0.206 (+0.174 to +0.237) |
| MFCC-TMP (`timit_matlab`) | -0.745 (-0.762 to -0.727) | -0.339 (-0.374 to -0.303) | -0.435 (-0.485 to -0.382) | +0.035 (+0.003 to +0.067) | +0.076 (+0.044 to +0.107) |

alpha-hat correlates negatively with utterance F0 overall and within each F0
group (< 165 Hz, >= 165 Hz) in every run; the within-group values are smaller
than the overall one. The partial correlation of alpha-hat with mean c0 given
F0 is small and positive in the three runs (MFCC 0.235, PLP 0.206, MFCC-TMP
0.076). PLP's value is close to MFCC's, although only MFCC's alpha-hat
responds to gain (cycle 8), so the partial correlation does not indicate the
level mechanism. The HF TIMIT copy has no speaker field and its rows are
shuffled, so the intervals are over utterances. All of this is descriptive;
the D3 (c) gate already passed.

### Gain split of the un-normalised rows (declared)

**Declared before any S2 number** (cycle 9, S2). The VTLN row changes two
things at once: the model (lambda_init to lambda_r) and the test-time
selection (alpha = 1 to alpha-hat per document and per query). This splits
them. Un-normalised, earlier-reference rows only: MFCC 0-4000 Hz and PLP
0-4000 Hz (`htk_described_4k`), GMM-64, split v2, existing models and warp
caches, no training.

| | alpha = 1 everywhere | alpha-hat per document and query |
|---|---|---|
| lambda_init (plain GMM-64) | existing no-VTLN row | **selection only** (`--vtln-cell selection_only`) |
| lambda_r (final VTLN model) | **model only** (`--vtln-cell model_only`) | existing VTLN row |

- **Fifth cell, `query_inherit`:** documents as in the VTLN row, and each
  query clip at its source utterance's final alpha-hat (`iter4_alphas.tsv`)
  instead of its own estimate.
- **Evaluations:** 6 (three cells for each of the two features), same
  protocol as W3 (LC2, A1 scorer, clip query features, 145 queries,
  keyword-cluster bootstrap with 10000 resamples, seed 0). The two existing
  rows of each feature (no VTLN, VTLN) are **re-evaluated** once more into
  separate directories, so that they also carry the mean posteriorgram
  entropy (K3); their scores must reproduce the W3 rows and any difference is
  reported.
- **Comparisons:** each cell minus the no-VTLN row on the same 145 queries,
  paired keyword-cluster bootstrap. Every cell is reported and nothing is
  chosen from them.
- **Reading rule:** the cells describe where the gain shows up. No mechanism
  is claimed, and the two halves need not add up to the total.

### Gain split of the un-normalised rows (result)

Run as declared (clean tree, commit `d4422af`). The "no VTLN" and "both"
rows are the W3 rows; their entropy comes from the re-evaluations below.

#### MFCC 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference)

| Cell | p@N, instance (95% CI) | MAP, instance (95% CI) | p@N, keyword (95% CI) | MAP, keyword (95% CI) | Mean entropy documents / queries (nats) | git commit | Dirty |
|---|---|---|---|---|---|---|---|
| no VTLN (existing row) | 37.48 (28.0-47.6) | 40.50 (30.1-52.1) | 35.07 (26.6-43.9) | 37.84 (28.4-47.6) | 0.4402 / 0.4470 | `be5c4f0` | not recorded |
| model only (lambda_r, alpha = 1) | 39.45 (28.9-50.8) | 41.92 (30.6-54.4) | 35.87 (26.5-45.6) | 38.74 (29.1-49.0) | 0.4404 / 0.4576 | `d4422af` | False |
| selection only (lambda_init, alpha-hat) | 41.25 (32.4-51.0) | 44.57 (34.1-56.0) | 38.84 (30.2-47.8) | 41.67 (31.8-51.9) | 0.4383 / 0.4392 | `d4422af` | False |
| both = VTLN row (existing) | 48.17 (37.3-59.9) | 50.58 (39.0-62.9) | 44.95 (34.5-55.9) | 46.88 (35.7-58.5) | 0.4235 / 0.4390 | `0f899b3` | False |
| query_inherit (lambda_r, documents alpha-hat, queries at the source alpha-hat) | 48.66 (37.9-59.9) | 51.35 (39.9-63.5) | 44.99 (34.1-56.1) | 47.71 (36.6-59.3) | 0.4235 / 0.4449 | `d4422af` | False |

| Cell minus no VTLN | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) |
|---|---|---|---|---|
| model only (lambda_r, alpha = 1) | instance | +1.98 (-1.1 to +4.5) | +1.42 (-0.9 to +3.7) | no / no |
| model only (lambda_r, alpha = 1) | keyword | +0.80 (-1.8 to +3.4) | +0.90 (-1.3 to +3.2) | no / no |
| selection only (lambda_init, alpha-hat) | instance | +3.77 (+0.4 to +7.2) | +4.07 (+0.7 to +7.5) | yes / yes |
| selection only (lambda_init, alpha-hat) | keyword | +3.77 (-0.2 to +8.0) | +3.83 (-0.4 to +8.3) | no / no |
| both = VTLN row (existing) | instance | +10.69 (+6.8 to +14.3) | +10.08 (+6.2 to +13.9) | yes / yes |
| both = VTLN row (existing) | keyword | +9.88 (+5.1 to +15.1) | +9.04 (+3.5 to +14.8) | yes / yes |
| query_inherit (lambda_r, documents alpha-hat, queries at the source alpha-hat) | instance | +11.18 (+7.7 to +14.4) | +10.84 (+7.3 to +14.2) | yes / yes |
| query_inherit (lambda_r, documents alpha-hat, queries at the source alpha-hat) | keyword | +9.92 (+5.0 to +15.3) | +9.87 (+5.0 to +15.2) | yes / yes |
`query_inherit` query edge shares (thesis 0.88 / 1.12): 0.041 / 0.110.

#### PLP 0-4000 Hz (`htk_described_4k`, un-normalised, earlier reference)

| Cell | p@N, instance (95% CI) | MAP, instance (95% CI) | p@N, keyword (95% CI) | MAP, keyword (95% CI) | Mean entropy documents / queries (nats) | git commit | Dirty |
|---|---|---|---|---|---|---|---|
| no VTLN (existing row) | 38.59 (29.1-48.5) | 39.75 (29.3-50.9) | 35.82 (27.1-44.8) | 36.81 (27.5-46.5) | 0.4361 / 0.4458 | `be5c4f0` | not recorded |
| model only (lambda_r, alpha = 1) | 37.06 (28.4-46.6) | 39.63 (29.2-51.2) | 35.44 (27.1-43.9) | 37.43 (28.1-47.0) | 0.4373 / 0.4385 | `d4422af` | False |
| selection only (lambda_init, alpha-hat) | 44.11 (34.0-55.0) | 46.65 (35.5-58.7) | 41.32 (31.6-51.1) | 43.39 (33.1-53.9) | 0.4341 / 0.4375 | `d4422af` | False |
| both = VTLN row (existing) | 45.37 (35.5-56.2) | 48.99 (38.2-60.9) | 43.29 (33.6-53.5) | 46.55 (36.0-57.7) | 0.4160 / 0.4131 | `0f899b3` | False |
| query_inherit (lambda_r, documents alpha-hat, queries at the source alpha-hat) | 47.35 (37.6-57.9) | 50.86 (40.4-62.2) | 44.95 (35.5-54.9) | 47.93 (37.5-58.9) | 0.4160 / 0.4126 | `d4422af` | False |

| Cell minus no VTLN | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) |
|---|---|---|---|---|
| model only (lambda_r, alpha = 1) | instance | -1.53 (-3.6 to +1.0) | -0.12 (-1.6 to +1.6) | no / no |
| model only (lambda_r, alpha = 1) | keyword | -0.38 (-3.1 to +2.5) | +0.62 (-1.2 to +2.5) | no / no |
| selection only (lambda_init, alpha-hat) | instance | +5.52 (+2.3 to +8.5) | +6.89 (+4.1 to +9.4) | yes / yes |
| selection only (lambda_init, alpha-hat) | keyword | +5.50 (+2.4 to +8.6) | +6.58 (+4.0 to +9.1) | yes / yes |
| both = VTLN row (existing) | instance | +6.78 (+3.4 to +10.2) | +9.24 (+6.3 to +12.4) | yes / yes |
| both = VTLN row (existing) | keyword | +7.46 (+3.4 to +12.4) | +9.74 (+5.7 to +14.7) | yes / yes |
| query_inherit (lambda_r, documents alpha-hat, queries at the source alpha-hat) | instance | +8.76 (+5.6 to +12.0) | +11.11 (+9.0 to +13.5) | yes / yes |
| query_inherit (lambda_r, documents alpha-hat, queries at the source alpha-hat) | keyword | +9.12 (+5.3 to +13.8) | +11.12 (+7.5 to +15.6) | yes / yes |
`query_inherit` query edge shares (thesis 0.88 / 1.12): 0.055 / 0.207.

Re-evaluation check (the existing rows evaluated once more, same models):

| Row | Scores and per-query rows against the W3 evaluation | Mean entropy documents (nats) | Mean entropy queries (nats) |
|---|---|---|---|
| MFCC 0-4000 Hz, no VTLN | identical | 0.4402 | 0.4470 |
| MFCC 0-4000 Hz, VTLN | identical | 0.4235 | 0.4390 |
| PLP 0-4000 Hz, no VTLN | identical | 0.4361 | 0.4458 |
| PLP 0-4000 Hz, VTLN | identical | 0.4160 | 0.4131 |

The cells describe where the gain shows up; no mechanism is claimed, and the
two halves need not add up to the total. Which cell carries the gain is read
from the paired intervals above, not from their sum.

What the tables show, as facts: in no cell does *model only* have an
interval that excludes 0 (MFCC +1.98 / +1.42, PLP -1.53 / -0.12 for p@N /
MAP, instance average). *Selection only* excludes 0 on the instance average
for both features and on the keyword average for PLP only (MFCC keyword
intervals include 0). The `query_inherit` cell is within about 0.5 to 2
points of the VTLN row (MFCC +0.49 / +0.77 above it, PLP +1.98 / +1.87),
Mean entropy of the documents is lower under VTLN (0.4235 against 0.4402
for MFCC, 0.4160 against 0.4361 for PLP). No mechanism is claimed.

**Post hoc paired comparisons (not declared; computed after the runs).**
`qbestd.eval.post_hoc` (commit `b4aeebb`) reads the finished `per_query.tsv`
files and applies `paired_keyword_bootstrap` (10000 resamples, seed 0). The
output is `outputs/posthoc/post_hoc.md` (git-ignored). Differences are B minus
A as labelled; "excludes 0" means the 95 % interval lies wholly on one side.

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) |
|---|---|---|---|---|
| MFCC un-normalised: VTLN minus selection only | instance | +6.92 (+3.76 to +10.19) | +6.01 (+3.20 to +8.86) | yes / yes |
| MFCC un-normalised: VTLN minus selection only | keyword | +6.11 (+2.49 to +9.62) | +5.22 (+2.03 to +8.41) | yes / yes |
| MFCC un-normalised: VTLN minus model only | instance | +8.71 (+5.34 to +12.32) | +8.66 (+5.66 to +11.64) | yes / yes |
| MFCC un-normalised: VTLN minus model only | keyword | +9.08 (+4.79 to +14.06) | +8.14 (+3.64 to +13.09) | yes / yes |
| MFCC un-normalised: query_inherit minus VTLN | instance | +0.49 (-1.07 to +2.28) | +0.77 (-0.26 to +1.91) | no / no |
| MFCC un-normalised: query_inherit minus VTLN | keyword | +0.04 (-1.18 to +1.36) | +0.82 (-0.19 to +2.07) | no / no |
| MFCC pn: VTLN minus selection only | instance | +5.92 (+3.06 to +9.04) | +6.56 (+4.16 to +9.13) | yes / yes |
| MFCC pn: VTLN minus selection only | keyword | +5.45 (+2.24 to +8.77) | +6.22 (+3.70 to +8.92) | yes / yes |
| MFCC pn: VTLN minus model only | instance | +7.14 (+4.33 to +9.91) | +7.37 (+5.20 to +9.56) | yes / yes |
| MFCC pn: VTLN minus model only | keyword | +6.75 (+1.73 to +11.78) | +7.06 (+3.16 to +11.35) | yes / yes |
| PLP un-normalised: VTLN minus selection only | instance | +1.26 (-1.99 to +4.95) | +2.34 (-0.11 to +5.19) | no / no |
| PLP un-normalised: VTLN minus selection only | keyword | +1.97 (-1.86 to +6.15) | +3.16 (-0.44 to +7.42) | no / no |
| PLP un-normalised: VTLN minus model only | instance | +8.31 (+5.08 to +11.49) | +9.36 (+6.52 to +12.21) | yes / yes |
| PLP un-normalised: VTLN minus model only | keyword | +7.85 (+4.18 to +11.74) | +9.12 (+5.13 to +13.23) | yes / yes |
| PLP un-normalised: query_inherit minus VTLN | instance | +1.98 (+0.54 to +3.48) | +1.87 (+0.54 to +3.18) | yes / yes |
| PLP un-normalised: query_inherit minus VTLN | keyword | +1.66 (+0.39 to +3.00) | +1.38 (+0.40 to +2.54) | yes / yes |
| PLP pn: VTLN minus selection only | instance | +4.48 (+1.16 to +8.42) | +5.49 (+1.81 to +9.56) | yes / yes |
| PLP pn: VTLN minus selection only | keyword | +6.24 (+2.29 to +10.48) | +7.37 (+2.88 to +12.28) | yes / yes |
| PLP pn: VTLN minus model only | instance | +9.94 (+7.63 to +12.42) | +10.10 (+7.46 to +12.84) | yes / yes |
| PLP pn: VTLN minus model only | keyword | +10.50 (+7.51 to +13.88) | +10.34 (+6.64 to +14.41) | yes / yes |

Which comparisons exclude 0, per feature (all four p@N / MAP, instance and
keyword, unless stated):

- **MFCC un-normalised:** VTLN minus selection only excludes 0; VTLN minus model
  only excludes 0; `query_inherit` minus VTLN includes 0.
- **PLP un-normalised:** VTLN minus selection only includes 0; VTLN minus model
  only excludes 0; `query_inherit` minus VTLN excludes 0.
- **MFCC `pn`:** VTLN minus selection only and VTLN minus model only both
  exclude 0.
- **PLP `pn`:** VTLN minus selection only and VTLN minus model only both
  exclude 0.

`query_inherit` is an analysis cell, not a deployable condition: it uses each
query's source-utterance alpha-hat from the training trace. For PLP, using the
clip's own alpha-hat instead of the source utterance's gives a lower score by
about 2 points (post hoc). It was not run under `pn`.

### Normalised reference runs (declared)

**Declared before any S3 number** (cycle 9, S3; user decision D6, 2026-11-18).
The author stated that the thesis's HTK pipeline subtracted the mean and then
scaled the waveform to +-1. `htk_described_4k_pn` is `htk_described_4k` with
`remove_dc=True` and `normalize_peak=True` (known approximation: our code
peak-normalises first and removes the mean afterwards; S1 (c) measured the
gap as negligible, a 99th-percentile c0 offset of 0.003). **It is the
reference for MFCC and PLP whatever it scores.** The `htk_described_4k`
rows are the un-normalised earlier reference.

- **Runs:** MFCC first, then PLP, one at a time, clean tree, no commit while
  a run goes. Each: (1) feature caches; (2) plain GMM-64 on the v2 train
  split (`train-gmm`, 64 components); (3) no-VTLN evaluation; (4) the 26 warp
  caches; (5) `train-vtln` with N_iter = 5 and fresh LBG (D4); (6) VTLN
  evaluation; (7) the 2x2 cells *model only* and *selection only*. Same
  protocol as W3 and S2 (LC2, A1 scorer, clip query features, 145 queries,
  keyword-cluster bootstrap, 10000 resamples, seed 0).
- **Targets:** `Tab:TIMITPerformance` GMM-64 rows (34.91 / 36.71 for MFCC,
  35.50 / 37.58 for PLP) and `Tab:TIMITVTLNPerformance1` (36.26 / 39.62 and
  37.48 / 39.95), p@N / MAP.
- **Comparisons:** paired VTLN minus no-VTLN; paired `pn` minus un-normalised
  (same queries, with and without VTLN); MFCC-TMP minus MFCC under the `pn`
  reference, with and without VTLN; PLP minus MFCC.
- **Rule:** the `pn` rows are the reference whatever they score. An interval
  that includes 0 gets the usual wording (the direction matches or does not
  match the thesis; the interval does not establish a difference) and nothing
  more. Nothing is tuned; no band or level choice is made by score.
- **Recorded:** everything W3 recorded (alpha-hat histograms in the thesis
  label, edge shares, LL, `ll_decreased`, `selection_step_ok`, mean
  alpha-hat per iteration, hashes, runtime, peak memory, provenance) plus the
  mean posteriorgram entropy.
- A `ll_decreased` is recorded and does not stop the chain (D4); a failing
  `selection_step_ok` or any need to edit a feature source file is a STOP.

### Normalised HTK reference (D6)

**User decision D6 (2026-11-18): `htk_described_4k_pn` is the reference for
MFCC and PLP, whatever it scores.** Declared above ("Normalised reference
runs (declared)"); run as declared, one run at a time on a clean tree, from
`84e26bc` (the MFCC train-vtln was first killed by a machine shutdown and
re-run from the same commit; the MFCC plain GMM-64, its no-VTLN evaluation
and the 26 MFCC warp caches from before the stop were reused, each after its
model hash or fingerprint check). GMM-64, split v2, N_iter 5, fresh LBG (D4),
145 queries, 1344 documents, clip query features, A1 scorer, 10000 bootstrap
resamples, seed 0. These rows are **not** merged into the un-normalised
tables above; the un-normalised rows are repeated here only for the paired
comparison. Nothing was tuned.

| Row | p@N, instance avg (95% CI) | MAP, instance avg (95% CI) | p@N, keyword avg (95% CI) | MAP, keyword avg (95% CI) | Queries | Non-matches |
|---|---|---|---|---|---|---|
| MFCC thesis (`Tab:TIMITPerformance`), no VTLN | 34.91 | 36.71 | n/s | n/s | 145 | n/a |
| MFCC thesis (`Tab:TIMITVTLNPerformance1`), VTLN | 36.26 | 39.62 | n/s | n/s | 145 | n/a |
| MFCC 0-4000 Hz, normalised (`htk_described_4k_pn`), per-clip, earlier reference (D7), GMM-64, no VTLN | 37.04 (27.7-47.0) | 38.75 (28.5-50.0) | 34.23 (25.7-43.1) | 36.44 (27.0-46.2) | 145 | 1 |
| MFCC 0-4000 Hz, normalised (`htk_described_4k_pn`), per-clip, earlier reference (D7), GMM-64, GMM-VTLN | 45.10 (35.1-55.5) | 48.10 (37.0-59.8) | 43.06 (32.7-53.6) | 45.80 (35.0-56.9) | 145 | 2 |
| MFCC 0-4000 Hz, un-normalised (earlier reference), GMM-64, no VTLN | 37.48 (28.0-47.6) | 40.50 (30.1-52.1) | 35.07 (26.6-43.9) | 37.84 (28.4-47.6) | 145 | 3 |
| MFCC 0-4000 Hz, un-normalised (earlier reference), GMM-64, GMM-VTLN | 48.17 (37.3-59.9) | 50.58 (39.0-62.9) | 44.95 (34.5-55.9) | 46.88 (35.7-58.5) | 145 | 1 |
| PLP thesis (`Tab:TIMITPerformance`), no VTLN | 35.50 | 37.58 | n/s | n/s | 145 | n/a |
| PLP thesis (`Tab:TIMITVTLNPerformance1`), VTLN | 37.48 | 39.95 | n/s | n/s | 145 | n/a |
| PLP 0-4000 Hz, normalised (`htk_described_4k_pn`), per-clip, earlier reference (D7), GMM-64, no VTLN | 36.88 (28.0-46.4) | 37.83 (28.2-48.3) | 34.20 (26.0-42.7) | 35.25 (26.6-44.1) | 145 | 0 |
| PLP 0-4000 Hz, normalised (`htk_described_4k_pn`), per-clip, earlier reference (D7), GMM-64, GMM-VTLN | 45.85 (36.3-56.5) | 49.03 (38.4-60.6) | 44.61 (34.9-54.6) | 47.34 (36.7-58.3) | 145 | 0 |
| PLP 0-4000 Hz, un-normalised (earlier reference), GMM-64, no VTLN | 38.59 (29.1-48.5) | 39.75 (29.3-50.9) | 35.82 (27.1-44.8) | 36.81 (27.5-46.5) | 145 | 0 |
| PLP 0-4000 Hz, un-normalised (earlier reference), GMM-64, GMM-VTLN | 45.37 (35.5-56.2) | 48.99 (38.2-60.9) | 43.29 (33.6-53.5) | 46.55 (36.0-57.7) | 145 | 0 |

(n/s: not stated in the thesis.) Targets: `Tab:TIMITPerformance` GMM-64 rows
for the no-VTLN pairs, `Tab:TIMITVTLNPerformance1` for the VTLN pairs.

#### Gap to the thesis (descriptive, no cause attached)

Instance average, ours minus thesis, p@N / MAP; last column the thesis's own
gain.

| Run | no VTLN | VTLN | Thesis gain (VTLN minus no VTLN) |
|---|---|---|---|
| MFCC normalised | +2.13 / +2.04 | +8.84 / +8.48 | +1.35 / +2.91 |
| PLP normalised | +1.38 / +0.25 | +8.37 / +9.08 | +1.98 / +2.37 |

#### Paired VTLN minus no-VTLN, normalised reference

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) | Thesis gain against our instance interval (p@N / MAP) |
|---|---|---|---|---|---|
| MFCC normalised | instance | +8.07 (+3.7 to +12.0) | +9.35 (+4.9 to +13.1) | yes / yes | below / below |
| MFCC normalised | keyword | +8.83 (+4.1 to +14.0) | +9.35 (+4.8 to +14.2) | yes / yes | |
| PLP normalised | instance | +8.97 (+6.1 to +12.2) | +11.20 (+8.4 to +14.3) | yes / yes | below / below |
| PLP normalised | keyword | +10.42 (+6.5 to +15.4) | +12.10 (+8.3 to +16.8) | yes / yes | |

The last column puts the thesis's gain against our instance interval
("below", "inside", "above"); it is descriptive, not a test.

#### Normalised minus un-normalised (same queries)

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) |
|---|---|---|---|---|
| MFCC normalised minus un-normalised, no VTLN | instance | -0.44 (-2.0 to +1.1) | -1.76 (-3.36 to +0.03) | no / no |
| MFCC normalised minus un-normalised, no VTLN | keyword | -0.84 (-2.4 to +0.7) | -1.40 (-2.9 to +0.2) | no / no |
| MFCC normalised minus un-normalised, VTLN | instance | -3.06 (-6.8 to +0.8) | -2.49 (-5.8 to +1.0) | no / no |
| MFCC normalised minus un-normalised, VTLN | keyword | -1.89 (-5.5 to +1.8) | -1.09 (-4.5 to +2.5) | no / no |
| PLP normalised minus un-normalised, no VTLN | instance | -1.71 (-4.3 to +0.8) | -1.92 (-4.1 to +0.3) | no / no |
| PLP normalised minus un-normalised, no VTLN | keyword | -1.62 (-4.1 to +0.9) | -1.56 (-3.6 to +0.5) | no / no |
| PLP normalised minus un-normalised, VTLN | instance | +0.48 (-1.0 to +2.2) | +0.04 (-1.2 to +1.5) | no / no |
| PLP normalised minus un-normalised, VTLN | keyword | +1.33 (-0.5 to +3.4) | +0.79 (-0.8 to +2.7) | no / no |

#### MFCC-TMP minus MFCC, and PLP minus MFCC, under the normalised reference

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) |
|---|---|---|---|---|
| MFCC-TMP minus MFCC normalised, no VTLN | instance | +2.14 (-0.1 to +4.2) | +2.40 (-0.6 to +4.9) | no / no |
| MFCC-TMP minus MFCC normalised, no VTLN | keyword | +1.21 (-1.0 to +3.5) | +1.21 (-1.7 to +4.0) | no / no |
| MFCC-TMP minus MFCC normalised, VTLN | instance | -1.03 (-4.3 to +2.0) | -0.73 (-3.6 to +2.7) | no / no |
| MFCC-TMP minus MFCC normalised, VTLN | keyword | -1.63 (-4.8 to +1.4) | -1.24 (-4.1 to +1.9) | no / no |
| PLP minus MFCC, both normalised, no VTLN | instance | -0.15 (-2.9 to +2.8) | -0.92 (-3.4 to +1.7) | no / no |
| PLP minus MFCC, both normalised, no VTLN | keyword | -0.03 (-2.7 to +2.7) | -1.20 (-3.5 to +1.3) | no / no |
| PLP minus MFCC, both normalised, VTLN | instance | +0.75 (-2.1 to +4.2) | +0.93 (-1.9 to +4.0) | no / no |
| PLP minus MFCC, both normalised, VTLN | keyword | +1.56 (-1.4 to +4.8) | +1.54 (-1.0 to +4.1) | no / no |

MFCC-TMP (`timit_matlab`) is the same row as in the earlier tables. The
thesis's MFCC-TMP advantage is +5.12 / +4.79 without VTLN and +6.62 / +5.90
with VTLN. Under VTLN it is not reproduced (-1.03 / -0.73; the thesis's values
lie above our intervals). Without VTLN the direction matches (+2.14 / +2.40,
both intervals include 0); the thesis's p@N advantage lies above our interval
and its MAP advantage lies inside it. As before, the features differ in
lineage, filter count, level handling and VTLN response at once, so nothing is
claimed about Teager energy.

#### Gain split of the normalised rows (model only, selection only)

| Cell | p@N, instance (95% CI) | MAP, instance (95% CI) | p@N, keyword (95% CI) | MAP, keyword (95% CI) | Mean entropy documents / queries (nats) |
|---|---|---|---|---|---|
| MFCC normalised, no VTLN | 37.04 (27.7-47.0) | 38.75 (28.5-50.0) | 34.23 (25.7-43.1) | 36.44 (27.0-46.2) | 0.4357 / 0.4670 |
| MFCC normalised, model only | 37.96 (28.8-48.0) | 40.73 (30.3-52.0) | 36.31 (27.5-45.5) | 38.74 (29.1-48.7) | 0.4366 / 0.4392 |
| MFCC normalised, selection only | 39.18 (29.7-49.0) | 41.54 (30.9-52.6) | 37.61 (28.4-47.1) | 39.57 (29.3-49.9) | 0.4347 / 0.4590 |
| MFCC normalised, both = VTLN row | 45.10 (35.1-55.5) | 48.10 (37.0-59.8) | 43.06 (32.7-53.6) | 45.80 (35.0-56.9) | 0.4200 / 0.4098 |
| PLP normalised, no VTLN | 36.88 (28.0-46.4) | 37.83 (28.2-48.3) | 34.20 (26.0-42.7) | 35.25 (26.6-44.1) | 0.4490 / 0.4631 |
| PLP normalised, model only | 35.91 (27.5-45.1) | 38.93 (29.1-49.9) | 34.12 (26.1-42.3) | 37.00 (28.3-46.1) | 0.4430 / 0.4480 |
| PLP normalised, selection only | 41.37 (31.0-52.7) | 43.54 (31.9-56.4) | 38.37 (29.1-47.8) | 39.97 (29.9-50.4) | 0.4489 / 0.4562 |
| PLP normalised, both = VTLN row | 45.85 (36.3-56.5) | 49.03 (38.4-60.6) | 44.61 (34.9-54.6) | 47.34 (36.7-58.3) | 0.4198 / 0.4230 |

| Comparison | Average | p@N diff (95% CI) | MAP diff (95% CI) | Excludes 0 (p@N / MAP) |
|---|---|---|---|---|
| MFCC normalised, model only | instance | +0.92 (-2.0 to +3.6) | +1.98 (-1.2 to +4.6) | no / no |
| MFCC normalised, model only | keyword | +2.08 (-1.2 to +5.6) | +2.30 (-0.7 to +4.9) | no / no |
| MFCC normalised, selection only | instance | +2.14 (-1.9 to +6.2) | +2.79 (-0.9 to +6.4) | no / no |
| MFCC normalised, selection only | keyword | +3.39 (-1.0 to +8.0) | +3.13 (-0.7 to +7.1) | no / no |
| MFCC normalised, both = VTLN row | instance | +8.07 (+3.7 to +12.0) | +9.35 (+4.9 to +13.1) | yes / yes |
| MFCC normalised, both = VTLN row | keyword | +8.83 (+4.1 to +14.0) | +9.35 (+4.8 to +14.2) | yes / yes |
| PLP normalised, model only | instance | -0.98 (-3.2 to +1.5) | +1.10 (-0.9 to +3.2) | no / no |
| PLP normalised, model only | keyword | -0.08 (-2.3 to +2.4) | +1.76 (-0.2 to +3.7) | no / no |
| PLP normalised, selection only | instance | +4.48 (+0.5 to +8.4) | +5.71 (+2.0 to +9.4) | yes / yes |
| PLP normalised, selection only | keyword | +4.18 (+0.3 to +8.1) | +4.73 (+1.5 to +8.3) | yes / yes |
| PLP normalised, both = VTLN row | instance | +8.97 (+6.1 to +12.2) | +11.20 (+8.4 to +14.3) | yes / yes |
| PLP normalised, both = VTLN row | keyword | +10.42 (+6.5 to +15.4) | +12.10 (+8.3 to +16.8) | yes / yes |

The cells describe where the gain shows up; no mechanism is claimed, and the
two halves need not add up to the total.

#### LL per iteration, `ll_decreased` and `selection_step_ok` (fresh LBG, D4)

`ll_decreased` is recorded and did not stop the chain; `selection_step_ok`
is the check of K1 (a `False` would have been a STOP).

**MFCC normalised**

| Iteration | LL of lambda_init on X^alpha_hat | LL of new model | ll_decreased | selection_step_ok | Share changed | Edge share 0.88 | Edge share 1.12 |
|---|---|---|---|---|---|---|---|
| 0 | -116.3300 | -116.2476 | no | n/a | 0.748 | 0.014 | 0.044 |
| 1 | -116.2050 | -116.2002 | no | True | 0.468 | 0.038 | 0.070 |
| 2 | -116.1846 | -116.1598 | no | True | 0.314 | 0.048 | 0.088 |
| 3 | -116.1491 | -116.1524 | **yes** | True | 0.246 | 0.055 | 0.112 |
| 4 | -116.1461 | -116.1330 | no | True | 0.204 | 0.055 | 0.128 |

**PLP normalised**

| Iteration | LL of lambda_init on X^alpha_hat | LL of new model | ll_decreased | selection_step_ok | Share changed | Edge share 0.88 | Edge share 1.12 |
|---|---|---|---|---|---|---|---|
| 0 | 13.4833 | 13.7460 | no | n/a | 0.852 | 0.081 | 0.067 |
| 1 | 13.8324 | 13.8233 | **yes** | True | 0.554 | 0.115 | 0.113 |
| 2 | 13.8404 | 13.8838 | no | True | 0.292 | 0.112 | 0.147 |
| 3 | 13.8904 | 13.8838 | **yes** | True | 0.190 | 0.103 | 0.172 |
| 4 | 13.8871 | 13.8710 | **yes** | True | 0.146 | 0.095 | 0.197 |

#### Warp statistics and provenance

Mean alpha-hat in the thesis label per iteration over the 3696 train
utterances, with the share above 1.00 in brackets (iterations 0 to 4):

| Run | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| MFCC normalised | 1.003 (0.388) | 1.006 (0.477) | 1.011 (0.526) | 1.015 (0.565) | 1.018 (0.581) |
| PLP normalised | 1.010 (0.520) | 1.019 (0.618) | 1.025 (0.649) | 1.028 (0.659) | 1.031 (0.665) |

Final train alpha-hat histogram (thesis label, counts of 3696):

| Run | 1.12 | 1.10 | 1.08 | 1.06 | 1.04 | 1.02 | 1.00 | 0.98 | 0.96 | 0.94 | 0.92 | 0.90 | 0.88 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MFCC normalised | 473 | 209 | 180 | 553 | 421 | 313 | 412 | 110 | 225 | 252 | 245 | 100 | 203 |
| PLP normalised | 729 | 567 | 243 | 521 | 265 | 133 | 142 | 47 | 167 | 153 | 238 | 139 | 352 |

| Run | VTLN model hash | ll_decreased at iteration | selection_step_ok all | Train edge shares 0.88 / 1.12 (final) | Share changed (final) | Test-document edge shares | Query edge shares | Queries with alpha-hat different from source | train-vtln time / peak memory | Start commit | Dirty |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MFCC normalised | `b1f4340f926b...` | 3 | True | 0.055 / 0.128 | 0.204 | 0.056 / 0.154 | 0.041 / 0.228 | 0.71 | 1078 s / 931 MB | `84e26bc` | False |
| PLP normalised | `c36b1d136023...` | 1, 3, 4 | True | 0.095 / 0.197 | 0.146 | 0.083 / 0.219 | 0.062 / 0.290 | 0.61 | 1823 s / 1256 MB | `84e26bc` | False |

#### What the normalised rows show (facts only)

- Normalised minus un-normalised: every paired interval includes 0, with and
  without VTLN, for both features (MFCC no VTLN -0.44 / -1.76, VTLN -3.06 /
  -2.49; PLP no VTLN -1.71 / -1.92, VTLN +0.48 / +0.04, p@N / MAP instance).
  The normalisation does not establish a difference at this sample size.
- Gap to the thesis: the no-VTLN rows stay above the thesis's (MFCC +2.13 /
  +2.04, PLP +1.38 / +0.25), and the paired VTLN gains (MFCC +8.07 / +9.35,
  PLP +8.97 / +11.20) stay far above the thesis's (+1.35 / +2.91 and
  +1.98 / +2.37), which lie below our instance intervals. No cause is
  claimed.
- MFCC-TMP minus MFCC: without VTLN +2.14 / +2.40 and with VTLN -1.03 /
  -0.73; every interval includes 0. Under VTLN the thesis's MFCC-TMP advantage
  is not reproduced; without VTLN the direction matches, and the thesis's p@N
  advantage lies above our interval while its MAP advantage lies inside it.
  Nothing is claimed about Teager energy. PLP minus MFCC intervals all include 0.
- Gain split: for MFCC neither cell's interval excludes 0 (model only
  +0.92 / +1.98, selection only +2.14 / +2.79); for PLP *selection only*
  excludes 0 (+4.48 / +5.71) and *model only* does not (-0.98 / +1.10).
- `ll_decreased` fired at iteration 3 (MFCC) and at 1, 3 and 4 (PLP);
  `selection_step_ok` held in every iteration of both runs.
  `selection_step_ok` holds by construction (alpha-hat_k maximises each
  utterance's LL under lambda_{k-1}); it is a bug guard, not an empirical
  finding.

**Level handling (Reviewer checks, post hoc, not declared).**

- Under `pn`, alpha-hat is invariant to waveform gain on real utterances: 100
  train utterances (seed 1), waveform x0.5 and x2, under lambda_r, changed for
  0 % of utterances in both MFCC and PLP. K4 tests the same invariance on
  synthetic signals.
- The paired VTLN gain stays at +8.07 / +9.35 (MFCC) and +8.97 / +11.20 (PLP).
  Level normalisation therefore does not bring our VTLN gain to the thesis's.
  The 1.12 edge share is unchanged: MFCC 0.128 against 0.129 un-normalised,
  PLP 0.197 against 0.200.
- Every thesis row lies inside our marginal keyword-cluster intervals. The
  paired gain is the comparison that separates us from the thesis.
- Two things change in every `pn` minus un-normalised comparison. The
  normalisation changes, and a query/document level mismatch appears: query
  clips are peak-normalised on their own, while documents and training
  utterances are normalised per utterance. Over the 145 queries (post hoc, from
  `qbestd.eval.post_hoc`, commit `b4aeebb`), the ratio of utterance peak to clip
  peak has median 1.44, p90 2.70 and max 4.96. The VTLN minus no-VTLN
  comparisons within `pn` carry the same mismatch on both sides.

**Convergence and query edges (caveat only).** The share of train utterances
whose warp changed at iteration 4 is 0.204 (MFCC) and 0.146 (PLP). The final
train 1.12 shares are still growing (0.128 and 0.197). The grid stays 0.88 to
1.12, the thesis grid, and N_iter = 5 is the thesis value. The query 1.12
shares are 0.228 (MFCC) and 0.290 (PLP) under `pn`, against 0.186 and 0.283
without normalisation, so `pn` adds about 0.04 and 0.01. The query excess is
therefore mostly a clip property, with no level effect shown. The cause (for
example short clips giving noisy alpha-hat) is not measured here.

**Status (D7, user decision 2026-11-21, author fact).** The thesis normalised
the whole utterance and then cut the query from it. The per-clip `pn` rows
above are now the earlier reference. The reference query path is the
level-matched clip, `clip_lm`, which section "Level-matched reference (D7)"
reports once N2 has run.
