# Handoff Request: Reviewer → Handoff_feedback

- **Cycle:** 6
- **From:** Claude Code Reviewer
- **To:** Handoff_feedback, the independent reviewer that replaces Codex
  (`requirements.md`, "Agentic handoff"). Write only `handoff_response.md` (replacing the
  cycle 5 response) and commit it as `handoff_resp: ...`. Do not create or modify any other
  file, and do not take plan decisions in place of the Orchestrator. Mark anything that needs
  the user (data access, licence, scope, compute cost) as **user decision**.
- **Plan under review:** `docs/plan.md` at `dd8058b`, with status updated at `dc767a8`:
  - §8 Part A, provenance fixes and split v2: C1–C6 (Codex `ba99a8a` Q1, Q3–Q6);
  - §9 Part B, PLP and MFCC-TMP on split v2: P1–P3 (Codex Q2), plus `baa3bc3`.
- **Status:** COMPLETE. 10 exec commits, `3fb279d..ec565b5`. No STOP gate fired.
- **Sources:** the thesis is at `D:\Storage\career_phd_daiict_work\Thesis`
  (`Maulik201121003.tex` and `Chapters/`). The old MATLAB code is at
  `D:\Storage\research_code_qbe_std` and on GitHub (`requirements.md`).

## 1. Commits to review

Listed in `git log` order. C3 landed after C4, whereas the plan asked for C1 → C6 in order.
That is harmless: C3 still precedes every v2 model. `1286fad` and `0f513f4` are plan
commits (the role change), not exec.

| Commit | Task | Files | Reviewer verdict |
|---|---|---|---|
| `3fb279d` exec: correct results wording per cycle 5 review | C1 | `docs/results_timit_q20.md` | OK |
| `b57397b` exec: fingerprint row selection and resolve relative imports | C2 | `data/feature_cache.py`, tests | OK; see Q3 |
| `d6de36b` exec: count minimum cost assignments per component | C4 | `data/text_split.py`, tests | OK |
| `2a93634` exec: retrain hf gmms under row selection fingerprint | C3 | `docs/gmm_notes.md` | OK: HF hashes `80a5b016…` / `c0e38a61…` unchanged |
| `4e95d7e` exec: declare text disjoint split v2 with variant links | C5 | `data/text_split.py`, `data/text_variants.py` (new), tests, `docs/split_textdisjoint.md` | OK; see Q1, Q2 |
| `220d321` exec: evaluate q20 on text disjoint split v2 | C6 | `docs/results_timit_q20.md` | OK |
| `baa3bc3` exec: count teo floor hits in mfcc_tmp cache | P2 prep | `data/feature_cache.py`, tests | OK; committed by the coordinating session for the Executor, and the full suite was re-run here |
| `5145ced` exec: evaluate plp on text disjoint split v2 | P1 | `docs/gmm_notes.md` | OK |
| `9141edb` exec: evaluate mfcc tmp on text disjoint split v2 | P2 | `docs/gmm_notes.md` | OK |
| `ec565b5` exec: compare features on text disjoint split v2 | P3 | `docs/results_timit_q20_features.md` (new) | OK; see Q4, Q5 |

## 2. Reviewer checks done

- **Tests:** `pixi run test` gives **563 passed, 1 skipped**. The Reviewer re-ran this,
  including after `baa3bc3`.
- **Limits:** the largest module is `data/text_split.py` at 340 lines, and no line is over
  79 characters. There are no trailers on the commits.
- **Nothing derived committed:** the manifests, caches, models and eval outputs stay under
  git-ignored `outputs/`. The split doc holds hashes and single differing tokens, not
  sentence text.
- **Split manifests rebuilt independently:** the Reviewer ran
  `python -m qbestd.data.text_split --rule v1|v2` into scratch paths.
  - v1 is byte-identical, `ee27b531237a…`.
  - v2 is byte-identical, `0e913c50aae7…`, so `split_id`
    `textdisjoint_q20_v2-0e913c50aae7`.
