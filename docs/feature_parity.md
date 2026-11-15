# Feature parity: Python vs MATLAB vs HTK vs thesis

Scope: every Stage 2 setting in `src/qbestd/features/`. No numeric comparison
against MATLAB output was run (no MATLAB or Octave here), so "parity" below
means the same algorithm and settings, not matching numbers.

Sources and how much to trust them:
- **MATLAB** columns cite file and line from
  `github.com/maulikmadhavi/research_myMATLAB_codes`, folder
  `Analysis/Feature_Extraction`, read on 2026-11-14 with `gh api`. `Features/`
  holds `Fx_mfcc.m` (FM), `Fx_mfcc_lift.m` (FL), `Fx_mfcc_vtmp_cep.m` (FT),
  `Fx_PLPCC_htk.m` (FP), `Deltacep.m` (DC), `Fx_dctmat.m`, `VTLN/Fx_vtln_warp.m`.
  `Signal_Processing/` holds `myspectrogram.m` (MS), `enframe_m.m` (EF),
  `hz2bark.m`.
- **HTK** column is the HTK Book default as recalled from memory. **Every HTK
  cell is unverified**; nothing was checked against HTK here.
- **Thesis** column: re-read on 2026-11-15 from `Chapters/ExpSetup.tex` lines
  191-223 (acoustic representation) and `Backmatter/Warped_Feature.tex` line
  30 (VTLN cutoff). The thesis states far less per feature than the earlier
  version of this table implied; see "What the thesis says, per feature".
  Where a cell says "not stated" the thesis passage is silent.

## Settings

