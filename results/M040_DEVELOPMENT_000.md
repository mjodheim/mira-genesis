# M040 development result 000 — transported ordering did not help

**Status: consumed negative development result. Not canonical.**

Evaluated head: `a2d8948246a0ceeebe88496e860695760dbe16e1`  
Development seed: `400040`  
Protocol commitment: `m040-development-v1`  
Focused workflow run: `30916305338`

The first integrated M040 mechanism successfully completed the trans-substrate continuity
path but failed the pre-registered learning-state efficiency comparison.

## What worked

- a fresh deterministic M039-style cumulative lineage completed before migration;
- its final body migrated exactly to an opaque Boolean substrate;
- its source representation, tool registry and declared learning state round-tripped in the
  M040 packet;
- the post-migration task was revealed only after packet validation;
- the complete migrated lineage adopted an exact post-migration rewrite;
- fresh, unchanged-parent, output-only and learned-tool-ablated controls did not solve under
  the equal committed language and node budget;
- the forced post-migration rollback restored the accepted source/native pair exactly;
- seed-only replay reproduced the packet and journal bytes.

The engine therefore reported:

- `trans_substrate_continuity_supported = true`;
- `post_migration_plasticity_supported = false`;
- `replay_supported = true`.

## Failure

The transported memory contained only a preferred-tool ordering. It did not reduce search
cost:

| Arm | Symbolic search nodes |
|---|---:|
| complete migrated lineage | 875 |
| learning-state ablation | 873 |

The preference was two nodes worse. Seven focused tests passed and the test requiring a
strict memory advantage failed. No development artefact was uploaded because the workflow
correctly stopped at the failed permanent test.

## Interpretation

This is not evidence that transported memory is generally useless. It shows that a single
preferred-tool list was not a load-bearing memory mechanism in this transfer family. The
packet transported information, but the information did not encode a reusable continuation
policy.

Seed `400040` and this exact mechanism are consumed. They may not later be used to confirm a
replacement memory mechanism.

## Required repair before another development run

The next mechanism must carry a replayable continuation frontier derived from accepted
pre-migration proposals, not a cosmetic ranking. The post-migration task must still be
revealed only after packet validation, and the frontier may contain no target body, target
digest or accepted post-migration candidate.
