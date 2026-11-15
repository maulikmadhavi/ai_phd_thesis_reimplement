# Handoff Response: Cycle 4

Scope: `handoff_request.md` at `d668cf9`. The present Hugging Face split is a useful baseline, but its sentence-text overlap makes its scores unsuitable as a thesis-parity claim. Keep the existing results and label any new split separately.

## 1. Q20 spoken instances — **unknown**

`Chapters/Unsupervised.tex:74` says all available training instances were considered (7–15 per keyword). It does not specify whether the final TIMIT p@N/MAP averages over instances or keywords, nor a score-fusion rule. The explicit multiple-example fusion discussion elsewhere concerns SWS 2013, so it does not establish TIMIT fusion. Keep each instance as a separate query in `src/qbestd/eval/run_timit.py`, report both instance and keyword averages, and do not describe either as the confirmed thesis aggregate. The 221 scored instances versus the thesis's 145 remain a protocol mismatch.

## 2. Q21 occurrences and relevance — **agree**

`Chapters/ExpSetup.tex:75,80` defines train as total query examples and test as total *occurrences*; `Table:TIMITdata` calls Occ. the total number of occurrences. Thus Occ. is a token count, not inherently a document count. Ranked retrieval is over utterances, so relevance remains binary per document, even if a word occurs twice in it. In the current HF test copy, exact-token occurrences happen to equal relevant-document counts for Q-20. The thesis does not specify stemming or morphological variants; keep exact normalized-token matching in `src/qbestd/eval/timit_queries.py` and mark variant inclusion unknown. Do not compare the present 52 document-keyword pairs with the thesis's 160 occurrences as though they were the same denominator.

## 3. Sentence-text overlap — **change requested**

Choose **(a)** as a separately named, text-disjoint sensitivity experiment. Keep the current HF results for auditability. In `src/qbestd/data/feature_cache.py` and `src/qbestd/eval/timit_queries.py`, create a deterministic non-SA split manifest that assigns every row of a normalized sentence text to one side, then use that same manifest for GMM training, query extraction, documents, and relevance. In `src/qbestd/eval/run_timit.py`, load and record the split identity, and fail when a model or manifest belongs to a different split. Add a test that train/test text sets are disjoint and row assignments are stable; report counts and scores in `docs/results_timit_q20.md` without replacing the HF baseline. Declare the split rule and seed before evaluating scores, and avoid selecting a split to improve a metric. This is *closer to the thesis protocol on sentence context*, not an official TIMIT reconstruction: speaker identities and the official partition are still unavailable. The [NIST TIMIT documentation](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir4930.pdf) confirms that the official train/test sentence texts are disjoint apart from SA.

## 4. Query feature extraction — **change requested**

Keep cut-clip extraction as the named primary baseline. In `src/qbestd/eval/run_timit.py`, add a separately selected full-utterance-feature slicing mode and run both on GMM-64 with the same split, alignments, relevance, and model. Record the mode in `summary.json` and compare p@N/MAP in `docs/results_timit_q20.md`. Slicing changes delta/delta-delta boundary behavior and possibly utterance-level normalization, so call this a sensitivity result, not a thesis-mandated correction. Run it after the text-disjoint experiment is defined; do not silently switch the primary result.

## 5. Path validity and utterance score — **change requested**

`Chapters/ExpSetup.tex:442–448` defines `dist(i)=S(i,N)/T(i,N)` and `wr(i)=(i-P(i,N))/N`, then accepts `0.5 <= wr <= 2`. Selection in lines 467–469 minimizes `dist` among valid endpoints within each path group. Hence validity uses test-frame displacement from `P`, not `T`; `T` normalizes distance. In `src/qbestd/search/subdtw.py`, change the current `(end-start+1)/N` to the thesis's `(end-start)/N` with the appropriate zero-based indexing conversion, and test the two boundary values. Keep the minimum normalized distance among valid endpoints for the one-best TIMIT utterance score. The C++ `argmin S` shortcut need not replace this rule: with LC2 every complete endpoint has `T=N`, so minimizing `S` and `S/T` agrees only over the **same candidate set**. Remove the silent invalid-path fallback; when no endpoint satisfies the constraint, return a clearly marked nonmatch or raise an explicit evaluation error, with a test. Existing runs report zero fallbacks, so this change should not be described as explaining their score gap.

## 6. Cache and model consistency — **change requested**

Yes, `src/qbestd/eval/run_timit.py` should reject a GMM whose metadata `kind`, `profile`, training feature fingerprint, or split identity conflicts with the requested evaluation. The model already stores `kind`, `profile`, and `feature_fingerprint` in `src/qbestd/ml/train.py`; compare them to the requested settings and corresponding training-feature identity before scoring, with a mismatch test. The train and test caches can have the same feature fingerprint while containing different rows, so split identity must be checked separately. Also make `src/qbestd/data/feature_cache.py` hash the relevant feature-extraction source files alongside its existing config, dataset revision, and explicit schema version, rather than relying on a remembered manual bump for algorithm changes. Use stable sorted paths and file bytes, and test that changing a relevant source digest invalidates the cache. Keep an explicit schema version for changes to the cache format.

## 7. Bootstrap uncertainty — **change requested**

The instance bootstrap treats repeated queries for one keyword as independent even though they share the same relevant set. In `src/qbestd/eval/metrics.py` (or a small evaluation helper), add a seeded bootstrap that resamples the 18 scored **keywords** and carries all of each selected keyword's instances together. In `docs/results_timit_q20.md`, report those cluster intervals for the instance-weighted and keyword-weighted estimates, identify the resampling unit, and retain the old interval only if explicitly labeled exploratory. For the GMM-128 versus GMM-64 comparison, bootstrap paired per-keyword score differences. An overlap of separate model intervals is not a test of their paired difference; none of these intervals cures the split mismatch.

## 8. GMM-128 thesis target — **change requested**

Yes. `Chapters/Unsupervised.tex:125–134`, `Tab:ExpResultTIMIT`, reports MFCC, GMM, LC2, **128 Gaussians: p@N 36.81 and MAP 38.34**. The matching 64-Gaussian row is 34.91 / 36.71. In `docs/results_timit_q20.md`, add the 128 target and correct the sentence saying no target is available; cite that table. Keep both targets labeled protocol references, not directly comparable to the current HF split. The thesis's 128-over-64 difference is +1.90 p@N and +1.63 MAP; the HF difference is +2.69 and +3.03, respectively, without implying parity.

## 9. Other issues — **agree**

The reviewer’s 457-passed/1-skipped result and code audit support the listed implementations. I found no additional concrete PEP 8, security, or test-coverage blocker in this scope. The remaining consequential correctness work is the split/provenance guard in Q3 and Q6, the endpoint semantics in Q5, and the comparison labels in Q7–Q8. Keep the first scores explicitly marked as affected by sentence-text overlap and by the 989-document/52-relevant-pair HF setup.
