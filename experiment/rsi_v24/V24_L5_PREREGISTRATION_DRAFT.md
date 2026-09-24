# RSI V24 / L5 — semantic-bridge causal recursion draft

Status: **DEVELOPMENT DRAFT — NOT FROZEN — SCIENTIFIC ARMS MUST NOT BE RUN YET**

Date: 2026-09-24.

## Why V24 exists

The first prospectively frozen L5 attempt, V23, was negative before fresh holdout exposure.

V23 did find a strict public-development successor to G2 and that candidate passed the zero-tolerance
L4 retention gate. The causal predicate nevertheless failed because exact G2-meta and the narrow
G2 early-stop ablation selected the same successor with identical process utility. G1-meta reached the
same successor with fewer represented requests and rounds.

The failure is informative. V23 exposed exact G2 to a percentile-like tier quality whose best revealed
successor was still below G2's already-acquired strong-result threshold of 780. The L4 mechanism under
causal test therefore remained inactive in the meta-search where it was supposed to matter.

The fresh BrewTrack/Brewstead holdout was not consumed.

## V24 change: measurement interface, not G2

V24 does **not** lower or rewrite G2's thresholds.

The exact G2 program remains byte-identical. Its narrow causal ablation remains byte-identical except
for removal of the already-validated strong-result early-stop block: best >= 780 -> return [].

V24 changes only the controller-facing encoding of the already-public meta-development utility.

The complete V23 public development universe is partitioned relative to exact root G2:

- development utility strictly worse than G2: quality in **0..710**;
- development utility exactly equal to G2: quality **750**;
- development utility strictly better than G2: quality in **780..1000**.

Strict utility order is preserved inside the worse and better regions.

This gives the thresholds already present in exact G2 a direct successor-search meaning:

- <= 710: no successor yet; continuation remains promising;
- 711..779: neutral/root-equivalent region;
- >= 780: a strict public-development successor exists.

The bridge is computed from the complete public candidate universe before any meta-search traversal.
It consumes no fresh holdout outcome and does not affect final successor selection, which still uses
the original lexicographic public development utility.

## What remains unchanged from V23

The current V24 apparatus intentionally reuses, unchanged:

- exact G1 and G2 controller bytes;
- the finite depth-2 G2 descendant grammar;
- the complete 12-landscape public development population;
- equal external meta-search budgets: 9 represented requests, 8 rounds, parallelism 2;
- the four arms: G2-meta, G1-meta, G2 early-stop ablation, deterministic no-meta;
- mechanical successor selection by lexicographic development utility;
- zero-tolerance L4 retention;
- the still-unconsumed four-task BrewTrack/Brewstead fresh holdout.

No holdout execution is authorized by this draft.

## Intended causal criterion

For a later frozen V24 attempt, G2-meta must not win merely because the bridge makes its stop rule
fire. Its complete meta-process utility remains lexicographic:

(selected successor development utility..., -requests, -rounds).

Therefore an ablation that discovers a genuinely better successor defeats G2-meta regardless of
cost. G2-meta gains a causal process win only if the acquired stop mechanism reduces search cost
without sacrificing the selected successor's public development utility.

A positive L5 result would still additionally require:

1. G2-meta selects a strict public-development successor G3.
2. G3 passes zero-tolerance L4 retention.
3. On the still-fresh cross-stack holdout, G3 strictly beats exact G2.
4. On that same holdout, G3 strictly beats the successor selected by G1-meta.
5. G2-meta process utility strictly beats the exact G2 early-stop ablation.
6. all frozen identities remain unchanged and no holdout result enters construction or ranking.

## Freeze discipline

Before any call to experiment/rsi_v24/l5_meta_search.py::run_all(), V24 must gain a new freeze
record binding the bridge implementation, exact reused V23 apparatus identities, holdout identities,
budgets, tests, calibration records and this preregistration in final (non-draft) form.

Until then, only structural tests and bridge invariants may execute.
