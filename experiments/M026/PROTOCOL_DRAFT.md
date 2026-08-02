# M026 — Decidable metaproductivity guidance protocol draft

**Status: FROZEN FOR THE M026 DEVELOPMENT RUN. Not a canonical protocol.**

## Question

When immediate benchmark performance disagrees with exact hidden descendant potential,
does observed clade-level guidance discover a better final rewrite lineage than
immediate-performance guidance under the same finite expansion budget?

## Scope and naming

The compared policies are named `dgm_immediate` and `hgm_clade` because they adapt one
published parent-selection idea from each system. They are not reproductions of DGM or
HGM. M026 fixes every other major difference: one child is expanded and fully evaluated
per step, both receive the same finite cases and action orders, and final selection uses
the same visible development score.

## Finite rewrite domain

A node is a set of macros added to M017's primitive structural language. A task is a
finite sequence of structural atoms. A node solves a task when the exact minimum
description length in its current library is at most two symbols.

The evaluator can exhaust every reachable macro set up to depth five. It therefore
computes exact current hidden quality and exact best reachable rooted-clade quality,
including the clade root as in HGM's theoretical CMP definition. Public selectors
receive only node identity, ancestry, direct children and development-case success
counts.

## Positive mismatch control

- four generic motifs are locked behind one `platform` rewrite;
- six development cases contain every pair of generic motifs;
- six hidden cases reverse those pairs;
- the platform has zero immediate successes but can reach six hidden successes;
- each of six shortcuts immediately solves one development case but no hidden case;
- after consuming the shortcut's depth slot, at most three hidden cases remain
  reachable.

This creates a pre-written ordering reversal: immediate performance prefers a shortcut,
while exact descendant potential prefers the platform.

## Aligned negative control

Six generic motifs each solve one distinct development case and one distinct hidden
case. The two suites use different fixed context motifs, but every reachable node has
exactly equal development and hidden quality. A platform action consumes depth and
unlocks nothing.

Any reported visible/hidden gap in this control invalidates the rig.
The implementation enumerates every reachable aligned-control state when checking this
invariant.

## Policies

1. `dgm_immediate` — fixed-point λ=10, midpoint=.5 sigmoid of immediate development
   accuracy, divided by one plus the number of direct children;
2. `hgm_clade` — successes and failures aggregated over the observed clade, sampled
   through a reproducible 64-bit integer order-statistic analogue of Beta Thompson
   sampling;
3. `uniform` — uniform eligible-archive selection;
4. `oracle_descendant` — evaluator-only ceiling using exact hidden clade quality.

The oracle is a positive ceiling, never a deployable policy.

## Pairing and scale

- 64 paired seeds, numbered 0 through 63;
- 40 successful expansions per rig, policy and seed;
- identical task generator and deterministic per-node action order for each paired
  seed;
- no hidden field in the selector-facing dataclasses or function signatures;
- integer-only selection traces;
- four worker processes by default.

Below 64 paired seeds, output must say `insufficient_paired_seeds`.

## Prediction and decision rule

Written before the 64-seed development comparison:

- the positive control will expose the declared score/potential reversal;
- `hgm_clade` will exceed `dgm_immediate` on final exact hidden quality because it can
  credit productive observed descendants to an initially weak ancestor;
- the aligned control will retain exact equality between visible and hidden quality.

The HGM-inspired policy advantage is supported only if:

1. the median paired hidden-quality difference is at least **167 per mille**;
2. `hgm_clade` wins at least **40 of 64** paired mismatch seeds;
3. all aligned-control rows preserve exact visible/hidden equality;
4. every structural, isolation and reproducibility guard passes.

Failure of this rule rejects the prediction for these adaptations. It does not reject
HGM, whose full evaluation scheduler, asynchronous implementation, coding environment
and foundation-model expansion are outside M026.

## Prohibited conclusions

M026 cannot establish recursive self-improvement at software-engineering scale,
general superiority of HGM or DGM, statistical safety, autonomous diagnosis,
unknown-substrate migration, consciousness, AGI or open-ended improvement.
