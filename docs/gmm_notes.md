# Baseline GMM notes (Stage 3)

MFCC, profile `timit_matlab` (16 kHz, 0-4000 Hz band, 26 filters, 13 cepstra
including c0, plus delta and delta-delta = 39 dimensions), diagonal GMMs with
64 and 128 components, trained on the Hugging Face TIMIT **train** split
without the two SA sentences. Nothing here is thesis-verified except the
settings listed under "Thesis facts".

## Thesis facts used

- Posterior `P(C_k|o_t) = pi_k N(o_t; mu_k, Sigma_k) / sum_j pi_j N(...)`
  (`ExpSetup.tex` 229-237); GMM estimated by EM from an LBG initialisation
  (line 238).
- LBG: K-means VQ, splitting constant 0.2, split at `mu +- eps * sigma` with
  the per-dimension standard deviation of the cluster (`Algorithm_LC.tex`).
- 10 EM iterations (`Representation.tex` lines 196 and 1089); 64 and 128
  mixtures for TIMIT (line 335).

## Assumptions (thesis silent)

- Diagonal covariances.
- Variance floor of 0.01 times the global per-dimension variance (HTK `vFloor`
  style). Open question 17.
- k-means inside LBG stops at a relative distortion change below 1e-3 or after
  20 iterations; an empty cluster is re-seeded by splitting the cluster with
  the highest distortion.
- Training on all 39 dimensions and on every frame, with no speech-activity
  detection (open questions 18 and 19). The thesis used BUT phone-posterior
  SAD, which we do not have.

## Data

| Item | Value |
|---|---|
| Dataset | `Siyong/speech_timit`, revision `ef7bffd88de7065b8b1c2fdc76e8364921c30e58` |
| Training rows | 4051 (5040 train rows minus 989 SA rows; the thesis used 3696 utterances of the official train set, so our set is larger because the split was redrawn) |
| Training frames | 1,232,912 (about 3.4 h at a 10 ms shift) |
| Features | 39-d float32, cached in `outputs/features/` (git-ignored) |
| Seed | 0 |
| Run | `pixi run -e align train-gmm --kind mfcc --profile timit_matlab --components 64` (and 128). The align environment is used only because it has `huggingface_hub`, which the core environment lacks; no torch code runs |

## LBG distortion (mean squared Euclidean distance per frame)

GMM-128 run (the GMM-64 run is the same up to size 64, since LBG is
deterministic):

| Codebook size | k-means iterations | Mean distortion at start | at end |
|---|---|---|---|
| 1 | 0 | 400.357 | 400.357 |
| 2 | 7 | 320.337 | 181.447 |
| 4 | 4 | 159.735 | 113.010 |
| 8 | 7 | 106.200 | 84.007 |
| 16 | 17 | 79.776 | 65.898 |
| 32 | 15 | 62.348 | 53.390 |
| 64 | 14 | 50.820 | 44.854 |
| 128 | 14 | 42.891 | 38.483 |

## EM log-likelihood

| Iteration | GMM-64 mean frame log-likelihood | GMM-128 |
|---|---|---|
| 0 (LBG init) | -34.0032 | -33.3825 |
| 1 | -33.3347 | -32.6367 |
| 2 | -32.8668 | -32.1283 |
| 3 | -32.5247 | -31.7703 |
| 4 | -32.3101 | -31.5456 |
| 5 | -32.1911 | -31.4017 |
| 6 | -32.1214 | -31.3085 |
| 7 | -32.0746 | -31.2495 |
| 8 | -32.0392 | -31.2081 |
| 9 | -32.0103 | -31.1766 |
| 10 | -31.9857 | -31.1511 |

Both curves rise monotonically and flatten: the last iteration still adds
0.025 (GMM-64) and 0.025 (GMM-128) per frame,
about 1.2% and
1.1% of the total gain, so
10 iterations are close to, but not fully at, convergence. The thesis figure
`LthetaConverge` was not compared numerically.

## Model summary

| | GMM-64 | GMM-128 |
|---|---|---|
| Final mean frame log-likelihood | -31.9857 | -31.1511 |
| Smallest component weight | 0.00880 | 0.00418 |
| Largest component weight | 0.02567 | 0.01799 |
| Variances at the floor | 0 of 2496 | 0 of 4992 |
| Wall time (feature cache already built for 128) | 102.5 s | 153.6 s |
| Model file | `outputs/models/mfcc_timit_matlab_gmm64.npz` | `..._gmm128.npz` |
| File SHA-256 | `114f8ca8c0df8f943694d0ebe38423bde6773010e40aede562f16593ddecbfc5` | `f0956010c1cdda0e300bf5a2255ef1afe02c1cc062806fc09b397a7c5e3ef7f8` |
| Parameter SHA-256 | `80a5b016398bd7e388ce2157465dd7ae55cb7d166ab492a2c2edd55f622603c1` | `c0e38a61730529dddcd5b33a8f84723b64b19a67f26d07edc619b505793a25b9` |

The **file** hash includes zip timestamps, so a re-run gives a different file
hash. The **parameter** hash covers the weights, means and variances as
little-endian float64 and is what to compare. It repeated exactly for two runs
in the same process (unit test); across machines or BLAS builds it may differ
in the last bits. The feature-cache build took about 2 minutes for 4051 rows
(first run only).

## What this does not show

- No comparison with the thesis figure and no held-out likelihood.
- No component-level inspection (what the components mean).
- Weights are fairly even (largest about 3x the smallest at 64, 4.3x at 128),
  so no component collapsed.
