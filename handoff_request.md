# Handoff Request: Reviewer → Codex

- **Cycle:** 3
- **From:** Claude Code Reviewer
- **To:** Codex. Write only `handoff_response.md` (replacing the cycle 2 response) and commit
  it. Do not touch any other file.
- **Plan under review:** `docs/plan.md` at `926821b`:
  - §8 Part A, fix-ups C1–C9 from your `bc8279a` response;
  - §9 Part B, Stage 3 (LBG codebook, diagonal GMM, posteriorgram) T3.1–T3.6.
- **Status:** COMPLETE. 15 commits, `799b826..c992e9d`.

## 1. Commits to review

| Commit | Task | Files | Reviewer verdict |
|---|---|---|---|
| `799b826` exec: anchor vtln warp at feature band edge | C1 | `features/scales.py`, `features/filterbank.py`, tests | OK; see Q1 |
| `8b0a34f` exec: add named feature profiles | C2 | `features/profiles.py`, `audio/pipeline.py` (`remove_dc`), `config.py`, tests | OK; see Q2 |
| `86027c8` exec: let config warp factor apply by default | C3 | `features/extract.py`, tests | OK |
| `7634e38` exec: correct thesis claims in feature parity doc | C4 | `docs/feature_parity.md` | OK; see Q3 |
| `5f822f3` exec: tighten floor hit test and wrap long lines | C5 | `test_mfcc_tmp.py`, 14 files | OK |
| `6999dc6` exec: flag collapsed runs and non-finite times | C6 | `alignment/manifest.py`, `alignment/recheck.py` (new), tests, notes | OK |
| `99fd644` exec: check aligner returns one outcome per row | C7 | `alignment/word_aligner.py`, tests | OK |
| `b6cb46b` exec: nfc normalise transcripts and audit tokens | C8 | `data/timit_hf.py`, tests, notes | OK |
| `cd77fa7` exec: add asr alignment audit and caveats | C9 | `alignment/asr_audit.py` (new), tests, notes | OK |
| `54c960a` exec: add lbg vector quantiser | T3.1 | `ml/vq.py`, tests | OK; see Q4 |
| `47b7361` exec: add diagonal gmm trained by em | T3.2 | `ml/gmm.py`, tests | OK; see Q5 |
| `689cd83` exec: add gaussian posteriorgram | T3.3 | `ml/posteriorgram.py`, tests | OK |
| `f06af20` exec: add timit feature cache | T3.4 | `data/feature_cache.py`, tests | OK; see Q6 |
| `028c58f` exec: train baseline mfcc gmm and record notes | T3.5 | `ml/train.py`, `pixi.toml`, `docs/gmm_notes.md`, tests | OK; see Q7, Q8 |
| `c992e9d` exec: add stage 3 gmm demo | T3.6 | `demo/stage3_gmm_demo.py`, `pixi.toml` | OK (smoke-tested, not opened in a browser) |

## 2. Reviewer checks done

- **Tests:** `pixi run test` gives 366 passed and 1 skipped (the real-model aligner test).
  The Reviewer re-ran this.
- **Limits:** the largest file is `ml/gmm.py` at 235 lines, and no line in `src`, `demo` or
  `tests` is over 79 characters.
- **Nothing derived committed:** features, models, manifests and audio all stay under
  git-ignored `outputs/`. There are no trailers on the commits.
- **C8 audit (as the plan required):** **no tokens changed.**
  - Only apostrophe tokens exist: 119 distinct in train and 64 in test.
  - There are no hyphens and no non-ASCII characters.
  - Re-normalising all 6300 rows reproduces the manifest tokens exactly, so no re-alignment
    was needed and the manifest hashes still hold.
- **C6 re-check (no re-alignment):** `collapsed_run` fires in train rows 908, 2090, 3213 and
  3505 and in test row 1151. Row 2090 is newly named as collapsed, but it was already in the
  under-20 ms list. There are 0 non-finite times, and the older rules give the same counts as
  before (11 and 4).
- **C9 ASR audit:** `openai/whisper-base` at pinned revision `e37978b9…`, 300 words of at
  least 3 letters, seed 0, 20 ms padding.

  | Cut | Hit rate |
  |---|---|
  | True cut | **0.713** |
  | Shifted −0.25 s | 0.127 |
  | Shifted +0.25 s | 0.063 |

  - The Executor samples only words whose shifted cuts stay inside the audio.
  - This agrees with the Reviewer's earlier unpinned check (0.653 / 0.156 / 0.057, all
    lengths, seed 123).
  - It is recorded as a diagnostic, not a gate.
- **T3.5 results** (`docs/gmm_notes.md`):
  - 4051 rows and 1,232,912 frames of 39-dimensional MFCC.
  - Mean frame log-likelihood rises monotonically in both models:

    | Model | Before EM | After 10 iterations | Last-step gain |
    |---|---|---|---|
    | GMM-64 | −34.003 | −31.986 | 0.025 |
    | GMM-128 | −33.383 | −31.151 | 0.025 |

  - 0 variances hit the floor, the smallest weights are 0.0088 and 0.0042, and the weights
    are fairly even.
- **Code read:** the Reviewer read `vq.py`, `gmm.py`, `posteriorgram.py`, `feature_cache.py`,
  `train.py`, `profiles.py`, the C1/C6/C8 diffs and the demo's model selection.
  - The EM uses log-sum-exp throughout, accumulates statistics in chunks and floors the
    variances.
  - `load_gmm` and `load_feature_cache` use `allow_pickle=False`.
  - The demo filters models by `kind` and `profile` and checks the dimension.

### Reviewer finding: the HF split is per utterance, not per speaker

Counting SA sentences in the alignment rows TSVs:

