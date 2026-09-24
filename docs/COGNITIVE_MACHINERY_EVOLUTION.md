# Evolvable cognitive machinery — foundation

Status: **DEVELOPMENT engineering design**, 24 September 2026. No scientific claim, no gate movement,
no V22/V22R/V23 result, and no change to the immutable trust root.

## Baseline before this line

This branch starts from main commit 1e3f81a148d41ca50665e29ab4502efb86174b3e, which merged the
identity-corrected retained-evaluator V22R replication apparatus.

At branch creation, active work already existed in PRs #332–#336 around V23 replay, repository/state
synchronisation, real-project gate hardening, and prospective L6–L8 RSI apparatus. This line is kept
orthogonal to those experiments. It does not edit their frozen evidence, select a V22/V23 outcome, or
reuse hidden observations.

The integrated runtime already has several prerequisites this line should preserve rather than
rebuild:

- immutable genesis.trust_root separated from mutable Genesis;
- persistent generated program bodies and interpreter-form migration;
- search-policy and MetaPolicy evolution;
- recursive research strategy;
- provenance classes distinguishing lineage-owned, host-written and model-mediated artifacts;
- explicit budget accounting;
- compute proxies that deliberately refuse to masquerade as energy measurements.

## Research question

Can Genesis improve the **machinery that produces cognition**, rather than only search for a better
program inside fixed machinery, while remaining externally measurable and resource-bounded?

The target is not “a larger Transformer”. A Transformer, state-space model, recurrent network,
memory system, router, symbolic module, mixture of specialists, or a future mechanism without a
current name should all be representable as possible descendants. Architecture family must therefore
be mutable data rather than a hard-coded design decision.

A later experiment should optimise a frontier such as:

    capability / reliability / transfer
                   versus
    measured compute / latency / memory / energy when actually instrumented

No scalar “intelligence score” or energy estimate is introduced in this foundation.

## Increment 0 — canonical cognitive architecture genome

The first implementation is intentionally small: genesis/cognitive_architecture.py.

It adds a canonical, content-addressed graph representation with:

- externally admitted primitive identifiers rather than a fixed neural family;
- complete configuration included in identity;
- explicit feedforward and recurrent edges;
- acyclic within-step feedforward dependencies;
- recurrent loops permitted only when declared as such;
- optional externally imposed node/edge bounds;
- deterministic structural profiling;
- no execution, learning, mutation search, or adoption yet;
- no FLOP, watt, energy, latency, parameter-count or intelligence inference from topology.

This is an IR, not a model.

The important design choice is that primitive semantics live outside the genome. Genesis can later
change topology and select among admitted primitives without this module deciding that attention,
recurrence, SSMs, memory, routers or symbolic operators are the privileged substrate. A later
primitive registry/executor can itself become an evolvable lineage artifact only after its authority
and measurement boundaries are explicit.

## Boundary that must not move

Mutable Genesis may eventually change:

- topology;
- primitive selection;
- memory layout;
- recurrence;
- routing;
- learning/update rules;
- mutation operators;
- architecture search policy;
- allocation of its own admitted compute budget.

It must not gain authority over:

- hidden/fresh evaluation cases;
- correctness grading;
- final accept/reject;
- resource ceilings;
- measurement provenance;
- evaluator identity;
- rollback / integrity checks.

Those remain external or trust-root-governed.

## Planned increments

### Increment 1 — executable primitive registry

Add a tiny deterministic executor for a deliberately small primitive catalogue. The catalogue should
include structurally different mechanisms, for example feedforward transform, state cell, gated
router and memory read/write, so architecture search is not merely tuning layer counts.

The executor must expose exact runtime observations. CPU time remains a compute proxy, never energy.
Actual energy enters only when an external meter or trustworthy host telemetry is available.

### Increment 2 — bounded architecture mutations

Introduce canonical mutation intents such as add/remove node, add/remove edge, replace primitive and
change configuration. Every mutation receives externally imposed size and evaluation budgets.
Mutation identity and parent identity are journalled.

Do not allow arbitrary Python rewriting as the first architecture mutation mechanism.

### Increment 3 — lineage-held architecture search

Let a lineage-held policy propose architecture mutations from admitted evidence. Candidate
architectures execute in isolation and the unchanged evaluator compares them with the parent under
matched budgets and fresh holdout tasks.

Selection should preserve a Pareto view rather than reward capability at any compute cost.

### Increment 4 — resource-aware causal adoption

Require an adopted architecture to carry independently measured capability and resource evidence.
Where energy cannot be measured, say so; do not substitute an invented conversion from CPU seconds.

Run ablations to distinguish “new topology caused the gain” from noise, larger budget, or a changed
evaluation path.

### Increment 5 — mutate the mutation machinery

Only after architecture descent works, make the operators/search strategy themselves lineage-held and
content-addressed. A descendant may then improve how Genesis changes architectures, while the trust
root still decides whether that meta-change produced better externally measured descendants.

### Increment 6 — world/curriculum factory

Add a separate environment generator that produces new externally verifiable pressures near the
current capability frontier. Keep generation seeds, verifiers and hidden evaluation inaccessible to
the organism being judged.

This is where open-ended pressure can begin without turning the evaluator into mutable Genesis.

## What would count as progress

A meaningful future result is not “Genesis generated a novel graph”. It should demonstrate at least:

1. a descendant architecture differs materially from its parent;
2. the difference is lineage-produced and survives restore;
3. it improves fresh capability or the capability/resource frontier under matched external budgets;
4. the gain disappears or weakens under an appropriate causal ablation;
5. later descendants inherit and build on the acquired machinery;
6. the evaluation/root-of-trust bytes and hidden cases remain outside the lineage.

Until those hold, this remains DEVELOPMENT apparatus.
