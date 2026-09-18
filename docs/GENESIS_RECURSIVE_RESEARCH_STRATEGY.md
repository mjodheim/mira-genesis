# Genesis recursive research strategy — DEVELOPMENT architecture

Status: **DEVELOPMENT**, 18 September 2026. This is engineering apparatus, not a scientific result,
not a rewrite of any frozen protocol, and not authority to consume a sealed or canonical evaluation.

## Purpose

Genesis already supports persistent body evolution, lineage-held search policy evolution, MetaPolicy
evolution, recursive transformation-language acquisition, causal journalling and process-death
recovery. The remaining weakness in the external cumulative-search line is one level higher:

> measured outcomes are retained, but the *strategy used to choose the next experiment* is mostly
> fixed by apparatus or rediscovered informally by each proposer.

This design adds a content-addressed, lineage-held **recursive research strategy**. The strategy
changes how Genesis allocates attention among hypothesis families and candidate experiments. It may
adapt from aggregate empirical outcomes, but it never receives evaluator internals and never decides
scientific acceptance.

The intended recursive chain is therefore:

```text
body
  -> search policy
    -> MetaPolicy
      -> transformation machinery
        -> research strategy
          -> next experiment choice
             -> external measurement
                -> research strategy descendant
```

The final measurement remains outside every mutable level.

## Authority split

The mutable research layer may read only inert admitted records:

- attempt identity;
- hypothesis family;
- targeted aggregate capability axes;
- declared mechanisms and changed architectural regions;
- hard-pass / hard-fail status;
- aggregate capability deltas;
- public improvement/regression labels;
- parent kind and neutral depth;
- content digests binding the exact result.

It may not receive:

- individual hidden cases;
- answer keys;
- grader state;
- evaluator source or control-plane internals;
- unrevealed sealed-bank material;
- host credentials;
- deployment authority;
- any ability to alter the trust root or scientific decision rule.

The record constructors use exact schemas and content digests. Extra fields do not survive
validation, so a caller cannot smuggle an evaluator hint into a nominally aggregate observation.

## Persistent research-strategy artifact

`genesis.recursive_research_strategy` introduces
`genesis-recursive-research-strategy-v1`.

A strategy contains:

- a bounded deterministic weight vector;
- a strategy generation;
- the exact parent strategy digest for descendants;
- the exact research-memory digest that licensed the adaptation;
- its own content digest.

The seed strategy is host-admitted prospectively. A descendant is lineage-owned and may replace the
held strategy only when it names the exact current strategy and the exact aggregate memory used to
derive it.

The same memory digest is idempotent: replaying identical evidence cannot repeatedly increase search
weights. New recursive depth therefore requires **new measured evidence**, not repeated invocation.

## Empirical memory and falsification

Each admitted outcome is assigned to a declared hypothesis family. The memory records, per family:

- attempts;
- zero-signal outcomes;
- promotions;
- regressions;
- hard failures;
- mechanisms already tried;
- architectural regions already changed;
- targeted axes;
- a bounded confidence value.

Two hard-pass zero-signal observations mark a family as empirically weakened. This is not a claim
that the hypothesis is false. It is a deterministic search heuristic saying that another near-copy
of the same causal mechanism has lower expected information value.

The strategy adapts by increasing weight on:

- architectural novelty;
- information gain;
- causal specificity;
- unresolved measured axes;
- safety after observed regression;

and by increasing the penalty for repeated zero-signal families.

## Pre-evaluation candidate tournament

Genesis may construct several **inert** candidate experiment descriptions before spending an external
evaluation. The tournament ranks them deterministically using only:

- new mechanisms;
- new architectural regions;
- whether the hypothesis family is new or empirically weakened;
- whether a candidate is a genuine mechanism pivot inside a weakened family;
- explicit causal claims;
- local validation checks;
- declared risk flags;
- unresolved aggregate axes;
- stepping-stone value of a depth-one neutral parent.

The tournament does **not** run the frozen external evaluator on multiple proposals and then select a
winner. There is still one external observation for the selected candidate. This preserves the
difference between better pre-experiment reasoning and result-shopping.

Candidate order is not selection authority: ties are resolved by canonical candidate digest, and the
test suite checks order invariance.

## Auto-recursive focus

The core recursive property is not merely that the system writes code which later writes code.
Genesis now has a path where empirical consequences can modify the machinery that chooses later
experiments:

```text
strategy S0
  -> chooses experiment E1
  -> aggregate observation O1

S0 + O1 + O2 ...
  -> evidence-backed strategy descendant S1
  -> S1 changes the ranking of later candidate experiments

new evidence
  -> descendant S2(parent=S1)
  -> later experiment choice
```

Every edge is content-addressed. A later audit can therefore ask whether an experiment depended on
the research strategy that existed at that point in the lineage.

This remains bounded recursion. The weight schema, adaptation rules, trust root and external
measurement authority are apparatus. Open-ended self-programming is not claimed.

## Local validation

Before a future external campaign spends an observation, candidate proposals should be able to
declare local checks such as:

- compilation;
- organism unit tests;
- deterministic round-trip tests;
- static authority-boundary checks;
- patch application checks;
- source-size and workspace limits.

These checks improve proposal quality but are not fitness and cannot promote a descendant.

A proposer sandbox may therefore include the language/toolchain needed to compile and run organism
tests while remaining offline and unable to inspect the external evaluator.

## Integration path

The DEVELOPMENT implementation is deliberately additive.

1. Keep all frozen V1-V6 records and controls immutable.
2. Exercise the recursive research strategy in ordinary CI.
3. Bind future external cumulative-search adapters to the exact aggregate outcome schema.
4. Pre-register the candidate-tournament and strategy-adaptation rules before any V7 proposal.
5. Freeze a V7 control head.
6. Only then run a new scientific campaign.

V6 should finish under its already-frozen rules. Its outcomes may later be imported only as explicitly
declared prior evidence if the V7 protocol prospectively permits that; they must not be silently used
to rewrite V6.

## Required regressions

The implementation must keep at least these properties green:

1. repeated zero-signal evidence can evolve the research strategy;
2. the descendant names the exact prior strategy and evidence-memory digest;
3. identical evidence cannot trigger a second strategy mutation;
4. new evidence can produce a second strategy generation;
5. tournament selection is invariant to authored candidate order;
6. a repeated weakened-family mechanism loses to a sufficiently novel architectural pivot under the
   admitted default strategy;
7. records with undeclared extra fields are refused;
8. no trust-root, frozen experiment or evaluator module is modified by this feature.

## Claim boundary

Passing these tests establishes only that Genesis has a persistent, evidence-adaptive experiment
selection mechanism whose own strategy can evolve recursively under a fixed authority boundary.

It does **not** establish that the strategy is optimal, that it can beat any particular champion, that
recursive improvement is open-ended, or that a later V7 scientific campaign will succeed.
