# M039 — consumed three-cycle development result

**Status: positive development result; consumed; not canonical.**

M039's committed development seed `390039` produced one continuous lineage:

```text
F0 (4 states) -> F1 (5) -> F2 (6) -> F3 (7)
```

Cycle 1 constructed one lineage-owned macro from its accepted three-symbol primitive trace.
Cycles 2 and 3 each used that exact earlier tool as block zero of the adopted proposal. Under
the same symbolic depth, ordering and node budget, primitive-only ablation solved neither
later target. Every cycle also survived the fixed failing `flip(initial)` provisional probe
and restored the exact accepted functional state.

This is development evidence only. The generated tasks and all observations of them are
consumed by implementation decisions and may never support the future canonical result.

## Final verified development identity

| Identity | Value |
|---|---|
| Pull request | `#54` |
| Development head | `8bcd8dccf1fd34934d452b518b2b979caa95029a` |
| Workflow run | `30906574031` |
| Artifact id | `8891290506` |
| Artifact archive digest | `sha256:15caaa27c00e48d55f990bbe718c9549797c8044b2692078d1993d9c680f9c09` |
| JSON bytes | `198024` |
| JSON SHA-256 | `935dbebc773394881e46405f3dcb923ee246c555b61ba2a41d6aa456e816fffa` |
| Manifest digest | `faa418a69ea5e8f00b78f2e8add82c8647e758fd4700cbf3d357e074c3328207` |
| Lineage journal head | `1c55ac1ce12f4e60f8ac183be68f5209f4bdd7a7d5dfc201822f384cbb8d70eb` |
| Journal-record digest | `00579f4202c7f4645d04ae495ba9a60723d5bce523746604cf26cbd5048ba0d9` |
| Persisted journal records | `38` |
| Journal-verified lineage tool | `5f312b64a9831b19839f94a7879ce3babe866184c6d5e7e0081d048b4a9bdb24` |

## Functional chain

| Cycle | Body | Target | Tool constructed | Earlier tool used | Rollback exact |
|---:|---:|---:|---:|---:|---:|
| 1 | 4 states | 5 states | yes | no | yes |
| 2 | 5 states | 6 states | no | yes, block 0 | yes |
| 3 | 6 states | 7 states | no | yes, block 0 | yes |

The same tool was present in two exact `ToolReused` journal events. Independent provenance
verification required exact agreement between the persisted `ToolConstructed` event, the
final registry entry, all committed inputs, both later reuse events and the ablation record.
The engine's own eligibility candidate was retained only as diagnostic data.

## Exhaustive search replay

The operational journal records evidence-admitted proposals. A separate deterministic audit
commits every symbolic expansion and every evidence-rejected completed body, so identical
final candidates or counters cannot conceal a different search history.

| Cycle | Symbolic nodes | Completed bodies | Evidence rejected | Evidence admitted | Transcript entries | Transcript digest |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 4308 | 3717 | 3716 | 1 | 8026 | `c84f7969419d01131a003caa45045748c65a509f77eea61681283077c8c02d67` |
| 2 | 2073 | 2004 | 2003 | 1 | 4078 | `a9d5ed6af050a7f458dfa08ad594c1315ccfa6b5d0a90217475a925331128b05` |
| 3 | 2075 | 1993 | 1992 | 1 | 4069 | `aeb248a5305f183a05908eff1b7a7f3e524b47b730a43f2cddc77ff1c8bfe6b8` |

All three mappings and digests were regenerated independently from the replayed tasks,
registry and seed and matched exactly.

## Corrections learned from the consumed seed

The development sequence exposed three mechanism defects before freeze:

1. a cycle event relabelled `cycle = 0` was caught only by the following hash link; the
   verifier now rejects it semantically at its own record;
2. the first eligibility check trusted a construction identifier repeated from the tool's
   own provenance; eligibility is now recomputed from authoritative journal bytes;
3. evidence-rejected search bodies were counted but not individually committed; an
   independent exhaustive transcript now binds their identities, order and rejection reason.

Earlier artifacts from runs `30905839481` and `30906170734` remain consumed diagnostic
records. They are not evidence for Gate 2 or Gate 9 and are superseded for development
review by the artifact above.

## Development verdict

Within this consumed deterministic DFA task chain:

- three cumulative accepted cycles: **supported**;
- exact preservation across failed provisional changes: **supported**;
- earlier lineage-owned tool reused in later adopted traces: **supported**;
- equal-budget tool necessity by ablation: **supported**;
- journal-verified provenance eligibility: **supported**;
- seed-to-head journal replay: **supported**;
- exhaustive rejected-search replay: **supported**.

No Gate 2 or Gate 9 result is claimed yet. Those labels require a separately frozen protocol,
an unrevealed canonical task derived after the immutable arming commit, one preserved first
run, and no tuning against that task.