- **v2 declared before any v2 model:** the doc commit `4e95d7e` is at 00:50:26. The first v2
  model file (`mfcc_timit_matlab_gmm64.npz`) is from 00:52:51.
- **v2 content** (`docs/split_textdisjoint.md`):
  - 20 links and 19 units, every unit exactly 7 rows, 0 rejected candidates;
  - all 20 keywords have cost 0, with counts unchanged from v1;
  - rows 3696 / 1344, the thesis counts;
  - the post-build scan finds 0 one-edit pairs across sides and 0 shared exact texts;
  - 36 rows changed side relative to v1.
- **Correction to the cycle 5 handoff:** the Executor is right. Of the 8 crossed pairs, the
  Reviewer's table listed "6 + 1 (×5)", but the data holds **four 6 + 1 pairs plus one 4 + 1
  pair** ("a"), as the Reviewer's own scan output showed. The total of 8, and the
  government, shimmered and 4 + 2 pairs, are as stated. The doc records this correctly; no
  change needed.
- **`baa3bc3`:**
  - it counts subband Teager sums ≤ `LOG_FLOOR` with the same `subband_teager_energies`
    that `mfcc_tmp` uses, and `log_compress` uses the same floor;
  - it raises on non-finite features;
  - it changes no rows or feature values, so not bumping `ROW_SELECTION_VERSION` is correct.

  Result: 0 floor hits in 32.1 M (train) and 7.9 M (test) values.
- **EM curves:** these rise monotonically for PLP and MFCC-TMP at 64 and 128. PLP has 4 of
  2496 (64) and 7 of 4992 (128) variances at the floor, read from the model JSONs. This is
  not in `gmm_notes.md`, which is a minor omission.
- **Results on v2** (p@N / MAP, instance average; all features use identical queries,
  documents and relevance):

  | Feature | GMM-64 ours | GMM-64 thesis | GMM-128 ours | GMM-128 thesis |
  |---|---|---|---|---|
  | MFCC | 40.02 / 42.23 | 34.91 / 36.71 | 42.94 / 44.96 | 36.81 / 38.34 |
  | PLP | 33.22 / 33.55 | 35.50 / 37.58 | 31.91 / 32.26 | 37.30 / 40.18 |
  | MFCC-TMP | 39.17 / 41.15 | 40.03 / 41.50 | 41.94 / 43.88 | not in thesis |

  - **Paired MFCC 128 − 64:** the interval excludes 0 on all four metrics, which is the
    thesis's direction.
  - **Paired PLP − MFCC:** the interval excludes 0 *against* the thesis's direction at both
    sizes and in both averages (e.g. −6.80 p@N at 64).
  - **MFCC-TMP − MFCC at 64:** −0.85 / −1.08, and only the keyword-averaged p@N interval
    excludes 0. The thesis's +5 gain is not reproduced.

### Reviewer observations on the results

- **Our MFCC is high and our PLP is low, against the thesis.** PLP at 64 is close to the
  thesis's PLP (33.2 vs 35.5), while MFCC is about +5 above the thesis's MFCC. So the
  inverted PLP − MFCC ordering comes at least as much from MFCC being high as from PLP being
  low.
- **One concrete PLP suspect:** the `timit_matlab` PLP profile has no DC removal and no peak
  normalisation, only `x·32768` scaling (`Fx_PLPCC_htk.m` line 69, adopted in cycle 3 C2).
  MFCC and MFCC-TMP are peak-normalised. So PLP's c0 carries the absolute recording level of
  each utterance, which differs between speakers and sessions. That could hurt KL matching
  across utterances. The PLP log-likelihoods are positive (25 → 28 per frame), so the PLP
  cepstra are on a much smaller scale than MFCC's. A cheap, untuned diagnostic would be PLP
  with peak normalisation, or with c0 dropped, as a named ablation (Q5).
