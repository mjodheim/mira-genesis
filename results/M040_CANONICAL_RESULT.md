# M040 canonical result — positive cumulative post-migration plasticity

**Scientific status: positive on the frozen bounded binary-DFA scope.**

M040 joins a fresh three-cycle cumulative lineage, lineage-owned tool reuse, exact
opaque-substrate migration and a new exact self-rewrite after migration in one replayable
lineage.

## Frozen identities

| Identity | Value |
|---|---|
| Frozen protocol SHA-256 | `4816bc3c32e4fc04df5de4fad784a8935f0b8757c544dbc3862a1d2cb7b59d30` |
| Frozen parent | `bc6e73c591cc9e996d5cb22ded71384b57d0c8cc` |
| Marker-only arming head | `5a5c2370231806b3295e0bce3f8aa449b2a465b3` |
| First canonical workflow run | `30930249547` |
| Preservation reproduction run | `30930586262` |
| Preserved workflow artifact | `8900997802` |
| Sealed task seed | `18441616668168956400` |
| Sealed-spec digest | `9457c6b680a306076edbc7ac1b95abc23ed9b910a5049e14aa0a3ce931fc0440` |
| Canonical JSON SHA-256 | `d7415c61e5dda1017d0e5484d5a54dd7550c87dcafdfae0e26f6eb2efa3daf3e` |
| Canonical JSON bytes | `2,107,888` |
| Canonical JSON Git blob | `656214639e45b951d32cad33e9017b539b51e36f` |
| Packet SHA-256 | `0e70fc9b0b7c2cf23441dd88ac57110d457c3c10897b1ab854af0351149b938d` |
| M040 journal head | `5c5e0f2a1f0eb70b567426e4e3e1e0fe8c5d6571aed8ca3d82e7efe6f5ffa450` |
| M040 journal records | `20` |

The exact result is committed as
`results/artifacts/M040_CANONICAL_RESULT.json`.

## Canonical verdicts

| Verdict | Result |
|---|---|
| Trans-substrate continuity | **supported** |
| Post-migration plasticity | **supported** |
| Seed-only replay | **supported** |
| Exact post-migration native synthesis | **supported** |
| Exact rollback | **supported** |
| Pre-migration lineage-owned tool used after migration | **yes** |
| Combined frozen claim | **supported** |
| Scientific outcome | **positive** |

## Continuous lineage

The canonical lineage:

1. completed three exact pre-migration improvement cycles;
2. retained its exact source body, causal journal, cumulative registry and continuation state;
3. discovered an initially opaque Boolean substrate through 84 public probes;
4. migrated its seven-state pre-migration body exactly;
5. committed and rehydrated the source representation, native body, discovered substrate,
   tool registry and learning state in one externally anchored packet;
6. derived a hidden lineage-anchor task only after packet validation;
7. proved that the seven-state parent was structurally insufficient for the eight-state
   target;
8. reused a transformation anchor owned by the pre-migration lineage and added bounded
   primitive adaptation;
9. adopted the exact eight-state source rewrite;
10. synthesised that rewrite exactly on the opaque substrate;
11. rejected one fixed bad provisional source/native pair and restored the accepted pair;
12. independently reproduced all pre- and post-migration searches, controls, packet bytes,
    journal bytes and decisions from the sealed seed.

## Opaque migration

The pre-migration source body digest was:

`72da2633d9bdbcf59017810b2b4388e6422f6209edefb2bb35c7f598eb76c082`

Migration results:

- machine family: `1`;
- public probe calls: `84`;
- migration candidate evaluations: `349`;
- native components: `67`;
- serialised native body: `8,150` bytes;
- migrated native SHA-256:
  `ea2dc857638cea8a9bc0bc0b3b342423d584deca5ee4ea8a1eb8f327bf371d12`.

## Hidden post-migration task

