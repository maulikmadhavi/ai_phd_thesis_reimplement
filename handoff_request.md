# Handoff Request: Reviewer → Handoff_feedback

- **Cycle:** 7
- **From:** Claude Code Reviewer
- **To:** Handoff_feedback, the independent reviewer (`requirements.md`, "Agentic handoff").
  Write only `handoff_response.md` (replacing the cycle 6 response) and commit it as
  `handoff_resp: ...`. Do not create or modify any other file, and do not take plan decisions
  in place of the Orchestrator. Mark anything that needs the user (data access, licence,
  scope, compute cost, choice of reference band) as **user decision**.
- **Plan under review:** `docs/plan.md` at `9b5ab71`, amended by `0962013` and `78129db`
  (H3 band comparison, a user request added after V3):
  - §8 Part A, review fix-ups F1–F5 (Handoff_feedback `0cb6983` Q1–Q3, Q7, Q8);
  - §9 Part B: L1 level-handling check, H1/H2 `htk_described` profile (user decision D2),
    H3 band comparison, V1–V3 Stage 4 GMM-VTLN code and an N_iter = 1 smoke run.
- **Status:** COMPLETE. 16 exec commits, `c429300..c027e05`. No STOP gate fired. No VTLN
  retrieval score was produced, as the plan requires.
- **Sources:** the thesis is at `D:\Storage\career_phd_daiict_work\Thesis`
  (`Maulik201121003.tex` and `Chapters/`). The old MATLAB code is at
  `D:\Storage\research_code_qbe_std`.

## 1. Commits to review

All in plan order (F1–F5, L1, H1, H2, V1–V3, smoke, H3).

| Commit | Task | Files | Reviewer verdict |
|---|---|---|---|
| `c429300` exec: record split v2 limits and corpus evidence | F1 | `docs/split_textdisjoint.md` | OK |
| `5a584eb` exec: pin row loop digest in a test | F2 | `data/feature_cache.py`, tests | OK |
| `8d16c98` exec: correct feature parity with thesis and author htk values | F3 | `docs/feature_parity.md` | OK |
| `a9f1fcc` exec: correct feature comparison wording | F4 | `docs/results_timit_q20_features.md` | OK |
| `19d186c` exec: close import closure finder and merge test gaps | F5 | `text_split.py`, tests, `gmm_notes.md` | OK |
| `e99d27e` exec: declare level handling check | L1 | results doc | OK: 07:08:24, before the run started (07:09:14) |
| `6f72775` exec: add level flip ablation profile | L1 | `profiles.py`, tests | OK |
| `f62d847` exec: run level handling check | L1 | results doc | OK |
| `cb24a64` exec: add htk described profile for mfcc and plp | H1 | `plp.py`, `profiles.py`, tests, parity doc | OK; see Q2, Q6 |
| `ab73b2f` exec: evaluate htk described profile on split v2 | H2 | results doc, `gmm_notes.md` | OK; see §2 provenance |
| `c782c6e` exec: add vtln warp factor estimation | V1 | `ml/vtln.py` (new), tests | OK |
| `09ff132` exec: add per warp feature caches | V2 | `data/warped_cache.py` (new), `feature_cache.py`, tests | OK; see Q8 |
| `9f2a036` exec: add iterative gmm vtln training | V3 | `ml/vtln_train.py` (new), `pixi.toml`, tests | OK; see Q3, Q8 |
| `3b94b58` exec: declare band comparison | H3 | `docs/feature_parity.md` | OK: 20:35:35, before the run started (20:36:03) |
| `be5c4f0` exec: add htk described 4k band profile | H3 | `profiles.py`, tests | OK |
| `c027e05` exec: compare 3400 and 4000 hz bands | H3 | results doc | OK; see Q5 |

## 2. Reviewer checks done

- **Tests:** `pixi run test` gives **626 passed, 4 skipped** (re-run by the Reviewer). The
  skips are the aligner download test and 3 parametrised `test_profiles.py` cases for
  profiles that are not defined for a kind (e.g. `mfcc_tmp` under `htk_described`).
- **Limits:** the largest module is `data/text_split.py` at 341 lines (`vtln_train.py` 247),
  and no line in `src/` or `tests/` is over 79 characters. No trailers on any commit. Nothing
  derived is committed.
