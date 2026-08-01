# Changelog

## 0.14.0 — 2026-08-01

- Reoriented the project onto what its own failures identified: **when does a proxy
  measure stop tracking what it claims to track?** (D011, H9)
- Added `MEASURES.md`, a first-class register beside `FAILURE_LOG.md`, cataloguing six
  measures that came loose from what they claimed to measure — with ground truth.
- Made that catalogue executable: `scripts/reproduce_measure_failures.py` replays every
  case on demand.
- Replaced the probabilistic confirmation with an exact conformance test
  (`metamorphosis/conformance.py`). M017's "zero false successes" had been a favourable
  draw, not a guarantee.
- M017: all six freeze gates passed. The 50-environment sweep invalidated the proposed
  10× threshold and the criterion became directional.
- M018: hypothesis not supported — destroying does not restore improvement.
- M019: rig not valid — selection too impatient to value learning.
- M021 opened: do these selection measures move true quality?
- Parallelised the measurement scripts, verified bit-identical against the sequential
  outputs.
- Repository made public and translated to English (D012).

## 0.13.0 — 2026-07-31

- Consolidated the repository around living code only: retired the orphan M012/M013b
  stack, about 2,400 lines forming a disconnected import subgraph (D007).
- Added the first permanent CI and `scripts/check_repository_integrity.py` (D008).
- Fixed `pytest -q` and `pip install -e ".[dev]"`, both of which had never worked.
- M014c halted before evaluation and replaced by M017 — self-extending language (D009).
- D010: a measured quantity must have an established dynamic range.

## 0.12.0 — 2026-07-31

- Created the canonical repository.
- Consolidated Metamorphosis M001–M011.
- Added protocols, reports, aggregated results, tests and scripts.
- Created the state, hypothesis, decision and failure registers.
- Opened phase M012: autonomous morphogenesis.
