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
- 64 and 128 mixtures for TIMIT (`Representation.tex` line 335).
- `Representation.tex` line 1089 states ten EM iterations only for the
  **mixture-of-GMMs** setup; line 196 is commented out. So ten iterations
  are **not** a verified thesis value for this baseline.

## Assumptions (thesis silent)

- Diagonal covariances.
- `n_iter = 10` is an **experimental choice** (see above and the 30-iteration
  sensitivity run below).
- Variance floor of 0.01 times the global per-dimension variance: HTK
  `HCompV`-style, **unverified for the thesis**. Open question 17.
- k-means inside LBG stops when the relative distortion *decrease* is in
  `[0, 1e-3)` or after 20 iterations; `tol = 1e-3` is **unverified**. A
  distortion increase (for example after an empty-cluster re-seed) does not
  stop it. An empty cluster is re-seeded by splitting the cluster with the
  highest distortion.
- c0 is **kept**: 13 cepstra including c0, as `Fx_mfcc.m` retains DCT row 1.
  The thesis does not state a c0 policy (open question 19).
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
| Run | `pixi run train-gmm --kind mfcc --profile timit_matlab --components 64` (and 128), from the core environment (it now includes `huggingface_hub`). Both models were re-trained after the k-means stop-rule fix and reproduced the earlier parameter hashes exactly |

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

## 30-iteration sensitivity run (GMM-64)

Same data, seed and settings with `--n-iter 30`; the 10-iteration model stays
the baseline. Model written to `outputs/models_30iter/` (git-ignored).

| Iteration | 0 | 5 | 10 | 15 | 20 | 25 | 30 |
|---|---|---|---|---|---|---|---|
| mean frame log-likelihood | -34.0032 | -32.1911 | -31.9857 | -31.9018 | -31.8564 | -31.8372 | -31.8223 |

Going from 10 to 30 iterations adds 0.163 per frame; iteration 30
still adds 0.0033. The curve flattens but has not fully converged.
This run was **not** used for any evaluation; whether it changes retrieval
is untested.

## Model summary

| | GMM-64 | GMM-128 |
|---|---|---|
| Final mean frame log-likelihood | -31.9857 | -31.1511 |
| Smallest component weight | 0.00880 | 0.00418 |
| Largest component weight | 0.02567 | 0.01799 |
| Variances at the floor | 0 of 2496 | 0 of 4992 |
| Wall time (feature cache already built for 128) | 109.7 s | 155.8 s |
| Model file | `outputs/models/mfcc_timit_matlab_gmm64.npz` | `..._gmm128.npz` |
| File SHA-256 | `d7abf929bd18dced0a6124789e54e38ec2710bbc232d45db836c0389ddf650c0` | `0c6d020063c4db3e40599f7f1b6584057dac23abf472ee2edbb90e7387e01b73` |
| Parameter SHA-256 | `80a5b016398bd7e388ce2157465dd7ae55cb7d166ab492a2c2edd55f622603c1` | `c0e38a61730529dddcd5b33a8f84723b64b19a67f26d07edc619b505793a25b9` |

The **file** hash includes zip timestamps, so a re-run gives a different file
hash. The **parameter** hash covers the weights, means and variances as
little-endian float64 and is what to compare. It repeated exactly for two runs
in the same process (unit test); across machines or BLAS builds it may differ
in the last bits. The feature-cache build took about 2 minutes for 4051 rows
(first run only).

**Cycle 5 retrain (A4).** After the source digest was added to the
feature fingerprint, both caches and both models were rebuilt. Feature
fingerprint `2c337a2602c49699416c0d75b1dc722c09e0f160047b074b9185fcc7f1f65df2`,
`split_id` `hf-ef7bffd88de7-nonsa`; the parameter hashes above are
**unchanged** (GMM-64 `80a5b016...`, GMM-128 `c0e38a61...`), so the front
end did not move.

**Cycle 6 retrain (C3).** After the row-selection identity (`timit_hf.py`
digest, `SA_TOKENS`, `ROW_SELECTION_VERSION`) joined the fingerprint, both HF
caches and both models were rebuilt. New feature fingerprint
`200751d44f47885af13b43dd16c2fed8a9361923d33620a8e47f36d9e8172c36`,
`split_id` `hf-ef7bffd88de7-nonsa`; parameter hashes **unchanged**
(GMM-64 `80a5b016...`, GMM-128 `c0e38a61...`), so no row or feature changed.

## What this does not show

- No comparison with the thesis figure and no held-out likelihood.
- No component-level inspection (what the components mean).
- Weights are fairly even (largest about 3x the smallest at 64, 4.3x at 128),
  so no component collapsed.
