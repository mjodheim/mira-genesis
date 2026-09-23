# RSI V23 — audit of recursive machinery already present on main

Status: **DEVELOPMENT apparatus audit, not a V23 result and not a V22 observation.**

## Why this audit exists

A September repository-consolidation review found that the old integrated-runtime PR #275 still
carried unique early implementations of generated bodies and policy replacement. Before porting that
code, the current `main` was checked for semantic successors.

The port should **not** proceed. Current `main` already contains substantially later machinery that
subsumes the relevant old mechanisms.

## What current main already has

### Generated bodies rather than catalogue-only selection

The controller exposes `GenerateTransform` and `genesis.programs` constructs bounded inert program
data under a fixed interpreter. The test suite includes generated-search and generated-restore
regressions. This is a later descendant of the older #275 `SearchTransform` / `program.py` design.

### Persistent search-policy evolution

Current `main` contains lineage-held search policies, canonical structural policy mutations and
evidence-backed policy updates. Candidate policies do not own the evaluator.

### MetaPolicy evolution

`genesis.meta_policy_evolution` can extend the machinery that exposes lower-level policy mutations
after the currently held MetaPolicy is empirically exhausted. Candidate descendants are evaluated
through the unchanged trust-root measure and selection requires a unique strict maximum.

The retained certificate explicitly records:

`counterfactual_meta_machinery_ablation_established = false`.

That field is important: the mechanism is stronger than a hand-coded one-step policy update, but its
own record does **not** claim the causal ablation V23 needs.

### Repeated retained meta descent

`tests/test_genesis_repeated_meta_policy_descent.py` exercises two consecutive objective-driven
transitions in one persistent campaign:

```text
MetaPolicy: M0 -> M1 -> M2
Search policy: P0 -> P1 -> P2
Body:        B0 -> B1 -> B2
```

The first objective makes adding `square` the unique useful MetaPolicy extension. The second retains
the first objective and makes depth growth the unique useful next extension, exposing
`square -> square`.

The regression checks:

- one persistent lineage;
- exact parent MetaPolicy identity for each descendant;
- retained old work;
- unchanged admitted source/trust root and evaluation contract;
- process-death restoration of the final MetaPolicy, search policy, body and retention corpus.

## What this does not establish

This is DEVELOPMENT fixture evidence. It does not establish the V23 hypothesis because:

1. the objectives and useful structural edits are project-authored;
2. the fixture is not a fresh online holdout;
3. there is no matched G2-meta versus G1-meta discovery comparison;
4. the MetaPolicy certificate itself says the counterfactual machinery ablation is unestablished;
5. two successful fixture transitions do not demonstrate open-ended recursive improvement;
6. the apparatus has not been tied prospectively to the real-project V22 transfer result.

## Consequence for V23

V23 should **reuse and test** this existing machinery rather than rebuild recursive policy evolution
from scratch.

If V22 is positive, the clean bridge is:

```text
V22: G1 vs G2 on fresh real-project repair processes
                 |
                 v
V23 meta-search: existing persistent policy / MetaPolicy machinery
                 |
                 +-- G2-meta
                 +-- G1-meta
                 +-- G2 acquired-mechanism ablation
                 +-- no-meta fixed-order control
                 |
                 v
           one frozen G3 identity
                 |
                 v
      fresh online cross-stack holdout
```

The decisive new evidence is therefore not “Genesis can mutate a MetaPolicy” — the DEVELOPMENT
apparatus already does that. The decisive evidence is **causal recursive attribution plus fresh
transfer**: the acquired G2 mechanism must measurably improve discovery of G3, G3 must beat G2 on
unseen tasks, and removing the acquired G2 mechanism must weaken that successor transition under an
equal external budget.

## Repository consequence

The old #275 branch remains useful provenance but should not be merged wholesale into modern main.
Its unique implementation is an ancestor of concepts now represented by later modules and tests; a
whole-file transplant would reintroduce older interfaces and duplicate `genesis.programs` /
`GenerateTransform`.
