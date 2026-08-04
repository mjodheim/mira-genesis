# M040 development result 002 — positive bounded post-migration plasticity

**Status: consumed positive development result. Not canonical.**

Evaluated head: `35884c3d957f5faa12dde14a94a8e7db196e3717`  
Development seed: `400042`  
Workflow run: `30917494410`  
Workflow artefact: `8895681588`  
Exact JSON SHA-256: `7e44a4f1d63347c8cd2add65b7456b131b781c495ba495be8b25b461069a07d2`  
Exact JSON size: `50,946` bytes

The byte-exact result is preserved as
`results/artifacts/M040_DEVELOPMENT_002.json`.

## Verdicts

| Development verdict | Result |
|---|---|
| trans-substrate continuity | **supported** |
| post-migration plasticity | **supported** |
| seed-only replay | **supported** |
| rollback restoration | **exact** |

## Continuous lineage

A fresh M039-style lineage completed three accepted pre-migration cycles. Its final source
body had digest:

`2685468cc63dd58fbae74dea4a4f17f87ee45ada13caa3b6e0ccf497cac102a2`

That body migrated exactly to an initially opaque Boolean machine after 84 probes and 475
migration candidate evaluations. The native parent used 78 unique components and serialised
to 8,723 bytes.

The packet then carried:

- the exact portable source DFA;
- the exact opaque native body;
- the discovered stable substrate semantics;
- the complete M039 tool registry;
- causal tool-use identifiers;
- two continuation programs extracted from authoritative pre-migration adoption events.

The post-migration task was generated only after packet digest verification and canonical
rehydration.

## New post-migration task

The target had eight minimal states. The accepted transported continuation used two tool
symbols and expanded to four primitive structural operations:

```text
flip(deepest_rejecting)
flip(initial)
grow(max_indegree_rejecting, 0)
flip(deepest_rejecting)
```

The first tool in the accepted sequence was lineage-owned before migration.

## Controls

All search arms received the same 127 oracle observations, symbolic depth and node budget.

| Arm | Exact | Best quality | Symbolic nodes |
|---|---:|---:|---:|
| complete migrated lineage | yes | 127 / 127 | **2** |
| learning-state ablation | yes | 127 / 127 | 183 |
| fresh on B | no | 125 / 127 | 2,024 |
| learned-tool ablation | no | 125 / 127 | 2,024 |
| unchanged founder migrated | no | 111 / 127 | 2,024 |
| output-only | no | reported as 0 / 127 | 0 |

The continuation frontier reduced symbolic search from 183 to 2 nodes. Removing the
lineage-owned tool prevented exact solution under the same language depth and node budget.

## Native post-migration rewrite

The accepted eight-state source body was synthesised exactly into a new native opaque body:

- 699 candidate evaluations;
- 112 unique native components;
- 25,554 serialised bytes.

A fixed bad provisional rewrite was then synthesised, rejected and rolled back. Both the
accepted source digest and accepted native JSON were restored exactly.

## Replay

A second seed-only execution reproduced:

- the pre-migration lineage identities;
- opaque machine and migration result;
- packet bytes and packet digest;
- post-migration task;
- all six control summaries;
- accepted source/native pair;
- rollback result;
- all 18 M040 journal records and the journal head
  `fb79dd04f703e7218637e6e0c48163d091c9474a2ddfd55dd483aec73495e382`.

## Limitations found after the run

This positive result is not ready for canonical freeze.

1. The output-only control received the correct incapacity to rewrite, but its reported
   behavioural quality was zero instead of the real migrated-parent quality.
2. The unchanged-founder control searched at source level but did not yet commit a separately
   synthesised native founder body on B.
3. The packet used the pre-migration sub-protocol commitment as its top-level commitment
   instead of separating the M040 packet commitment from the embedded source-lineage
   commitment.
4. Search replay compared packet and journal bytes plus summaries, but did not independently
   commit every rejected M040 post-migration search path.

Those defects do not reverse the development result. They must be corrected and measured on
a new consumed seed before any canonical protocol is frozen.
