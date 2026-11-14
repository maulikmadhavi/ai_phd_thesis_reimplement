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
- **HTK** column is the HTK Book default as recalled from memory, not checked
  against HTK here.
- **Thesis** column repeats what `docs/plan.md` section 2 says about the
  thesis. The Executor did not re-read the thesis `.tex`.

## Settings

| Setting | Ours | `Fx_mfcc.m` | `Fx_mfcc_vtmp_cep.m` | `Fx_PLPCC_htk.m` | HTK default | Thesis |
|---|---|---|---|---|---|---|
| Sample rate | 8000 (`AudioFrontEndConfig`, unverified); resamples if source differs | 16000 (FM:17) | 16000 (FT:27) | 16000 (FP:30) | n/a | 8 kHz data; TIMIT is 16 kHz, so open (plan 4 #14) |
| DC removal | whole-utterance mean, all extractors | `x - mean(x)` (FM:29) | `x - mean(x)` (FT:41) | **none** | ZMEANSOURCE off | not stated |
| Peak normalisation | `x / max abs x`, on for MFCC and MFCC-TMP, off for PLP | `/ max(x)` (FM:29), **not** max abs | `/ max(abs(x))` (FT:41) | none | none | not stated |
| PCM scale | x 32768 (`PCM_SCALE`) | `2^15 * xp` (FM:43) | `32768 * xp` (FT:54) | `x * 32768` (FP:69) | n/a | n/a |
| Pre-emphasis | 0.97 for MFCC and MFCC-TMP, **0.0** for PLP | 0.97 (FM:18) | 0.97 (FT:28) | **none** | PREEMCOEF 0.97 | 0.97 (plan 2) |
| Frame / shift | 25 ms / 10 ms | `floor(25*fs/1000)`, `floor(10*fs/1000)` (FM:19-20) | same (FT:29-30) | same (FP:36-37) | 25 ms / 10 ms | 25 / 10 ms |
| Framing | complete frames only, no padding | `floor(1 + (len-win)/inc)` (EF:40) | same | same | same | n/a |
| Window | Hamming, symmetric `0.54 - 0.46 cos(2 pi n/(N-1))` | `'h'` Hamming (FM:43, EF:51) | `'h'` (FT:54) | `'h'` (FP:69) | Hamming | Hamming (plan 2) |
| FFT size | next power of two >= frame length (256 at 8 kHz) | `2^nextpow2(win)` (FM:23) | same (FT:33) | same (FP:38) | next power of two | n/a |
| FFT scaling | unnormalised | unnormalised (MS:67) | unnormalised (MS:69) | unnormalised | n/a | n/a |
| Spectrum used | magnitude (default) or power | magnitude, then squared after filtering: `log((M*y).^2)` (FM:46) | complex STFT, `specopt='mp'` (FT:38, 54-61) | power `y.^2` (FP:69) | magnitude (USEPOWER off) | n/a |
| Filter count | 26 (MFCC, MFCC-TMP); PLP `ceil(bark(fs/2)) + 1` = 17 at 8 kHz | 26 (FM:21) | 26 (FT:31) | `ceil(nyqmel) + 1` (FP:39) | NUMCHANS 20 | 26 (plan 2) |
| Band | 0 to 4000 Hz (MFCC, MFCC-TMP); 0 to fs/2 (PLP) | fL 0, fH `fs/2` (FM:24-25) | fL 0, fH **4000** (FT:35-36) | 0 to `fs/2` (FP:31-32, 65) | LOFREQ 0, HIFREQ fs/2 | 0 to 4000 Hz (plan 2) |
| Filter shape | triangles, equal mel spacing, unit peak, edges at `n+2` points | `Fx_melfiltbank` (**file missing**) (FM:34) | same (FT:46) | same (FP:65) | triangles, mel spacing | n/a |
| Mel formula | `2595 log10(1 + f/700)` | `hz2mel` in FP:132 | n/a | same | same | same |
| Cepstra | 13 including c0 | rows `1:Nc` of DCT (FM:39, 50-51) | rows `1:Nc` (FT:78) | `lpc2cep(.., Nc)`, Nc 13 (FP:42, 103) | NUMCEPS 12 plus optional C0 | 13 (plan 2); formula indexes 1..N_c, errata |
| DCT | orthonormal type 2 (`scipy.fft.dct`, `norm="ortho"`) | `Fx_dctmat(Nc,p,2)` (FM:39), unitary | `dct(eye(p))` (FT:50), orthonormal | none (LPC cepstrum) | type 2 with sqrt(2/N) | `sum_j S_ij cos(k(j-0.5)pi/N_F)` |
| Lifter | MFCC 0, MFCC-TMP 0, PLP 22 (HTK sine, `1 + L/2 sin(pi n/L)`) | none | none | `lifter(cepstra, Nlift)` (FP:109); `Nlift` has **no default** (FP:42 stops at Nc) | CEPLIFTER 22 | not stated |
| `Fx_mfcc_lift.m` lifter | n/a | n/a | n/a | n/a | n/a | `Nlift = -20` (FL:24), i.e. HTK sine, L = 20; also fH 8000 (FL:27) |
| Deltas | regression, window 2, edge frames replicated; delta and acceleration give 39 dims | n/a | n/a | n/a | DELTAWINDOW 2, ACCWINDOW 2 | delta and acceleration, 39-dim (plan 2) |
| Delta formula | `sum k (x[t+k]-x[t-k]) / (2 sum k^2)` | `Deltacep(x,N)` (DC:49-53), N is a parameter, edge copy (DC:28-38) | same | same | same | same |
| LPC order | 12 (unverified) | n/a | n/a | 8 (FP:35) | LPCORDER 12 | not stated |
| Equal loudness | `f^4/(f^2+1.6e5)^2 * (f^2+1.44e6)/(f^2+9.61e6)` at the warped filter centre | n/a | n/a | same formula, centre `fhz(i)` (FP:57-62) | same | plan 2 |
| Compression | power 0.33 | n/a | n/a | `.^0.33` (FP:93) | 0.33 | n/a |
| Edge bands | first and last copied from neighbours | n/a | n/a | `z([2,2:(nfilt-1),nfilt-1],:)` (FP:95) | same idea | n/a |
| RASTA | not implemented | n/a | n/a | `dorasta=0` default (FP:40) | off | not stated |
| Teager energy | lag 1, `x(n)^2 - x(n-1)x(n+1)`, summed per subband frame | n/a | `vteo(y1', DI)` summed (FT:70), `DI=1` (FT:34); **`vteo.m` missing** | n/a | n/a | `psi{x(n)} = x^2(n) - x(n+1)x(n-1)` |
| Log floor | `1e-10` (explicit) | none, `log` of a magnitude-squared | none; TEO sum can be <= 0 so MATLAB would give complex/-inf | none | floor on energy | n/a |
| VTLN warp | piecewise linear, cutoff 0.875 Nyquist with 0.05 back-off, applied to FFT bin frequencies | `wp` passed to filterbank (FM:34) | `wp` (FT:46) | `Fx_vtln_warp((0:NFFT/2)*fs/NFFT, wp, fs)` (FP:47) and on centres (FP:57) | VTLN via WARPFREQ (different warp) | alpha 0.88 to 1.12 step 0.02 (plan 2) |

## Known differences from MATLAB

1. `Fx_mfcc.m` divides by `max(x)`, not `max(abs(x))` (FM:29). We use
   `max abs`, as `Fx_mfcc_vtmp_cep.m` does. The two differ for signals whose
   largest peak is negative; the effect is only an overall scale before the
   log, which shifts c0 and nothing else.
2. PLP in MATLAB does no pre-emphasis and no peak normalisation (FP:69). Our
   `PlpConfig` defaults match that, but we still remove the DC offset.
3. Default sample rate and band: MATLAB assumes 16 kHz and fH 4000 for
   MFCC-TMP, but fH `fs/2` for MFCC. We default to 8 kHz with 0 to 4000 Hz for
   both, following the thesis description.
4. Mel filterbank, loudness weights and warping interact in PLP. We warp the
   FFT bins and evaluate the loudness curve at the warped centre, as FP:57-65
   suggests, but without `Fx_melfiltbank.m` the filter shape is an assumption.
5. The PLP filter count of 17 at 8 kHz comes from the Bark-span default
   (FP:39), not from a number stated in the thesis.
6. In MFCC-TMP `log` can see zero or negative sums; we floor them. MATLAB has
   no floor.

## Remaining unknowns

- **TIMIT sample rate and mel ceiling** (plan 4 #14): the data is 16 kHz
  (`docs/data_notes.md`), MATLAB defaults to 16 kHz, the thesis filters stop
  at 4000 Hz. Whether the thesis downsampled to 8 kHz is unknown. `sample_rate`
  and `high_hz` are separate settings for that reason.
- **`vteo.m` is not in the public repository.** `teager_energy_lagged` is the
  standard lagged form and may differ in edge handling and in whether the sum
  is normalised.
- **`Fx_melfiltbank.m` is not in the public repository.** Triangle edges,
  normalisation (unit peak versus unit area) and the exact warping rule are
  assumed HTK-like.
- **PLP `Nlift`** has no default in `Fx_PLPCC_htk.m`; the 22 here is HTK's.
- **Delta window N** is a free argument of `Deltacep` (DC:12); 2 is HTK's.
- **PLP LPC order**: 8 in MATLAB, 12 in HTK; ours 12 is unverified.
- **Whether the thesis uses deltas for PLP and MFCC-TMP** (all kinds produce
  39 dimensions by default here).