| Setting | Ours | `Fx_mfcc.m` | `Fx_mfcc_vtmp_cep.m` | `Fx_PLPCC_htk.m` | HTK default (unverified) | Thesis (ExpSetup 191-223) |
|---|---|---|---|---|---|---|
| Sample rate | generic default 8000 (unverified); the profiles use 16000 (TIMIT native); resamples if source differs | 16000 (FM:17) | 16000 (FT:27) | 16000 (FP:30) | n/a | not stated in 191-223 |
| DC removal | whole-utterance mean by default (`remove_dc=True`); the `timit_matlab` PLP profile turns it off | `x - mean(x)` (FM:29) | `x - mean(x)` (FT:41) | **none** | ZMEANSOURCE off | not stated |
| Peak normalisation | `x / max abs x`, on for MFCC and MFCC-TMP, off for PLP | `/ max(x)` (FM:29), **not** max abs | `/ max(abs(x))` (FT:41) | none | none | not stated |
| PCM scale | x 32768 (`PCM_SCALE`) | `2^15 * xp` (FM:43) | `32768 * xp` (FT:54) | `x * 32768` (FP:69) | n/a | n/a |
| Pre-emphasis | 0.97 for MFCC and MFCC-TMP, **0.0** for PLP | 0.97 (FM:18) | 0.97 (FT:28) | **none** | PREEMCOEF 0.97 | not stated in 191-223 |
| Frame / shift | 25 ms / 10 ms | `floor(25*fs/1000)`, `floor(10*fs/1000)` (FM:19-20) | same (FT:29-30) | same (FP:36-37) | 25 ms / 10 ms | 25 / 10 ms, stated for MFCC-TMP only (line 198) |
| Framing | complete frames only, no padding | `floor(1 + (len-win)/inc)` (EF:40) | same | same | same | n/a |
| Window | Hamming, symmetric `0.54 - 0.46 cos(2 pi n/(N-1))` | `'h'` Hamming (FM:43, EF:51) | `'h'` (FT:54) | `'h'` (FP:69) | Hamming | not stated |
| FFT size | next power of two >= frame length (256 at 8 kHz) | `2^nextpow2(win)` (FM:23) | same (FT:33) | same (FP:38) | next power of two | n/a |
| FFT scaling | unnormalised | unnormalised (MS:67) | unnormalised (MS:69) | unnormalised | n/a | n/a |
| Spectrum used | magnitude (default) or power | magnitude, then squared after filtering: `log((M*y).^2)` (FM:46) | complex STFT, `specopt='mp'` (FT:38, 54-61) | power `y.^2` (FP:69) | magnitude (USEPOWER off) | n/a |
| Filter count | 26 (MFCC, MFCC-TMP); PLP `ceil(bark(fs/2)) + 1` = 17 at 8 kHz | 26 (FM:21) | 26 (FT:31) | `ceil(nyqmel) + 1` (FP:39) | NUMCHANS 20 | MFCC 26 (191), MFCC-TMP 26 (198, 223); PLP 26 (`Unsupervised.tex` 113, "26 subband filters" for MFCC and PLP; **not stated** in ExpSetup) |
| Band | 0 to 4000 Hz (MFCC, MFCC-TMP); 0 to fs/2 (PLP) | fL 0, fH `fs/2` (FM:24-25) | fL 0, fH **4000** (FT:35-36) | 0 to `fs/2` (FP:31-32, 65) | LOFREQ 0, HIFREQ fs/2 | MFCC 0-4000 Hz (191); MFCC-TMP and PLP **not stated** in this passage |
| Filter shape | triangles, equal mel spacing, unit peak, edges at `n+2` points | `Fx_melfiltbank` (**file missing**) (FM:34) | same (FT:46) | same (FP:65) | triangles, mel spacing | n/a |
| Mel formula | `2595 log10(1 + f/700)` | `hz2mel` in FP:132 | n/a | same | same | same |
| Cepstra | 13 including c0 | rows `1:Nc` of DCT (FM:39, 50-51) | rows `1:Nc` (FT:78) | `lpc2cep(.., Nc)`, Nc 13 (FP:42, 103) | NUMCEPS 12 plus optional C0 | MFCC 13 (191); MFCC-TMP 13, k = 1..13 (198, 223); PLP 13 (`Unsupervised.tex` 113); c0 policy not stated |
| DCT | orthonormal type 2 (`scipy.fft.dct`, `norm="ortho"`) | `Fx_dctmat(Nc,p,2)` (FM:39), unitary | `dct(eye(p))` (FT:50), orthonormal | none (LPC cepstrum) | type 2 with sqrt(2/N) | MFCC "Type III of DCT" (191); MFCC-TMP formula `sum_j S_ij cos(k(j-0.5)pi/N_F)` (221). Naming/convention **not checked** against our orthonormal DCT-II |
| Lifter | MFCC 0, MFCC-TMP 0, PLP 22 (HTK sine, `1 + L/2 sin(pi n/L)`) | none | none | `lifter(cepstra, Nlift)` (FP:109); `Nlift` has **no default** (FP:42 stops at Nc) | CEPLIFTER 22 | not stated |
| `Fx_mfcc_lift.m` lifter (a separate MATLAB script, not a thesis statement) | n/a | `Nlift = -20` (FL:24), i.e. HTK sine, L = 20; also fH 8000 (FL:27) | n/a | n/a | n/a | **not stated**: the thesis gives no lifter |
| Deltas | regression, window 2, edge frames replicated; delta and acceleration give 39 dims | n/a | n/a | n/a | DELTAWINDOW 2, ACCWINDOW 2 | MFCC-TMP: 13 + delta + delta-delta (198); MFCC and PLP: 13 + delta + delta-delta (`Unsupervised.tex` 113, not in ExpSetup) |
| Delta formula | `sum k (x[t+k]-x[t-k]) / (2 sum k^2)` | `Deltacep(x,N)` (DC:49-53), N is a parameter, edge copy (DC:28-38) | same | same | same | **not stated** |
| LPC order | generic default 12 (unverified); `timit_matlab` PLP 8 | n/a | n/a | 8 (FP:35) | LPCORDER 12 | not stated |
| Equal loudness | `f^4/(f^2+1.6e5)^2 * (f^2+1.44e6)/(f^2+9.61e6)` at the warped filter centre | n/a | n/a | same formula, centre `fhz(i)` (FP:57-62) | same | not stated (PLP cites Hermansky 1990 only, 194) |
| Compression | power 0.33 | n/a | n/a | `.^0.33` (FP:93) | 0.33 | n/a |
| Edge bands | first and last copied from neighbours | n/a | n/a | `z([2,2:(nfilt-1),nfilt-1],:)` (FP:95) | same idea | n/a |
| RASTA | not implemented | n/a | n/a | `dorasta=0` default (FP:40) | off | not stated |
| Teager energy | lag 1, `x(n)^2 - x(n-1)x(n+1)`, summed per subband frame | n/a | `vteo(y1', DI)` summed (FT:70), `DI=1` (FT:34); **`vteo.m` missing** | n/a | n/a | `psi{x(n)} = x^2(n) - x(n+1) x(n-1)` (206); lag-1 form |
| Log floor | `1e-10` (explicit) | none, `log` of a magnitude-squared | none; TEO sum can be <= 0 so MATLAB would give complex/-inf | none | floor on energy | n/a |
| VTLN warp | piecewise linear, cutoff 0.875 of the **band edge** (`upper_hz = high_hz` if below Nyquist, else Nyquist; 3500 Hz for a 4 kHz band), 0.05 back-off, applied to FFT bin frequencies | `wp` passed to filterbank (FM:34) | `wp` (FT:46) | `Fx_vtln_warp((0:NFFT/2)*fs/NFFT, wp, fs)` (FP:47) and on centres (FP:57) | VTLN via WARPFREQ (different warp) | alpha 0.88-1.12 step 0.02 (plan 2); cutoff 3500 Hz and 7000 Hz "corresponding to sampling frequencies of 4000 Hz and 8000 Hz" (`Warped_Feature.tex` 30), i.e. 0.875 of the band edge; wording ambiguous |

