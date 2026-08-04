# M040 development amendment 001 — causal continuation frontier

**Status: committed before the second M040 development run.**

The first development mechanism transported only a preferred-tool ordering. On consumed
seed `400040`, this did not help: the complete arm used 875 symbolic nodes and the
learning-state ablation used 873. See `results/M040_DEVELOPMENT_000.md`.

## Repair

The learning state is upgraded from a ranking to a causal continuation frontier.

For each accepted pre-migration cycle after the lineage-owned macro exists, the organism
records the exact ordered tool-ID sequence from the authoritative `MutationAdopted` journal
event. Only sequences that contain a lineage-owned tool are retained.

The packet may carry:

- tool identifiers already present in the committed registry;
- their order in previously adopted proposals;
- the pre-migration event-derived continuation sequences;
- the remaining symbolic depth and node budget.

It may not carry:

- the post-migration target or its digest;
- the target-generating primitive selected after migration;
- a post-migration candidate identifier;
- a discovered post-migration successful program;
- evaluator-only truth tables beyond the substrate semantics discovered during migration.

## Post-migration use

After packet validation, the transfer-task generator applies the committed continuation
frontiers to the new migrated parent in seed-defined order. It accepts the first frontier
that produces a strictly larger target, is unreachable by the birth registry under the
same depth, and yields a sound incapacity certificate.

The complete arm evaluates the transported continuation frontiers before generic symbolic
enumeration. The learning-state ablation receives the identical body, registry, target,
observations, depth and node budget but must rediscover the sequence through generic search.

This is a bounded continuation-transfer test. It asks whether a previously successful
transformation strategy remains useful on the changed post-migration body. It does not claim
arbitrary task generalisation.

## New consumed development identity

The replacement mechanism uses development seed `400041` and learning-state schema
`m040-learning-state/2`. Seed `400040` remains consumed by the failed ordering mechanism.

The primary memory verdict remains unchanged:

- both complete and memory-ablated arms must have the same exact-quality opportunity and
  equal budgets;
- the complete arm must use strictly fewer `symbolic_search_nodes`;
- the complete arm's accepted sequence must be one of the transported continuation
  frontiers;
- removing the lineage-owned tool must prevent exact solution under the same depth and node
  budget.
