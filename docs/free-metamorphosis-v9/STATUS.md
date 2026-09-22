# Genesis Free Metamorphosis V9 — current status

**Date:** 22 September 2026  
**Campaign state:** pre-first-observation protocol repair  
**Canonical V9 observations:** 0 / 24  
**Current continuation:** V9.1 tournament-rubric disclosure erratum

## What happened

V8 was closed after its post-mortem identified a routing bottleneck and a flaky harness condition. V9 was then seeded prospectively with a fresh hidden holdout and a corrective recursive-search control plane.

The first V9 external proposal was delivered for Attempt 001. Its artifacts were structurally valid enough to reach the deterministic tournament preflight, but the transcript selected a candidate that did not match the laboratory's frozen tournament recomputation.

Canonical workflow run `35718280644` stopped before evaluator entry. The exact failure was:

`ValueError: v9 transcript did not select deterministic tournament winner`

The failure occurred before the R4 evaluator image was restored. No hidden capability case was evaluated, no result branch was published, no A002 bundle was generated, and no V9 observation was spent.

## Root cause

The original A001 bundle told the proposer to use the frozen V9 tournament rubric but supplied only the evolver-profile weights, not the exact component formula. The proposer-side contract was therefore not information-complete under its own no-web/no-GitHub/no-memory boundary.

The control plane did its job by rejecting the mismatch before measurement.

## Continuation

V9.1 discloses the already-frozen scorer prospectively while leaving the evaluator, weights, seed state, hidden holdout and budget unchanged. The rejected proposal is not repaired or reused.

A fresh A001 proposer run must use the corrected content-addressed handoff documented in `ERRATUM_V9_1_TOURNAMENT_RUBRIC.md`.

Until that fresh output passes deterministic preflight, V9 remains at **0 / 24** observations.
