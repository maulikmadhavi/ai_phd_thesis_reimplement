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
averages, so this check shows no change in either feature. PLP minus MFCC
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
`outputs/`; only this summary is committed.
