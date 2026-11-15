# Handoff Response: Cycle 3

Scope: `handoff_request.md` at `821bca6`. This replaces the cycles 2/2b response. The answers distinguish thesis statements, public MATLAB variants, and choices made for the current Hugging Face TIMIT experiment.

## 1. VTLN cutoff anchor — **agree**

Keep the feature-band anchor introduced in C1. `Backmatter/Warped_Feature.tex:30` gives 3500/7000 Hz cutoffs paired with 4000/8000 Hz limits. Those limits cannot literally be sampling rates, since a 4000 Hz sampled signal has only a 2000 Hz Nyquist; read them as band edges/Nyquist values, corresponding to 8/16 kHz sample rates. Thus a 0–4000 Hz MFCC band uses the 3500 Hz cutoff. The missing `Fx_melfiltbank.m` still prevents a claim of exact MATLAB parity; `Fx_vtln_warp.m` itself anchors to the Nyquist of its `fs` argument.

## 2. `htk_like` profile — **change requested**

Remove `htk_like` from `src/qbestd/features/profiles.py` and its profile tests until an HTK configuration or HTK output is checked. Only its PLP settings differ, and a named HTK profile based on recalled defaults implies more evidence than we have. Keep the generic `PlpConfig` options for experiments and retain the documented, explicitly approximate `timit_matlab` profile.

## 3. Feature parity document — **change requested**

The per-feature summary in `docs/feature_parity.md` now tracks `Chapters/ExpSetup.tex:191–223`: MFCC has 26 filters, 0–4000 Hz and 13 coefficients; PLP has no stated count/band/c0/delta policy there; MFCC-TMP has 25/10 ms, 26 filters and 13 plus delta/delta-delta, with no band stated in that passage. HTK cells are marked unverified. Correct two remaining cells in that file: the `Fx_mfcc_lift.m` row places MATLAB's `Nlift=-20` in the **Thesis** column even though the thesis passage gives no lifter; and the **Thesis** cell for “Delta formula” says “same” although no regression formula appears in those lines. The DCT Type III wording and unresolved convention are appropriately flagged.

## 4. LBG split and stop rule — **change requested**

Using `mu ± 0.2 sigma` per dimension for each cluster is a reasonable reading of the VQ flowchart caption (`Backmatter/Algorithm_LC.tex`, Fig. VQ), though the caption does not specify the refinement stop rule. In `src/qbestd/ml/vq.py`, change `kmeans_refine` to stop only when the relative distortion **decrease** is nonnegative and below `tol`; an increase after empty-cluster reseeding must continue until recovery or `max_iter`. Add a targeted reseed/increase test in `tests/ml/test_vq.py`. The logged baseline runs did not hit this path.

## 5. GMM variance and dead components — **agree**

Float64 sufficient statistics with `E[x²] - E[x]²` are adequate for this baseline: both logged models improve monotonically, no variance reaches the floor, and no component is dead. A centred accumulation would be safer for much larger offsets, but adds another pass or more state without a demonstrated problem here. Keeping a dead component's parameters with a tiny weight is an explicit fallback, not evidence of a current failure. Log any future dead components; if they occur, compare reseeding or a smaller K before trusting a result.

## 6. Feature-cache identity — **change requested**

In `src/qbestd/data/feature_cache.py`, store a deterministic fingerprint of the full feature config (`get_profile(...).to_dict()`), dataset revision, `exclude_sa`, feature kind, and a manually bumped feature-algorithm/schema version. In `src/qbestd/ml/train.py`, pass the requested settings to a validating cache loader and rebuild or fail clearly on mismatch. Include a test that a changed config or `exclude_sa` cannot silently reuse a cache. A Git commit hash alone would invalidate it after unrelated documentation commits; the explicit algorithm version must be bumped whenever feature semantics change.

## 7. Training environment — **change requested**

Add `huggingface_hub` to the core dependencies in `pixi.toml` and update `pixi.lock`, since the feature-cache builder and later TIMIT search need it without torch. Then `pixi run train-gmm` should work as advertised, and `src/qbestd/ml/train.py` should no longer claim a core command that actually requires the align environment. Keep GPU/transformers dependencies isolated in `align`.

## 8. Model hashes — **agree**

The parameter SHA-256 in `src/qbestd/ml/gmm.py` identifies the exact weight/mean/variance bytes, while the file SHA-256 identifies the particular `.npz` artifact. Recording both plus the model metadata is sufficient. Different zip timestamps explain a file-hash change without a parameter change; bitwise parameter identity across GPU/BLAS environments is not guaranteed either. Deterministic zip writing or multiple `.npy` files adds complexity with no present benefit.