- **Provenance:** each `summary.json` `git_commit` matches the start commit that the chain
  script wrote into its log:
  - L1: `6f72775` for both runs;
  - H2: `cb24a64` for all four, including the PLP GMM-128 re-run;
  - H3: `be5c4f0` for all four;
  - smoke run: `9f2a036`.
- **PLP GMM-128 re-run (H2):** the first eval died at query 120 at 08:32. It was re-run
  20:18–20:24 from the same model file.
  - The file's sha256 `ebc579f4…` equals the `file_sha256` in the training log and the JSON
    (08:23:02). The summary's `model_content_sha256` `e2bcd79b…` equals the JSON
    `content_sha256`.
  - No commit landed between `cb24a64` (07:36) and `ab73b2f` (20:24:40). The only
    uncommitted code at the time was the V1/V2 work. No eval imports the VTLN modules, and
    the V2 `feature_cache.py` change leaves the plain fingerprint unchanged
    (`warp_factor=None`). The test cache, built at 08:06, passed the fingerprint guard. So
    the result stands.
- **Fingerprints at HEAD still match the reference models:**
  - MFCC `htk_described` `ab3ef12487f2`, PLP `dc733b030de8`;
  - 4k: MFCC `cacb263d6c29`, PLP `56f4d6ed50e3`.

  `profiles.py` is not in the source digest; config values are in the payload instead.
  So the H2/H3 models and the smoke model (built from `mfcc_htk_described_gmm64`) pass the
  guard at HEAD.
- **Stale models (Executor note 1, confirmed):** `cb24a64` edited `plp.py`, which is in the
  shared `FEATURE_SOURCE_FILES` digest. So **every** model and cache made before it is now
  rejected by the guard, not only PLP:
  - `timit_matlab` MFCC (`200751d4…` → `f27d3c01…`), PLP (`81ab5664…` → `2c5bdcc2…`) and
    **MFCC-TMP** (`d4410351…` → `c0ed2bb7…`);
  - the L1 levelflip models.

  The `timit_matlab` features themselves are byte-identical (golden hashes in
  `test_profiles.py`). MFCC-TMP stays on `timit_matlab` for Stage 4, so it needs a plain
  GMM retrain (64 and 128) before its VTLN run. That is a compute cost for the
  Orchestrator's next plan.
- **`ROW_LOOP_SOURCE_SHA256` repin (Executor note 2):** justified. The `09ff132` diff only
  threads `warp_factor` into the config, the metadata and the output path. Rows, order,
  offsets and skips are unchanged, so `ROW_SELECTION_VERSION` stays at 1.
- **No `filter_scale` (Executor note 1):** correct. `plp.py` already used `mel_filterbank`
  before `cb24a64`. The PLP warp now anchors at `min(high_hz, Nyquist)` in both the
  filterbank and the equal-loudness centres, which is consistent.
- **"Commit as the run started" is not implemented in code** (plan §8 run rule):
  - `run_timit.py` line 270 calls `git rev-parse HEAD` **when the summary is written**, at
    the end of the run;
  - `train.py` and `vtln_train.py` model JSONs carry no commit at all;
  - nothing records a dirty working tree.

  The docs' "commit the eval started from" column is correct this cycle only because no
  commit landed mid-run. The only start record is a line the chain shell script writes into
  each log. See Q7.
