# Genesis Free Metamorphosis v7 — sanitized public protocol mirror

**Policy:** `GENESIS_FREE_METAMORPHOSIS_RECURSIVE_SEARCH_V7_2026-09-18`  
**Attempt budget:** 24 canonical observations  
**Frozen external authority:** not editable by the proposer

## Research question

v7 asks whether a bounded research strategy can use aggregate experimental evidence to change how it searches for later software improvements while evaluator authority stays external and frozen.

```text
aggregate observations
  -> empirical research memory
  -> content-addressed research strategy
  -> 4–6 inert hypotheses
  -> deterministic tournament
  -> one selected proposal
  -> frozen external evaluation
  -> retain / neutral frontier / reject
  -> new empirical memory
```

Every attempt declares 4–6 candidates with id, family, target axes, mechanisms, changed regions, causal claims, local checks and risk flags. The laboratory recomputes the tournament; only the deterministic winner may be evaluated.

Parent selection is frozen for causal isolation: odd attempts use the current champion; even attempts use a deterministic eligible neutral when one exists, otherwise the champion. Neutral depth is capped at 2.

A descendant becomes champion only if it improves at least one positive capability axis and regresses none relative to the current champion. Champion-equivalent hard-pass descendants may enter the bounded neutral frontier. Hard-boundary failures are rejected. Wall time is observational only.

## v7.1 proposer-information erratum

Before the next canonical A017 proposer run, the proposer-side information boundary must disclose the exact already-frozen deterministic tournament rubric. This is an information-completeness repair only: it changes no scorer, weight, memory, evaluator, parent rule, budget or prior measurement.

The exact rubric and A017 reconstruction check are recorded in [ERRATUM_V7_1_TOURNAMENT_RUBRIC.md](ERRATUM_V7_1_TOURNAMENT_RUBRIC.md). The laboratory continues to recompute the tournament independently before any external evaluation is spent.

## v7.2 research-history synchronization erratum

After canonical A018 completed its single frozen external evaluation, the laboratory discovered that the post-observation research refresh used unbounded aggregate history while the proposer context already enforced the frozen `MAX_HISTORY = 24` window. Crossing that boundary caused next-context generation to fail closed.

v7.2 synchronizes those two control-plane paths to the same 24-item history window. The A018 external evaluator was not rerun; scorer, fitness, strategy weights, parent selection and budgets remain unchanged. The full recovery boundary is recorded in [ERRATUM_V7_2_HISTORY_WINDOW.md](ERRATUM_V7_2_HISTORY_WINDOW.md).

## Strong cumulative criterion

Within the frozen budget:

1. at least two champion promotions;
2. at least one promotion causally through a previously admitted neutral;
3. at least one post-bootstrap proposal selected under a strategy descendant generated from new v7 evidence;
4. a later proposer bundle inheriting a promoted champion.

A neutral traversal does not satisfy condition 2 unless the descendant is actually promoted.

## Claim boundary

A positive v7 result may support only the bounded claim that an evidence-adaptive recursively mutable research strategy improved cumulative search on a frozen real-software surface while evaluator authority remained external.

It does not establish unrestricted recursive self-improvement, arbitrary self-rewrite, autonomous production deployment, evaluator self-modification, AGI or general intelligence.
