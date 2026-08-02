# Changelog

## 0.18.0 — 2026-08-02

- Added M028's finite adaptive evaluation-weighting comparison over the common M027
  breadth-seeded archive.
- Preserved the 64-seed negative development result: adaptive allocation improved
  clade/exact-CMP concordance by only 40 per mille, produced no median hidden-quality
  advantage and returned 2 wins, 60 ties and 2 losses against uniform allocation.
- Recorded 256 trajectories, 30,720 expansions, 92,928 unique evaluations and a
  byte-identical replay without exposing hidden fields to either selector.
- Localised the next measurement failure: performance-adaptive weighting can sharpen a
  misaligned proxy while allocating less evidence to high-potential lineages.

## 0.17.1 — 2026-08-02

- Hardened human-only attribution with exact registered identities and a trusted-base
  pull-request check that never executes proposed code.

## 0.17.0 — 2026-08-02

- Added M027's hidden-blind exhaustive coverage through the first reward-bearing depth.
- Preserved the 64-seed negative development result: exposing productive descendants
  did not align the unweighted clade estimator or improve final hidden quality.
- Added permanent human-attribution rules and pull-request checks for commit authors,
  committers, co-authors, branch names, titles and descriptions.
- Removed historical automated inline-review comments and neutralized the submitted
  review summaries that GitHub does not permit the repository owner to delete.

## 0.16.0 — 2026-08-02

- Added M026, the first direct literature-facing benchmark, with explicit mappings to
  DGM, HGM and SGM and equally explicit non-reproduction boundaries.
- Added an exact finite performance/potential reversal, an exhaustive aligned control,
  selector isolation, fixed-point stochastic policies and four-worker replay.
- Preserved the 64-seed negative development result: HGM-inspired clade aggregation
  did not beat DGM-inspired immediate guidance under the fixed expansion process.
- Recorded the frozen implementation and protocol identities, the reproducible
  512-run artifact hash and a byte-identical full replay.

## 0.15.0 — 2026-08-02

- Ran M021 across 24 paired seeds and preserved the development result: implemented
  selection measures produced different exact hidden transferred quality.
- Added M022's pre-written seed-0 positive and negative adaptation controls with full
  row-level evidence; cross-seed stability remains open.
- Hardened M023 so independent adoption fails closed when the parent workspace fails.
- Added M024's integrity-checked rewrite passport for the active body, rollback lineage
  and complete learned-tool registry.
- Added M025's transactional portable rewrite lifecycle. Rejection or exceptions now
  restore both the body and registry exactly; accepted state migrates, replays its
  learned transformation and survives forced rollback.
- Reconciled the public project narrative, state and roadmap in English and recovered
  the useful evidence that had existed only on stale local branches.

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