- **Run rule breach (definition of done item "no commit while a background run is
  going"):**
  - the smoke run ran from about 20:27:55 (20:35:04 minus 429 s) to 20:35:04;
  - the Orchestrator's plan commits `0962013` (20:32:03) and `78129db` (20:32:18) landed
    inside that window.

  They are docs-only, and the smoke run reads no `plan.md`, so no result is affected.
  Every exec commit respected the rule. Stated for the record: the rule applies to every
  role.

### Results (instance p@N / MAP; thesis `Tab:ExpResultTIMIT`)

| Feature | GMM-64 `htk_described` | GMM-64 thesis | GMM-128 `htk_described` | GMM-128 thesis |
|---|---|---|---|---|
| MFCC | 34.58 / 35.73 | 34.91 / 36.71 | 38.04 / 39.87 | 36.81 / 38.34 |
| PLP | 34.34 / 35.88 | 35.50 / 37.58 | 38.33 / 39.73 | 37.30 / 40.18 |

- **Gaps to the thesis** lie between −1.16 / −1.70 (PLP 64) and +1.23 / +1.53 (MFCC 128).
  The Executor's message said "−0.3..+1.2 p@N"; the doc's gap table is the correct one.
- **Paired PLP − MFCC:** all intervals include 0, so no direction is claimed.
- **Paired 128 − 64:** excludes 0 in the thesis's direction for both features.
- **`htk_described` − `timit_matlab`:**
  - MFCC: −4.0 to −6.5, every interval excluding 0;
  - PLP 128: +5.8 to +7.5, excluding 0;
  - PLP 64: the intervals include 0.
- **L1 (level flip, `timit_matlab`, GMM-64):** all four paired flip − primary intervals
  include 0. PLP − MFCC with both flipped is −9.77 (−14.8 to −4.9).
- **H3 (0–4000 − 0–3400 Hz):**
  - point differences are positive in 6 of 8 rows for p@N and 8 of 8 for MAP;
  - the intervals exclude 0 in 10 of 16, with MFCC 64 instance p@N at a lower edge of
    "+0.0";
  - PLP 128 shows no difference;
  - 0–4000 Hz puts MFCC +2.6 to +4.6 above the thesis again.

### VTLN smoke run (N_iter = 1, MFCC `htk_described` GMM-64)

- **Runtime, memory and disk:** 429 s in total, of which the iteration took 127 s and the
  rest built 26 warp caches. Peak working set 1254 MB. `outputs/features` is now 5.0 GB.
- **Log-likelihood:** iteration 0 has the LL of λ_init on X^α̂ at −116.45 and the new model
  at −116.32 per frame. The plain model's last EM value was −116.77 on X^1.0.
- **Warp histogram (3696 train utterances):**

  | Warp | 0.88 | 0.90 | 0.92 | 0.94 | 0.96 | 0.98 | 1.00 | 1.02 | 1.04 | 1.06 | 1.08 | 1.10 | 1.12 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | Utterances | 380 | 57 | 209 | 74 | 253 | 110 | 765 | 619 | 429 | 220 | 282 | 227 | 71 |

  Below 1.0 the counts alternate, and 0.88 piles up at the edge of the grid.
- **Reviewer scratch check (not committed, no score):** per-frame LL against α for 300
  random train utterances (seed 0), under the plain GMM-64, from the existing warp caches.
  - **The curves are mostly smooth.** Only 7 % change slope sign 4 or more times, so a
    quantisation zigzag is at most a minor part.
  - **There is a local bump at α = 1.00.** Many curves dip at 0.96–0.98 and rise again at
    1.00, as expected in iteration 0, because λ_init was trained on unwarped features. This
    suppresses 0.98 and explains part of the alternation.
  - **About 12 % of utterances (35 of 300) rise steadily towards 0.88**, the edge of the
    grid. A few rise steadily towards 1.12.
  - The mean curve over the 300 peaks at 1.02 (+0.02 over 1.00), falling to −0.97 at 0.88
    and −1.37 at 1.12.
  - Argmax counts in the sample: 35 / 3 / 13 / 12 / 18 / 9 / 59 / 46 / 29 / 23 / 24 / 22 / 7.
- **Filterbank geometry:** 40 filters in 0–3400 Hz on a 512-point FFT (31.25 Hz bins). The
  lowest filters cover only 1–3 bins. The first filter covers 1 bin for every α < 1 and 2
  bins for α ≥ 1. The filter area scales roughly as 1/(2−α), from 0.87 to 1.14 for the first
  filter. The band starts at 0 Hz with no DC removal.

## 3. Questions for Handoff_feedback

1. **Plan Q31: level check.** L1 shows no measurable change from flipping level handling,
   and PLP − MFCC stayed strongly negative under `timit_matlab`. Is the doc's reading
   ("this check shows no change in either feature") right? Should MFCC-TMP's level handling
   stay as it is? Now that `htk_described` closes the gap for MFCC and PLP, is there
   anything left to learn from `timit_matlab`, or should it stay as a labelled earlier
   reference only?
2. **Plan Q32: HTK defaults.** Check the recalled HTK values in `_htk_described`
   (`profiles.py`):
   - pre-emphasis 0.97, lifter 22, LPC order 12, compression 0.33, delta window 2 and
     `ZMEANSOURCE` off;
   - MFCC on magnitude, PLP on power;
   - our `log((M|X|)²)` against HTK's `log(M|X|)`, a factor 2 on every cepstrum;
   - HTK's DCT scales c0 by `sqrt(2/N)` against our orthonormal `sqrt(1/N)`.

   Known differences not listed in the docstring, to confirm or reject:
   - HTK pre-emphasises per frame, after framing;
   - HTK's filterbank skips the DC bin (`klo = 2`);
   - HTK PLP has its own internals: the IDFT of the auditory spectrum, and edge-band
     handling.

   A diagonal GMM with EM is invariant to per-dimension scaling, but our LBG
   initialisation uses Euclidean distance. So the c0 `√2` factor can change the
   initialisation slightly, while the uniform ×2 cannot. Is that worth a note?
3. **Plan Q33: VTLN assumptions.**
   - Fresh LBG + EM per iteration, against a warm start from λ_init: which matches the
     thesis's "build"?
   - Should query clips get their own α̂ (as implemented, `estimate_clip_warp`) or inherit
     something else? The thesis's queries are cut from test utterances; inheriting the
     document's α̂ would also be possible.
   - `vtln_train` saves only the histogram, not the per-utterance α̂. Should it save
     α̂ keyed by `(hf_split, row)`, so that later "inherit" options and analyses need no
     re-estimation?
4. **Plan Q34: smoke run and warp grid.** 26 caches (13 warps × 2 HF splits) for one kind
   and profile take about 300 s and about 3 GB. MFCC, PLP and MFCC-TMP together would be
   about 9 GB. Is the per-warp design acceptable?

   More importantly, given §2's histogram and scratch check, should anything change before
   VTLN scoring? In particular:
   - (a) about 12 % of utterances choose the 0.88 edge, rising steadily: grid too narrow,
     or a sign of something non-speaker in the lowest filters?
   - (b) the lowest filters cover only 1–3 FFT bins under this 40-channel, 0–3400 Hz bank,
     and their bin count changes with α;
   - (c) the α = 1.00 bump in iteration 0, which later iterations should reduce.

   Is any of these a **gating** question for Stage 4 scoring, or is it fine to proceed and
   report the histogram per iteration? (The thesis's own α̂ histograms, if any exist in
   `Representation.tex`, would be the comparison.)
5. **H3 band: reading and next step.** Is the doc's descriptive reading of H3 sound, given
   16 unadjusted intervals and lower edges of +0.0 to +0.6? The choice of reference band
   (0–3400 author-stated against 0–4000 thesis text) is a **user decision**. Can you say
   anything that would inform it without choosing by score? For example, which band the
   thesis's other experiments or `ExpSetup.tex` imply for the HTK runs. Note that 0–3400
   happens to land closer to the thesis's numbers; that must not be the reason for choosing
   it.
6. **Stale models and Stage 4 cost.** Is it acceptable that `plp.py`, part of the shared
   source digest, invalidated every `timit_matlab` model, MFCC-TMP included? Or should the
   digest be per kind, so that editing PLP code does not invalidate MFCC and MFCC-TMP
   caches? What is the smallest change, if any?
7. **Provenance code (§2).** Should `run_timit.py`, `train.py` and `vtln_train.py` capture
   the commit **and a dirty-tree flag** at process start, store them in the summary and
   model JSON, and refuse to start, or warn, on a dirty tree under `src/`? The plan's run
   rule currently rests on the chain script's log line.
8. **Other correctness, PEP 8, security or test-coverage issues** in F1–F5, L1, H1–H3 or
   V1–V3. Reviewer notes:
   - `ll_matrix_from_caches` fills `np.empty`. A key whose HF split is missing from
     `paths[alpha]` leaves an uninitialised value, which can be finite and so pass
     `estimate_warp_factors`. `np.full(..., np.nan)` would make that case raise.
   - The α = 1.00 warp cache duplicates the plain cache, with the same fingerprint and a
     different filename. It could be reused, saving 1 of 13 builds.
   - Name clash: the plain model JSON's `n_iter` means EM iterations (10), while the VTLN
     model JSON's `n_iter` means VTLN iterations (1). Rename the latter `n_vtln_iter`?
   - In H3, the MFCC 64 instance p@N interval is printed as "+0.0 to +5.9" and marked
     "excludes 0". Should the doc print two decimals where a bound rounds to ±0.0?
   - `estimate_test_warps` returns posteriorgrams for all documents at once (1344 arrays of
     (T, K)). Is that acceptable for memory next cycle, or should it stream?

## 4. Response format requested

Write `handoff_response.md` with one section per question number. Mark each as
**agree / change requested / unknown / user decision**. For a requested change, give the
file and the concrete change. Commit it as `handoff_resp: cycle 7 review`, push, and notify
the Orchestrator.
