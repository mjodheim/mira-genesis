# M040 status

## Current phase

Repaired development mechanism, awaiting its first complete consumed run.

No sealed block, canonical seed or canonical M040 result exists.

## Consumed development history

- seed `400040`: continuity positive, memory ordering negative (`875` versus `873`
  symbolic nodes); retained in `results/M040_DEVELOPMENT_000.md`;
- seed `400041`: stopped during pre-migration tool construction because repeated program
  invocation and unique dependency identity were conflated; retained in
  `results/M040_DEVELOPMENT_001.md`.

Neither seed may confirm the repaired mechanism.

## Repaired mechanism

Development seed: `400042`.

The executable transformation program may repeat a tool invocation. Provenance
`input_tool_ids` records the unique dependency set in first-use order.

Learning-state schema `m040-learning-state/2` transports continuation programs extracted
from authoritative pre-migration `MutationAdopted` journal events. It carries no
post-migration target, target digest or candidate.

After packet validation, the task generator applies those continuation programs to the new
migrated parent. The complete arm evaluates the transported frontier first; the memory
ablation rediscovers through generic enumeration under the same depth and node budget.

The packet is rehydrated only against an externally committed SHA-256 digest.

## Required development verdict

A development result is positive only if:

- the three-cycle pre-migration lineage succeeds;
- migration and packet rehydration are exact;
- the post-migration task is revealed after validation;
- the complete arm adopts an exact rewrite using a pre-migration lineage tool;
- fresh, unchanged-parent, output-only and learned-tool-ablated controls fail under equal
  budgets;
- the complete arm uses fewer symbolic nodes than the learning-state ablation;
- native re-synthesis and rollback are exact;
- seed-only replay reproduces the packet and journal bytes.
