# M040 development amendment 002 — transported prefix plus one new operation

**Status: committed before implementation and before seed 400044 is evaluated.**

The exact-continuation mechanism succeeded on consumed seed `400042` but failed to define an
admissible post-migration task on consumed seed `400043`. The latter is retained in
`results/M040_DEVELOPMENT_003.md`.

## Question repaired

The transported continuation is now treated as a reusable causal prefix, not as an immutable
complete solution.

After migration and packet validation, the task generator:

1. selects a transported continuation prefix in task-seed order;
2. selects exactly one protocol-supplied primitive tool in task-seed order;
3. applies `prefix + primitive` to the migrated parent;
4. accepts the first result that is strictly larger, not reachable by the birth registry at
   the same total symbolic depth, and supported by an exact incapacity certificate.

Neither the selected suffix primitive nor the resulting target may appear in the packet.

## Complete arm

The complete migrated lineage evaluates each transported prefix and then enumerates one
protocol-supplied suffix. Its search cost includes every prefix symbol and every tested suffix.
The accepted proposal must:

- start with one of the packet's continuation prefixes;
- contain exactly one additional protocol-supplied tool;
- use at least one lineage-owned tool created before migration;
- pass exact equivalence and native re-synthesis.

## Controls

- Learning-state ablation receives the same body and registry but no prefix frontier. It must
  rediscover the full program by generic enumeration at the same total depth.
- Learned-tool ablation receives no lineage-owned prefix tool and must not solve under the
  same depth and node budget.
- Fresh and unchanged-parent controls retain only the birth registry.
- Output-only retains the exact migrated behaviour but no source rewrite state.

## Search depth and budgets

- Total post-migration symbolic depth: `3`.
- Prefix length: one or two tool symbols as transported by the packet.
- Adaptive suffix length: exactly one protocol-supplied tool symbol.
- Symbolic node budget: `20,000`, unchanged.
- Observation depth and native synthesis budgets: unchanged.

## Audit requirement

The independent M040 search auditor must record:

- every transported prefix expansion;
- every suffix primitive attempted after that prefix;
- every generic expansion in the memory-ablated and control arms;
- every invalid body, evidence rejection and exact evaluation;
- the accepted prefix/suffix boundary.

The audit transcript must reproduce engine counters, accepted IDs and verdicts exactly.

## Consumed identity

The first implementation of this amendment uses development seed `400044`.

Seeds `400040` through `400043` remain consumed for their respective mechanisms and may not
confirm this amendment.

## Scope

This remains a bounded transfer test. It demonstrates reuse of a previous transformation
strategy plus one new adaptation on a changed body. It does not demonstrate arbitrary
strategy invention or open-ended generalisation.