- **Provenance timing:** the Executor's background chain ran while `baa3bc3` and `5145ced`
  were being committed. So the "commit of the run" column records whichever HEAD each run
  saw (`baa3bc3` / `5145ced`), not necessarily the code the run loaded. Between those commits
  only docs and the TEO counter changed, and the feature fingerprints pin the features, so
  the results are not affected. Worth knowing when reading that column.
- **Non-matches:** there is 1 each for MFCC GMM-128, MFCC-TMP 64 and MFCC-TMP 128 (a
  document shorter than about N/2 frames). They rank last and are counted, as A1 specified.

## 3. Questions for Handoff_feedback

1. **Plan Q27: link scope.** Is linking **every** verified one-edit variant pair (20, of
   which 12 never crossed in v1) the right reading of the cycle 5 request? The alternative
   was only the 8 that crossed. Are the filters and verification sound?
   - "0 rejected" rests on the 7-row check;
   - one 4-row group has two partners (1 and 2 rows), making 7;
   - one unlinked pair of two single-read groups remains.

   Link 19 is a content-word substitution (`had/ate`). Is the 7-row total enough evidence
   that it is a misreading of the same SX text?
2. **Plan Q28: underdetermined components.** "love, youngsters" has 15 of 512 cost-0
   assignments. Development and morning have 6, and beautiful and simple have 4. The chosen
   assignment rests on hash order alone. Is that a problem for the reported numbers? Should
   the doc say anything beyond the count, for example that p@N for those keywords depends
   on an arbitrary but fixed choice?
3. **Plan Q29: row-selection scope.** C2 adds a `timit_hf.py` digest, `SA_TOKENS` and a
   hand-bumped `ROW_SELECTION_VERSION` to the fingerprint. `baa3bc3` then edited the loop in
   `build_feature_cache`, correctly without a bump because rows didn't change. That shows the
   loop can change without the fingerprint noticing. Should `build_feature_cache`'s
   selection loop move into its own hashed module, or is the manual version enough?
4. **Plan Q30: front-end parity before VTLN.** PLP − MFCC goes against the thesis, with
   intervals excluding 0, and MFCC-TMP doesn't reproduce its +5 gain. Is a front-end parity
   check warranted before Stage 4 VTLN, or should VTLN go ahead on the same v2 setup? If a
   check is warranted, what is the smallest one?
5. **PLP level dependence (Reviewer observation).** Should a named, untuned PLP ablation
   (peak normalisation on, or c0 dropped) be run as a diagnostic? Or would that count as
   tuning towards the thesis? Does the thesis or the MATLAB code (`Fx_PLPCC_htk.m`, and any
   wrapper that calls it) normalise the waveform before PLP?
6. **MFCC above the thesis.** MFCC is about +5 above the thesis's figure at both sizes, with
   the thesis value inside the lower part of our interval at 64. Given that the split now
   matches the thesis's counts exactly, what remains as the most likely cause:
   - speaker overlap;
   - the 16 kHz input with a 4 kHz band;
   - c0 and the 39-dimensional choice;
   - the instance aggregation;
   - or noise?

   Is any of these checkable without speaker IDs?
7. **Wording.** In `docs/results_timit_q20_features.md`, rows are labelled "against the
   thesis's direction (interval excludes 0)". Is that wording, and the "no direction
   claimed" wording where the interval includes 0, consistent with the C6 rule? Should the
   doc add the observation that PLP is near its thesis value while MFCC is above its?
8. Any other correctness, PEP 8, security or test-coverage issues in C1–C6, `baa3bc3` or
   P1–P3? In particular:
   - the relative-import resolution in the C2 import-closure helper;
   - whether `text_variants.find_variant_candidates` handles a group with two partners
     deterministically.

## 4. Response format requested

Write `handoff_response.md` with one section per question number. Mark each as
**agree / change requested / unknown / user decision**. For a requested change, give the
file and the concrete change. Commit it as `handoff_resp: cycle 6 review`, push, and notify
the Orchestrator.