## 9. HF speaker overlap — **change requested**

The unequal SA1/SA2 train counts (488/501) prove the HF split is **not strictly speaker-independent**, assuming each of TIMIT's 630 speakers has both SA sentences: at least 13 speakers' SA utterances cross the split. Those counts alone do **not** prove a random split or that *most* speakers overlap. In `docs/data_notes.md`, `docs/alignment_notes.md` and the Stage 7 result notes, state this narrower finding and label HF results “speaker overlap present; approximate versus the thesis.” Do not infer speaker IDs from audio and silently re-split: the parquet rows lack identifiers, and an inferred split would not restore the official 3696/1344 non-SA partition or its query counts. If a reliable speaker manifest appears later, run a separately named speaker-disjoint sensitivity experiment.

## 10. SA rows in search documents — **change requested**

Exclude both SA sentence texts from **test documents** in the Stage 7 TIMIT loader/search manifest, using `normalize_transcript` and the existing `is_sa_sentence` logic in `src/qbestd/data/feature_cache.py`. Test the 271-row exclusion and retain row-index mapping for evaluation. `Chapters/ExpSetup.tex:73–75` says `/sa/` sentences are neglected, so leaving repeated SA documents would distort rankings and keyword counts.

## 11. Variance-floor and stopping evidence — **unknown**

The [HTK Book's HCompV example](https://labrosa.ee.columbia.edu/doc/HTKBook21/node28.html) uses `-f 0.01` to create a per-dimension floor of 1% of global variance; [HERest's `-v`](https://www.ee.columbia.edu/~dpwe/LabROSA/doc/HTKBook21/node166.html) instead sets an absolute minimum variance. These show that the chosen ratio is HTK-like, **not** that this thesis's standalone LBG-initialized GMM used it. `Chapters/ExpSetup.tex:229–238` and `Backmatter/Algorithm_LC.tex` do not state a variance floor or k-means tolerance, and the public `research_qbestd` tree contains matching code rather than a GMM training configuration. Keep both parameters marked unverified in `src/qbestd/ml/gmm.py`, `vq.py`, and `docs/gmm_notes.md`.

## 12. Speech activity detection — **change requested**

Do not silently trim GMM training or search to the forced aligner's first/last word: that alignment is approximate, word boundaries can cut weak consonants, and it would entangle the search baseline with alignment errors. Keep the current all-frame baseline. In the Stage 7 evaluation pipeline, add an **optional** energy-based SAD or padded edge trim as a named ablation, preserve original frame-to-time indices, and compare p@N/MAP before enabling it. The thesis used BUT CZ/HU/RU nonspeech phone posteriors (`Chapters/ExpSetup.tex:241–243`), which is a different detector; neither simple replacement should be called thesis parity.

## 13. GMM input dimensions and c0 — **agree**

Keep 39-dimensional MFCC (13 statics including c0, plus delta and delta-delta) for the baseline. `Chapters/Unsupervised.tex:113` explicitly describes 13 coefficients plus both derivatives for MFCC and PLP, and `Chapters/ExpSetup.tex:198` does so for MFCC-TMP. The thesis passages do not settle c0 versus log-energy for the reported HTK features, but the public `Fx_mfcc.m` retains DCT row 1 (c0). Record the current c0 choice and, once Stage 7 works, compare 13-static and c0-omitted variants as labeled ablations rather than changing the baseline now.

## 14. Ten EM iterations — **change requested**

Keep `n_iter=10` as the fixed baseline for reproducibility, but correct the evidence in `src/qbestd/ml/gmm.py` and `docs/gmm_notes.md`: `Chapters/Representation.tex:1089` states ten iterations for the **mixture-of-GMMs** experiment; the apparent ten-iteration sentence at `Representation.tex:196` is commented out in the source and does not establish the baseline GMM's count. The positive final-step gain means ten iterations are not full convergence. Label ten as an experimental choice informed by a related thesis setup, and optionally run a longer convergence sensitivity check without replacing the ten-iteration model.

## 15. Other correctness and coverage issues — **agree**

The main additional risk is the cache provenance mismatch in Q6; address it before Stage 7 so a model cannot be attributed to feature settings it did not use. `tests/ml/test_train.py` already checks that the parameter hash is deterministic and changes between distinct trained models. I found no further specific PEP 8, security, or test-coverage blocker in the listed commits. The reported 366 passing tests and the independent alignment audit support the completed scope, but do not establish thesis-level numerical parity.
