# M040 development result 007 — positive lineage-anchor post-migration plasticity

**Status: consumed positive development result. Not canonical.**

Evaluated head before the result commit: `021d7d73d3a27d2549f45f6a6273cfa30e981647`  
Measured mechanism commit: `243080c73d13bbe5f86a366d7cb2bab9a68df2e2`  
Development seed: `400047`  
Workflow run: `30922038874`  
Exact artefact: `results/artifacts/M040_DEVELOPMENT_007.json`  
Artefact SHA-256: `8ecd4e6e08a6c2c9939fa81fc03366d7f92277159fceb9d21fe7cc48f4585197`  
Artefact size: `2,094,120` bytes  
Compact summary: `results/artifacts/M040_DEVELOPMENT_007_SUMMARY.json`

## Verdicts

| Development verdict | Result |
|---|---|
| trans-substrate continuity | **supported** |
| post-migration plasticity | **supported** |
| seed-only replay | **supported** |
| exact rollback | **supported** |
| pre-migration lineage tool used after migration | **yes** |

This is the first development result that actually evaluated the committed `lineage_anchor`
task family. Before the engine started, both the private and public task-family defaults were
verified as `lineage_anchor` by signature introspection.

## Continuous history

A fresh three-cycle M039-style lineage was regenerated from the M040 seed. Its complete search
histories were independently reproduced before migration:

| Cycle | Symbolic nodes | Completed candidates | Evidence rejections | Transcript entries |
|---:|---:|---:|---:|---:|
| 1 | 3,562 | 3,284 | 3,283 | 6,847 |
| 2 | 321 | 303 | 302 | 625 |
| 3 | 643 | 596 | 595 | 1,240 |

The final pre-migration source body had digest:

`8e74e8f116a2ecf09f7ffcb3ab5ad1ea562c7118e482d23b304f73d585bea2ad`

The lineage identities before migration were:

- manifest: `ec7539d9f05ea550abb5739280d643209c1b0d8177e6548750c1f95dfc5735e0`;
- journal head: `f4ac53e961cb81fa418e5b5513f4cf73ce45553576237b76bc5fa9785aafcbf4`;
- journal-record digest: `215c26080d2921a45fd9ac11bc087230413899e7850213252aad7af359b1f503`.

## Opaque migration

The initially unknown machine was discovered and the final lineage body migrated exactly:

- machine family: `0`;
- substrate probes: `84`;
- migration candidate evaluations: `309`;
- native components: `70`;
- serialised native body: `14,046` bytes;
- migrated native SHA-256:
  `71ac86afa35a8ddd56ea25fc764778a0b62846b339c5c853dcdcde718b330282`.

The packet carrying source representation, exact native body, discovered substrate, registry
and learning state had SHA-256:

`aa1a787969d299a0120b20ff4b6148d3bde351202384c6526bf8f616cccfffc4`

The packet was externally anchored and rehydrated before the post-migration task was derived.

## Hidden lineage-anchor task

Task seed: `15864591337369544597`  
Task digest: `dabfc7dfe5965123189cd585e11189382f119455b339d130aebf196fd1a5873b`  
Task family: `lineage_anchor`  
Migrated parent: eight states  
New target: **nine minimal states**

The accepted four-symbol tool program began with a derived lineage anchor and added bounded
protocol-supplied adaptation. Its six primitive structural operations were:

```text
redirect(initial, 0, deepest_accepting)
flip(initial)
grow(deepest_accepting, 0)
flip(deepest_accepting)
grow(initial, 1)
redirect(initial, 1, deepest_rejecting)
```

The complete accepted body had digest:

`8666169adf265564e66c901cf1b157e766f9b0b582ca21d9464c91dbcd322419`

## Equal-budget controls

Every search arm received depth 4, 127 oracle observations and the same 4,096-node budget.
A counter value of 4,097 is the deterministic first over-budget expansion.

| Arm | Exact | Best quality | Symbolic nodes | Audit entries |
|---|---:|---:|---:|---:|
| complete migrated lineage | **yes** | **127 / 127** | **248** | 305 |
| learning-state ablation | no | 123 / 127 | 4,097 | 8,026 |
| fresh on B | no | 123 / 127 | 4,097 | 8,027 |
| learned-tool ablation | no | 123 / 127 | 4,097 | 8,027 |
| unchanged founder migrated | no | 102 / 127 | 4,097 | 7,878 |
| output-only | no rewrite | 91 / 127 | 0 | 1 |

The full lineage therefore required about **16.5 times fewer symbolic nodes** than the equal
budget limit reached by the ablated and fresh arms. Both transported components were
load-bearing on this development seed:

- removing the lineage-owned tool prevented exact solution;
- retaining the tool but removing the continuation frontier also prevented exact solution.

All six engine transcripts were independently re-enumerated. Their transcript digests are
recorded in the compact summary and the full artefact.

## Native rewrite and rollback

The new nine-state source body was synthesised exactly on the discovered substrate:

- native candidate evaluations: `286`;
- native components: `85`;
- serialised native body: `31,722` bytes;
- accepted native SHA-256:
  `6c14dffac1ed823a4fc5b771eb7f69d9a9048d4c775cf58427c5cf06c1f89203`.

A fixed bad provisional source/native pair was then produced, rejected and rolled back. The
accepted source digest and exact native JSON were restored.

The unchanged-founder control was separately synthesised on the same opaque substrate, rather
than treated as a source-only fiction:

- `443` candidate evaluations;
- `58` native components;
- `33,874` serialised bytes;
- exact native SHA-256:
  `947b0b648e3031cb6e2017d20088d86da3c7152bb9bed53cddf797d285d74175`.

## Replay identities

A second seed-only execution reproduced the complete lineage, migration, packet, hidden task,
all controls, audits, native bodies, rollback and M040 journal.

- result digest: `0b1b82a742e341fdc304fe2ea4dbeb53000ff129bce32d0571ec4bf6e9373e2d`;
- M040 journal head:
  `ede875043da116aaef06e76545eed80c54a609f22a2ba8d196f2d8b24425006c`;
- 20 persisted M040 journal records;
- journal-record digest:
  `f38f9a358e7733e22d4bdeabc3fa2371332f353b28187dd42827b4f60a6a066f`.

## Interpretation and limits

This result is materially stronger than output preservation across a substrate boundary. A
single lineage accumulated tools and continuation state before migration, migrated its
competence and rewrite state to an opaque representation, then used both transported elements
to complete a new exact rewrite and native synthesis after migration.

It remains a consumed development result in a finite deterministic DFA laboratory. The
4,096-node budget was chosen after the consumed 400044 calibration and must be described as
calibration-derived. This result does not establish arbitrary substrate migration, arbitrary
strategy invention, open-ended evolution, general intelligence or consciousness.

The mechanism must still pass mutation probes, the complete Python 3.11/3.13 suite and a
frozen first canonical run before M040 can support a canonical claim.
