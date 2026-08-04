# M040 development result 004 — transfer advantage without strict control separation

**Status: consumed negative plasticity result. Not canonical.**

Evaluated patch head: `8d0f0c7b82b5c25ea639fcb5fe922167c3780355`  
Development seed: `400044`  
Task family: `prefix_plus_primitive`  
Workflow run: `30919751716`

The amended mechanism completed its pre-migration cumulative lineage, opaque migration,
packet rehydration, post-migration task generation and exact rewrite. The independent search
auditor agreed with the engine after its missing protocol-origin import was corrected.

The complete migrated lineage solved the task and replay succeeded. However, the fresh-on-B
control also found an exact candidate under the equal 20,000-node budget:

| Arm | Exact | Symbolic search nodes |
|---|---:|---:|
| complete migrated lineage | yes | less than fresh control |
| fresh on B | **yes** | **7,700** |

The pre-registered plasticity rule required fresh-on-B to have lower exact quality, so
`post_migration_plasticity_supported` was false even though the transported prefix provided a
large search advantage.

The focused suite reported one scientific assertion failure and fourteen passing tests. The
failure was exactly the fresh-control separation criterion; it was not a migration, packet,
rollback or replay failure.

Seed `400044` is consumed for the 20,000-node prefix-adaptation mechanism. It may not confirm
a later resource threshold.

## Interpretation

The result shows that the learned continuation is useful but not uniquely expressive at
this depth. A fresh organism can rediscover the same transformation through a much larger
search. The meaningful remaining question is therefore resource-bounded transfer:

> under an equal budget committed before a new seed, does the transported lineage solve
> while the fresh organism cannot complete its rediscovery?

Any lower budget must be declared as calibration-derived from this consumed result and tested
on a new seed. The 400044 result itself cannot support that claim.
