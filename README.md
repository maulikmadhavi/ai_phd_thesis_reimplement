# QbE-STD thesis reimplementation

Python reimplementation of the query-by-example spoken term detection (QbE-STD)
experiments from the PhD thesis (originally MATLAB). Goal: reproduce results
similar to those reported in the thesis.

## Stages

1. Audio processing base (I/O, resampling, framing, windowing, spectrum, energy)
2. Feature extraction (mel filterbank, MFCC, PLP, MFCC-TMP)
3. Machine learning (LBG VQ, GMM by EM)
4. Posteriorgrams (Gaussian, VTLN, mixture of GMMs)
5. Matching (DTW, subDTW, fastDTW, scoring)
6. Indexing / search-space reduction
7. Evaluation (p@N, MAP, MTWV, Cnxe)

## Usage

Environment is managed with [pixi](https://pixi.sh).

```
pixi run test                    # run the test suite
pixi run -e demo demo-stage1     # launch the Stage 1 Gradio demo
```

Dataset locations are read from `QBESTD_*` environment variables or a local,
git-ignored `paths.local.toml` (see `src/qbestd/config.py`). No data or audio
is stored in this repository.

## Layout

- `src/qbestd/` library code
- `tests/` unit tests
- `demo/` Gradio demos, one per stage
- `docs/` plan and reference notes, start with [docs/plan.md](docs/plan.md)
