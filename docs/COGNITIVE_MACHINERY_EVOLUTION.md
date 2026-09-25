# Evolvable cognitive machinery — foundation

Status: **DEVELOPMENT engineering design**, 24 September 2026. No scientific claim, no gate movement,
no V22/V22R/V23/V24 result, and no change to the immutable trust root.

## Baseline before this line

This line began immediately after the identity-corrected retained-evaluator V22R replication apparatus
was integrated. It is continuously rebased/merged forward onto the live scientific mainline without
editing frozen evidence.

At branch creation, active work already existed in PRs #332–#336 around V23 replay, repository/state
synchronisation, real-project gate hardening, and prospective L6–L8 RSI apparatus. Later V23/V24 work
has continued independently on main. This line remains orthogonal to those experiments: it does not
edit their frozen evidence, select an RSI outcome, or reuse hidden observations.

The integrated runtime already has several prerequisites this line should preserve rather than rebuild:

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

## Implemented increments

### Increment 0 — canonical cognitive architecture genome

`genesis/cognitive_architecture.py` provides a canonical, content-addressed graph representation with
externally admitted primitive identifiers, complete configuration in identity, explicit feedforward
and recurrent edges, acyclic within-step dependencies, optional external node/edge bounds and
deterministic structural profiling. It deliberately makes no FLOP, watt, energy, latency,
parameter-count or intelligence inference from topology.

### Increment 1 — executable primitive registry

`genesis/cognitive_executor.py` executes a deliberately small deterministic primitive catalogue under
an externally imposed node-execution ceiling. Recurrent state remains outside the genome. Actual CPU
process time is reported only as a compute proxy; energy remains unavailable unless it is independently
instrumented.

### Increment 2 — bounded architecture mutations

`genesis/cognitive_mutation.py` applies explicit externally chosen mutation intents and validates the
result against admitted primitives and externally supplied size bounds. Primitive/config replacement,
node addition/removal and edge addition/removal are implemented. Every applied mutation can emit a
content-addressed `MutationRecord` binding the canonical parent digest, proposal digest and child
digest. Input/output protection, admitted primitive constraints and node/edge ceilings fail closed.

Mutation policy, scoring and scientific selection remain outside this module; the mutation engine
therefore cannot decide that its own descendant is better.

## Boundary that must not move

Mutable Genesis may eventually change topology, primitive selection, memory layout, recurrence,
routing, learning/update rules, mutation operators, architecture search policy and allocation of its
own admitted compute budget.

It must not gain authority over hidden/fresh evaluation cases, correctness grading, final
accept/reject, resource ceilings, measurement provenance, evaluator identity, rollback or integrity
checks. Those remain external or trust-root-governed.

## Planned increments

### Increment 3 — lineage-held architecture search

Let a lineage-held policy propose architecture mutations from admitted evidence. Candidate
architectures execute in isolation and the unchanged evaluator compares them with the parent under
matched budgets and fresh holdout tasks. Selection should preserve a Pareto view rather than reward
capability at any compute cost.

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

## What would count as progress

A meaningful future result is not “Genesis generated a novel graph”. It should demonstrate at least:

1. a descendant architecture differs materially from its parent;
2. the difference is lineage-produced and survives restore;
3. it improves fresh capability or the capability/resource frontier under matched external budgets;
4. the gain disappears or weakens under an appropriate causal ablation;
5. later descendants inherit and build on the acquired machinery;
6. the evaluation/root-of-trust bytes and hidden cases remain outside the lineage.

Until those hold, this remains DEVELOPMENT apparatus.