## Profiles

`qbestd.features.profiles.get_profile(name, kind)` bundles settings. No profile
is thesis-verified.

| Profile | MFCC / MFCC-TMP | PLP |
|---|---|---|
| `timit_matlab` | 16 kHz, 0-4000 Hz | 16 kHz, 0-8000 Hz, LPC order 8, no DC removal, no pre-emphasis, no peak normalisation, x 32768 (FP:30-39, 69) |

The generic config defaults (8 kHz, order 12) are unchanged.

## Known differences from MATLAB

1. **Peak normalisation.** `Fx_mfcc.m` divides by `max(x)`, not `max(abs(x))`
   (FM:29). We use `max abs`, as `Fx_mfcc_vtmp_cep.m` does. They differ when
   the largest peak is negative; the effect is an overall scale before the
   log, which shifts c0 and nothing else. Assumption, not parity.
2. **PLP in MATLAB** does no DC removal, pre-emphasis or peak normalisation
   (FP:69). The `timit_matlab` profile matches that. The generic `PlpConfig`
   still removes DC.
3. **Default sample rate and band.** MATLAB assumes 16 kHz and fH 4000 for
   MFCC-TMP, but fH `fs/2` for MFCC. The generic default is 8 kHz with 0 to
   4000 Hz for both; the profiles use 16 kHz with 0 to 4000 Hz (MFCC, MFCC-TMP)
   and 0 to 8000 Hz (PLP).
4. **PLP equal-loudness centres are the forward-warped centres.** FP:57 warps
   the centres with `Fx_vtln_warp`, and we do the same (MATLAB-faithful). Codex
   reviewed this and agreed it follows the script; it is not an independent
   validation of the physical meaning of the warp.
5. **Unit-peak triangles.** `Fx_melfiltbank.m` is missing, so triangle edges,
   peak normalisation (unit peak versus unit area) and the warping rule are
   assumptions. The thesis does not specify them either.
6. **VTLN anchor.** The warp maps the band edge to itself, so a 4 kHz band has
   a 3500 Hz cutoff, as `Warped_Feature.tex` line 30 describes (that sentence
   says "sampling frequencies of 4000 Hz and 8000 Hz", which we read as the
   band edge or Nyquist). This is thesis-based, **not proven MATLAB parity**,
   because the filterbank file is missing. `Fx_vtln_warp.m` itself uses the
   `fs` argument's Nyquist.
7. **PLP filter count** of 17 at 8 kHz and 21 at 16 kHz comes from the
   Bark-span default (FP:39), not from a number in the thesis.
8. **MFCC-TMP log floor.** `log` can see zero or negative sums; we floor them
   at 1e-10. MATLAB has no floor.
9. **DCT convention.** The thesis says "Type III of DCT" for MFCC; the
   MFCC-TMP formula is a type-II cosine sum. We use the orthonormal DCT-II
   (as `Fx_dctmat`). The naming is **not checked**.

