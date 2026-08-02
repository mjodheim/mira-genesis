# M026 — Decidable metaproductivity guidance development result

**Status: DEVELOPMENT — PRE-WRITTEN HGM-INSPIRED ADVANTAGE NOT SUPPORTED**

This is a development result, not a canonical validation and not a reproduction of
DGM or HGM.

## Identity

- evaluated implementation commit:
  `3fa79d264c125be3e73f2751298cbd430109eb8a`;
- protocol version: `M026-development-v1`;
- frozen protocol SHA-256:
  `5df38412a6abe762e9ab5c43bfbca511cb5e9d49760b4267375dd19b9ab5c671`;
- result artifact SHA-256:
  `9b288557571aafb450fbe891c7a0d4a74c95513e86fdf516915774652cf32289`;
- 64 paired seeds, 512 trajectories and 20,480 completed expansions;
- local runtime: Python 3.14.6, four worker processes;
- a second complete four-worker run produced the identical artifact hash;
- 18 focused tests, 123 repository tests and the repository integrity audit passed.

## Pre-written decision

The HGM-inspired policy advantage required all of the following:

1. median paired final hidden quality at least 167 per mille above the DGM-inspired
   policy;
2. at least 40 HGM-inspired wins among 64 mismatch seeds;
3. exact visible/hidden equality throughout the aligned control;
4. passing structural, isolation and reproducibility guards.

The first two requirements failed. The latter two passed.

## Primary result

| Mismatch metric | DGM immediate | HGM clade | Uniform | Oracle-guided control |
|---|---:|---:|---:|---:|
| Median final development quality | 833 | 833 | 833 | 1000 |
| Median final hidden exact quality | **0** | **0** | **0** | 1000 |
| Median best hidden quality found | 166 | 0 | 166 | 1000 |

The paired HGM-minus-DGM final hidden difference had median **0 per mille**. HGM won
4 seeds, tied 59 and lost 1; the pre-written rule required 40 wins. The non-ties were
three +500 results, one +166 result and one -500 result.

The final hidden distributions were:

| Policy | 0 | 166 | 500 | 1000 |
|---|---:|---:|---:|---:|
| DGM immediate | 63 | 0 | 1 | 0 |
| HGM clade | 60 | 1 | 3 | 0 |
| Uniform | 58 | 0 | 6 | 0 |
| Oracle-guided control | 0 | 1 | 5 | 58 |

The prediction is therefore rejected for these two adaptations under this fixed
40-expansion process.

## Controls

The positive structural control passed before either run:

- the platform state has 0 immediate development successes;
- a shortcut has 1 immediate development success;
- the platform's exact best reachable rooted-clade hidden quality is 6/6;
- the shortcut's exact best reachable rooted-clade hidden quality is 3/6.

The aligned negative control was exhaustive over every reachable state. Development
and hidden exact quality were equal for every state, and all 256 aligned run rows also
returned equal final development and hidden quality.

Every selector-facing record omitted hidden and exact fields. All selection traces
used integer decisions. Every trajectory completed exactly 40 expansions and produced
41 archive nodes.

## Interpretation

M026 establishes a decidable Metaproductivity–Performance Mismatch in its positive
control, but it does **not** establish that observed clade aggregation alone overcomes
that mismatch. In this sparse-reward rewrite tree, the clade estimator receives no
positive evidence until search has already seeded and extended the platform lineage.
Without that evidence, it cannot infer the lineage's exact latent potential.

This is the useful negative result: replacing immediate performance with observed
clade performance is insufficient when the expansion process rarely reveals the
productive descendants that would make the clade estimate informative. A successor
would need a pre-written exploration or evaluation intervention, not a relaxed outcome
threshold.

M026 deliberately held HGM's evaluation scheduler, expansion generation, asynchronous
execution and best-belief final selection out of scope. The result consequently says
nothing about full HGM, its published SWE-bench evidence or general HGM-versus-DGM
performance.

## Oracle-label correction

The frozen protocol called `oracle_descendant` a ceiling. The implementation grants it
exact hidden rooted-clade quality for **parent selection** but preserves the same
deterministic next-action order as every other policy. It reaches 1000 per mille in
58/64 seeds, not 64/64. It is therefore an oracle-guided positive control, not a strict
per-seed upper bound. This interpretation correction was made after observing the full
run; the evaluated implementation and frozen protocol were not rewritten.

## Conclusion

The first literature-facing benchmark is complete as a reproducible development
failure. It supplies an exact finite counterexample to immediate-performance guidance,
an exhaustive no-gap control, and a negative test of clade aggregation without HGM's
other scheduling mechanisms. No canonical or system-level self-improvement claim is
made.