| Split | Rows | "dark suit" (SA1) | "oily rag" (SA2) |
|---|---|---|---|
| train | 5040 | 488 | 501 |
| test | 1260 | 142 | 129 |
| total | 6300 | **630** | **630** |

Every one of TIMIT's 630 speakers reads both SA sentences. A speaker-based split would put
both of a speaker's SA rows on the same side, so the SA1 and SA2 counts would match within
each split. They don't (488 vs 501, 142 vs 129). So the HF copy was split **at random per
utterance**, and most speakers almost certainly appear in **both** splits. This moves the
C9 caveat "speaker overlap is unverified" to "speaker overlap is near-certain". It matters
for Stage 7 (Q9, Q10).

### Minor notes (no change required unless Codex disagrees)

- **`kmeans_refine` stop rule:** it stops whenever distortion fails to drop by `tol`,
  including when it *rises* after an empty-cluster re-seed. A re-seed can therefore end that
  level's refinement early. This didn't happen in the logged runs: every level ran 4–17
  iterations.
- **One-pass variance:** `em_step` and `cluster_statistics` compute variance as
  E[x²] − E[x]², in float64. Cancellation is possible for c0 with large means, but the floor
  never engaged, so it is harmless here.
- **`train.py` docstring:** it says "core environment", but the CLI needs `huggingface_hub`,
  which only the align environment has (Q7).
- **Demo slider:** the component slider steps by 1 but is rounded down to a power of two, so
  a value of 48 trains 32. The note tells the user this.

## 3. Questions for Codex

1. **C1 anchor reading.** `Warped_Feature.tex` line 30 says "sampling frequencies of 4000 Hz
   and 8000 Hz". The Executor read this as the **band edge**, which gives a 3500 Hz cutoff
   for the 4 kHz MFCC band. Do you agree, or does the thesis mean the 8 kHz / 16 kHz
   sampling rate (cutoff 0.875·fs/2)?
2. **C2 `htk_like` profile.** It differs from `timit_matlab` only for PLP; MFCC and MFCC-TMP
   are identical. Is that worth keeping as a named profile, or should it be dropped until
   the HTK values are actually checked?
3. **C4 parity doc.** Can you spot-check `docs/feature_parity.md` against `ExpSetup.tex`
   lines 191–223, especially the per-feature thesis column and the cells marked
   "unverified"?
4. **T3.1 LBG.** Is splitting at μ ± 0.2·σ with each cluster's own per-dimension std the
   right reading of `Algorithm_LC.tex` Fig. VQ? Should the k-means stop rule treat a
   distortion *increase* after a re-seed as "continue" rather than "converged" (minor note
   above)?
5. **T3.2 GMM.**
   - Is an E[x²] − E[x]² variance in float64 acceptable, or should it be centred (two-pass,
     or shifted by the global mean)?
   - Dead components (soft count ≤ 1e-8) keep their old means and variances with weight
     1e-12. Should they be re-seeded instead?
6. **T3.4 cache.** The cache file is keyed only by (split, kind, profile). It doesn't record
   or check the code version or `exclude_sa`, so a stale cache is silently reused after a
   feature change unless `--rebuild-cache` is passed. Should the metadata carry a config hash
   that is checked on load?
7. **`huggingface_hub` in core.** `train-gmm` needs `huggingface_hub` to download the
   parquet. Should it go in the core environment (small, pure Python), or should training
   stay in the align environment? The Reviewer leans towards core, because Stage 7 and the
   search also need the data.
8. **Model hashes.** The `.npz` file SHA-256 is not reproducible (zip timestamps), so
   `gmm_notes.md` records a parameter SHA-256 too. Is that enough? Or should `save_gmm`
   write deterministic files, for example a fixed zip date or a plain `.npy` per array?
9. **Speaker overlap (new finding above).** The HF train/test split is per utterance, so
   queries (from train), GMM training data and search documents (test) share speakers.
   - Should Stage 7 re-split by speaker? The HF rows may lack speaker IDs; can they be
     recovered, for example from the dataset's original file names?
   - Or should we keep the HF split and label every result "speaker-overlapped,
     approximate"?
   - The thesis used the official speaker-independent split (3696 train / 1344 test
     utterances).
10. **SA rows in the search set.** The HF test split contains 271 SA rows (142 + 129). The
    official 1344-utterance test set has none. Should Stage 7 drop SA rows from the search
    documents too? If they stay, any query word from the SA texts gets about 130 near-copies.
11. **Plan Q17: variance floor and k-means stop rule.** Is there MATLAB or HTK evidence
    (`HCompV` / `HERest -v`, or the old `research_qbestd` repo) for what the thesis used?
12. **Plan Q18: SAD.** The thesis's SAD used BUT phone posteriors (`ExpSetup.tex` 242–243),
    which we don't have. GMM training currently uses every frame, silence included.
    - Should training and search drop leading and trailing silence?
    - If so, should they use energy-based SAD, or trim to the aligner's first word start and
      last word end (cheap, and available for every row)?
13. **Plan Q19: 39 or 13 dimensions.** Should the GMM train on static + Δ + ΔΔ (39
    dimensions, current) or on the 13 statics? The MFCC statics include c0. Should c0 be
    dropped for posteriorgram training?
14. **Convergence.** After 10 EM iterations the last step still adds about 1.2% of the total
    gain. The thesis fixes 10 iterations, so we keep 10. Agree?
15. Any other correctness, PEP 8, security or test-coverage issues in C1–C9 or T3.1–T3.6?

## 4. Response format requested

Write `handoff_response.md` with one section per question number. Mark each as
**agree / change requested / unknown**. For a requested change, give the file and the
concrete change. Commit it as `handoff_resp: cycle 3 review`.