## What the thesis says, per feature (`ExpSetup.tex` 191-223)

| Feature | Stated | Not stated |
|---|---|---|
| MFCC | HTK, 25 ms / 10 ms, 26 subband filters, 13 coefficients plus delta and delta-delta (`Unsupervised.tex` 113); 26 filters, 0-4000 Hz, 13 coefficients ("Type III of DCT") (`ExpSetup.tex` 191) | sample rate, c0 policy, lifter, pre-emphasis |
| PLP | HTK, 25 ms / 10 ms, 26 subband filters, 13 coefficients plus delta and delta-delta (`Unsupervised.tex` 113); HTK extraction, Hermansky 1990 (`ExpSetup.tex` 194) | band, LPC order, c0, lifter |
| MFCC-TMP | 25 ms / 10 ms, 26 filters, 13 coefficients plus delta and delta-delta, `k = 1..13`, TEO `psi{x} = x^2(n) - x(n+1) x(n-1)` (198-223) | band, lag, spectrum option, c0 policy |

## Author statement, 2026-11-16 (user decision D2)

The author states that the HTK configuration used for the thesis MFCC **and**
PLP had:

| Setting | Author statement | Thesis text |
|---|---|---|
| `NUMCHANS` | **40** for both MFCC and PLP | "26 subband filters" (`Unsupervised.tex` 113), so the thesis number is inaccurate for them |
| Sample rate | 16 kHz | not stated |
| Band | **0-3400 Hz** | MFCC 0-4000 Hz (`ExpSetup.tex` 191) |

The band was stated for the HTK configuration and is applied to both
features; the conflict with the thesis text for MFCC (0-4000 Hz) is
recorded, not resolved. **MFCC-TMP is unaffected**: it came from the MATLAB
script (`Fx_mfcc_vtmp_cep.m`), which uses 26 filters, so it stays on
`timit_matlab`. The remaining HTK settings (pre-emphasis, lifter, LPC order,
compression, delta window) are not in this statement; the profile
`htk_described` takes them from recalled, unverified HTK defaults and says so
per value.

### How `timit_matlab` MFCC and PLP differ (Handoff_feedback Q4)

| Setting | Our MFCC | Our PLP | Thesis text | Author statement |
|---|---|---|---|---|
| Tool | from `Fx_mfcc.m` | from `Fx_PLPCC_htk.m` defaults | HTK for both | HTK for both |
| Filters | 26 | 21 | 26 for both | 40 for both |
| Band | 0-4000 Hz | 0-8000 Hz | 0-4000 Hz stated for MFCC only | 0-3400 Hz |
| Pre-emphasis | 0.97 | none | not stated | not stated |
| LPC order | n/a | 8 | not stated | not stated |
| Level handling | DC removed, peak-normalised | neither | not stated | not stated |

Our two features therefore differ in band, filter count, pre-emphasis and
level handling at once, and PLP minus MFCC on `timit_matlab` does not test
the thesis's PLP minus MFCC. `Fx_PLPCC_htk.m` takes `nfilt` and `LP_order` as
arguments; 21 and 8 are only its defaults, and no caller is in the
repository.

## Remaining unknowns

- **TIMIT sample rate and mel ceiling** (plan 4 #14): the data is 16 kHz
  (every row, `docs/alignment_notes.md`), MATLAB defaults to 16 kHz, the
  thesis filters stop at 4000 Hz. Whether the thesis downsampled to 8 kHz is
  unknown; `sample_rate` and `high_hz` are separate settings for that reason.
- **`vteo.m` is not in the public repository.** `teager_energy_lagged` is the
  standard lagged form and may differ in edge handling and in whether the sum
  is normalised.
- **`Fx_melfiltbank.m` is not in the public repository** (see item 5 above).
- **PLP `Nlift`** has no default in `Fx_PLPCC_htk.m`; the 22 here is HTK's
  (unverified).
- **Delta window N** is a free argument of `Deltacep` (DC:12); 2 is HTK's
  (unverified).
- **PLP LPC order**: 8 in MATLAB, 12 in HTK; both are profiles now, neither is
  thesis-verified.
- **Whether the thesis uses deltas for PLP and MFCC** (all kinds produce 39
  dimensions by default here; only MFCC-TMP is stated).
