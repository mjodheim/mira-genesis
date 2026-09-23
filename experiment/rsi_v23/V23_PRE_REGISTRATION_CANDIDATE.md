# RSI V23 — Recursive policy evolution pre-registration candidate

Status: **candidate frozen before the V22 result; implementation is conditional on V22**.

## Primary hypothesis H-V23

If V22 is positive, the acquired G2 exploration policy will produce a successor search policy G3
with higher fresh-holdout process utility than G2 under an equal proposal/evaluation budget, and a
matched G2-mechanism ablation will materially reduce that successor gain.

This is a stronger question than G3 > G2. The causal target is:

`G2 acquired mechanism -> better meta-search -> G3 -> fresh transfer gain`.

## Fixed comparison arms

- **A / G2-meta:** exact frozen G2 controls meta-search.
- **B / G1-meta:** exact frozen G1 controls the same meta-search.
- **C / G2-ablation:** G2 with the acquired stopping/continuation mechanism removed or reverted to
  its preregistered predecessor-equivalent behavior.
- **D / no-meta:** fixed candidate-order baseline with the same candidate/evaluator budget.

All arms use identical candidate generator version, public meta-development archive, evaluator,
hardware class, maximum represented requests and proposal model identity if a model is used.

## Editable object

Only the executable search-policy source may change. Candidates may modify parent selection,
parallelism, stopping, continuation evidence and budget allocation within the frozen ABI.

Candidates may not modify:

- meta-development worlds after freeze;
- holdout worlds;
- scoring/utility;
- policy loader/ABI guard;
- request accounting;
- evaluator;
- proposal model;
- hidden-test access;
- permissions or execution isolation.

## Two-timescale evaluation

### Fast loop — public meta-development

Candidate policies replay accumulated discovery trees and may receive cheap off-policy feedback.
This is development evidence only and selects the single G3 candidate.

### Slow loop — fresh online holdout

After G3 identity is committed, G3 and the baselines run on fresh tasks not present in the replay
archive. Those outcomes are never fed back into G3 construction.

## Required causal predicates

A positive V23 requires all of:

1. G3 is selected by the frozen meta-search, not by a human ranking candidates after inspection.
2. G3 fresh-holdout global utility is strictly greater than G2.
3. G2-meta discovers/selects a G3 with strictly greater holdout utility than the best successor
   produced by G1-meta under equal represented-request budget.
4. G2-ablation loses a preregistered amount of meta-search utility or fails to obtain the same G3
   identity within budget.
5. no old required capability regresses outside a preregistered tolerance;
6. replay-development gain alone is insufficient: all decisive comparisons use the fresh holdout;
7. all negative attempts remain in the archive.

Numeric margins, task count, task sources and budget must be frozen after V22 adjudication but
before any V23 proposer call, because those quantities depend on the measured V22 cost scale.

## Failure interpretation

- G3 > G2 but G1-meta finds the same G3: useful policy improvement, **not recursive attribution**.
- G2-meta wins development but not holdout: overfit meta-search.
- G2-meta beats G1-meta but G2-ablation is unchanged: attribution unresolved.
- G3 wins by changing evaluator/budget/accounting: invalid attempt, not positive evidence.
- no G3 improves G2 within budget: valid negative on this recursive step.

## Successor rule

Only a positive V23 may open L6 repeated meta-descent. A negative V23 must produce a successor
targeted at its measured failure class; it may not be relabelled as evidence of recursive
self-improvement.
