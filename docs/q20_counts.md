# Q-20 counts: thesis against this reimplementation

Thesis table: `ExpSetup.tex` lines 78-97 (`Table:TIMITdata`). Ours: the
Hugging Face TIMIT copy. Label:
*speaker overlap present; approximate versus the thesis*.
Counts only; nothing here is audio or transcript text.

- Search documents: test split without the two SA sentences,
  **989** documents (1260 test rows minus the SA rows).
- Query instances: train split without SA rows, exact token match on the
  aligned word, padded by 20 ms and clipped. **251** usable
  instances; **2** more were skipped because their segment was
  flagged (under 20 ms or inside a collapsed run).
- "Test documents" counts documents containing the token at least once;
  "test token occurrences" counts every token.
- Keywords with no test document cannot be scored (p@N needs at least one
  relevant document) and are left out of the evaluation:
  simple, youngsters.
- Thesis Inst. is the number of spoken instances; whether thesis Occ. is a
  document or a token count is open question 21.

| Keyword | Thesis Inst. | Thesis Occ. | Our train instances | Our flagged (skipped) | Our test documents | Our test token occurrences |
|---|---|---|---|---|---|---|
| artists | 7 | 7 | 13 | 0 | 1 | 1 |
| beautiful | 3 | 8 | 9 | 0 | 2 | 2 |
| birth | 4 | 7 | 9 | 0 | 2 | 2 |
| destroy | 9 | 7 | 12 | 0 | 4 | 4 |
| development | 9 | 8 | 14 | 0 | 3 | 3 |
| garbage | 8 | 7 | 13 | 0 | 2 | 2 |
| government | 14 | 8 | 17 | 0 | 5 | 5 |
| intelligence | 8 | 7 | 10 | 0 | 5 | 5 |
| love | 4 | 16 | 18 | 0 | 2 | 2 |
| marriage | 3 | 7 | 9 | 0 | 1 | 1 |
| meeting | 7 | 7 | 8 | 2 | 4 | 4 |
| morning | 15 | 14 | 21 | 0 | 8 | 8 |
| ocean | 7 | 7 | 13 | 0 | 1 | 1 |
| organizations | 7 | 7 | 10 | 0 | 4 | 4 |
| problems | 5 | 7 | 10 | 0 | 2 | 2 |
| shellfish | 14 | 7 | 18 | 0 | 3 | 3 |
| simple | 8 | 8 | 16 | 0 | 0 | 0 |
| surface | 3 | 7 | 9 | 0 | 1 | 1 |
| tomorrow | 3 | 7 | 8 | 0 | 2 | 2 |
| youngsters | 7 | 7 | 14 | 0 | 0 | 0 |
| **total** | **145** | **160** | **251** | **2** | **52** | **52** |