| Field | Value |
|---|---|
| Task family | `lineage_anchor` |
| Derived task seed | `402751298619840230` |
| Task digest | `de446c099ed8fc6244ed9db139a0840c2b1e79d2544684e1b249b52ec3b20da4` |
| Parent states | `7` |
| Certified lower bound | `8` |
| Target states | `8` |
| Target and accepted digest | `676a72b5503014fef63e2a697f8b1cad70f3fdfa51cf912456785d45aa51ed9b` |

The accepted primitive expansion was:

```text
flip(deepest_rejecting)
flip(initial)
grow(deepest_accepting, 0)
flip(deepest_accepting)
redirect(deepest_accepting, 0, deepest_accepting)
redirect(deepest_accepting, 0, initial)
```

The accepted tool sequence matched the hidden generating sequence exactly and contained a
lineage-owned tool constructed before migration.

## Equal-budget controls

Every arm received 127 observations, symbolic depth four and the same 4,096-node budget.
A counter of 4,097 is the deterministic first over-budget expansion.

| Arm | Exact | Best quality | Symbolic nodes | Outcome |
|---|---:|---:|---:|---|
| Complete migrated lineage | **yes** | **127 / 127** | **99** | transported continuation adopted |
| Learning-state ablation | no | 124 / 127 | 4,097 | budget exhausted |
| Fresh on B | no | 120 / 127 | 4,097 | budget exhausted |
| Learned-tool ablation | no | 120 / 127 | 4,097 | budget exhausted |
| Unchanged parent migrated | no | 101 / 127 | 4,097 | budget exhausted |
| Output only | no rewrite | 104 / 127 | 0 | no portable rewrite state |

The complete lineage used approximately **41.4 times fewer symbolic nodes** than the first
over-budget count reached by every search-capable control.

Both transported components were load-bearing on the sealed task:

- removing the lineage-owned tool prevented exact solution;
- retaining the tool but removing the continuation state also prevented exact solution.

## Native rewrite and rollback

The accepted eight-state source body was synthesised exactly on substrate B:

- candidate evaluations: `433`;
- native components: `82`;
- serialised native body: `8,072` bytes;
- accepted native SHA-256:
  `ec80f7483eea289a6fc17f49ed73b62a83c1f0994ec396b3df77ff56604eab4c`.

The fixed provisional failure was rejected, and the exact accepted source digest and native
body were restored.

## Search replay

All three pre-migration search histories were independently reconstructed:

| Cycle | Symbolic nodes | Completed bodies | Evidence rejected |
|---:|---:|---:|---:|
| 1 | 3,738 | 3,629 | 3,628 |
| 2 | 183 | 179 | 178 |
| 3 | 183 | 180 | 179 |

All six post-migration arm transcripts were independently re-enumerated and matched their
committed summaries and transcript digests. The complete twenty-record M040 causal hash chain,
packet, task, certificate, migration, native controls, adoption and rollback cross-references
were also recalculated from the preserved artefact.

## Preservation incident

The first immutable execution, workflow run `30930249547`, completed the canonical engine and
independent result verification. It then failed in the envelope's final `json.dumps` call
because raw causal-journal records were Python `bytes` and had not been converted to the
hexadecimal representation already used by the development artefacts.

No threshold, budget, seed, generator, engine, protocol, control or scientific decision was
changed. A preservation-only repair added that established byte encoding. Workflow run
`30930586262` then reproduced the exact original arming-head seed, identified itself as a
reproduction of run `30930249547`, independently verified the positive result again and
preserved the artefact.

The incident is therefore an artefact-serialization failure after scientific verification,
not a replacement scientific run. Both workflow identities remain part of the record.

## Scope and non-claims

This supports cumulative post-migration plasticity in the frozen deterministic binary-DFA
laboratory. It establishes that the transported history was functionally useful for a new
exact rewrite after opaque-substrate migration under the committed controls and budgets.

It does not establish arbitrary substrate migration, unrestricted code rewriting,
open-ended evolution, general intelligence, consciousness or permission to modify external
systems. The repository's explicit human-controlled engineering release boundary remains in
force.
